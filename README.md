# DTX Studio Patient Info Updater v2

A clinical informatics-based patient matching system for updating DTX patient records with PMS data using evidence-based matching algorithms.

There is another rewrite of this tool in develop, refactored logistically to better be able to manage matching, but it is still incomplete.

## 🏥 Clinical Features

- **Hierarchical Matching**: 9 evidence-based strategies (55%-100% confidence)
- **Italian Healthcare Support**: Codice Fiscale validation and gender correction
- **Clinical Audit Trails**: HIPAA-compliant logging and reporting
- **Manual Review Queues**: Borderline matches flagged for human review
- **Quality Metrics**: Match rates, correction types, confidence distributions
- **Fuzzy Date Matching**: OCR error handling for date discrepancies
- **Name Flip Detection**: First ↔ last name swap correction
- **Partial Name Matching**: BIS/TRIS suffix handling

## 📊 CSV File Format Requirements

### DTX CSV Format (Input)
The DTX CSV file should contain patient records with these columns:

```csv
family_name,given_name,sex,dob,pms_id,practice_pms_id,dicom_id,middle_name
Rossi,Mario,M,1985-03-15,,,12345,
Smith,Jane,F,1990-07-22,,,67890,A
```

**Required DTX Columns:**
- `family_name` - Patient's last name
- `given_name` - Patient's first name  
- `sex` - Gender (M/F/MALE/FEMALE)
- `dob` - Date of birth (YYYY-MM-DD format preferred)

**Optional DTX Columns:**
- `pms_id` - PMS identifier (will be updated by matching)
- `practice_pms_id` - Practice-specific PMS ID
- `dicom_id` - DICOM identifier
- `middle_name` - Middle name or initial

### PMS CSV Format (Reference Data)
The PMS CSV file should contain reference patient data with these columns:

```csv
custom_identifier,first_name,last_name,gender,dob,middle_initial,ssn
12345,Mario,Rossi,MALE,1985-03-15,,RSSMRA85C15H501Z
67890,Jane,Smith,FEMALE,1990-07-22,A,SMTJNA90L62Z404Y
```

**Required PMS Columns:**
- `custom_identifier` - Unique PMS patient ID
- `first_name` - Patient's first name
- `last_name` - Patient's last name
- `gender` - Gender (MALE/FEMALE/M/F)
- `dob` - Date of birth (YYYY-MM-DD format preferred)

**Optional PMS Columns:**
- `middle_initial` - Middle initial
- `ssn` - Italian Codice Fiscale (used for gender validation)

### PMS Database Export Example

If you're exporting from a PMS database, here's a sample SQL query:

```sql
-- Export patients from PMS database to CSV format
COPY (
    SELECT 
        p.custom_identifier,
        p.first_name,
        p.last_name,
        CASE 
            WHEN gt.permanent_label ILIKE 'male%' THEN 'MALE'
            WHEN gt.permanent_label ILIKE 'female%' THEN 'FEMALE'
            ELSE UPPER(gt.permanent_label)
        END as gender,
        p.dob,
        p.middle_initial,
        p.ssn
    FROM patients p
    LEFT JOIN gender_types gt ON gt.type_id = p.gender_id
    WHERE p.active = true
      AND p.dob IS NOT NULL
      AND p.first_name IS NOT NULL
      AND p.last_name IS NOT NULL
    ORDER BY p.last_name, p.first_name
) TO '/tmp/pms_export.csv' 
WITH CSV HEADER;
```

## 🚀 Installation & Usage

### Installation
```bash
# Install the package
pip install -e .

# With development dependencies  
pip install -e ".[dev]"
```

### Command Line Usage
```bash
# Basic usage
clinical-patient-updater dtx.csv pms.csv -o updated.csv

# With custom confidence threshold
clinical-patient-updater dtx.csv pms.csv --confidence-threshold 0.85 --verbose

# Audit-only mode (no output file)
clinical-patient-updater dtx.csv pms.csv --audit-only

# Legacy system (preserved)
patient-info-updater dtx.csv pms.csv -o updated.csv
```

### Clinical Confidence Levels
- **Gold Standard (100%)**: Exact match on all fields
- **High Confidence (95-99%)**: Exact match with minor gender variations
- **Moderate Confidence (80-95%)**: Name flips or partial matches
- **Acceptable Confidence (70-80%)**: Fuzzy date matching
- **Manual Review (<70%)**: Requires human verification

## 🏗️ Architecture

```
dtxstudio_patient_info/
├── main.py                     # Clean CLI entrypoint
├── core/
│   ├── controller.py           # Workflow orchestration
│   ├── clinical_service.py     # Business logic
│   ├── reporting_service.py    # Audit reports
│   ├── patient_matcher.py      # Core matching engine
│   ├── data_models.py          # Data structures & types
│   └── confidence_scoring.py   # Confidence calculations
└── utils/                      # Utility functions
```

## 📋 Clinical Audit Reports

The system generates comprehensive audit trails:

```
CLINICAL PATIENT MATCHING AUDIT REPORT
======================================================================

OVERALL STATISTICS:
Total records processed: 1,234
Automatic matches: 1,156 (93.7%)
Manual review required: 45 (3.6%)
No matches found: 33 (2.7%)

CONFIDENCE LEVEL DISTRIBUTION:
  Gold standard (100%): 892
  High confidence (95-99%): 264
  Moderate confidence (80-95%): 45
  Acceptable confidence (70-80%): 33

CORRECTION TYPE DISTRIBUTION:
  Gender corrections: 23
  Date corrections: 12
  Name flips corrected: 8
  Partial name matches: 15
  PMS gender errors corrected: 5
```

## 🧪 Testing

```bash
# Test the framework
test-clinical-framework

# Run with sample data
clinical-patient-updater examples/dtx_sample.csv examples/pms_sample.csv --verbose
```

## 📚 References

- Fellegi-Sunter Model for record linkage
- Grannis et al. (2019): "Analysis of identifier performance for patient matching"
- Karimi et al. (2011): "Patient name matching in healthcare"
- HL7 FHIR Patient Matching specifications

# dtxstudio-patient-info v1
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