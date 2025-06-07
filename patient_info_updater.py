#!/usr/bin/env python3
"""
Patient Info Updater

This script loads patient data from a DTX CSV file and matches it with a PMS CSV file
based on family_name, given_name, sex, and dob. For matches found, it updates the
pms_id field with the custom_identifier from the PMS file.
"""

import csv
import argparse
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re


def normalize_string(s: str) -> str:
    """Normalize string by removing spaces and converting to lowercase."""
    if not s:
        return ""
    return re.sub(r'\s+', '', s.lower())


def normalize_date(date_str: str) -> str:
    """Normalize date string to YYYY-MM-DD format."""
    if not date_str:
        return ""

    # Try different date formats
    formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return date_str  # Return original if no format matches


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


def calculate_digit_similarity(date1: str, date2: str) -> float:
    """
    Calculate similarity between two dates based on digit differences.
    Returns a score from 0.0 (completely different) to 1.0 (identical).
    """
    if not date1 or not date2:
        return 0.0

    # Normalize dates to YYYY-MM-DD format
    norm_date1 = normalize_date(date1)
    norm_date2 = normalize_date(date2)

    if norm_date1 == norm_date2:
        return 1.0

    # Remove hyphens for digit comparison
    digits1 = norm_date1.replace('-', '')
    digits2 = norm_date2.replace('-', '')

    if len(digits1) != len(digits2) or len(digits1) != 8:
        return 0.0

    # Define similar digits (visually or by proximity on keyboard)
    similar_digits = {
        '0': ['0', '8', 'o', 'O'],
        '1': ['1', 'l', 'I', '|'],
        '2': ['2', 'z', 'Z'],
        '3': ['3', '8'],
        '4': ['4', 'A'],
        '5': ['5', 'S', 's'],
        '6': ['6', 'G'],
        '7': ['7', 'T'],
        '8': ['8', '0', '3', 'B'],
        '9': ['9', 'g', 'q']
    }

    matches = 0
    partial_matches = 0

    for i in range(len(digits1)):
        d1, d2 = digits1[i], digits2[i]
        if d1 == d2:
            matches += 1
        elif d1 in similar_digits.get(d2, []) or d2 in similar_digits.get(d1, []):
            partial_matches += 1

    # Calculate similarity score
    total_positions = len(digits1)
    similarity = (matches + 0.5 * partial_matches) / total_positions

    return similarity


def is_fuzzy_date_match(date1: str, date2: str, threshold: float = 0.75) -> bool:
    """
    Check if two dates are similar enough to be considered a fuzzy match.

    Args:
        date1: First date string
        date2: Second date string
        threshold: Minimum similarity score (0.75 means 75% similarity)

    Returns:
        True if dates are similar enough to be considered a match
    """
    similarity = calculate_digit_similarity(date1, date2)
    return similarity >= threshold


def load_pms_data(pms_file: str) -> Dict[str, dict]:
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
                    match_key = create_match_key(
                        family_name, given_name, corrected_sex, dob)
                    # Also store with loose match key (without gender)
                    loose_match_key = create_loose_match_key(
                        family_name, given_name, dob)
                    # Store with name-only key for fuzzy date matching
                    name_only_key = create_name_only_match_key(
                        family_name, given_name)

                    # Store with flipped name keys (for name reversal detection)
                    flipped_match_key = create_flipped_match_key(
                        family_name, given_name, corrected_sex, dob)
                    flipped_loose_match_key = create_flipped_loose_match_key(
                        family_name, given_name, dob)

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

                    pms_lookup[match_key] = pms_data
                    # Also store under loose key if not already present
                    if loose_match_key not in pms_lookup:
                        pms_lookup[loose_match_key] = pms_data

                    # Store under name-only key for fuzzy date matching
                    if name_only_key not in pms_lookup:
                        pms_lookup[name_only_key] = pms_data
                    elif isinstance(pms_lookup[name_only_key], dict):
                        # Convert to list if we have multiple candidates
                        pms_lookup[name_only_key] = [
                            pms_lookup[name_only_key], pms_data]
                    elif isinstance(pms_lookup[name_only_key], list):
                        # Add to existing list
                        pms_lookup[name_only_key].append(pms_data)

                    # Store under flipped name-only key for fuzzy matching as well
                    flipped_name_only_key = create_name_only_match_key(
                        given_name, family_name)  # Flipped order
                    if flipped_name_only_key not in pms_lookup:
                        pms_lookup[flipped_name_only_key] = pms_data
                    elif isinstance(pms_lookup[flipped_name_only_key], dict):
                        # Convert to list if we have multiple candidates
                        pms_lookup[flipped_name_only_key] = [
                            pms_lookup[flipped_name_only_key], pms_data]
                    elif isinstance(pms_lookup[flipped_name_only_key], list):
                        # Add to existing list
                        pms_lookup[flipped_name_only_key].append(pms_data)

                    # Store under flipped keys if not already present
                    if flipped_match_key not in pms_lookup:
                        pms_lookup[flipped_match_key] = pms_data
                    if flipped_loose_match_key not in pms_lookup:
                        pms_lookup[flipped_loose_match_key] = pms_data

    except FileNotFoundError:
        logging.error(f"PMS file '{pms_file}' not found.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error reading PMS file: {e}")
        sys.exit(1)

    logging.info(f"Loaded {len(pms_lookup)} records from PMS file.")
    return pms_lookup


