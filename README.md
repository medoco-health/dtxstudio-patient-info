# dtxstudio-patient-info v1 and v2

Tools to clean up Patient Info in DTX Studio

## Overview

This repository contains tools to match, update, and merge patient information between DTX Studio and Practice Management System (PMS) data. The main tools are:

1. **`patient_info_updater.py`** - Matches patients based on personal information and updates DTX records with correct PMS identifiers and data
2. **`merge_patients.py`** - Merges duplicate patients with the same PMS ID prefix using the DTX API

There are two modules: 

## Installation

### Standard Installation (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd dtxstudio-patient-info

# Install the package
pip install .
```

### Development Installation

```bash
# Clone the repository
git clone <repository-url>
cd dtxstudio-patient-info

# Install in development mode
pip install -e .

# Or using Poetry (if available)
poetry install
```

### Dependencies

The package requires Python 3.9+ and will automatically install:

## Usage

After installation, the tools are available as command-line utilities:

### Patient Info Updater

```bash
# Using the installed package entry point
dtxstudio-patient-updater <dtx_file> <pms_file> [-o output_file] [--verbose]

# Or running the module directly (if not installed)
python -m dtxstudio_patient_info.entrypoint <dtx_file> <pms_file> [-o output_file] [--verbose]
```

### Patient Merger

```bash
# Using the installed package entry point  
dtxstudio-patient-merge <input_file> -t <bearer_token> [--hostname <hostname>] [--port <port>]

# Or running the module directly (if not installed)
python -m dtxstudio_patient_info.merge_patients <input_file> -t <bearer_token> [--hostname <hostname>] [--port <port>]
```

### Examples

#### Patient Info Updater Examples

```bash
# Output to stdout
dtxstudio-patient-updater dtx_patients.csv pms_patients.csv

# Output to file
dtxstudio-patient-updater dtx_patients.csv pms_patients.csv -o updated_patients.csv

# Verbose output with detailed logging
dtxstudio-patient-updater dtx_patients.csv pms_patients.csv -o updated_patients.csv --verbose
```

#### Patient Merger Examples

```bash
# Basic merge with default localhost:44389
dtxstudio-patient-merge updated_patients.csv -t your_bearer_token

