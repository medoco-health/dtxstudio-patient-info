"""
DTX Patient Merge Application - Python Version
This script merges two patients together using their PMS IDs.
It reads patient ID pairs from a CSV file and calls the PMS OPP Web API.
"""

import csv
import sys
import os
import requests
import urllib3
import argparse
from urllib3.exceptions import InsecureRequestWarning
from collections import defaultdict

# Suppress SSL warnings for insecure requests
urllib3.disable_warnings(InsecureRequestWarning)

# API Configuration - Default values
DEFAULT_API_HOSTNAME = "localhost"
DEFAULT_API_PORT = "44389"


def validate_input_file(input_file):
    """Validate that the input file exists and is readable"""
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        return False

    if not os.path.isfile(input_file):
        print(f"Error: '{input_file}' is not a file.")
        return False

    try:
        with open(input_file, 'r') as f:
            f.read(1)  # Try to read one character
        return True
    except Exception as e:
        print(f"Error: Cannot read file '{input_file}': {e}")
        return False


def find_duplicate_pms_ids(input_file):
    """
    Find rows with duplicate PMS IDs (same prefix before dash).
    Returns a dictionary mapping base_id to list of (row_data, pms_id) tuples.
    """
    duplicates = defaultdict(list)

    try:
        with open(input_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                pms_id = row.get('pms_id', '').strip()
                if not pms_id:
                    continue

                # Extract base ID (prefix before dash)
                base_id = pms_id.split('-')[0]
                duplicates[base_id].append((row, pms_id))

    except Exception as e:
        print(f"Error reading file '{input_file}': {e}")
        return {}

    # Filter to only keep groups with multiple entries
    return {base_id: entries for base_id, entries in duplicates.items() if len(entries) > 1}


def merge_patients(input_file, bearer_token, hostname=DEFAULT_API_HOSTNAME, port=DEFAULT_API_PORT):
    """Process the CSV file and make API calls to merge patients"""
    api_url = f"https://{hostname}:{port}/api/message"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }

    merge_count = 0
    error_count = 0

    # Find duplicate PMS IDs first
    print("Scanning for duplicate PMS IDs...")
    duplicates = find_duplicate_pms_ids(input_file)

    if not duplicates:
        print("No duplicate PMS IDs found. Nothing to merge.")
        return True

    print(f"Found {len(duplicates)} groups of duplicate PMS IDs to process.")

    # Process each group of duplicates
    for base_id, entries in duplicates.items():
        print(f"\nProcessing duplicate group for base ID: {base_id}")

        # Find the target (no suffix) and sources (with suffix)
        target_entry = None
        source_entries = []

        for row_data, pms_id in entries:
            if pms_id == base_id:  # No suffix
                target_entry = (row_data, pms_id)
            else:  # Has suffix
                source_entries.append((row_data, pms_id))

        if not target_entry:
            print(
                f"Warning: No target patient found for base ID {base_id} (no unsuffixed ID). Skipping group.")
            continue

        if not source_entries:
            print(
                f"Warning: No source patients found for base ID {base_id} (no suffixed IDs). Skipping group.")
            continue

        target_patient_id = target_entry[1]

        # Merge each source into the target
        for source_row_data, src_patient_id in source_entries:
            # Prepare the JSON payload
            payload = {
                "header": {
                    "version": "1.0"
                },
                "message": {
                    "contract": "patient",
                    "operation": "merge.request",
                    "context": {},
                    "sourcePatientId": src_patient_id,
                    "targetPatientId": target_patient_id
                }
            }

            try:
                # Make the API call
                response = requests.put(
                    api_url,
                    headers=headers,
                    json=payload,
                    verify=False,  # Equivalent to --insecure in curl
                    timeout=30
                )

                # Log the response
                log_entry = f"Merge: {src_patient_id} -> {target_patient_id}\n"
                log_entry += f"Status: {response.status_code}\n"
                log_entry += f"Response: {response.text}\n"
                log_entry += "-" * 50 + "\n"

                with open("merge_log.txt", "a") as log_file:
                    log_file.write(log_entry)

                if response.status_code == 200:
                    merge_count += 1
                    print(
                        f"✓ Successfully merged patient {src_patient_id} -> {target_patient_id}")
                else:
                    error_count += 1
                    print(
                        f"✗ Failed to merge patient {src_patient_id} -> {target_patient_id} (Status: {response.status_code})")

            except requests.RequestException as e:
                error_count += 1
                error_msg = f"API call failed for {src_patient_id} -> {target_patient_id}: {str(e)}\n"

                with open("merge_error_log.txt", "a") as error_file:
                    error_file.write(error_msg)

                print(
                    f"✗ API call failed for {src_patient_id} -> {target_patient_id}: {e}")

    print(f"\nProcessing complete!")
    print(f"Successful merges: {merge_count}")
    print(f"Failed merges: {error_count}")
    print(f"Check merge_log.txt and merge_error_log.txt for detailed logs.")

    return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Merge duplicate patients using DTX API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dtxstudio-patient-merge -t your_bearer_token input.csv 
  dtxstudio-patient-merge --token abc123token --hostname 192.168.1.100 --port 26854 updated_patients.csv
        """
    )

    parser.add_argument('input_file', help='Path to the CSV file containing patient data')
    parser.add_argument('-t', '--token', required=True, help='Bearer token for API authentication')
    parser.add_argument('--hostname', default=DEFAULT_API_HOSTNAME, help=f'API hostname (default: {DEFAULT_API_HOSTNAME})')
    parser.add_argument('--port', default=DEFAULT_API_PORT, help=f'API port (default: {DEFAULT_API_PORT})')

    args = parser.parse_args()

    # Validate inputs
    if not args.input_file:
        print("Error: Input file name is required.")
        sys.exit(1)

    if not args.token:
        print("Error: Bearer token is required.")
        sys.exit(1)

    if not validate_input_file(args.input_file):
        sys.exit(1)

    # Process the merge requests
    success = merge_patients(args.input_file, args.token, args.hostname, args.port)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
