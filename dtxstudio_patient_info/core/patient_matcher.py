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

        # Initialize matching strategies in priority order
        self.strategies = self._initialize_strategies()

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Session statistics
        self.session_stats = SessionStatistics()

    def _initialize_strategies(self) -> List[MatchingStrategy]:
        """Initialize the hierarchical matching strategies."""
        return [
            MatchingStrategy(
                name="GOLD_STANDARD",
                rules=["family_name_exact", "given_name_exact",
                       "dob_exact", "gender_exact"],
                confidence=1.0,
                priority=1,
                description="Perfect match on all fields"
            ),
            MatchingStrategy(
                name="EXACT_GENDER_LOOSE",
                rules=["family_name_exact", "given_name_exact",
                       "dob_exact", "gender_loose"],
                confidence=0.98,
                priority=2,
                description="Names and DOB exact, gender differs"
            ),
            MatchingStrategy(
                name="FLIPPED_EXACT",
                rules=["family_name_flipped_exact",
                       "given_name_flipped_exact", "dob_exact", "gender_exact"],
                confidence=0.97,
                priority=3,
                description="Names flipped but all fields exact"
            ),
            MatchingStrategy(
                name="FLIPPED_GENDER_LOOSE",
                rules=["family_name_flipped_exact",
                       "given_name_flipped_exact", "dob_exact", "gender_loose"],
                confidence=0.90,
                priority=4,
                description="Names flipped, DOB exact, gender differs"
            ),
            MatchingStrategy(
                name="PARTIAL_EXACT",
                rules=["family_name_partial", "given_name_partial",
                       "dob_exact", "gender_exact"],
                confidence=0.85,
                priority=5,
                description="Partial name match with exact DOB and gender"
            ),
            MatchingStrategy(
                name="PARTIAL_GENDER_LOOSE",
                rules=["family_name_partial", "given_name_partial",
                       "dob_exact", "gender_loose"],
                confidence=0.75,
                priority=6,
                description="Partial name match with exact DOB, gender differs"
            ),
            MatchingStrategy(
                name="EXACT_FUZZY_DOB",
                rules=["family_name_exact", "given_name_exact",
                       "dob_fuzzy", "gender_exact"],
                confidence=0.72,
                priority=7,
                description="Names exact, fuzzy DOB match"
            ),
            MatchingStrategy(
                name="FLIPPED_FUZZY_DOB",
                rules=["family_name_flipped_exact",
                       "given_name_flipped_exact", "dob_fuzzy", "gender_loose"],
                confidence=0.65,
                priority=8,
                description="Names flipped with fuzzy DOB match"
            ),
            MatchingStrategy(
                name="PARTIAL_FUZZY_DOB",
                rules=["family_name_partial", "given_name_partial",
                       "dob_fuzzy", "gender_loose"],
                confidence=0.55,
                priority=9,
                description="Partial names with fuzzy DOB match"
            )
        ]

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

        # Extract core identifiers
        family_name = dtx_record.get('family_name', '')
        given_name = dtx_record.get('given_name', '')
        sex = dtx_record.get('sex', '')
        dob = dtx_record.get('dob', '')

        # Generate composite keys for matching
        keys = create_composite_keys(family_name, given_name, sex, dob)

        # Try strategies in priority order
        for strategy in self.strategies:
            match_result = self._evaluate_strategy(
                dtx_record, pms_lookup, strategy, keys)

            if match_result.match_found:
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

    def _evaluate_strategy(self,
                           dtx_record: dict,
                           pms_lookup: Dict[str, Any],
                           strategy: MatchingStrategy,
                           keys: dict) -> MatchResult:
        """Evaluate a specific matching strategy."""

        # Select appropriate key based on strategy
        match_key = self._select_match_key(strategy, keys)

        if match_key and match_key in pms_lookup:
            pms_data = pms_lookup[match_key]

            # Handle multiple candidates
            if isinstance(pms_data, list):
                pms_data = pms_data[0]  # Take first candidate for now

            # Calculate confidence with corrections
            corrections = self._identify_corrections(
                dtx_record, pms_data, strategy)
            adjusted_confidence = self.confidence_calculator.calculate_adjusted_confidence(
                strategy.confidence, corrections
            )

            # Check for manual review requirement
            requires_review = self.confidence_calculator.requires_manual_review(
                adjusted_confidence)

            return MatchResult(
                match_found=True,
                pms_data=PatientRecord(
                    **pms_data) if isinstance(pms_data, dict) else pms_data,
                confidence_score=adjusted_confidence,
                match_type=MatchType(strategy.name),
                requires_manual_review=requires_review,
                match_details={
                    'strategy': strategy.name,
                    'match_key': match_key,
                    'corrections': corrections,
                    'base_confidence': strategy.confidence
                },
                **corrections  # Unpack correction flags
            )

        # Strategy didn't find a match
        return MatchResult(
            match_found=False,
            pms_data=None,
            confidence_score=0.0,
            match_type=MatchType.NO_MATCH,
            requires_manual_review=False,
            match_details={'strategy_attempted': strategy.name}
        )

    def _select_match_key(self, strategy: MatchingStrategy, keys: dict) -> Optional[str]:
        """Select the appropriate match key based on strategy."""
        strategy_name = strategy.name.upper()

        if "FLIPPED" in strategy_name:
            if "GENDER_LOOSE" in strategy_name or "FUZZY_DOB" in strategy_name:
                return keys.get('flipped_loose')
            else:
                return keys.get('flipped_exact')
        elif "PARTIAL" in strategy_name:
            # Partial matching requires special handling
            return None  # Will be handled separately
        elif "FUZZY_DOB" in strategy_name:
            return keys.get('name_only')  # For fuzzy date matching
        elif "GENDER_LOOSE" in strategy_name:
            return keys.get('loose')
        else:
            return keys.get('exact')

    def _identify_corrections(self,
                              dtx_record: dict,
                              pms_data: dict,
                              strategy: MatchingStrategy) -> dict:
        """Identify what corrections are needed."""
        corrections = {
            'is_gender_mismatch': False,
            'is_date_correction': False,
            'is_name_flip': False,
            'is_partial_match': False,
            'is_pms_gender_error': False
        }

        dtx_sex = normalize_gender(dtx_record.get('sex', ''))
        pms_sex = normalize_gender(pms_data.get('gender', ''))
        dtx_dob = normalize_date(dtx_record.get('dob', ''))
        pms_dob = normalize_date(pms_data.get('dob', ''))

        # Check for gender mismatch
        if dtx_sex and pms_sex and dtx_sex != pms_sex:
            corrections['is_gender_mismatch'] = True

            # Check if PMS has codice fiscale gender error
            cf = pms_data.get('ssn', '')
            if cf and not is_codice_fiscale_gender_consistent(cf, pms_sex):
                corrections['is_pms_gender_error'] = True

        # Check for date correction (fuzzy matching)
        if dtx_dob and pms_dob and dtx_dob != pms_dob:
            if is_fuzzy_date_match(dtx_dob, pms_dob):
                corrections['is_date_correction'] = True

        # Check for name flip
        if "FLIPPED" in strategy.name.upper():
            corrections['is_name_flip'] = True

        # Check for partial match
        if "PARTIAL" in strategy.name.upper():
            corrections['is_partial_match'] = True

        return corrections

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
