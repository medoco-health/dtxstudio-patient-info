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

                if all([family_name, given_name, sex, dob, custom_identifier]):
                    match_key = create_match_key(
                        family_name, given_name, sex, dob)
                    # Store all the data we want to update, not just custom_identifier
                    pms_lookup[match_key] = {
                        'custom_identifier': custom_identifier,
                        'first_name': given_name,
                        'last_name': family_name,
                        'middle_initial': middle_name
                    }

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

                    # Create match key
                    match_key = create_match_key(
                        family_name, given_name, sex, dob)

                    # Check for match in PMS data
                    if match_key in pms_lookup:
                        matches_found += 1
                        pms_data = pms_lookup[match_key]

                        # Store old values for logging
                        old_pms_id = row.get('pms_id', '')
                        old_given_name = row.get('given_name', '')
                        old_family_name = row.get('family_name', '')
                        old_middle_name = row.get('middle_name', '')

                        # Get new values from PMS
                        new_pms_id = pms_data['custom_identifier']
                        new_given_name = pms_data['first_name']
                        new_family_name = pms_data['last_name']
                        new_middle_name = pms_data['middle_initial']

                        # Check if any fields need updating
                        needs_update = (old_pms_id != new_pms_id or
                                        old_given_name != new_given_name or
                                        old_family_name != new_family_name or
                                        old_middle_name != new_middle_name)

                        if needs_update:
                            # Update all fields
                            row['pms_id'] = new_pms_id
                            row['given_name'] = new_given_name
                            row['family_name'] = new_family_name
                            row['middle_name'] = new_middle_name

                            records_updated += 1
                            changes = []
                            if old_pms_id != new_pms_id:
                                changes.append(
                                    f"pms_id: '{old_pms_id}' -> '{new_pms_id}'")
                            if old_given_name != new_given_name:
                                changes.append(
                                    f"given_name: '{old_given_name}' -> '{new_given_name}'")
                            if old_family_name != new_family_name:
                                changes.append(
                                    f"family_name: '{old_family_name}' -> '{new_family_name}'")
                            if old_middle_name != new_middle_name:
                                changes.append(
                                    f"middle_name: '{old_middle_name}' -> '{new_middle_name}'")

                            logging.info(
                                f"Updated: {old_given_name} {old_family_name} - {', '.join(changes)}")
                        else:
                            records_unchanged += 1
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
        f"Processing complete: {total_records} records processed, {matches_found} matches found, {records_updated} records updated, {records_unchanged} records unchanged")
    print(f"\nProcessing complete:", file=sys.stderr)
    print(f"Total records processed: {total_records}", file=sys.stderr)
    print(f"Matches found: {matches_found}", file=sys.stderr)
    print(f"Records updated: {records_updated}", file=sys.stderr)
    print(
        f"Records unchanged (already correct): {records_unchanged}", file=sys.stderr)
    if output_file:
        print(f"Output written to: {output_file}", file=sys.stderr)


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
