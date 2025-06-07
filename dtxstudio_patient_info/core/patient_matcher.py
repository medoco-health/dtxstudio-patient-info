"""
Clinical Patient Matcher - Core matching engine.

This module implements the main patient matching algorithm following
clinical informatics best practices and evidence-based approaches.
"""

import logging
from typing import Dict, List, Optional, Any
from .data_models import (
    MatchType,
    ConfidenceLevel,
    PatientRecord,
    MatchResult,
    MatchingStrategy,
    SessionStatistics
)
from .confidence_scoring import ConfidenceCalculator
from ..utils.normalizers import normalize_string, normalize_date, normalize_gender
from ..utils.key_builders import create_composite_keys
from ..utils.italian_cf import extract_gender_from_codice_fiscale, is_codice_fiscale_gender_consistent
from ..utils.date_similarity import is_fuzzy_date_match

# Import the actual strategy implementations
from ..strategies.deterministic import (
    GoldStandardStrategy, ExactNamesGenderLooseStrategy, FlippedNamesExactStrategy,
    FlippedNamesGenderLooseStrategy, PartialNamesExactStrategy, PartialNamesGenderLooseStrategy
)
from ..strategies.probabilistic import (
    ExactNamesFuzzyDateStrategy, FlippedNamesFuzzyDateStrategy, PartialNamesFuzzyDateStrategy
)


class ClinicalPatientMatcher:
    """
    Evidence-based patient matching system for clinical environments.

    This class implements hierarchical patient matching strategies based on
    clinical informatics research and healthcare data quality standards.

    References:
    - Grannis et al. (2019): "Analysis of identifier performance for patient matching"
    - Karimi et al. (2011): "Patient name matching in healthcare" 
    - Just et al. (2016): "Record linkage software in the public domain"
    """

    def __init__(self, confidence_threshold: float = 0.70, enable_partial_matching: bool = True):
        """
        Initialize the clinical patient matcher.

        Args:
            confidence_threshold: Minimum confidence for automatic matching (default: 0.70)
            enable_partial_matching: Enable partial name matching for suffixes (default: True)
        """
        self.confidence_threshold = confidence_threshold
        self.enable_partial_matching = enable_partial_matching
        self.confidence_calculator = ConfidenceCalculator()

        # Initialize actual strategy instances
        self.strategy_instances = self._initialize_strategy_instances()

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Session statistics
        self.session_stats = SessionStatistics()

    def _initialize_strategy_instances(self) -> List:
        """Initialize the actual strategy instances in priority order."""
        strategy_instances = [
            GoldStandardStrategy(),
            ExactNamesGenderLooseStrategy(),
            FlippedNamesExactStrategy(),
            FlippedNamesGenderLooseStrategy(),
            PartialNamesExactStrategy(),
            PartialNamesGenderLooseStrategy(),
            ExactNamesFuzzyDateStrategy(),
            FlippedNamesFuzzyDateStrategy(),  # This will now be used!
            PartialNamesFuzzyDateStrategy()
        ]
        
        # Filter based on settings
        if not self.enable_partial_matching:
            strategy_instances = [s for s in strategy_instances 
                                if 'Partial' not in s.__class__.__name__]
        
        return strategy_instances



    def match_patient(self, dtx_record: dict, pms_lookup: Dict[str, Any]) -> MatchResult:
        """
        Match a DTX patient record against PMS data using hierarchical strategies.

        Args:
            dtx_record: DTX patient record dictionary
            pms_lookup: PMS lookup dictionary with normalized keys

        Returns:
            MatchResult with match details and confidence scoring
        """
        self.session_stats.total_processed += 1

        # Convert dict to PatientRecord for strategy execution
        patient_record = PatientRecord(
            family_name=dtx_record.get('family_name', ''),
            given_name=dtx_record.get('given_name', ''),
            sex=dtx_record.get('sex', ''),
            dob=dtx_record.get('dob', ''),
            pms_id=dtx_record.get('pms_id'),
            practice_pms_id=dtx_record.get('practice_pms_id'),
            dicom_id=dtx_record.get('dicom_id'),
            middle_name=dtx_record.get('middle_name')
        )

        # Try strategy instances in priority order
        for strategy_instance in self.strategy_instances:
            match_result = strategy_instance.execute(patient_record, pms_lookup)

            if match_result and match_result.match_found:
                # Update session statistics
                self._update_session_stats(match_result)
                return match_result

        # No match found
        self.session_stats.no_matches += 1
        return MatchResult(
            match_found=False,
            pms_data=None,
            confidence_score=0.0,
            match_type=MatchType.NO_MATCH,
            requires_manual_review=False,
            match_details={'reason': 'No matching strategy succeeded'}
        )



    def _update_session_stats(self, match_result: MatchResult):
        """Update session statistics based on match result."""
        if match_result.requires_manual_review:
            self.session_stats.manual_review_required += 1
        else:
            self.session_stats.auto_matched += 1

        # Update confidence level stats
        confidence_level = match_result.get_confidence_level()
        if confidence_level == ConfidenceLevel.GOLD_STANDARD:
            self.session_stats.gold_standard_matches += 1
        elif confidence_level == ConfidenceLevel.HIGH_CONFIDENCE:
            self.session_stats.high_confidence_matches += 1
        elif confidence_level == ConfidenceLevel.MODERATE_CONFIDENCE:
            self.session_stats.moderate_confidence_matches += 1
        elif confidence_level == ConfidenceLevel.ACCEPTABLE_CONFIDENCE:
            self.session_stats.acceptable_confidence_matches += 1

        # Update correction type stats
        if match_result.is_gender_mismatch:
            self.session_stats.gender_corrections += 1
        if match_result.is_date_correction:
            self.session_stats.date_corrections += 1
        if match_result.is_name_flip:
            self.session_stats.name_flips += 1
        if match_result.is_partial_match:
            self.session_stats.partial_name_matches += 1
        if match_result.is_pms_gender_error:
            self.session_stats.pms_gender_errors += 1

    def get_session_statistics(self) -> SessionStatistics:
        """Get current session statistics."""
        return self.session_stats

    def reset_session_statistics(self):
        """Reset session statistics for a new matching session."""
        self.session_stats = SessionStatistics()
