"""
File: match_keys.py
Author: amagni@medoco.health
Date: 2025-06-10
"""

from dtxstudio_patient_info.utils import normalize_string, normalize_date


def create_match_key_exact(family_name: str, given_name: str, sex: str, dob: str) -> str:
    """Create a normalized key for matching patients.

    Example matches:
    - "Smith, John M" + "John" + "M" + "1990-01-01" → "smith|john|m|1990-01-01"
    - "SMITH" + "JOHN" + "Male" + "01/01/1990" → "smith|john|m|1990-01-01"
    """
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}|{normalize_string(sex)}|{normalize_date(dob)}"


def create_match_key_no_gender(family_name: str, given_name: str, dob: str) -> str:
    """Create a normalized key for loose matching patients (without gender).

    Matches patients regardless of sex field differences:
    - "Smith" + "John" + "1990-01-01" → "smith|john|1990-01-01"
    - Could match both Male and Female patients with same name/DOB
    """
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}|{normalize_date(dob)}"


def create_match_key_name_only(family_name: str, given_name: str) -> str:
    """Create a normalized key for name-only matching (for fuzzy date matching).

    Used when dates might be slightly different but names match:
    - "Smith" + "John" → "smith|john"
    - Matches patients with same names but potentially different DOBs
    """
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}"


def create_match_key_no_suffix(family_name: str, given_name: str, sex: str, dob: str) -> str:
    """Create a normalized key for partial name matching (PMS names without suffixes).

    Matches patients when DTX has extra suffixes in name:
    - "Smith BIS" + "John Michael" → "smith|john|m|1990-01-01"
    - Matches PMS record with "Smith" + "John" (suffixes/middle names removed), but exact birtdate and sex
    """
    # Remove suffixes and middle names by taking only the first word of each name
    family_first_word = family_name.split()[0] if family_name.strip() else ""
    given_first_word = given_name.split()[0] if given_name.strip() else ""

    return f"{normalize_string(family_first_word)}|{normalize_string(given_first_word)}|{normalize_string(sex)}|{normalize_date(dob)}"
