"""Shared source-filename metadata parsing for PlanetScope 8-band rasters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

CA_REGION_NAMES = {
    "001": "baja_islaNavidad",
    "002": "baja_puntaEugenia",
    "003": "sanDiego",
    "004": "palosVerdes",
    "005": "channelIslands",
    "006": "channelIslands",
    "007": "refugioStateBeach",
    "008": "bigSur",
    "009": "monterey",
    "010": "northernCalifornia",
    "011": "calvertIsland",
}

DATE_RE = re.compile(r"^(?P<date>\d{8})_")
CA_RE = re.compile(r"^(?P<region>\d{3})_(?P<date>\d{8})_")


@dataclass(frozen=True)
class SourceMetadata:
    """Dataset identity parsed from a source TIFF stem."""

    region_id: str
    region_name: str
    acquisition_date: date


def parse_compact_date(value: str) -> date:
    """Parse a YYYYMMDD string, rejecting invalid calendar dates."""
    if len(value) != 8 or not value.isdigit():
        raise ValueError(f"Expected YYYYMMDD date, got {value!r}")
    return date.fromisoformat(f"{value[:4]}-{value[4:6]}-{value[6:8]}")


def parse_ca_stem(stem: str) -> SourceMetadata:
    """Parse a California source stem and enforce the current region range."""
    match = CA_RE.match(stem)
    if match is None or match["region"] not in CA_REGION_NAMES:
        raise ValueError(
            "Expected California stem beginning <region_001-011>_<YYYYMMDD>_"
        )
    return SourceMetadata(
        region_id=f"ca_{match['region']}",
        region_name=CA_REGION_NAMES[match["region"]],
        acquisition_date=parse_compact_date(match["date"]),
    )


def parse_bc_stem(stem: str) -> SourceMetadata:
    """Parse a BC source stem beginning with an acquisition date."""
    match = DATE_RE.match(stem)
    if match is None:
        raise ValueError("Expected BC stem beginning <YYYYMMDD>_")
    return SourceMetadata(
        region_id="bc",
        region_name="british_columbia",
        acquisition_date=parse_compact_date(match["date"]),
    )
