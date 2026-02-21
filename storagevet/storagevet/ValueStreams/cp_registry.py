"""
cp_registry.py

Coincident Peak date registry for PJM territory utilities.
Extension of DER-VET by Brightfield Inc.
"""
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict, Set, Tuple


@dataclass(frozen=True)
class CP:
    date: date
    he: int  # Hour Ending (1-24)


class UtilityEnum(Enum):
    PSEG = "pseg"
    JCPL = "jcpl"


CP_REGISTRY: Dict[int, Dict[str, object]] = {
    2024: {
        "pjm": {
            CP(date(2024, 7, 16), 18),
            CP(date(2024, 7, 15), 18),
            CP(date(2024, 6, 21), 18),
            CP(date(2024, 8, 1), 18),
            CP(date(2024, 8, 28), 18),
        },
        "utilities": {
            UtilityEnum.PSEG: {
                CP(date(2024, 7, 16), 18),
            },
            UtilityEnum.JCPL: {
                CP(date(2024, 7, 16), 18),
            },
        },
        "jcpl_5cp": {
            CP(date(2024, 7, 9), 18),
            CP(date(2024, 7, 10), 18),
            CP(date(2024, 7, 15), 19),
            CP(date(2024, 7, 16), 18),
            CP(date(2024, 8, 1), 19),
        },
    },
    2025: {
        "pjm": {
            CP(date(2025, 6, 23), 18),
            CP(date(2025, 6, 24), 18),
            CP(date(2025, 6, 25), 15),
            CP(date(2025, 7, 28), 18),
            CP(date(2025, 7, 29), 18),
        },
        "utilities": {
            UtilityEnum.PSEG: {
                CP(date(2025, 6, 24), 19),
            },
            UtilityEnum.JCPL: {
                CP(date(2025, 6, 24), 18),
            },
        },
    },
}


def get_cps(year: int, utility: UtilityEnum) -> Tuple[Set[CP], Set[CP]]:
    """Returns (pjm_cps, utility_cps) for the given year and utility."""
    if year not in CP_REGISTRY:
        raise ValueError(f"No CP data for year {year}")
    year_data = CP_REGISTRY[year]
    if utility not in year_data["utilities"]:
        raise ValueError(f"No CP data for {utility.name} in {year}")
    return (year_data["pjm"], year_data["utilities"][utility])


def get_all_cps(year: int, utility: UtilityEnum) -> Set[CP]:
    """Returns the union of PJM CPs and utility-specific CPs."""
    pjm_cps, utility_cps = get_cps(year, utility)
    return pjm_cps.union(utility_cps)


def parse_cp_dates_string(dates_str):
    """Parse a comma-separated string of 'YYYY-MM-DD:HE' into a list of (date, he) tuples.

    Args:
        dates_str (str): e.g. '2025-06-23:18,2025-06-24:18,2025-06-25:15'

    Returns:
        list of (datetime.date, int) tuples
    """
    result = []
    for entry in dates_str.strip().split(','):
        entry = entry.strip()
        if not entry:
            continue
        date_part, he_part = entry.split(':')
        year, month, day = date_part.split('-')
        result.append((date(int(year), int(month), int(day)), int(he_part)))
    return result