def process_dtx_file(dtx_file: str, pms_lookup: Dict[str, dict], output_file: Optional[str] = None) -> None:
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
                    match_key = create_match_key(
                        family_name, given_name, sex, dob)
                    loose_match_key = create_loose_match_key(
                        family_name, given_name, dob)

                    # Create flipped name keys
                    flipped_match_key = create_flipped_match_key(
                        family_name, given_name, sex, dob)
                    flipped_loose_match_key = create_flipped_loose_match_key(
                        family_name, given_name, dob)

                    # Create partial match keys (for PMS names without suffixes)
                    partial_match_key = create_partial_match_key(
                        family_name, given_name, sex, dob)
                    partial_loose_match_key = create_partial_loose_match_key(
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
                        match_type = "exact"
                    elif loose_match_key in pms_lookup:
                        # Loose match (names and DOB match, but gender might differ)
                        pms_data = pms_lookup[loose_match_key]
                        is_gender_mismatch = (sex != pms_data['gender'])
                        match_type = "loose"
                    elif flipped_match_key in pms_lookup:
                        # Flipped name exact match
                        pms_data = pms_lookup[flipped_match_key]
                        is_name_flip = True
                        match_type = "flipped_exact"
                    elif flipped_loose_match_key in pms_lookup:
                        # Flipped name loose match
                        pms_data = pms_lookup[flipped_loose_match_key]
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
                            # Try fuzzy date matching (names match, dates similar)
                            name_only_key = create_name_only_match_key(
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


def extract_gender_from_codice_fiscale(ssn: str) -> Optional[str]:
    """
    Extract gender from Italian codice fiscale (SSN).

    Args:
        ssn: The codice fiscale string

    Returns:
        'MALE' for male, 'FEMALE' for female, None if invalid or can't determine
    """
    if not ssn or len(ssn) < 11:
        return None

    try:
        # Get chars 10-11 (0-based indexing: chars 9-10)
        day_chars = ssn[9:11]
        day_number = int(day_chars)

        # For females, day is encoded with +40 offset
        if 41 <= day_number <= 71:
            return 'FEMALE'  # Female (day - 40 gives actual day 1-31)
        elif 1 <= day_number <= 31:
            return 'MALE'  # Male (actual day)
        else:
            return None  # Invalid day

    except (ValueError, IndexError):
        return None


def is_partial_name_match(pms_name: str, dtx_name: str) -> bool:
    """
    Check if PMS name is a substring of DTX name (case insensitive).
    This handles cases where DTX has suffixes like 'BIS', 'TRIS', etc.

    Args:
        pms_name: Name from PMS (shorter, without suffix)
        dtx_name: Name from DTX (potentially with suffix)

    Returns:
        True if PMS name matches the beginning of DTX name
    """
    if not pms_name or not dtx_name:
        return False

    pms_normalized = normalize_string(pms_name)
    dtx_normalized = normalize_string(dtx_name)

    # PMS name should be at the start of DTX name
    return dtx_normalized.startswith(pms_normalized) and len(pms_normalized) > 0


def main():
    """Main function to handle command line arguments and orchestrate the process."""
    parser = argparse.ArgumentParser(
        description="Update DTX patient data with PMS custom identifiers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python patient_info_updater.py dtx_patients.csv pms_patients.csv -o updated_patients.csv
  python patient_info_updater.py input.csv reference.csv --output result.csv
        """
    )

    parser.add_argument(
        'dtx_file', help='Path to the DTX CSV file to be updated')
    parser.add_argument(
        'pms_file', help='Path to the PMS CSV file for reference')
    parser.add_argument('-o', '--output',
                        help='Path to the output CSV file (default: stdout)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()

    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    if args.verbose:
        print(f"DTX file: {args.dtx_file}")
        print(f"PMS file: {args.pms_file}")
        print(f"Output file: {args.output}")
        print()

    # Load PMS data for lookup
    logging.info("Loading PMS reference data...")
    pms_lookup = load_pms_data(args.pms_file)

    # Process DTX file and create updated output
    logging.info("Processing DTX file...")
    process_dtx_file(args.dtx_file, pms_lookup, args.output)

    logging.info("Done!")


if __name__ == "__main__":
    main()
