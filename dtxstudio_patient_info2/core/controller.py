"""
Clinical Patient Matching Controller

Controller for orchestrating clinical patient matching operations.
Coordinates between services and handles high-level workflow.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from .clinical_service import ClinicalMatchingService
from .reporting_service import ClinicalReportingService


class ClinicalMatchingController:
    """Controller for clinical patient matching operations."""

    def __init__(self, confidence_threshold: float = 0.70):
        """
        Initialize the controller.

        Args:
            confidence_threshold: Minimum confidence for automatic matching
        """
        self.confidence_threshold = confidence_threshold
        self.service = ClinicalMatchingService(confidence_threshold)
        self.reporting = ClinicalReportingService()

    def execute_matching_workflow(self,
                                  dtx_file: str,
                                  pms_file: str,
                                  output_file: Optional[str] = None,
                                  generate_audit: bool = True) -> bool:
        """
        Execute the complete clinical matching workflow.

        Args:
            dtx_file: Path to DTX CSV file
            pms_file: Path to PMS CSV file
            output_file: Output CSV file path (None for no output)
            generate_audit: Whether to generate audit report

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate input files
            if not self._validate_input_files(dtx_file, pms_file):
                return False

            # Load PMS data
            logging.info("🏥 Starting clinical patient matching workflow")
            pms_lookup = self.service.load_pms_data(pms_file)

            # Log readiness (only to log file)
            logging.info("🏥 Clinical patient matching framework ready!")
            logging.info(f"Loaded {len(pms_lookup)} PMS lookup keys")
            logging.info(f"Confidence threshold: {self.confidence_threshold:.1%}")

            if output_file is None:
                logging.info("Audit-only mode: No output file will be generated")

            # Process DTX file
            stats = self.service.process_dtx_file(
                dtx_file, pms_lookup, output_file)

            # Generate reports
            if generate_audit:
                manual_review_queue = self.service.get_manual_review_queue()
                self.reporting.generate_audit_report(
                    stats, manual_review_queue)
                self.reporting.print_session_summary(stats)

            return True

        except Exception as e:
            logging.exception(e)
            logging.error(f"Clinical matching workflow failed: {e}")
            return False

    def _validate_input_files(self, dtx_file: str, pms_file: str) -> bool:
        """Validate that input files exist."""
        if not Path(dtx_file).exists():
            print(f"Error: DTX file not found: {dtx_file}", file=sys.stderr)
            return False

        if not Path(pms_file).exists():
            print(f"Error: PMS file not found: {pms_file}", file=sys.stderr)
            return False

        return True
