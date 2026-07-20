r"""Create NPZ segmentation chips from aligned georeferenced rasters.

Manifested runs use an explicit top-left pixel grid and write restartable
per-source fragments. Legacy train/val/test invocations retain the original
TorchGeo loading path for compatibility.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
import torch
from rasterio.windows import Window
from torch.utils.data import DataLoader
from torchgeo.datasets import RasterDataset
from torchgeo.datasets.utils import stack_samples
from torchgeo.samplers import GridGeoSampler
from tqdm.auto import tqdm

from src.prepare.nodata import declared_nodata_values, nodata_mask, nodata_value_text

IGNORE_INDEX = -100
BASE_MANIFEST_COLUMNS = [
    "chip_id",
    "chip_path",
    "source_tiff_id",
    "dataset",
    "region_id",
    "region_name",
    "acquisition_date",
    "source_width",
    "source_height",
    "source_crs",
    "source_nodata_value",
    "chip_index",
    "row_off",
    "col_off",
    "chip_width",
    "chip_height",
    "minx",
    "miny",
    "maxx",
    "maxy",
    "total_pixel_count",
]
TRAILING_MANIFEST_COLUMNS = [
    "ignore_pixel_count",
    "nodata_pixel_count",
    "nodata_pct",
    "image_dtype",
    "label_dtype",
]


def remap_label(labels, band_remapping, device=None):
    """Remap integer labels, assigning all unspecified values to ignore."""
    if device is None:
        device = labels.device
    lookup = torch.tensor(band_remapping, dtype=labels.dtype, device=device)
    mask = (labels >= 0) & (labels < len(lookup))
    result = torch.full_like(labels, IGNORE_INDEX)
    result[mask] = lookup[labels[mask]]
    return result


def remap_label_array(
    labels: np.ndarray, band_remapping: tuple[int, ...]
) -> np.ndarray:
    """Numpy equivalent of :func:`remap_label` for manifested raster windows."""
    result = np.full(labels.shape, IGNORE_INDEX, dtype=np.int64)
    mask = (labels >= 0) & (labels < len(band_remapping))
    lookup = np.asarray(band_remapping, dtype=np.int64)
    result[mask] = lookup[labels[mask]]
    return result


class RasterMosaicDataset(RasterDataset):
    is_image = True
    separate_files = False

    def __init__(self, *args, img_name, **kwargs):
        self.filename_glob = img_name
        super().__init__(*args, **kwargs)


class KomLabelsDataset(RasterDataset):
    is_image = False

    def __init__(self, *args, img_name, **kwargs):
        self.filename_glob = img_name
        super().__init__(*args, **kwargs)


def _validate_image_range(image: np.ndarray, dtype: np.dtype) -> None:
    dtype = np.dtype(dtype)
    if np.issubdtype(dtype, np.integer):
        limits = np.iinfo(dtype)
    elif np.issubdtype(dtype, np.floating):
        limits = np.finfo(dtype)
    else:
        raise TypeError(f"Unsupported image dtype: {dtype}")
    if image.max() > limits.max or image.min() < limits.min:
        raise ValueError(
            f"Image values must be in [{limits.min}, {limits.max}] for {dtype}"
        )


def create_chips(
    out_root,
    name,
    dset,
    img_path,
    chip_size=224,
    chip_stride=224,
    num_bands=3,
    band_remapping=(0, 1),
    dtype=np.uint8,
    num_workers=0,
):
    """Legacy chip writer retained for existing unmanifested invocations."""
    out_dir = out_root / name
    out_dir.mkdir(exist_ok=True, parents=True)
    sampler = GridGeoSampler(dset, size=chip_size, stride=chip_stride)
    dataloader_kwargs = {
        "sampler": sampler,
        "num_workers": num_workers,
        "collate_fn": stack_samples,
    }
    if num_workers > 0:
        dataloader_kwargs["prefetch_factor"] = 2
    dataloader = DataLoader(dset, **dataloader_kwargs)

    for i, batch in enumerate(tqdm(dataloader, desc=img_path.stem)):
        img = batch["image"]
        label = batch["mask"]
        height, width = img.shape[2:]
        if height < chip_size or width < chip_size:
            continue
        img_array = img[0, :num_bands].numpy()
        _validate_image_range(img_array, np.dtype(dtype))
        img_array = img_array.astype(dtype)
        label_array = remap_label(label, band_remapping).numpy().astype(np.int64)[0]
        if np.all(img_array == 0):
            continue
        is_nodata = np.all(img_array == 0, axis=0)
        label_array[is_nodata] = 0
        np.savez_compressed(
            out_dir / f"{img_path.stem}_{i}.npz",
            image=np.moveaxis(img_array, 0, -1),
            label=label_array,
        )


def load_dataset(data_dir, img_name):
    images = RasterMosaicDataset(paths=[str(data_dir / "images")], img_name=img_name)
    labels = KomLabelsDataset(paths=[str(data_dir / "labels")], img_name=img_name)
    return images & labels


def process_split(
    data_dir: Path,
    split: str,
    output_dir: Path,
    chip_size: int = 224,
    chip_stride: int = 224,
    num_bands: int = 3,
    band_remapping: tuple[int, ...] = (0, 1),
    dtype: np.dtype = np.uint8,
    num_workers: int = 0,
):
    """Run the legacy, unmanifested chip path."""
    split_dir = data_dir / split
    imgs = sorted(split_dir.glob("images/*.tif", case_sensitive=False))
    for img in tqdm(imgs, desc=f"{split.capitalize()} chips"):
        ds = load_dataset(split_dir, img_name=img.name)
        create_chips(
            out_root=output_dir,
            name=split,
            dset=ds,
            img_path=img,
            chip_size=chip_size,
            chip_stride=chip_stride,
            num_bands=num_bands,
            band_remapping=band_remapping,
            dtype=dtype,
            num_workers=num_workers,
        )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _write_csv_atomic(
    path: Path, rows: list[dict[str, Any]], fieldnames: list[str]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)


def manifest_columns(band_remapping: tuple[int, ...]) -> list[str]:
    classes = sorted(set(band_remapping) - {IGNORE_INDEX})
    return [
        *BASE_MANIFEST_COLUMNS,
        *(f"class_{value}_pixel_count" for value in classes),
        *TRAILING_MANIFEST_COLUMNS,
    ]


def iter_windows(
    width: int, height: int, chip_size: int, chip_stride: int
) -> list[Window]:
    """Return top-left windows, spanning dimensions smaller than one chip."""
    if chip_size <= 0 or chip_stride <= 0:
        raise ValueError("Chip size and stride must both be positive")
    window_width = min(width, chip_size)
    window_height = min(height, chip_size)
    col_offsets = (
        [0] if width < chip_size else range(0, width - chip_size + 1, chip_stride)
    )
    row_offsets = (
        [0] if height < chip_size else range(0, height - chip_size + 1, chip_stride)
    )
    return [
        Window(col_off, row_off, window_width, window_height)
        for row_off in row_offsets
        for col_off in col_offsets
    ]


def _validate_npz(path: Path, row: dict[str, Any]) -> None:
    if not path.is_file():
        raise RuntimeError(f"Missing chip file for completed fragment: {path}")
    with np.load(path) as data:
        if set(data.files) != {"image", "label"}:
            raise RuntimeError(f"Unexpected NPZ keys in {path}: {data.files}")
        image, label = data["image"], data["label"]
    expected_shape = (int(row["chip_height"]), int(row["chip_width"]))
    if image.shape[:2] != expected_shape or label.shape != expected_shape:
        raise RuntimeError(f"Array shape does not match fragment for {path}")
    total = int(row["total_pixel_count"])
    count_columns = [key for key in row if key.startswith("class_")]
    stored_total = sum(int(row[key]) for key in count_columns) + int(
        row["ignore_pixel_count"]
    )
    if stored_total != total or label.size != total:
        raise RuntimeError(f"Pixel counts do not reconcile for {path}")
    if str(image.dtype) != row["image_dtype"] or str(label.dtype) != row["label_dtype"]:
        raise RuntimeError(f"Stored dtype does not match fragment for {path}")
    for key in count_columns:
        value = int(key.removeprefix("class_").removesuffix("_pixel_count"))
        if np.count_nonzero(label == value) != int(row[key]):
            raise RuntimeError(f"Stored class counts do not match fragment for {path}")
    if np.count_nonzero(label == IGNORE_INDEX) != int(row["ignore_pixel_count"]):
        raise RuntimeError(f"Stored ignore count does not match fragment for {path}")
    nodata_count = int(
        np.count_nonzero(
            nodata_mask(
                image,
                [np.asarray(row["source_nodata_value"], dtype=image.dtype).item()]
                * image.shape[-1],
                band_axis=-1,
            )
        )
    )
    if nodata_count != int(row["nodata_pixel_count"]):
        raise RuntimeError(f"Stored nodata count does not match fragment for {path}")
    expected_pct = 100.0 * nodata_count / total
    if not np.isclose(expected_pct, float(row["nodata_pct"])):
        raise RuntimeError(
            f"Stored nodata percentage does not match fragment for {path}"
        )


def _validate_fragment(
    fragment: Path, chip_root: Path, fieldnames: list[str]
) -> list[dict[str, str]]:
    with fragment.open(newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != fieldnames:
            raise RuntimeError(f"Fragment schema mismatch: {fragment}")
        rows = list(reader)
    if not rows:
        raise RuntimeError(f"Completed fragment is empty: {fragment}")
    for row in rows:
        _validate_npz(chip_root / row["chip_path"], row)
    return rows


def _source_paths(
    data_dir: Path, split: str, source_row: dict[str, str]
) -> tuple[Path, Path]:
    source_id = source_row["source_tiff_id"]
    images = list((data_dir / split / "images").glob(f"{source_id}.[tT][iI][fF]"))
    labels = list((data_dir / split / "labels").glob(f"{source_id}.[tT][iI][fF]"))
    if len(images) != 1 or len(labels) != 1:
        raise RuntimeError(
            f"Expected one image/label pair for {source_id}; "
            f"found {len(images)} image(s), {len(labels)} label(s)"
        )
    return images[0], labels[0]


def _validate_manifest_inventory(
    data_dir: Path, split: str, source_ids: list[str]
) -> None:
    image_ids = {
        path.stem
        for path in (data_dir / split / "images").glob("*.tif", case_sensitive=False)
    }
    label_ids = {
        path.stem
        for path in (data_dir / split / "labels").glob("*.tif", case_sensitive=False)
    }
    expected = set(source_ids)
    if image_ids != expected or label_ids != expected:
        missing_images = sorted(expected - image_ids)
        missing_labels = sorted(expected - label_ids)
        extra_images = sorted(image_ids - expected)
        extra_labels = sorted(label_ids - expected)
        raise RuntimeError(
            "Source manifest does not exactly match the raster inventory: "
            f"missing_images={missing_images[:5]}, missing_labels={missing_labels[:5]}, "
            f"extra_images={extra_images[:5]}, extra_labels={extra_labels[:5]}"
        )


def _chip_source(
    *,
    data_dir: Path,
    output_dir: Path,
    split: str,
    source_row: dict[str, str],
    fragment_path: Path,
    staging_dir: Path,
    chip_size: int,
    chip_stride: int,
    num_bands: int,
    band_remapping: tuple[int, ...],
    dtype: np.dtype,
    fieldnames: list[str],
) -> None:
    source_id = source_row["source_tiff_id"]
    image_path, label_path = _source_paths(data_dir, split, source_row)
    shutil.rmtree(staging_dir, ignore_errors=True)
    staging_dir.mkdir(parents=True)
    rows: list[dict[str, Any]] = []

    with rasterio.open(image_path) as image_ds, rasterio.open(label_path) as label_ds:
        if image_ds.width != label_ds.width or image_ds.height != label_ds.height:
            raise RuntimeError(f"Image/label dimensions differ for {source_id}")
        if image_ds.transform != label_ds.transform or image_ds.crs != label_ds.crs:
            raise RuntimeError(f"Image/label grids differ for {source_id}")
        if image_ds.crs is None:
            raise RuntimeError(f"Source raster has no CRS: {source_id}")
        if image_ds.count < num_bands:
            raise RuntimeError(
                f"{source_id} has {image_ds.count} bands, fewer than requested {num_bands}"
            )
        source_nodata = declared_nodata_values(
            image_ds, retained_bands=num_bands, missing_value=0
        )
        windows = iter_windows(image_ds.width, image_ds.height, chip_size, chip_stride)
        for chip_index, window in enumerate(windows):
            row_off, col_off = int(window.row_off), int(window.col_off)
            chip_width, chip_height = int(window.width), int(window.height)
            chip_id = f"{source_id}__r{row_off}_c{col_off}_h{chip_height}_w{chip_width}"
            chip_name = f"{chip_id}.npz"
            image = image_ds.read(indexes=range(1, num_bands + 1), window=window)
            raw_label = label_ds.read(1, window=window)
            _validate_image_range(image, dtype)
            image = image.astype(dtype)
            label = remap_label_array(raw_label, band_remapping)
            nodata = nodata_mask(image, source_nodata, band_axis=0)
            np.savez_compressed(
                staging_dir / chip_name,
                image=np.moveaxis(image, 0, -1),
                label=label,
            )
            minx, miny, maxx, maxy = rasterio.windows.bounds(window, image_ds.transform)
            total = int(label.size)
            row: dict[str, Any] = {
                "chip_id": chip_id,
                "chip_path": (Path(split) / chip_name).as_posix(),
                "source_tiff_id": source_id,
                "dataset": source_row["dataset"],
                "region_id": source_row["region_id"],
                "region_name": source_row["region_name"],
                "acquisition_date": source_row["acquisition_date"],
                "source_width": image_ds.width,
                "source_height": image_ds.height,
                "source_crs": image_ds.crs.to_string() if image_ds.crs else "",
                "source_nodata_value": nodata_value_text(source_nodata),
                "chip_index": chip_index,
                "row_off": row_off,
                "col_off": col_off,
                "chip_width": chip_width,
                "chip_height": chip_height,
                "minx": minx,
                "miny": miny,
                "maxx": maxx,
                "maxy": maxy,
                "total_pixel_count": total,
                "ignore_pixel_count": int(np.count_nonzero(label == IGNORE_INDEX)),
                "nodata_pixel_count": int(np.count_nonzero(nodata)),
                "nodata_pct": 100.0 * float(np.count_nonzero(nodata)) / total,
                "image_dtype": str(image.dtype),
                "label_dtype": str(label.dtype),
            }
            for value in sorted(set(band_remapping) - {IGNORE_INDEX}):
                row[f"class_{value}_pixel_count"] = int(
                    np.count_nonzero(label == value)
                )
            rows.append(row)

    chip_dir = output_dir / split
    chip_dir.mkdir(parents=True, exist_ok=True)
    for staged_chip in sorted(staging_dir.glob("*.npz")):
        os.replace(staged_chip, chip_dir / staged_chip.name)
    _write_csv_atomic(fragment_path, rows, fieldnames)
    shutil.rmtree(staging_dir)


def run_manifested_split(
    *,
    data_dir: Path,
    output_dir: Path,
    split: str,
    source_manifest: Path,
    manifest_output: Path,
    chip_size: int,
    chip_stride: int,
    num_bands: int,
    band_remapping: tuple[int, ...],
    dtype: np.dtype,
    resume: bool,
    num_workers: int = 0,
) -> None:
    """Create one manifested split and atomically consolidate its fragments."""
    source_rows = _read_csv(source_manifest)
    required = {
        "source_tiff_id",
        "dataset",
        "region_id",
        "region_name",
        "acquisition_date",
    }
    if not source_rows or not required.issubset(source_rows[0]):
        raise RuntimeError(f"Source manifest lacks required columns: {source_manifest}")
    source_ids = [row["source_tiff_id"] for row in source_rows]
    if len(source_ids) != len(set(source_ids)):
        raise RuntimeError("Source manifest contains duplicate source_tiff_id values")
    _validate_manifest_inventory(data_dir, split, source_ids)

    chip_dir = output_dir / split
    fragments_dir = output_dir / "manifest_parts" / split
    staging_root = output_dir / ".chip_staging" / split
    issues_dir = output_dir / ".chip_issues" / split
    if chip_dir.exists() and any(chip_dir.iterdir()) and not resume:
        raise RuntimeError(f"Target split is nonempty; use --resume: {chip_dir}")
    fieldnames = manifest_columns(band_remapping)
    fragments_dir.mkdir(parents=True, exist_ok=True)

    pending_rows: list[dict[str, str]] = []
    for source_row in sorted(source_rows, key=lambda row: row["source_tiff_id"]):
        source_id = source_row["source_tiff_id"]
        fragment = fragments_dir / f"{source_id}.csv"
        if fragment.exists():
            if not resume:
                raise RuntimeError(f"Completed fragment already exists: {fragment}")
            _validate_fragment(fragment, output_dir, fieldnames)
            continue
        if resume:
            for orphan in chip_dir.glob(f"{source_id}__*.npz"):
                orphan.unlink()
        pending_rows.append(source_row)

    def chip_one(source_row: dict[str, str]) -> None:
        source_id = source_row["source_tiff_id"]
        fragment = fragments_dir / f"{source_id}.csv"
        try:
            _chip_source(
                data_dir=data_dir,
                output_dir=output_dir,
                split=split,
                source_row=source_row,
                fragment_path=fragment,
                staging_dir=staging_root / source_id,
                chip_size=chip_size,
                chip_stride=chip_stride,
                num_bands=num_bands,
                band_remapping=band_remapping,
                dtype=dtype,
                fieldnames=fieldnames,
            )
        except Exception as error:
            issues_dir.mkdir(parents=True, exist_ok=True)
            issue_path = issues_dir / f"{source_id}.json"
            issue_path.write_text(
                json.dumps({"source_tiff_id": source_id, "error": str(error)}, indent=2)
                + "\n"
            )
            raise
        else:
            issue_path = issues_dir / f"{source_id}.json"
            issue_path.unlink(missing_ok=True)

    if num_workers < 0:
        raise ValueError("--num_workers cannot be negative")
    if num_workers == 0:
        for source_row in tqdm(pending_rows, desc=f"{split.capitalize()} sources"):
            chip_one(source_row)
    else:
        errors: list[Exception] = []
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(chip_one, source_row): source_row["source_tiff_id"]
                for source_row in pending_rows
            }
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc=f"{split.capitalize()} sources",
            ):
                try:
                    future.result()
                except Exception as error:
                    errors.append(error)
        if errors:
            raise RuntimeError(
                f"{len(errors)} source(s) failed; inspect {issues_dir}"
            ) from errors[0]

    all_rows: list[dict[str, str]] = []
    for source_id in sorted(source_ids):
        all_rows.extend(
            _validate_fragment(
                fragments_dir / f"{source_id}.csv", output_dir, fieldnames
            )
        )
    all_rows.sort(key=lambda row: (row["source_tiff_id"], int(row["chip_index"])))
    chip_ids = [row["chip_id"] for row in all_rows]
    if len(chip_ids) != len(set(chip_ids)):
        raise RuntimeError("Duplicate chip IDs found while consolidating fragments")
    _write_csv_atomic(manifest_output, all_rows, fieldnames)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--size", type=int, default=224)
    parser.add_argument("--num_bands", type=int, default=3)
    parser.add_argument("--stride", type=int, default=224)
    parser.add_argument("--dtype", type=np.dtype, default="uint8")
    parser.add_argument(
        "--num_workers",
        type=int,
        default=0,
        help="Concurrent source workers for manifested runs; 0 is sequential.",
    )
    parser.add_argument("--remap", "-r", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument(
        "--splits",
        nargs="+",
        choices=["all", "train", "val", "test"],
        default=["train", "val", "test"],
    )
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--manifest-output", type=Path)
    parser.add_argument("--resume", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    print(f"Creating dataset {args.output_dir.name}")
    print("Pixel values will be remapped:")
    for i, value in enumerate(args.remap):
        print(f"{i} -> {value}")
    print(f"All other values will be set to {IGNORE_INDEX}.")

    if args.source_manifest is None:
        if "all" in args.splits:
            raise SystemExit("--source-manifest is required with --splits all")
        if args.manifest_output is not None or args.resume:
            raise SystemExit("--manifest-output and --resume require --source-manifest")
        for split in args.splits:
            process_split(
                args.data_dir,
                split,
                args.output_dir,
                args.size,
                args.stride,
                args.num_bands,
                tuple(args.remap),
                args.dtype,
                args.num_workers,
            )
        return

    if len(args.splits) != 1:
        raise SystemExit("Manifested runs process exactly one split at a time")
    split = args.splits[0]
    manifest_output = args.manifest_output or args.output_dir / "chip_manifest.csv"
    run_manifested_split(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        split=split,
        source_manifest=args.source_manifest,
        manifest_output=manifest_output,
        chip_size=args.size,
        chip_stride=args.stride,
        num_bands=args.num_bands,
        band_remapping=tuple(args.remap),
        dtype=args.dtype,
        resume=args.resume,
        num_workers=args.num_workers,
    )


if __name__ == "__main__":
    main()
