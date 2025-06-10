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
    extract_gender_from_codice_fiscale
)

from dtxstudio_patient_info1.match_strategies import (
    try_exact_matches,
    try_flipped_matches,
    try_partial_matches,
    try_fuzzy_date_match
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



def _find_pms_match(dtx_record: dict, pms_lookup: Dict[str, Union[dict, List[dict]]]) -> Optional[tuple]:
    """Find the best PMS match for a DTX record using prioritized strategies.

    Returns: (pms_data, match_info) or None
    """
    # Try matching strategies in order of preference
    strategies = [
        try_exact_matches,
        try_flipped_matches,
        try_partial_matches,
        try_fuzzy_date_match
    ]

    for strategy in strategies:
        result = strategy(dtx_record, pms_lookup)
        if result:
            return result

    return None


def _build_dtx_record(row: dict) -> dict:
    """Extract DTX fields into a clean record."""
    return {
        'family_name': row.get('family_name', ''),
        'given_name': row.get('given_name', ''),
        'sex': row.get('sex', ''),
        'dob': row.get('dob', '')
    }


def _needs_update(old_values: dict, new_values: dict) -> bool:
    """Check if any fields need updating."""
    return any(old_values[field] != new_values[field] for field in old_values.keys())


def _log_changes(old_values: dict, new_values: dict, match_info: dict) -> None:
    """Log the changes being made."""
    changes = []
    for field, old_val in old_values.items():
        new_val = new_values[field]
        if old_val != new_val:
            changes.append(f"{field}: '{old_val}' -> '{new_val}'")

    if not changes:
        return

    # Build log prefix based on match info
    log_prefix = []
    if match_info.get('is_gender_mismatch'):
        log_prefix.append("GENDER MISMATCH")
    if match_info.get('is_date_correction'):
        log_prefix.append("DATE CORRECTION")
    if match_info.get('is_name_flip'):
        log_prefix.append("NAME FLIP")
    if match_info.get('is_partial_match'):
        log_prefix.append("PARTIAL NAME MATCH")

    prefix_str = " - ".join(log_prefix)
    log_message = f"Updated: {old_values['given_name']} {old_values['family_name']} - {', '.join(changes)}"

    if prefix_str:
        logging.warning(f"{prefix_str} - {log_message}")
    else:
        logging.info(log_message)


def process_dtx_file(dtx_file: str, pms_lookup: Dict[str, Union[dict, List[dict]]], output_file: Optional[str] = None) -> None:
    """
    Process DTX CSV file and update pms_id with matching custom_identifier.

    Args:
        dtx_file: Path to the DTX CSV file
        pms_lookup: Dictionary mapping match_key to PMS patient data
        output_file: Path to the output CSV file (None for stdout)
    """
    stats = {
        'matches_found': 0,
        'records_updated': 0,
        'records_unchanged': 0,
        'gender_mismatches': 0,
        'date_corrections': 0,
        'name_flips': 0,
        'partial_name_matches': 0,
        'pms_gender_errors': 0,
        'total_records': 0
    }

    try:
        with open(dtx_file, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames

            if not fieldnames:
                logging.error("No fieldnames found in DTX file.")
                return

            # Setup output file or stdout
            outfile = open(output_file, 'w', encoding='utf-8',
                           newline='') if output_file else sys.stdout

            try:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in reader:
                    stats['total_records'] += 1

                    # Build DTX record for matching
                    dtx_record = _build_dtx_record(row)

                    # Try to find a PMS match
                    match_result = _find_pms_match(dtx_record, pms_lookup)

                    if match_result:
                        pms_data, match_info = match_result
                        stats['matches_found'] += 1

                        # Process the match and update row if needed
                        _process_match(row, pms_data, match_info, stats)

                    # Write the row (modified or original)
                    writer.writerow(row)

            finally:
                if output_file and outfile != sys.stdout:
                    outfile.close()

    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user (Ctrl+C)", file=sys.stderr)
        print(f"Partial results written to output. Progress so far:", file=sys.stderr)
        _print_stats(stats, output_file)
        raise  # Re-raise so entrypoint can handle it
    except FileNotFoundError:
        logging.error(f"DTX file '{dtx_file}' not found.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error processing DTX file: {e}")
        sys.exit(1)

    _print_stats(stats, output_file)


def _process_match(row: dict, pms_data: dict, match_info: dict, stats: dict) -> None:
    """Process a successful match and update the row if needed."""
    # Extract old values
    old_values = {
        'pms_id': row.get('pms_id', ''),
        'practice_pms_id': row.get('practice_pms_id', ''),
        'dicom_id': row.get('dicom_id', ''),
        'given_name': row.get('given_name', ''),
        'family_name': row.get('family_name', ''),
        'middle_name': row.get('middle_name', ''),
        'sex': row.get('sex', ''),
        'dob': row.get('dob', '')
    }

    # Build new values from PMS data
    new_values = {
        'pms_id': pms_data['custom_identifier'],
        'practice_pms_id': pms_data['custom_identifier'],
        'dicom_id': pms_data['custom_identifier'],
        'given_name': pms_data['first_name'],
        'family_name': pms_data['last_name'],
        'middle_name': pms_data['middle_initial'],
        'sex': pms_data['gender'],
        'dob': pms_data['dob']
    }

    # Check if update is needed
    if _needs_update(old_values, new_values):
        # Update the row
        for field, value in new_values.items():
            row[field] = value

        stats['records_updated'] += 1
        _update_stats(match_info, pms_data, stats)
        _log_changes(old_values, new_values, match_info)
    else:
        stats['records_unchanged'] += 1
        _log_unchanged(old_values, match_info)


def _update_stats(match_info: dict, pms_data: dict, stats: dict) -> None:
    """Update statistics based on match type."""
    if match_info.get('is_gender_mismatch'):
        stats['gender_mismatches'] += 1
    if match_info.get('is_date_correction'):
        stats['date_corrections'] += 1
    if match_info.get('is_name_flip'):
        stats['name_flips'] += 1
    if match_info.get('is_partial_match'):
        stats['partial_name_matches'] += 1
    if pms_data.get('is_pms_gender_error', False):
        stats['pms_gender_errors'] += 1


def _log_unchanged(old_values: dict, match_info: dict) -> None:
    """Log when a match was found but no update was needed."""
    log_prefix = []
    if match_info.get('is_gender_mismatch'):
        log_prefix.append("GENDER MISMATCH")
    if match_info.get('is_date_correction'):
        log_prefix.append("DATE CORRECTION")

    prefix_str = " - ".join(log_prefix)
    name = f"{old_values['given_name']} {old_values['family_name']}"

    if prefix_str:
        logging.warning(
            f"{prefix_str} - Unchanged: {name} - DTX vs PMS differences detected but all fields already correct")
    else:
        logging.debug(f"Unchanged: {name} - all fields already correct")


def _print_stats(stats: dict, output_file: Optional[str]) -> None:
    """Print processing statistics to stderr."""
    # Log summary
    logging.info(
        f"Processing complete: {stats['total_records']} records processed, "
        f"{stats['matches_found']} matches found, {stats['records_updated']} records updated, "
        f"{stats['records_unchanged']} records unchanged, {stats['gender_mismatches']} gender corrections, "
        f"{stats['date_corrections']} date corrections, {stats['name_flips']} name flips corrected, "
        f"{stats['partial_name_matches']} partial name matches, {stats['pms_gender_errors']} PMS gender errors corrected"
    )

    # Print to stderr (won't interfere with CSV output to stdout)
    print(f"\nProcessing complete:", file=sys.stderr)
    print(
        f"Total records processed: {stats['total_records']}", file=sys.stderr)
    print(f"Matches found: {stats['matches_found']}", file=sys.stderr)
    print(f"Records updated: {stats['records_updated']}", file=sys.stderr)
    print(
        f"Records unchanged (already correct): {stats['records_unchanged']}", file=sys.stderr)
    print(f"Gender corrections: {stats['gender_mismatches']}", file=sys.stderr)
    print(f"Date corrections: {stats['date_corrections']}", file=sys.stderr)
    print(f"Name flips corrected: {stats['name_flips']}", file=sys.stderr)
    print(
        f"Partial name matches: {stats['partial_name_matches']}", file=sys.stderr)
    print(
        f"PMS gender errors corrected: {stats['pms_gender_errors']}", file=sys.stderr)

    if output_file:
        print(f"Output written to: {output_file}", file=sys.stderr)
