#!/usr/bin/env python3
"""
Clinical Patient Info Updater - Main Entrypoint

A clinical informatics-based patient matching system for updating DTX patient
records with PMS data using evidence-based matching algorithms.

This is the main entrypoint for the clinical matching system.
"""

import argparse
import logging
import sys

from dtxstudio_patient_info.core.controller import ClinicalMatchingController


def setup_logging(verbose: bool = False, log_file: str = "clinical_matching.log"):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = '%(asctime)s - %(levelname)s - %(message)s'

    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            # Only add stderr handler for critical errors
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    # Set stderr handler to only show ERROR and CRITICAL
    stderr_handler = logging.getLogger().handlers[-1]
    stderr_handler.setLevel(logging.ERROR)


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
    parser.add_argument('--log-file', default='clinical_matching.log',
                        help='Log file path (default: clinical_matching.log)')
    parser.add_argument('--audit-only', action='store_true',
                        help='Generate audit report only, no output file')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose, args.log_file)

    # Determine output file
    output_file = None if args.audit_only else args.output

    # Create controller and execute workflow
    controller = ClinicalMatchingController(
        confidence_threshold=args.confidence_threshold)

    success = controller.execute_matching_workflow(
        dtx_file=args.dtx_file,
        pms_file=args.pms_file,
        output_file=output_file,
        generate_audit=True
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
