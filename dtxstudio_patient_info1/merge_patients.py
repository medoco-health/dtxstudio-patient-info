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
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for insecure requests
urllib3.disable_warnings(InsecureRequestWarning)


def print_banner():
    """Print the welcome banner"""
    print("*" * 55)
    print("*****Welcome to the DTX Patient Merge Application!*****")
    print("*" * 55)
    print()


def print_instructions():
    """Print instructions for the user"""
    print("*" * 57)
    print("*****      You will now be asked two questions:     *****")
    print("*****                                               *****")
    print("*****The file name that contains the old and new IDs*****")
    print("*****         and the PMS Bearer Token.             *****")
    print("*****       Both are REQUIRED to proceed.           *****")
    print("*" * 57)
    print()
    print()


def get_user_input():
    """Get input file name and bearer token from user"""
    input_file = input("Enter the input file name: ").strip()
    bearer_token = input("Enter the PMS Bearer Token: ").strip()

    return input_file, bearer_token


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


def merge_patients(input_file, bearer_token):
    """Process the CSV file and make API calls to merge patients"""
    api_url = "https://localhost:44389/api/message"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }

    merge_count = 0
    error_count = 0

    try:
        with open(input_file, 'r', newline='') as csvfile:
            # Read CSV with comma delimiter
            reader = csv.reader(csvfile, delimiter=',')

            for row_num, row in enumerate(reader, 1):
                if len(row) < 2:
                    print(
                        f"Warning: Row {row_num} does not have enough columns. Skipping.")
                    continue

                src_patient_id = row[0].strip()
                target_patient_id = row[1].strip()

                if not src_patient_id or not target_patient_id:
                    print(
                        f"Warning: Row {row_num} contains empty patient IDs. Skipping.")
                    continue

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
                    log_entry = f"Row {row_num}: {src_patient_id} -> {target_patient_id}\n"
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
                    error_msg = f"Row {row_num}: API call failed for {src_patient_id} -> {target_patient_id}: {str(e)}\n"

                    with open("merge_error_log.txt", "a") as error_file:
                        error_file.write(error_msg)

                    print(
                        f"✗ API call failed for {src_patient_id} -> {target_patient_id}: {e}")

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return False
    except Exception as e:
        print(f"Error processing file: {e}")
        return False

    print(f"\nProcessing complete!")
    print(f"Successful merges: {merge_count}")
    print(f"Failed merges: {error_count}")
    print(f"Check merge_log.txt and merge_error_log.txt for detailed logs.")

    return True


def main():
    """Main function"""
    print_banner()
    input("Press Enter to continue...")
    os.system('cls' if os.name == 'nt' else 'clear')

    print_instructions()
    input("Press Enter to continue...")
    os.system('cls' if os.name == 'nt' else 'clear')

    # Get user input
    input_file, bearer_token = get_user_input()

    # Validate inputs
    if not input_file:
        print("Error: Input file name is required.")
        sys.exit(1)

    if not bearer_token:
        print("Error: Bearer token is required.")
        sys.exit(1)

    if not validate_input_file(input_file):
        sys.exit(1)

    # Process the merge requests
    success = merge_patients(input_file, bearer_token)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
