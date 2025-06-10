"""
Key building utilities for patient matching strategies.

This module provides functions to create normalized keys for different matching strategies.
"""

from typing import Dict
from .normalizers import normalize_string, normalize_date


def create_exact_match_key(family_name: str, given_name: str, sex: str, dob: str) -> str:
    """Create a key for exact matching (all fields)."""
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}|{normalize_string(sex)}|{normalize_date(dob)}"


def create_loose_match_key(family_name: str, given_name: str, dob: str) -> str:
    """Create a key for loose matching (without gender)."""
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}|{normalize_date(dob)}"


def create_flipped_exact_key(family_name: str, given_name: str, sex: str, dob: str) -> str:
    """Create a key for flipped exact matching (swapped names, exact gender/DOB)."""
    return f"{normalize_string(given_name)}|{normalize_string(family_name)}|{normalize_string(sex)}|{normalize_date(dob)}"


def create_flipped_loose_key(family_name: str, given_name: str, dob: str) -> str:
    """Create a key for flipped loose matching (swapped names, without gender)."""
    return f"{normalize_string(given_name)}|{normalize_string(family_name)}|{normalize_date(dob)}"


def create_name_only_key(family_name: str, given_name: str) -> str:
    """Create a key for name-only matching."""
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}"


def create_flipped_name_only_key(family_name: str, given_name: str) -> str:
    """Create a key for flipped name-only matching."""
    return f"{normalize_string(given_name)}|{normalize_string(family_name)}"


def create_composite_keys(family_name: str, given_name: str, sex: str, dob: str) -> Dict[str, str]:
    """Create all possible matching keys for patient data."""
    keys = {
        'exact': create_exact_match_key(family_name, given_name, sex, dob),
        'loose': create_loose_match_key(family_name, given_name, dob),
        'flipped_exact': create_flipped_exact_key(family_name, given_name, sex, dob),
        'flipped_loose': create_flipped_loose_key(family_name, given_name, dob),
        'name_only': create_name_only_key(family_name, given_name),
        'flipped_name_only': create_flipped_name_only_key(family_name, given_name)
    }
    
    return keys