# Merge with custom hostname and port
dtxstudio-patient-merge updated_patients.csv --token abc123token --hostname 192.168.1.100 --port 26854
```

## CSV File Formats

### DTX CSV File Format

The DTX CSV file should be generated from the **DTX Patient Import** feature in DTX Studio Core. The expected columns are:

| Column | Description | Required |
|--------|-------------|----------|
| `family_name` | Patient's last name | Yes |
| `given_name` | Patient's first name | Yes |
| `middle_name` | Patient's middle name/initial | No |
| `sex` | Patient's gender (M/F, Male/Female, etc.) | Yes |
| `dob` | Date of birth (various formats supported) | Yes |
| `pms_id` | PMS identifier (will be updated) | No |
| `practice_pms_id` | Practice PMS identifier (will be updated) | No |
| `dicom_id` | DICOM identifier (will be updated) | No |

**Note:** The script will update `pms_id`, `practice_pms_id`, and `dicom_id` fields with the matched `custom_identifier` from the PMS file. It will also correct any mismatched demographic data (names, gender, DOB) with the authoritative PMS data.

### PMS CSV File Format

The PMS CSV file should contain the authoritative patient data from your Practice Management System. The expected columns are:

| Column | Description | Required |
|--------|-------------|----------|
| `first_name` | Patient's first name | Yes |
| `last_name` | Patient's last name | Yes |
| `middle_initial` | Patient's middle name/initial | No |
| `gender` | Patient's gender | Yes |
| `dob` | Date of birth | Yes |
| `custom_identifier` | Unique patient identifier in PMS | Yes |
| `ssn` | Social Security Number/Codice Fiscale | No |

**Note:** If `ssn` contains an Italian Codice Fiscale, the script will validate and correct gender information based on the encoded gender in the Codice Fiscale.

## Supported Date Formats

The script supports multiple date formats and will normalize them to YYYY-MM-DD:

- `YYYY-MM-DD` (ISO format)
- `MM/DD/YYYY` (US format)
- `DD/MM/YYYY` (European format)
- `YYYY/MM/DD` (Alternative ISO format)

## Matching Logic

The script uses a sophisticated matching algorithm with multiple strategies:

1. **Exact Match**: Family name, given name, gender, and DOB all match exactly
2. **Loose Match**: Names and DOB match, but gender may differ
3. **Name Flip Match**: Handles cases where first/last names are swapped
4. **Partial Name Match**: PMS names are substrings of DTX names (handles suffixes like "BIS", "TRIS")
5. **Fuzzy Date Match**: Matches names exactly but allows for similar dates (handles OCR errors)

## Output and Logging

### Statistics

The script provides detailed statistics about the matching process:

- Total records processed
- Matches found
- Records updated vs. unchanged
- Gender corrections made
- Date corrections made
- Name flips corrected
- Partial name matches
- PMS gender errors corrected

### Logging Levels

- **INFO**: General processing information
- **WARNING**: Issues that need attention (gender mismatches, date corrections, etc.)
- **ERROR**: Critical errors that stop processing

Use `--verbose` flag to see detailed logging information.

## Special Features

### Gender Validation

If the PMS file contains Italian Codice Fiscale in the `ssn` field, the script will:
- Extract gender information from the Codice Fiscale
- Compare it with the recorded gender
- Use the Codice Fiscale gender if there's a mismatch
- Log any discrepancies for review

### Data Correction

The script not only matches records but also corrects:
- Inconsistent demographic data
- Gender mismatches
- Date formatting issues
- Name order problems
- Missing middle names/initials

## Error Handling

The script handles various error conditions:
- Missing or invalid CSV files
- Malformed date formats
- Missing required fields
- Encoding issues

All errors are logged with appropriate detail for troubleshooting.

## Patient Merger Tool

The `merge_patients.py` tool was developed to replace the original `dtx_merge_patients.bat` file provided by Medicim support. The batch file served as the starting point for understanding the DTX API merge operation and requirements.

### Original Batch File (`dtx_merge_patients.bat`)

The original Windows batch file from Medicim support:
- Required manual input of CSV file name and bearer token
- Used curl commands to call the DTX API
- Expected CSV format with two columns: `src_patient_id,target_patient_id`
- Merged patients one-by-one based on explicit source-target pairs

### Python Implementation Benefits

The Python version (`merge_patients.py`) improves upon the original by:

#### Intelligent Duplicate Detection
- Automatically scans CSV files for duplicate PMS IDs
- Groups patients by base ID (prefix before dash)
- Identifies target (no suffix) and source (suffixed) patients automatically

#### Enhanced User Experience
- Command-line argument parsing instead of interactive prompts
- Configurable hostname and port for different DTX environments
- Better error handling and logging
- Progress reporting during merge operations

#### Workflow Integration
- Works with output from `patient_info_updater.py`
- Handles the updated CSV format with `pms_id` column
- Only processes patients that actually have duplicates

#### Example Workflow

```bash
# Step 1: Update patient information and create corrected CSV
dtxstudio-patient-updater dtx_export.csv pms_data.csv -o updated_patients.csv

# Step 2: Merge duplicate patients found in the updated file
dtxstudio-patient-merge updated_patients.csv -t your_bearer_token --hostname your_dtx_server --port 26854
```

### Merge Logic

The merger identifies duplicates by:
1. Extracting the base ID (prefix before first dash) from each `pms_id`
2. Grouping patients with the same base ID
3. Setting the patient with no suffix as the target
4. Merging all suffixed variants into the target

For example, if you have patients with PMS IDs:
- `12345` (target)
- `12345-BIS` (source)  
- `12345-TRIS` (source)

The tool will merge `12345-BIS` and `12345-TRIS` into `12345`.