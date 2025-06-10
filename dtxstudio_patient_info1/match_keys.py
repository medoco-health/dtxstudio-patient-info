"""
File: match_keys.py
Author: amagni@medoco.health
Date: 2025-06-10
"""

from dtxstudio_patient_info1.utils import normalize_string, normalize_date

def create_match_key(family_name: str, given_name: str, sex: str, dob: str) -> str:
    """Create a normalized key for matching patients."""
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}|{normalize_string(sex)}|{normalize_date(dob)}"


def create_loose_match_key(family_name: str, given_name: str, dob: str) -> str:
    """Create a normalized key for loose matching patients (without gender)."""
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}|{normalize_date(dob)}"


def create_name_only_match_key(family_name: str, given_name: str) -> str:
    """Create a normalized key for name-only matching (for fuzzy date matching)."""
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}"


def create_flipped_match_key(family_name: str, given_name: str, sex: str, dob: str) -> str:
    """Create a normalized key for matching patients with flipped names."""
    return f"{normalize_string(given_name)}|{normalize_string(family_name)}|{normalize_string(sex)}|{normalize_date(dob)}"


def create_flipped_loose_match_key(family_name: str, given_name: str, dob: str) -> str:
    """Create a normalized key for loose matching patients with flipped names (without gender)."""
    return f"{normalize_string(given_name)}|{normalize_string(family_name)}|{normalize_date(dob)}"


def create_partial_match_key(family_name: str, given_name: str, sex: str, dob: str) -> str:
    """Create a normalized key for partial name matching (PMS names without suffixes)."""
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}|{normalize_string(sex)}|{normalize_date(dob)}"


def create_partial_loose_match_key(family_name: str, given_name: str, dob: str) -> str:
    """Create a normalized key for partial loose matching (without gender)."""
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}|{normalize_date(dob)}"


