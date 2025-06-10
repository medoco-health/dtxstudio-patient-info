"""
Probabilistic matching strategies with moderate confidence scores.

These strategies handle fuzzy matching scenarios with confidence scores
typically requiring manual review in clinical environments.
"""

from typing import Dict, Any, Optional, List, Union
from ..core.data_models import MatchingStrategy, MatchResult, MatchType, PatientRecord
from ..utils.key_builders import create_name_only_key, create_flipped_name_only_key
from ..utils.normalizers import normalize_string, is_partial_name_match
from ..utils.date_similarity import is_fuzzy_date_match


class ExactNamesFuzzyDateStrategy(MatchingStrategy):
    """
    Exact names with fuzzy date matching.

    Confidence: 72% - Auto-match with date correction
    Use case: Names are reliable, but DOB has data entry errors
    """

    @property
    def name(self) -> str:
        return "Exact Names with Fuzzy Date"

    @property
    def confidence_score(self) -> float:
        return 0.72

    @property
    def match_type(self) -> MatchType:
        return MatchType.EXACT_FUZZY_DOB

    def execute(self, dtx_record: PatientRecord, pms_lookup: Dict[str, Any]) -> Optional[MatchResult]:
        name_key = create_name_only_key(
            dtx_record.family_name, dtx_record.given_name)

        if name_key in pms_lookup:
            candidates = pms_lookup[name_key]

            # Handle single candidate or list of candidates
            if isinstance(candidates, dict):
                candidates = [candidates]
            elif not isinstance(candidates, list):
                return None

            # Check each candidate for fuzzy date match
            for candidate in candidates:
                if is_fuzzy_date_match(dtx_record.dob, candidate.get('dob', '')):
                    # Additional check: gender should match for this strategy
                    if normalize_string(dtx_record.sex) == normalize_string(candidate.get('gender', '')):
                        return self._create_match_result(
                            candidate, dtx_record,
                            {
                                'strategy': 'exact_names_fuzzy_date',
                                'name_key': name_key,
                                'fuzzy_date_detected': True,
                                'original_dtx_dob': dtx_record.dob,
                                'matched_pms_dob': candidate.get('dob', '')
                            }
                        )

        return None

    def _create_match_result(self, candidate: dict, dtx_record: PatientRecord, match_details: dict) -> MatchResult:
        """Create a MatchResult from a candidate match with proper field mapping."""
        # Map PMS fields to PatientRecord fields correctly
        pms_patient = PatientRecord(
            family_name=candidate.get('last_name', ''),
            given_name=candidate.get('first_name', ''),
            sex=candidate.get('gender', ''),
            dob=candidate.get('dob', ''),
            custom_identifier=candidate.get('custom_identifier', ''),
            middle_name=candidate.get('middle_initial', ''),
            ssn=candidate.get('ssn', '')
        )

        return MatchResult(
            match_found=True,
            pms_data=pms_patient,
            confidence_score=0.72,  # ExactNamesFuzzyDateStrategy confidence
            match_type=MatchType.EXACT_FUZZY_DOB,
            requires_manual_review=False,
            match_details=match_details,
            is_gender_mismatch=bool(pms_patient.sex != dtx_record.sex),
            is_date_correction=match_details.get('fuzzy_date_detected', False),
            is_name_flip=match_details.get('name_flip_detected', False),
            is_partial_match=match_details.get(
                'suffix_removal_detected', False),
            is_pms_gender_error=candidate.get('is_pms_gender_error', False)
        )


