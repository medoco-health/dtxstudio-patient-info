"""
Clinical Patient Matching Service

Service layer for handling patient matching operations, data loading,
and processing workflows.
"""

import csv
import logging
from typing import Dict, List, Optional, Tuple, Union

from .patient_matcher import ClinicalPatientMatcher
from .matching_strategies import SessionStatistics
from ..utils.key_builders import create_composite_keys
from ..utils.italian_cf import (
    extract_gender_from_codice_fiscale,
    is_codice_fiscale_gender_consistent
)


class ClinicalMatchingService:
    """Service for clinical patient matching operations."""

    def __init__(self, confidence_threshold: float = 0.70):
        """
        Initialize the clinical matching service.

        Args:
            confidence_threshold: Minimum confidence for automatic matching
        """
        self.confidence_threshold = confidence_threshold
        self.matcher = ClinicalPatientMatcher(confidence_threshold)
        self.manual_review_queue: List[dict] = []

    def load_pms_data(self, pms_file: str) -> Dict[str, Union[dict, List[dict]]]:
        """
        Load PMS data with clinical matching key generation.

        Args:
            pms_file: Path to PMS CSV file

        Returns:
            Dictionary with normalized keys and PMS data
        """
        pms_lookup: Dict[str, Union[dict, List[dict]]] = {}

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
                corrected_sex, is_pms_gender_error = self._validate_gender_with_cf(
                    sex, ssn, given_name, family_name
                )

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
                self._store_pms_record(pms_lookup, keys, pms_data)

        unique_records = len(set(
            d.get('custom_identifier') for d in pms_lookup.values()
            if isinstance(d, dict)
        ))
        logging.info(f"Loaded {unique_records} unique PMS records")
        return pms_lookup

    def process_dtx_file(self,
                         dtx_file: str,
                         pms_lookup: Dict[str, Union[dict, List[dict]]],
                         output_file: Optional[str] = None) -> SessionStatistics:
        """
        Process DTX file using clinical matching algorithms.

        Args:
            dtx_file: Path to DTX CSV file
            pms_lookup: PMS lookup dictionary
            output_file: Output file path (stdout if None)

        Returns:
            Session statistics
        """
        logging.info(f"Processing DTX file: {dtx_file}")

        # Reset for new session
        self.manual_review_queue = []

        with open(dtx_file, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = list(reader.fieldnames or [])

            # Process records
            processed_records = []
            for row in reader:
                updated_row = self._process_dtx_record(row, pms_lookup)
                processed_records.append(updated_row)

        # Write output
        if output_file:
            self._write_output_file(output_file, fieldnames, processed_records)

        return self.matcher.get_session_statistics()

    def get_manual_review_queue(self) -> List[dict]:
        """Get the current manual review queue."""
        return self.manual_review_queue.copy()

    def _validate_gender_with_cf(self, sex: str, ssn: str, given_name: str, family_name: str) -> Tuple[str, bool]:
        """Validate and correct gender using Codice Fiscale."""
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

        return corrected_sex, is_pms_gender_error

    def _store_pms_record(self, pms_lookup: Dict[str, Union[dict, List[dict]]], keys: Dict[str, str], pms_data: dict):
        """Store PMS record under all matching keys."""
        for key_type, key in keys.items():
            if key not in pms_lookup:
                pms_lookup[key] = pms_data
            else:
                existing = pms_lookup[key]
                if isinstance(existing, dict):
                    # Convert to list for multiple candidates
                    pms_lookup[key] = [existing, pms_data]
                elif isinstance(existing, list):
                    existing.append(pms_data)

    def _process_dtx_record(self, row: dict, pms_lookup: Dict[str, Union[dict, List[dict]]]) -> dict:
        """Process a single DTX record."""
        # Attempt clinical matching - pass raw DTX dict
        match_result = self.matcher.match_patient(row, pms_lookup)

        if match_result.match_found:
            if match_result.requires_manual_review:
                self._handle_manual_review(row, match_result)
            else:
                self._apply_automatic_update(row, match_result)

        return row

    def _handle_manual_review(self, row: dict, match_result):
        """Handle records requiring manual review."""
        self.manual_review_queue.append({
            'dtx_record': row,
            'match_result': match_result,
            'reason': f"Confidence {match_result.confidence_score:.1%} below threshold"
        })

        # Log for manual review
        log_prefix = self._build_log_prefix(match_result)
        logging.warning(
            f"MANUAL_REVIEW_REQUIRED - {log_prefix}"
            f"Confidence: {match_result.confidence_score:.1%} - "
            f"{row.get('given_name', '')} {row.get('family_name', '')} "
            f"(Match: {match_result.match_type.value})"
        )

    def _apply_automatic_update(self, row: dict, match_result):
        """Apply automatic updates to DTX record."""
        pms_data = match_result.pms_data
        if pms_data is None:
            return

        if hasattr(pms_data, 'to_dict'):
            pms_data_dict = pms_data.to_dict()
        elif isinstance(pms_data, dict):
            pms_data_dict = pms_data
        else:
            return

        # Update DTX record with PMS data
        row['family_name'] = pms_data_dict.get(
            'last_name', row.get('family_name', ''))
        row['given_name'] = pms_data_dict.get(
            'first_name', row.get('given_name', ''))
        row['sex'] = pms_data_dict.get('gender', row.get('sex', ''))
        row['pms_id'] = pms_data_dict.get(
            'custom_identifier', row.get('pms_id', ''))

        # Log successful update
        log_prefix = self._build_log_prefix(match_result)
        logging.info(
            f"UPDATED - {log_prefix}"
            f"Confidence: {match_result.confidence_score:.1%} - "
            f"{pms_data_dict.get('first_name', '')} {pms_data_dict.get('last_name', '')} "
            f"(Match: {match_result.match_type.value})"
        )

    def _build_log_prefix(self, match_result) -> str:
        """Build log prefix based on match result flags."""
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
        return f"{prefix_str} - " if prefix_str else ""

    def _write_output_file(self, output_file: str, fieldnames: List[str], records: List[dict]):
        """Write processed records to output file."""
        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
