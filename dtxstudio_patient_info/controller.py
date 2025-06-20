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
from tqdm import tqdm

from dtxstudio_patient_info.match_keys import (
    create_match_key_exact,
    create_match_key_no_gender,
    create_match_key_name_only,
    create_match_key_no_suffix,
)

from dtxstudio_patient_info.utils import (
    extract_gender_from_codice_fiscale
)

from dtxstudio_patient_info.match_strategies import (
    try_exact_matches,
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

                # Warn about missing date of birth
                if not dob.strip():
                    logging.warning(
                        f"MISSING_DOB: {given_name} {family_name} [{custom_identifier}] - Patient has no date of birth")

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
                    # Store with no-suffix keys (for DTX names with suffixes)
                    no_suffix_key = create_match_key_no_suffix(
                        family_name, given_name, corrected_sex, dob)

                    # Store all match keys using the helper function
                    _add_to_lookup(pms_lookup, match_key, pms_data)
                    _add_to_lookup(pms_lookup, loose_match_key, pms_data)
                    _add_to_lookup(pms_lookup, name_only_key,
                                   pms_data, allow_multiple=True)
                    _add_to_lookup(pms_lookup, no_suffix_key, pms_data)

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
    # Each strategy tries both normal and flipped names before moving to next strategy
    strategies = [
        try_exact_matches,
        try_partial_matches,
        try_fuzzy_date_match
    ]

    for strategy in strategies:
        # Try normal names first
        result = strategy(dtx_record, pms_lookup)
        if result:
            return result

        # Try flipped names for the same strategy
        flipped_dtx_record = {
            'family_name': dtx_record['given_name'],  # Swap names
            'given_name': dtx_record['family_name'],
            'sex': dtx_record['sex'],
            'dob': dtx_record['dob']
        }
        result = strategy(flipped_dtx_record, pms_lookup)
        if result:
            # Mark as name flip and return
            pms_data, match_info = result
            match_info['is_name_flip'] = True
            logging.debug(
                f"NAME_FLIP_DETECTED: DTX '{dtx_record['given_name']} {dtx_record['family_name']}' matched PMS '{pms_data['first_name']} {pms_data['last_name']}'")
            return pms_data, match_info

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

    # Track used pms_id values to ensure uniqueness
    used_pms_ids = set()

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

                # Convert reader to list to get total count for progress bar
                rows = list(reader)

                # Process rows with progress bar (always goes to stderr to stay visible)
                for row in tqdm(rows, desc="Processing DTX records", unit="records", file=sys.stderr):
                    stats['total_records'] += 1

                    # Build DTX record for matching
                    dtx_record = _build_dtx_record(row)

                    # Try to find a PMS match
                    match_result = _find_pms_match(dtx_record, pms_lookup)

                    if match_result:
                        pms_data, match_info = match_result
                        stats['matches_found'] += 1

                        # Process the match and update row if needed
                        _process_match(row, pms_data, match_info,
                                       stats, used_pms_ids)

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


def _process_match(row: dict, pms_data: dict, match_info: dict, stats: dict, used_pms_ids: set) -> None:
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

    # Generate unique pms_id
    base_pms_id = pms_data['custom_identifier']
    unique_pms_id = _generate_unique_pms_id(base_pms_id, used_pms_ids)

    # Build new values from PMS data
    new_values = {
        'pms_id': unique_pms_id,
        'practice_pms_id': '',  # Should be empty for DTX
        'dicom_id': unique_pms_id,  # Use same unique ID for consistency
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
    if match_info.get('is_name_flip'):
        log_prefix.append("NAME FLIP")

    prefix_str = " - ".join(log_prefix)
    name = f"{old_values['given_name']} {old_values['family_name']}"

    if prefix_str:
        logging.warning(
            f"{prefix_str} - Unchanged: {name} - DTX vs PMS differences detected but all fields already correct")
    else:
        logging.debug(f"Unchanged: {name} - all fields already correct")


def _print_stats(stats: dict, output_file: Optional[str]) -> None:
    """Print processing statistics."""
    # Log summary (goes to logging destination)
    logging.info(
        f"Processing complete: {stats['total_records']} records processed, "
        f"{stats['matches_found']} matches found, {stats['records_updated']} records updated, "
        f"{stats['records_unchanged']} records unchanged, {stats['gender_mismatches']} gender corrections, "
        f"{stats['date_corrections']} date corrections, {stats['name_flips']} name flips corrected, "
        f"{stats['partial_name_matches']} partial name matches, {stats['pms_gender_errors']} PMS gender errors corrected"
    )

    # Print to stdout if CSV went to file, stderr if CSV went to stdout
    stats_output = sys.stdout if output_file else sys.stderr

    print(f"\nProcessing complete:", file=stats_output)
    print(
        f"Total records processed: {stats['total_records']}", file=stats_output)
    print(f"Matches found: {stats['matches_found']}", file=stats_output)
    print(f"Records updated: {stats['records_updated']}", file=stats_output)
    print(
        f"Records unchanged (already correct): {stats['records_unchanged']}", file=stats_output)
    print(
        f"Gender corrections: {stats['gender_mismatches']}", file=stats_output)
    print(f"Date corrections: {stats['date_corrections']}", file=stats_output)
    print(f"Name flips corrected: {stats['name_flips']}", file=stats_output)
    print(
        f"Partial name matches: {stats['partial_name_matches']}", file=stats_output)
    print(
        f"PMS gender errors corrected: {stats['pms_gender_errors']}", file=stats_output)

    if output_file:
        print(f"Output written to: {output_file}", file=stats_output)


def _generate_unique_pms_id(base_id: str, used_ids: set) -> str:
    """Generate a unique PMS ID by adding suffix if needed.

    Args:
        base_id: The original PMS ID from the data
        used_ids: Set of already used IDs

    Returns:
        Unique PMS ID (with suffix if needed)
    """
    if base_id not in used_ids:
        used_ids.add(base_id)
        return base_id

    # Generate suffixed version
    counter = 1
    while True:
        unique_id = f"{base_id}-{counter}"
        if unique_id not in used_ids:
            used_ids.add(unique_id)
            logging.debug(
                f"DUPLICATE_PMS_ID: '{base_id}' already used, assigning '{unique_id}'")
            return unique_id
        counter += 1
