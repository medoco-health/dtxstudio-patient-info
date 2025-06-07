#!/usr/bin/env python3
"""
Clinical Patient Info Updater - Main Entrypoint

A clinical informatics-based patient matching system for updating DTX patient
records with PMS data using evidence-based matching algorithms.

This is the main entrypoint for the clinical matching system.
"""

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .core.patient_matcher import ClinicalPatientMatcher
from .core.matching_strategies import SessionStatistics
from .utils.normalizers import normalize_string, normalize_date, normalize_gender
from .utils.key_builders import create_composite_keys
from .utils.italian_cf import (
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
            keys = create_composite_keys(family_name, given_name, corrected_sex, dob)

            # Store under all keys for comprehensive matching
            for key_type, key in keys.items():
                if key not in pms_lookup:
                    pms_lookup[key] = pms_data
                elif isinstance(pms_lookup[key], dict):
                    # Convert to list for multiple candidates
                    pms_lookup[key] = [pms_lookup[key], pms_data]
                elif isinstance(pms_lookup[key], list):
                    pms_lookup[key].append(pms_data)

    logging.info(f"Loaded {len(set(d.get('custom_identifier') for d in pms_lookup.values() if isinstance(d, dict)))} unique PMS records")
    return pms_lookup


def process_dtx_file_clinical(dtx_file: str, 
                            pms_lookup: Dict[str, dict], 
                            output_file: Optional[str] = None,
                            confidence_threshold: float = 0.70) -> SessionStatistics:
    """
    Process DTX file using clinical matching algorithms.
    
    Args:
        dtx_file: Path to DTX CSV file
        pms_lookup: PMS lookup dictionary
        output_file: Output file path (stdout if None)
        confidence_threshold: Minimum confidence for automatic matching
        
    Returns:
        Session statistics
    """
    matcher = ClinicalPatientMatcher(confidence_threshold=confidence_threshold)
    manual_review_queue = []
    
    logging.info(f"Processing DTX file: {dtx_file}")
    
    # Open output
    output_handle = open(output_file, 'w', newline='', encoding='utf-8') if output_file else sys.stdout
    
    try:
        with open(dtx_file, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames or []
            writer = csv.DictWriter(output_handle, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                # Attempt clinical matching
                match_result = matcher.match_patient(row, pms_lookup)
                
                if match_result.match_found:
                    if match_result.requires_manual_review:
                        # ...existing code...
                        manual_review_queue.append({
                            'dtx_record': row,
                            'match_result': match_result,
                            'reason': f"Confidence {match_result.confidence_score:.1%} below threshold"
                        })
                        
                        # Log for manual review
                        log_prefix = []
                        if match_result.is_gender_mismatch:
                            log_prefix.append("GENDER MISMATCH")
                        if match_result.is_date_correction:
                            log_prefix.append("DATE CORRECTION")
                        if match_result.is_name_flip:
                            log_prefix.append("NAME FLIP")
                        if match_result.is_partial_match:
                            log_prefix.append("PARTIAL NAME MATCH")
                        if match_result.is_pms_gender_error:
                            log_prefix.append("CODICE_FISCALE_GENDER_ERROR")
                        
                        prefix_str = " - ".join(log_prefix)
                        if prefix_str:
                            prefix_str += " - "
                        
                        logging.warning(
                            f"MANUAL_REVIEW_REQUIRED - {prefix_str}"
                            f"Confidence: {match_result.confidence_score:.1%} - "
                            f"{row.get('given_name', '')} {row.get('family_name', '')} "
                            f"(Match: {match_result.match_type.value})"
                        )
                    else:
                        # Apply automatic update
                        pms_data = match_result.pms_data
                        if pms_data is None:
                            continue
                            
                        if hasattr(pms_data, 'to_dict'):
                            pms_data_dict = pms_data.to_dict()
                        elif isinstance(pms_data, dict):
                            pms_data_dict = pms_data
                        else:
                            continue
                        
                        # Update DTX record
                        row['family_name'] = pms_data_dict.get('last_name', row.get('family_name', ''))
                        row['given_name'] = pms_data_dict.get('first_name', row.get('given_name', ''))
                        row['sex'] = pms_data_dict.get('gender', row.get('sex', ''))
                        row['pms_id'] = pms_data_dict.get('custom_identifier', row.get('pms_id', ''))
                        
                        # Log successful update
                        log_prefix = []
                        if match_result.is_gender_mismatch:
                            log_prefix.append("GENDER MISMATCH")
                        if match_result.is_date_correction:
                            log_prefix.append("DATE CORRECTION")
                        if match_result.is_name_flip:
                            log_prefix.append("NAME FLIP")
                        if match_result.is_partial_match:
                            log_prefix.append("PARTIAL NAME MATCH")
                        if match_result.is_pms_gender_error:
                            log_prefix.append("CODICE_FISCALE_GENDER_ERROR")
                        
                        prefix_str = " - ".join(log_prefix)
                        if prefix_str:
                            prefix_str += " - "
                        
                        logging.info(
                            f"UPDATED - {prefix_str}"
                            f"Confidence: {match_result.confidence_score:.1%} - "
                            f"{pms_data_dict.get('first_name', '')} {pms_data_dict.get('last_name', '')} "
                            f"(Match: {match_result.match_type.value})"
                        )
                
                # Write row (updated or unchanged)
                writer.writerow(row)
    
    finally:
        if output_file:
            output_handle.close()
    
    # Generate clinical audit report
    generate_clinical_audit_report(matcher.get_session_statistics(), manual_review_queue)
    
    return matcher.get_session_statistics()


def generate_clinical_audit_report(stats: SessionStatistics, manual_review_queue: List[dict]):
    """Generate comprehensive clinical audit report."""
    print("\n" + "="*70, file=sys.stderr)
    print("CLINICAL PATIENT MATCHING AUDIT REPORT", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    print(f"\nOVERALL STATISTICS:", file=sys.stderr)
    print(f"Total records processed: {stats.total_processed:,}", file=sys.stderr)
    print(f"Automatic matches: {stats.auto_matched:,} ({stats.get_auto_match_rate():.1%})", file=sys.stderr)
    print(f"Manual review required: {stats.manual_review_required:,} ({stats.manual_review_required/stats.total_processed if stats.total_processed > 0 else 0:.1%})", file=sys.stderr)
    print(f"No matches found: {stats.no_matches:,} ({stats.no_matches/stats.total_processed if stats.total_processed > 0 else 0:.1%})", file=sys.stderr)
    
    print(f"\nCONFIDENCE LEVEL DISTRIBUTION:", file=sys.stderr)
    print(f"  Gold standard (100%): {stats.gold_standard_matches:,}", file=sys.stderr)
    print(f"  High confidence (95-99%): {stats.high_confidence_matches:,}", file=sys.stderr)
    print(f"  Moderate confidence (80-95%): {stats.moderate_confidence_matches:,}", file=sys.stderr)
    print(f"  Acceptable confidence (70-80%): {stats.acceptable_confidence_matches:,}", file=sys.stderr)
    
    print(f"\nCORRECTION TYPE DISTRIBUTION:", file=sys.stderr)
    print(f"  Gender corrections: {stats.gender_corrections:,}", file=sys.stderr)
    print(f"  Date corrections: {stats.date_corrections:,}", file=sys.stderr)
    print(f"  Name flips corrected: {stats.name_flips:,}", file=sys.stderr)
    print(f"  Partial name matches: {stats.partial_name_matches:,}", file=sys.stderr)
    print(f"  PMS gender errors corrected: {stats.pms_gender_errors:,}", file=sys.stderr)
    
    if manual_review_queue:
        print(f"\nMANUAL REVIEW QUEUE ({len(manual_review_queue)} items):", file=sys.stderr)
        print("-" * 50, file=sys.stderr)
        for i, item in enumerate(manual_review_queue[:10], 1):
            dtx = item['dtx_record']
            result = item['match_result']
            print(f"{i:2d}. {dtx.get('given_name', ''):<15} {dtx.get('family_name', ''):<15} | "
                  f"Match: {result.match_type.value:<20} | "
                  f"Confidence: {result.confidence_score:.1%}", file=sys.stderr)
        
        if len(manual_review_queue) > 10:
            print(f"... and {len(manual_review_queue) - 10} more items", file=sys.stderr)


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
    parser.add_argument('-o', '--output', help='Output CSV file (default: stdout)')
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

        print(f"🏥 Clinical patient matching framework ready!", file=sys.stderr)
        print(f"Loaded {len(pms_lookup)} PMS lookup keys", file=sys.stderr)
        print(f"Confidence threshold: {args.confidence_threshold:.1%}", file=sys.stderr)

        if args.audit_only:
            print("Audit-only mode: No output file will be generated", file=sys.stderr)

        # Process DTX file  
        output_file = None if args.audit_only else args.output
        stats = process_dtx_file_clinical(
            args.dtx_file, 
            pms_lookup, 
            output_file,
            args.confidence_threshold
        )

        # Final summary
        print(f"\n🏥 Clinical processing complete!", file=sys.stderr)
        print(f"Match rate: {stats.get_match_rate():.1%} | "
              f"Auto-match rate: {stats.get_auto_match_rate():.1%}", file=sys.stderr)

    except Exception as e:
        logging.error(f"Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()