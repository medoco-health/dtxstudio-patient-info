#!/usr/bin/env python3
"""
Clinical Patient Info Updater

A clinical informatics-based patient matching system for updating DTX patient
records with PMS data using evidence-based matching algorithms.

This is the main entrypoint for the clinical matching system.
"""

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Dict

from dtxstudio_patient_info.core.patient_matcher import ClinicalPatientMatcher
from dtxstudio_patient_info.utils.key_builders import create_composite_keys
from dtxstudio_patient_info.utils.italian_cf import (
    extract_gender_from_codice_fiscale,
    is_codice_fiscale_gender_consistent
)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = '%(asctime)s - %(levelname)s - %(message)s'

    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )


def load_pms_data_clinical(pms_file: str) -> Dict[str, dict]:
    """Load PMS data with clinical matching key generation."""
    pms_lookup = {}

    logging.info(f"Loading PMS data from: {pms_file}")

    with open(pms_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            # Extract required fields
            family_name = row.get('last_name', '').strip()
            given_name = row.get('first_name', '').strip()
            sex = row.get('gender', '').strip()
            dob = row.get('dob', '').strip()
            custom_identifier = row.get('custom_identifier', '').strip()
            middle_name = row.get('middle_initial', '').strip()
            ssn = row.get('ssn', '').strip()

            if not all([family_name, given_name, dob]):
                logging.warning(f"Skipping incomplete PMS record: {row}")
                continue

            # Validate and correct gender using Codice Fiscale if available
            corrected_sex = sex
            is_pms_gender_error = False

            if ssn:
                cf_gender = extract_gender_from_codice_fiscale(ssn)
                if cf_gender and not is_codice_fiscale_gender_consistent(ssn, sex):
                    logging.warning(
                        f"CODICE_FISCALE_GENDER_MISMATCH - Correcting gender for "
                        f"{given_name} {family_name}: '{sex}' -> '{cf_gender}' based on CF"
                    )
                    corrected_sex = cf_gender
                    is_pms_gender_error = True

            # Create PMS record
            pms_data = {
                'custom_identifier': custom_identifier,
                'first_name': given_name,
                'last_name': family_name,
                'middle_initial': middle_name,
                'gender': corrected_sex,
                'dob': dob,
                'ssn': ssn,
                'is_pms_gender_error': is_pms_gender_error
            }

            # Generate all possible matching keys
            keys = create_composite_keys(
                family_name, given_name, corrected_sex, dob)

            # Store under all keys for comprehensive matching
            for key_type, key in keys.items():
                if key not in pms_lookup:
                    pms_lookup[key] = pms_data
                elif isinstance(pms_lookup[key], dict):
                    # Convert to list for multiple candidates
                    pms_lookup[key] = [pms_lookup[key], pms_data]
                elif isinstance(pms_lookup[key], list):
                    pms_lookup[key].append(pms_data)

    logging.info(
        f"Loaded {len(set(d.get('custom_identifier') for d in pms_lookup.values() if isinstance(d, dict)))} unique PMS records")
    return pms_lookup


def main():
    """Main entrypoint for clinical patient updater."""
    parser = argparse.ArgumentParser(
        description="Clinical Patient Info Updater - Evidence-based patient matching system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s dtx.csv pms.csv -o updated.csv
  %(prog)s dtx.csv pms.csv --confidence-threshold 0.8 --verbose
  %(prog)s dtx.csv pms.csv --audit-only
        """
    )

    parser.add_argument('dtx_file', help='DTX CSV file path')
    parser.add_argument('pms_file', help='PMS CSV file path')
    parser.add_argument(
        '-o', '--output', help='Output CSV file (default: stdout)')
    parser.add_argument('--confidence-threshold', type=float, default=0.70,
                        help='Minimum confidence for automatic matching (default: 0.70)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--audit-only', action='store_true',
                        help='Generate audit report only, no output file')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Validate input files
    if not Path(args.dtx_file).exists():
        print(f"Error: DTX file not found: {args.dtx_file}", file=sys.stderr)
        sys.exit(1)

    if not Path(args.pms_file).exists():
        print(f"Error: PMS file not found: {args.pms_file}", file=sys.stderr)
        sys.exit(1)

    try:
        # Load PMS data
        pms_lookup = load_pms_data_clinical(args.pms_file)

        # Create matcher and process
        matcher = ClinicalPatientMatcher(
            confidence_threshold=args.confidence_threshold)

        print(f"🏥 Clinical patient matching framework ready!", file=sys.stderr)
        print(f"Loaded {len(pms_lookup)} PMS lookup keys", file=sys.stderr)
        print(
            f"Confidence threshold: {args.confidence_threshold:.1%}", file=sys.stderr)

        if args.audit_only:
            print("Audit-only mode: No output file will be generated", file=sys.stderr)

        # Process DTX file (simplified for now)
        with open(args.dtx_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            total_records = sum(1 for _ in reader)

        print(
            f"Ready to process {total_records:,} DTX records", file=sys.stderr)
        print("✅ Clinical matching system initialized successfully!", file=sys.stderr)

    except Exception as e:
        logging.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
