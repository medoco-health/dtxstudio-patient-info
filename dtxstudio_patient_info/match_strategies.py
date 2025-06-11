"""
File: match_strategies.py
Author: amagni@medoco.health
Date: 2025-06-10
"""

from typing import Dict, Union, List, Optional
import logging

from dtxstudio_patient_info.utils import (
    normalize_string,
    normalize_date,
    is_partial_name_match,
    is_fuzzy_date_match,
    is_partial_name_word_match
)

from dtxstudio_patient_info.match_keys import (
    create_match_key_exact,
    create_match_key_no_gender,
    create_match_key_name_only,
    create_match_key_no_suffix,
)


def _extract_candidate_data(candidate: Union[dict, List[dict]]) -> dict:
    """Extract first candidate if it's a list, or return the dict."""
    if isinstance(candidate, list):
        return candidate[0]
    return candidate


def try_exact_matches(dtx_record: dict, pms_lookup: Dict[str, Union[dict, List[dict]]]) -> Optional[tuple]:
    """Try exact and loose matching strategies.

    Returns: (pms_data, match_info) or None
    """
    family_name = dtx_record['family_name']
    given_name = dtx_record['given_name']
    sex = dtx_record['sex']
    dob = dtx_record['dob']

    # Exact match (including gender)
    match_key = create_match_key_exact(family_name, given_name, sex, dob)
    if match_key in pms_lookup:
        pms_data = _extract_candidate_data(pms_lookup[match_key])
        logging.debug(f"EXACT_MATCH: {given_name} {family_name}")
        return pms_data, {"type": "exact", "is_gender_mismatch": False, "is_name_flip": False}

    # Loose match (names and DOB match, but gender might differ)
    loose_match_key = create_match_key_no_gender(family_name, given_name, dob)
    if loose_match_key in pms_lookup:
        pms_data = _extract_candidate_data(pms_lookup[loose_match_key])
        is_gender_mismatch = (sex != pms_data['gender'])
        logging.debug(f"LOOSE_MATCH: {given_name} {family_name} (gender mismatch: {is_gender_mismatch})")
        return pms_data, {"type": "loose", "is_gender_mismatch": is_gender_mismatch, "is_name_flip": False}

    return None


def try_partial_matches(dtx_record: dict, pms_lookup: Dict[str, Union[dict, List[dict]]]) -> Optional[tuple]:
    """Try partial name matching strategies.

    Returns: (pms_data, match_info) or None
    """
    family_name = dtx_record['family_name']
    given_name = dtx_record['given_name']
    sex = dtx_record['sex']
    dob = dtx_record['dob']

    # Try no-suffix matching first (DTX has suffixes, PMS doesn't)
    no_suffix_key = create_match_key_no_suffix(
        family_name, given_name, sex, dob)
    if no_suffix_key in pms_lookup:
        pms_data = _extract_candidate_data(pms_lookup[no_suffix_key])
        logging.debug(f"NO_SUFFIX_MATCH: {given_name} {family_name}")
        return pms_data, {"type": "no_suffix_exact", "is_gender_mismatch": False, "is_partial_match": True}

    # Try partial name matching (PMS names are substrings of DTX names)
    for pms_candidate in pms_lookup.values():
        if isinstance(pms_candidate, dict):
            pms_family = pms_candidate.get('last_name', '')
            pms_given = pms_candidate.get('first_name', '')
            pms_sex = pms_candidate.get('gender', '')
            pms_dob = pms_candidate.get('dob', '')

            if (is_partial_name_match(pms_family, family_name) and
                is_partial_name_match(pms_given, given_name) and
                    normalize_date(pms_dob) == normalize_date(dob)):

                is_gender_mismatch = normalize_string(
                    pms_sex) != normalize_string(sex)
                match_type = "partial_loose" if is_gender_mismatch else "partial_exact"
                return pms_candidate, {"type": match_type, "is_gender_mismatch": is_gender_mismatch, "is_partial_match": True}

    # Try partial given name matching (any word overlap in given names)
    for pms_candidate in pms_lookup.values():
        if isinstance(pms_candidate, dict):
            pms_family = pms_candidate.get('last_name', '')
            pms_given = pms_candidate.get('first_name', '')
            pms_sex = pms_candidate.get('gender', '')
            pms_dob = pms_candidate.get('dob', '')

            if (normalize_string(pms_family) == normalize_string(family_name) and
                is_partial_name_word_match(given_name, pms_given) and
                    normalize_date(pms_dob) == normalize_date(dob)):

                is_gender_mismatch = normalize_string(
                    pms_sex) != normalize_string(sex)
                match_type = "partial_given_loose" if is_gender_mismatch else "partial_given_exact"
                return pms_candidate, {"type": match_type, "is_gender_mismatch": is_gender_mismatch, "is_partial_match": True}

    return None


def try_fuzzy_date_match(dtx_record: dict, pms_lookup: Dict[str, Union[dict, List[dict]]]) -> Optional[tuple]:
    """Try fuzzy date matching (names match, dates similar).

    Returns: (pms_data, match_info) or None
    """
    family_name = dtx_record['family_name']
    given_name = dtx_record['given_name']
    sex = dtx_record['sex']
    dob = dtx_record['dob']

    name_only_key = create_match_key_name_only(family_name, given_name)
    if name_only_key in pms_lookup:
        candidates = pms_lookup[name_only_key]
        if isinstance(candidates, dict):
            candidates = [candidates]
        elif not isinstance(candidates, list):
            return None

        # Check each candidate for fuzzy date match
        for candidate in candidates:
            if is_fuzzy_date_match(dob, candidate['dob']):
                is_gender_mismatch = (sex != candidate['gender'])
                logging.debug(f"FUZZY_DATE_MATCH: {given_name} {family_name} (DTX date: {dob}, PMS date: {candidate['dob']})")
                return candidate, {"type": "fuzzy_date", "is_gender_mismatch": is_gender_mismatch, "is_date_correction": True}

    return None
