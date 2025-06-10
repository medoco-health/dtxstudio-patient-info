"""
File: entrypoint.py
Author: amagni@medoco.health
Date: 2025-06-10
"""


import argparse
import logging
import sys

from dtxstudio_patient_info1.controller import load_pms_data, process_dtx_file


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

    # Configure logging level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    
    # Configure logging to go to stdout when CSV goes to file, stderr when CSV goes to stdout
    log_output = sys.stdout if args.output else sys.stderr
    
    # Create a custom handler that outputs to the appropriate stream
    handler = logging.StreamHandler(log_output)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(handler)
    
    # Clear any existing handlers to avoid duplicates
    logger.handlers = [handler]
    
    # Disable propagation to prevent duplicate messages
    logger.propagate = False

    if args.verbose:
        logging.info(f"DTX file: {args.dtx_file}")
        logging.info(f"PMS file: {args.pms_file}")
        logging.info(f"Output file: {args.output}")
        logging.info("")

    try:
        # Load PMS data for lookup
        logging.info("Loading PMS reference data...")
        pms_lookup = load_pms_data(args.pms_file)

        # Process DTX file and create updated output
        logging.info("Processing DTX file...")
        process_dtx_file(args.dtx_file, pms_lookup, args.output)

        logging.info("Done!")
    
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user (Ctrl+C)", file=sys.stderr)
        print("Partial results may have been written to output file.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