class FlippedNamesFuzzyDateStrategy(MatchingStrategy):
    """
    Flipped names with fuzzy date matching.

    Confidence: 65% - Requires manual review
    Use case: Names flipped AND date has errors - moderate confidence
    """

    @property
    def name(self) -> str:
        return "Flipped Names with Fuzzy Date"

    @property
    def confidence_score(self) -> float:
        return 0.65

    @property
    def match_type(self) -> MatchType:
        return MatchType.FLIPPED_FUZZY_DOB

    def execute(self, dtx_record: PatientRecord, pms_lookup: Dict[str, Any]) -> Optional[MatchResult]:
        # Try both normal and flipped name-only keys for fuzzy date matching
        name_keys = [
            create_name_only_key(dtx_record.family_name,
                                 dtx_record.given_name),
            create_flipped_name_only_key(
                dtx_record.family_name, dtx_record.given_name)
        ]

        for name_key in name_keys:
            if name_key in pms_lookup:
                candidates = pms_lookup[name_key]

                # Handle single candidate or list of candidates
                if isinstance(candidates, dict):
                    candidates = [candidates]
                elif not isinstance(candidates, list):
                    continue

                # Check each candidate for fuzzy date match
                for candidate in candidates:
                    if is_fuzzy_date_match(dtx_record.dob, candidate.get('dob', '')):
                        # For this strategy, accept any gender (loose matching)
                        is_flipped = name_key == create_flipped_name_only_key(
                            dtx_record.family_name, dtx_record.given_name
                        )

                        return self._create_match_result(
                            candidate, dtx_record,
                            {
                                'strategy': 'flipped_names_fuzzy_date',
                                'name_key': name_key,
                                'name_flip_detected': is_flipped,
                                'fuzzy_date_detected': True,
                                'requires_manual_review': True
                            }
                        )

        return None

    def _create_match_result(self, candidate: dict, dtx_record: PatientRecord, match_details: dict) -> MatchResult:
        """Create a MatchResult from a candidate match with proper field mapping."""
        # Map PMS fields to PatientRecord fields correctly
        pms_patient = PatientRecord(
            family_name=candidate.get('last_name', ''),
            given_name=candidate.get('first_name', ''),
            sex=candidate.get('gender', ''),
            dob=candidate.get('dob', ''),
            custom_identifier=candidate.get('custom_identifier', ''),
            middle_name=candidate.get('middle_initial', ''),
            ssn=candidate.get('ssn', '')
        )

        return MatchResult(
            match_found=True,
            pms_data=pms_patient,
            confidence_score=0.65,  # FlippedNamesFuzzyDateStrategy confidence
            match_type=MatchType.FLIPPED_FUZZY_DOB,
            requires_manual_review=True,  # Always requires manual review
            match_details=match_details,
            is_gender_mismatch=bool(pms_patient.sex != dtx_record.sex),
            is_date_correction=match_details.get('fuzzy_date_detected', False),
            is_name_flip=match_details.get('name_flip_detected', False),
            is_partial_match=match_details.get(
                'suffix_removal_detected', False),
            is_pms_gender_error=candidate.get('is_pms_gender_error', False)
        )


class PartialNamesFuzzyDateStrategy(MatchingStrategy):
    """
    Partial names with fuzzy date matching.

    Confidence: 55% - Requires manual review
    Use case: DTX has suffixes AND date errors - lowest acceptable confidence
    """

    @property
    def name(self) -> str:
        return "Partial Names with Fuzzy Date"

    @property
    def confidence_score(self) -> float:
        return 0.55

    @property
    def match_type(self) -> MatchType:
        return MatchType.PARTIAL_FUZZY_DOB

    def execute(self, dtx_record: PatientRecord, pms_lookup: Dict[str, Any]) -> Optional[MatchResult]:
        # This is the most complex strategy - iterate through all PMS records
        # looking for partial name matches with fuzzy dates
        for pms_key, pms_data in pms_lookup.items():
            if isinstance(pms_data, dict):
                pms_family = pms_data.get('last_name', '')
                pms_given = pms_data.get('first_name', '')
                pms_dob = pms_data.get('dob', '')

                # Check for partial name match AND fuzzy date match
                if (is_partial_name_match(pms_family, dtx_record.family_name) and
                    is_partial_name_match(pms_given, dtx_record.given_name) and
                        is_fuzzy_date_match(dtx_record.dob, pms_dob)):

                    return self._create_match_result(
                        pms_data, dtx_record,
                        {
                            'strategy': 'partial_names_fuzzy_date',
                            'suffix_removal_detected': True,
                            'fuzzy_date_detected': True,
                            'requires_manual_review': True,
                            'confidence_reason': 'Both name suffixes and date errors detected'
                        }
                    )

        return None

    def _create_match_result(self, candidate: dict, dtx_record: PatientRecord, match_details: dict) -> MatchResult:
        """Create a MatchResult from a candidate match with proper field mapping."""
        # Map PMS fields to PatientRecord fields correctly
        pms_patient = PatientRecord(
            family_name=candidate.get('last_name', ''),
            given_name=candidate.get('first_name', ''),
            sex=candidate.get('gender', ''),
            dob=candidate.get('dob', ''),
            custom_identifier=candidate.get('custom_identifier', ''),
            middle_name=candidate.get('middle_initial', ''),
            ssn=candidate.get('ssn', '')
        )

        return MatchResult(
            match_found=True,
            pms_data=pms_patient,
            confidence_score=0.55,  # PartialNamesFuzzyDateStrategy confidence
            match_type=MatchType.PARTIAL_FUZZY_DOB,
            requires_manual_review=True,  # Always requires manual review
            match_details=match_details,
            is_gender_mismatch=bool(pms_patient.sex != dtx_record.sex),
            is_date_correction=match_details.get('fuzzy_date_detected', False),
            is_name_flip=match_details.get('name_flip_detected', False),
            is_partial_match=match_details.get(
                'suffix_removal_detected', False),
            is_pms_gender_error=candidate.get('is_pms_gender_error', False)
        )


# Additional utility for handling candidate lists
def _get_candidates_from_lookup(lookup_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Helper function to normalize lookup data into a list of candidates.

    Args:
        lookup_data: Either a single dict or list of dicts from PMS lookup

    Returns:
        List of candidate dictionaries
    """
    if isinstance(lookup_data, dict):
        return [lookup_data]
    elif isinstance(lookup_data, list):
        return lookup_data
    else:
        return []
