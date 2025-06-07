# DTX Studio Patient Info Updater

A clinical informatics-based patient matching system for updating DTX patient records with PMS data using evidence-based matching algorithms.

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
│   ├── matching_strategies.py  # Algorithm definitions
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
