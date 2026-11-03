"""Metadata-only, training-only preview sample boundaries."""

import json

import pytest

from kelpseg.augmentation_debug.inputs import select_preview_windows


def _row(
    index,
    *,
    region="001",
    kelp=50000,
    background=None,
    nodata=0,
    width=512,
    split="train",
):
    return dict(
        source_key=f"source_{index}",
        source_id=f"original_{index}",
        row="0",
        col="0",
        region=region,
        split=split,
        payload=f"never-open-{index}.npz",
        kelp_pixels=str(kelp),
        background_pixels=str(
            512 * width - kelp - nodata if background is None else background
        ),
        nodata_pixels=str(nodata),
        height="512",
        width=str(width),
    )


@pytest.fixture
def metadata(tmp_path, monkeypatch):
    (tmp_path / "recipe.json").write_text(json.dumps({"chip_size": 512}))
    rows = [_row(i, region=f"{i % 12 + 1:03d}") for i in range(30)]
    rows[0].update(kelp_pixels="32")
    rows[1].update(kelp_pixels="1")
    rows[2].update(kelp_pixels="250000", background_pixels="10000")
    rows[3].update(nodata_pixels="1000")
    rows[4].update(width="257")
    rows.extend([_row(100, kelp=0, region="012"), _row(101, kelp=0)])
    # Held-out features would dominate if the selection accidentally used them.
    rows.extend(
        [_row(200, split="test", kelp=999999), _row(201, split="val", kelp=999998)]
    )

    def select(chips, assignments, experiment, variant):
        assert experiment == "baseline"
        assert variant == "augmented"
        return rows

    monkeypatch.setattr("kelpseg.augmentation_debug.inputs.select_windows", select)
    return tmp_path, rows


def test_replay_training_only_controls_and_feature_coverage(metadata):
    chips, rows = metadata
    actual = select_preview_windows(chips, "assignments.csv", "augmented", 14, 33)
    assert actual == select_preview_windows(
        chips, "assignments.csv", "augmented", 14, 33
    )
    assert len(actual) == 16
    assert len({row["source_key"] for row in actual}) == 16
    assert all(row["split"] == "train" for row in actual)
    assert len({row["region"] for row in actual[:14]}) == 12
    assert all(row["sample_reason"].startswith("visible_kelp_") for row in actual[:14])
    assert all(
        int(row["kelp_pixels"]) / (int(row["height"]) * int(row["width"])) >= 0.1
        for row in actual[:14]
    )
    assert all(
        row["source_key"] not in ("source_0", "source_1", "source_2") for row in actual
    )
    assert "visible_kelp_partial_edge" in {row["sample_reason"] for row in actual}
    assert "visible_kelp_native_nodata" in {row["sample_reason"] for row in actual}
    controls = actual[-2:]
    assert [row["preview_name"] for row in controls] == [
        "background_control_01",
        "background_control_02",
    ]
    assert all(
        row["background_control"] and row["kelp_pixels"] == "0" for row in controls
    )
    assert controls[0]["region"] == "012"
    assert all("preview_name" not in row for row in rows)


def test_source_diversity_preferred_without_losing_windows(metadata):
    chips, rows = metadata
    for row in rows[:10]:
        row["source_id"] = "shared-original"
    actual = select_preview_windows(chips, "assignments.csv", "augmented", 14, 33)
    assert len(actual) == 16
    assert len({row["source_id"] for row in actual}) > 8


def test_selection_does_not_depend_on_manifest_row_order(metadata):
    chips, rows = metadata
    expected = select_preview_windows(chips, "assignments.csv", "augmented", 14, 33)
    rows.reverse()
    assert (
        select_preview_windows(chips, "assignments.csv", "augmented", 14, 33)
        == expected
    )


@pytest.mark.parametrize(
    ("positive_samples", "seed", "message"),
    [
        (0, 33, "positive_samples"),
        (17, 33, "positive_samples"),
        (True, 33, "positive_samples"),
        (14, -1, "seed"),
        (14, True, "seed"),
    ],
)
def test_invalid_sampling_arguments_fail_before_manifest_reads(
    tmp_path, positive_samples, seed, message
):
    with pytest.raises(ValueError, match=message):
        select_preview_windows(
            tmp_path / "absent", "assignments.csv", "augmented", positive_samples, seed
        )


def test_insufficient_training_positives_and_controls(metadata):
    chips, rows = metadata
    for row in rows[:30]:
        row["split"] = "test"
    with pytest.raises(ValueError, match="positive training"):
        select_preview_windows(chips, "assignments.csv", "augmented", 14, 33)
    rows[0].update(split="train", kelp_pixels="50000", background_pixels="200000")
    rows[30]["split"] = "test"
    with pytest.raises(ValueError, match="two canonical background"):
        select_preview_windows(chips, "assignments.csv", "augmented", 1, 33)
