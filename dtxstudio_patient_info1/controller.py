"""
Patient Info Updater

This script loads patient data from a DTX CSV file and matches it with a PMS CSV file
based on family_name, given_name, sex, and dob. For matches found, it updates the
pms_id field with the custom_identifier from the PMS file.

The resulting output file can then be used to update the DTX patient records by uploading it into the Patient Info in DTX Studio Core GUI.
"""

import csv
import sys
import logging
from typing import Dict, Optional, Union, List

from dtxstudio_patient_info1.match_keys import (
    create_match_key_exact,
    create_match_key_no_gender,
    create_match_key_name_only,
    create_match_key_flipped_names,
    create_match_key_no_gender_flipped_names,
    create_match_key_no_suffix,
)

from dtxstudio_patient_info1.utils import (
    normalize_string,
    normalize_date,
    is_partial_name_match,
    is_fuzzy_date_match,
    is_partial_name_word_match,
    extract_gender_from_codice_fiscale
)


def _add_to_lookup(pms_lookup: Dict[str, Union[dict, List[dict]]], key: str, pms_data: dict, allow_multiple: bool = False) -> None:
    """
    Helper function to add PMS data to lookup dictionary.

    Args:
        pms_lookup: The lookup dictionary to add to
        key: The match key
        pms_data: The PMS patient data
        allow_multiple: If True, allows multiple candidates for the same key (stores as list)
    """
    if key not in pms_lookup:
        pms_lookup[key] = pms_data
    elif allow_multiple:
        existing = pms_lookup[key]
        if isinstance(existing, dict):
            # Convert to list if we have multiple candidates
            pms_lookup[key] = [existing, pms_data]
        elif isinstance(existing, list):
            # Add to existing list
            existing.append(pms_data)
    # If allow_multiple is False and key exists, don't overwrite (keep first occurrence)


