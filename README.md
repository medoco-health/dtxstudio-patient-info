# dtxstudio-patient-info
Tools to clean up Patient Info in DTX Studio

## Overview

This repository contains tools to match and update patient information between DTX Studio and Practice Management System (PMS) data. The main tool is `patient_info_updater.py`, which matches patients based on personal information and updates DTX records with correct PMS identifiers and data.

## Usage

### Basic Usage

```bash
python patient_info_updater.py <dtx_file> <pms_file> [-o output_file] [--verbose]
```

### Examples

```bash
# Output to stdout
python patient_info_updater.py dtx_patients.csv pms_patients.csv

# Output to file
python patient_info_updater.py dtx_patients.csv pms_patients.csv -o updated_patients.csv

# Verbose output with detailed logging
python patient_info_updater.py dtx_patients.csv pms_patients.csv -o updated_patients.csv --verbose
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