def load_pms_data(pms_file: str) -> Dict[str, Union[dict, List[dict]]]:
    """
    Load PMS CSV data and create a lookup dictionary.

    Args:
        pms_file: Path to the PMS CSV file

    Returns:
        Dictionary mapping match_key to PMS patient data
    """
    pms_lookup = {}

    try:
        with open(pms_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Extract required fields from PMS data
                family_name = row.get('last_name', '')
                given_name = row.get('first_name', '')
                middle_name = row.get('middle_initial', '')
                sex = row.get('gender', '')
                dob = row.get('dob', '')
                custom_identifier = row.get('custom_identifier', '')
                ssn = row.get('ssn', '')

                if all([family_name, given_name, sex, dob, custom_identifier]):
                    # Validate and potentially correct gender based on codice fiscale
                    corrected_sex = sex
                    is_pms_gender_error = False

                    if ssn:
                        cf_gender = extract_gender_from_codice_fiscale(ssn)
                        if cf_gender and cf_gender != sex:
                            logging.warning(
                                f"CODICE_FISCALE_GENDER_MISMATCH: {given_name} {family_name} [{custom_identifier}] - PMS gender '{sex}' doesn't match codice fiscale gender '{cf_gender}' (SSN: {ssn})")
                            corrected_sex = cf_gender
                            is_pms_gender_error = True

                # Store with exact match key (including gender)
                if all([family_name, given_name, sex, dob, custom_identifier]):
                    # Store all the data we want to update
                    pms_data = {
                        'custom_identifier': custom_identifier,
                        'first_name': given_name,
                        'last_name': family_name,
                        'middle_initial': middle_name,
                        'gender': corrected_sex,  # Use corrected gender
                        'dob': dob,
                        'is_pms_gender_error': is_pms_gender_error
                    }

                    match_key = create_match_key_exact(
                        family_name, given_name, corrected_sex, dob)
                    # Also store with loose match key (without gender)
                    loose_match_key = create_match_key_no_gender(
                        family_name, given_name, dob)
                    # Store with name-only key for fuzzy date matching
                    name_only_key = create_match_key_name_only(
                        family_name, given_name)

                    # Store with flipped name keys (for name reversal detection)
                    flipped_match_key = create_match_key_flipped_names(
                        family_name, given_name, corrected_sex, dob)
                    flipped_loose_match_key = create_match_key_no_gender_flipped_names(
                        family_name, given_name, dob)
                    # Store under flipped name-only key for fuzzy matching as well
                    flipped_name_only_key = create_match_key_name_only(
                        given_name=family_name, family_name=given_name)  # Flipped order

                    # Store all match keys using the helper function
                    _add_to_lookup(pms_lookup, match_key, pms_data)
                    _add_to_lookup(pms_lookup, loose_match_key, pms_data)
                    _add_to_lookup(pms_lookup, name_only_key,
                                   pms_data, allow_multiple=True)
                    _add_to_lookup(pms_lookup, flipped_match_key, pms_data)
                    _add_to_lookup(
                        pms_lookup, flipped_loose_match_key, pms_data)
                    _add_to_lookup(pms_lookup, flipped_name_only_key,
                                   pms_data, allow_multiple=True)

    except FileNotFoundError:
        logging.error(f"PMS file '{pms_file}' not found.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error reading PMS file: {e}")
        sys.exit(1)

    logging.info(f"Loaded {len(pms_lookup)} records from PMS file.")
    return pms_lookup


def process_dtx_file(dtx_file: str, pms_lookup: Dict[str, Union[dict, List[dict]]], output_file: Optional[str] = None) -> None:
    """
    Process DTX CSV file and update pms_id with matching custom_identifier.

    Args:
        dtx_file: Path to the DTX CSV file
        pms_lookup: Dictionary mapping match_key to PMS patient data
        output_file: Path to the output CSV file (None for stdout)
    """
    matches_found = 0
    records_updated = 0
    records_unchanged = 0
    gender_mismatches = 0
    date_corrections = 0
    name_flips = 0
    partial_name_matches = 0
    pms_gender_errors = 0
    total_records = 0

    try:
        with open(dtx_file, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)

            # Get the original fieldnames and write header
            fieldnames = reader.fieldnames
            if not fieldnames:
                logging.error("No fieldnames found in DTX file.")
                return

            # Use stdout or file based on output_file parameter
            if output_file:
                outfile = open(output_file, 'w', encoding='utf-8', newline='')
            else:
                outfile = sys.stdout

            try:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in reader:
                    total_records += 1

                    # Extract matching fields from DTX data
                    family_name = row.get('family_name', '')
                    given_name = row.get('given_name', '')
                    sex = row.get('sex', '')
                    dob = row.get('dob', '')

                    # Create match keys
                    match_key = create_match_key_exact(
                        family_name, given_name, sex, dob)
                    loose_match_key = create_match_key_no_gender(
                        family_name, given_name, dob)

                    # Create flipped name keys
                    flipped_match_key = create_match_key_flipped_names(
                        family_name, given_name, sex, dob)
                    flipped_loose_match_key = create_match_key_no_gender_flipped_names(
                        family_name, given_name, dob)

                    # Create partial match keys (for PMS names without suffixes)
                    partial_match_key = create_match_key_no_suffix(
                        family_name, given_name, sex, dob)
                    # Use no_gender for partial loose matching
                    partial_loose_match_key = create_match_key_no_gender(
                        family_name, given_name, dob)

                    # Check for match in PMS data (exact match first, then loose match, then flipped, then partial, then fuzzy)
                    pms_data = None
                    is_gender_mismatch = False
                    is_date_correction = False
                    is_name_flip = False
                    is_partial_match = False
                    match_type = None

                    if match_key in pms_lookup:
                        # Exact match (including gender)
                        pms_data = pms_lookup[match_key]
                        if isinstance(pms_data, list):
                            pms_data = pms_data[0]  # Take first match
                        match_type = "exact"
                    elif loose_match_key in pms_lookup:
                        # Loose match (names and DOB match, but gender might differ)
                        pms_data = pms_lookup[loose_match_key]
                        if isinstance(pms_data, list):
                            pms_data = pms_data[0]  # Take first match
                        is_gender_mismatch = (sex != pms_data['gender'])
                        match_type = "loose"
                    elif flipped_match_key in pms_lookup:
                        # Flipped name exact match
                        pms_data = pms_lookup[flipped_match_key]
                        if isinstance(pms_data, list):
                            pms_data = pms_data[0]  # Take first match
                        is_name_flip = True
                        match_type = "flipped_exact"
                    elif flipped_loose_match_key in pms_lookup:
                        # Flipped name loose match
                        pms_data = pms_lookup[flipped_loose_match_key]
                        if isinstance(pms_data, list):
                            pms_data = pms_data[0]  # Take first match
                        is_gender_mismatch = (sex != pms_data['gender'])
                        is_name_flip = True
                        match_type = "flipped_loose"
                    else:
                        # Try partial name matching (PMS names are substrings of DTX names)
                        for pms_key, pms_candidate in pms_lookup.items():
                            if isinstance(pms_candidate, dict):
                                # Check if this is a potential partial match
                                pms_family = pms_candidate.get('last_name', '')
                                pms_given = pms_candidate.get('first_name', '')
                                pms_sex = pms_candidate.get('gender', '')
                                pms_dob = pms_candidate.get('dob', '')

                                # Check if PMS names are substrings of DTX names and other fields match
                                if (is_partial_name_match(pms_family, family_name) and
                                    is_partial_name_match(pms_given, given_name) and
                                        normalize_date(pms_dob) == normalize_date(dob)):

                                    if normalize_string(pms_sex) == normalize_string(sex):
                                        # Exact partial match (names partial, gender and DOB exact)
                                        pms_data = pms_candidate
                                        is_partial_match = True
                                        match_type = "partial_exact"
                                        break
                                    else:
                                        # Loose partial match (names partial, DOB exact, gender differs)
                                        pms_data = pms_candidate
                                        is_partial_match = True
                                        is_gender_mismatch = True
                                        match_type = "partial_loose"
                                        break

                        if not pms_data:
                            # Try partial given name matching (any word overlap in given names)
                            for pms_key, pms_candidate in pms_lookup.items():
                                if isinstance(pms_candidate, dict):
                                    pms_family = pms_candidate.get(
                                        'last_name', '')
                                    pms_given = pms_candidate.get(
                                        'first_name', '')
                                    pms_sex = pms_candidate.get('gender', '')
                                    pms_dob = pms_candidate.get('dob', '')

                                    # Check if family names match exactly, given names have partial overlap, and DOB matches
                                    if (normalize_string(pms_family) == normalize_string(family_name) and
                                        is_partial_name_word_match(given_name, pms_given) and
                                            normalize_date(pms_dob) == normalize_date(dob)):

                                        if normalize_string(pms_sex) == normalize_string(sex):
                                            # Exact partial given name match
                                            pms_data = pms_candidate
                                            is_partial_match = True
                                            match_type = "partial_given_exact"
                                            break
                                        else:
                                            # Loose partial given name match
                                            pms_data = pms_candidate
                                            is_partial_match = True
                                            is_gender_mismatch = True
                                            match_type = "partial_given_loose"
                                            break

                        if not pms_data:
                            # Try fuzzy date matching (names match, dates similar)
                            name_only_key = create_match_key_name_only(
                                family_name, given_name)
                            if name_only_key in pms_lookup:
                                candidates = pms_lookup[name_only_key]
                                if isinstance(candidates, dict):
                                    candidates = [candidates]
                                elif not isinstance(candidates, list):
                                    candidates = []

                                # Check each candidate for fuzzy date match
                                for candidate in candidates:
                                    if is_fuzzy_date_match(dob, candidate['dob']):
                                        pms_data = candidate
                                        is_gender_mismatch = (
                                            sex != pms_data['gender'])
                                        is_date_correction = True
                                        match_type = "fuzzy_date"
                                        break  # Take first fuzzy match

                    if pms_data:
                        matches_found += 1

                        # Store old values for logging
                        old_pms_id = row.get('pms_id', '')
                        old_practice_pms_id = row.get('practice_pms_id', '')
                        old_dicom_id = row.get('dicom_id', '')
                        old_given_name = row.get('given_name', '')
                        old_family_name = row.get('family_name', '')
                        old_middle_name = row.get('middle_name', '')
                        old_sex = row.get('sex', '')
                        old_dob = row.get('dob', '')

                        # Get new values from PMS
                        new_pms_id = pms_data['custom_identifier']
                        # Set same as pms_id
                        new_practice_pms_id = pms_data['custom_identifier']
                        # Set same as pms_id
                        new_dicom_id = pms_data['custom_identifier']
                        new_given_name = pms_data['first_name']
                        new_family_name = pms_data['last_name']
                        new_middle_name = pms_data['middle_initial']
                        new_sex = pms_data['gender']
                        new_dob = pms_data['dob']

                        # Check if any fields need updating
                        needs_update = (old_pms_id != new_pms_id or
                                        old_practice_pms_id != new_practice_pms_id or
                                        old_dicom_id != new_dicom_id or
                                        old_given_name != new_given_name or
                                        old_family_name != new_family_name or
                                        old_middle_name != new_middle_name or
                                        old_sex != new_sex or
                                        old_dob != new_dob)

                        if needs_update:
                            # Update all fields
                            row['pms_id'] = new_pms_id
                            row['practice_pms_id'] = new_practice_pms_id
                            row['dicom_id'] = new_dicom_id
                            row['given_name'] = new_given_name
                            row['family_name'] = new_family_name
                            row['middle_name'] = new_middle_name
                            row['sex'] = new_sex
                            row['dob'] = new_dob

                            records_updated += 1

                            # Count specific types of corrections
                            if is_gender_mismatch:
                                gender_mismatches += 1
                            if is_date_correction:
                                date_corrections += 1
                            if is_name_flip:
                                name_flips += 1
                            if is_partial_match:
                                partial_name_matches += 1
                            if pms_data.get('is_pms_gender_error', False):
                                pms_gender_errors += 1

                            changes = []
                            if old_pms_id != new_pms_id:
                                changes.append(
                                    f"pms_id: '{old_pms_id}' -> '{new_pms_id}'")
                            if old_practice_pms_id != new_practice_pms_id:
                                changes.append(
                                    f"practice_pms_id: '{old_practice_pms_id}' -> '{new_practice_pms_id}'")
                            if old_dicom_id != new_dicom_id:
                                changes.append(
                                    f"dicom_id: '{old_dicom_id}' -> '{new_dicom_id}'")
                            if old_given_name != new_given_name:
                                changes.append(
                                    f"given_name: '{old_given_name}' -> '{new_given_name}'")
                            if old_family_name != new_family_name:
                                changes.append(
                                    f"family_name: '{old_family_name}' -> '{new_family_name}'")
                            if old_middle_name != new_middle_name:
                                changes.append(
                                    f"middle_name: '{old_middle_name}' -> '{new_middle_name}'")
                            if old_sex != new_sex:
                                changes.append(
                                    f"sex: '{old_sex}' -> '{new_sex}'")
                            if old_dob != new_dob:
                                changes.append(
                                    f"dob: '{old_dob}' -> '{new_dob}'")

                            # Log with appropriate level based on match type
                            log_prefix = []
                            if is_gender_mismatch:
                                log_prefix.append("GENDER MISMATCH")
                            if is_date_correction:
                                log_prefix.append("DATE CORRECTION")
                            if is_name_flip:
                                log_prefix.append("NAME FLIP")
                            if is_partial_match:
                                log_prefix.append("PARTIAL NAME MATCH")
                            if pms_data.get('is_pms_gender_error', False):
                                log_prefix.append(
                                    "CODICE_FISCALE_GENDER_ERROR")

                            prefix_str = " - ".join(log_prefix)
                            if prefix_str:
                                logging.warning(
                                    f"{prefix_str} - Updated: {old_given_name} {old_family_name} - {', '.join(changes)}")
                            else:
                                logging.info(
                                    f"Updated: {old_given_name} {old_family_name} - {', '.join(changes)}")
                        else:
                            records_unchanged += 1
                            log_prefix = []
                            if is_gender_mismatch:
                                log_prefix.append("GENDER MISMATCH")
                            if is_date_correction:
                                log_prefix.append("DATE CORRECTION")

                            prefix_str = " - ".join(log_prefix)
                            if prefix_str:
                                logging.warning(
                                    f"{prefix_str} - Unchanged: {old_given_name} {old_family_name} - DTX vs PMS differences detected but all fields already correct")
                            else:
                                logging.debug(
                                    f"Unchanged: {old_given_name} {old_family_name} - all fields already correct")

                    # Write the row (modified or original)
                    writer.writerow(row)

            finally:
                # Only close if it's a real file, not stdout
                if output_file and outfile != sys.stdout:
                    outfile.close()

    except FileNotFoundError:
        logging.error(f"DTX file '{dtx_file}' not found.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error processing DTX file: {e}")
        sys.exit(1)

    # Print stats to stderr so they don't interfere with CSV output to stdout
    logging.info(
        f"Processing complete: {total_records} records processed, {matches_found} matches found, {records_updated} records updated, {records_unchanged} records unchanged, {gender_mismatches} gender corrections, {date_corrections} date corrections, {name_flips} name flips corrected, {partial_name_matches} partial name matches, {pms_gender_errors} PMS gender errors corrected")
    print(f"\nProcessing complete:", file=sys.stderr)
    print(f"Total records processed: {total_records}", file=sys.stderr)
    print(f"Matches found: {matches_found}", file=sys.stderr)
    print(f"Records updated: {records_updated}", file=sys.stderr)
    print(
        f"Records unchanged (already correct): {records_unchanged}", file=sys.stderr)
    print(f"Gender corrections: {gender_mismatches}", file=sys.stderr)
    print(f"Date corrections: {date_corrections}", file=sys.stderr)
    print(f"Name flips corrected: {name_flips}", file=sys.stderr)
    print(f"Partial name matches: {partial_name_matches}", file=sys.stderr)
    print(f"PMS gender errors corrected: {pms_gender_errors}", file=sys.stderr)
    if output_file:
        print(f"Output written to: {output_file}", file=sys.stderr)
