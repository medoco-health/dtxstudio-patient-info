"""
Deterministic matching strategies with high confidence scores.

These strategies provide exact matches with 85-100% confidence based on
clinical informatics literature and healthcare data quality standards.
"""

from typing import Dict, Any, Optional
from ..core.data_models import MatchingStrategy, MatchResult, MatchType, PatientRecord
from ..utils.key_builders import (
    create_exact_match_key, create_loose_match_key,
    create_flipped_exact_key, create_flipped_loose_key
)
from ..utils.normalizers import is_partial_name_match, normalize_string, normalize_date


class GoldStandardStrategy(MatchingStrategy):
    """
    Gold standard exact matching - all fields match perfectly.
    
    Confidence: 100% - No manual review required
    Use case: Same patient, same data entry, no errors
    """
    
    @property
    def name(self) -> str:
        return "Gold Standard Exact Match"
    
    @property
    def confidence_score(self) -> float:
        return 1.0
    
    @property 
    def match_type(self) -> MatchType:
        return MatchType.GOLD_STANDARD
    
    def execute(self, dtx_record: PatientRecord, pms_lookup: Dict[str, Any]) -> Optional[MatchResult]:
        key = create_exact_match_key(
            dtx_record.family_name, dtx_record.given_name, 
            dtx_record.sex, dtx_record.dob
        )
        
        if key in pms_lookup:
            return self._create_match_result(
                pms_lookup[key], dtx_record,
                {'match_key': key, 'strategy': 'gold_standard'}
            )
        
        return None


class ExactNamesGenderLooseStrategy(MatchingStrategy):
    """
    Exact names and DOB, flexible gender matching.
    
    Confidence: 98% - Auto-match with gender correction warning
    Use case: Data entry gender errors, but names/DOB are reliable
    """
    
    @property
    def name(self) -> str:
        return "Exact Names with Gender Flexibility"
    
    @property
    def confidence_score(self) -> float:
        return 0.98
    
    @property
    def match_type(self) -> MatchType:
        return MatchType.EXACT_GENDER_LOOSE
    
    def execute(self, dtx_record: PatientRecord, pms_lookup: Dict[str, Any]) -> Optional[MatchResult]:
        key = create_loose_match_key(
            dtx_record.family_name, dtx_record.given_name, dtx_record.dob
        )
        
        if key in pms_lookup:
            pms_data = pms_lookup[key]
            # Only match if exact strategy didn't already match
            exact_key = create_exact_match_key(
                dtx_record.family_name, dtx_record.given_name,
                dtx_record.sex, dtx_record.dob
            )
            
            if exact_key not in pms_lookup:  # Avoid duplicate matches
                return self._create_match_result(
                    pms_data, dtx_record,
                    {'match_key': key, 'strategy': 'exact_names_gender_loose'}
                )
        
        return None


class FlippedNamesExactStrategy(MatchingStrategy):
    """
    Flipped names with exact gender and DOB.
    
    Confidence: 97% - Auto-match with name flip correction
    Use case: First/last names swapped between DTX and PMS systems
    """
    
    @property
    def name(self) -> str:
        return "Flipped Names Exact Match"
    
    @property
    def confidence_score(self) -> float:
        return 0.97
    
    @property
    def match_type(self) -> MatchType:
        return MatchType.FLIPPED_EXACT
    
    def execute(self, dtx_record: PatientRecord, pms_lookup: Dict[str, Any]) -> Optional[MatchResult]:
        key = create_flipped_exact_key(
            dtx_record.family_name, dtx_record.given_name,
            dtx_record.sex, dtx_record.dob
        )
        
        if key in pms_lookup:
            return self._create_match_result(
                pms_lookup[key], dtx_record,
                {
                    'match_key': key, 
                    'strategy': 'flipped_exact',
                    'name_flip_detected': True
                }
            )
        
        return None


class FlippedNamesGenderLooseStrategy(MatchingStrategy):
    """
    Flipped names with flexible gender matching.
    
    Confidence: 90% - Auto-match with name flip and gender corrections
    Use case: Names flipped AND gender data quality issues
    """
    
    @property
    def name(self) -> str:
        return "Flipped Names with Gender Flexibility"
    
    @property
    def confidence_score(self) -> float:
        return 0.90
    
    @property
    def match_type(self) -> MatchType:
        return MatchType.FLIPPED_GENDER_LOOSE
    
    def execute(self, dtx_record: PatientRecord, pms_lookup: Dict[str, Any]) -> Optional[MatchResult]:
        key = create_flipped_loose_key(
            dtx_record.family_name, dtx_record.given_name, dtx_record.dob
        )
        
        if key in pms_lookup:
            pms_data = pms_lookup[key]
            # Check that exact flipped match didn't already occur
            exact_flipped_key = create_flipped_exact_key(
                dtx_record.family_name, dtx_record.given_name,
                dtx_record.sex, dtx_record.dob
            )
            
            if exact_flipped_key not in pms_lookup:  # Avoid duplicate matches
                return self._create_match_result(
                    pms_data, dtx_record,
                    {
                        'match_key': key,
                        'strategy': 'flipped_gender_loose', 
                        'name_flip_detected': True
                    }
                )
        
        return None


class PartialNamesExactStrategy(MatchingStrategy):
    """
    Partial name matching with exact gender and DOB.
    
    Confidence: 85% - Auto-match with suffix removal
    Use case: DTX has suffixes like "BIS", "TRIS", "II", "JR"
    """
    
    @property
    def name(self) -> str:
        return "Partial Names Exact Match"
    
    @property
    def confidence_score(self) -> float:
        return 0.85
    
    @property
    def match_type(self) -> MatchType:
        return MatchType.PARTIAL_EXACT
    
    def execute(self, dtx_record: PatientRecord, pms_lookup: Dict[str, Any]) -> Optional[MatchResult]:
        # Iterate through PMS records to find partial matches
        for pms_key, pms_data in pms_lookup.items():
            if isinstance(pms_data, dict):
                pms_family = pms_data.get('last_name', '')
                pms_given = pms_data.get('first_name', '')
                pms_sex = pms_data.get('gender', '')
                pms_dob = pms_data.get('dob', '')
                
                # Check if PMS names are substrings of DTX names
                if (is_partial_name_match(pms_family, dtx_record.family_name) and
                    is_partial_name_match(pms_given, dtx_record.given_name) and
                    normalize_string(pms_sex) == normalize_string(dtx_record.sex) and
                    normalize_date(pms_dob) == normalize_date(dtx_record.dob)):
                    
                    return self._create_match_result(
                        pms_data, dtx_record,
                        {
                            'match_key': pms_key,
                            'strategy': 'partial_exact',
                            'suffix_removal_detected': True,
                            'dtx_family_suffix': dtx_record.family_name,
                            'dtx_given_suffix': dtx_record.given_name,
                            'pms_family_base': pms_family,
                            'pms_given_base': pms_given
                        }
                    )
        
        return None


class PartialNamesGenderLooseStrategy(MatchingStrategy):
    """
    Partial name matching with flexible gender.
    
    Confidence: 75% - Auto-match with suffix removal and gender correction
    Use case: DTX has suffixes AND gender data quality issues
    """
    
    @property
    def name(self) -> str:
        return "Partial Names with Gender Flexibility"
    
    @property
    def confidence_score(self) -> float:
        return 0.75
    
    @property
    def match_type(self) -> MatchType:
        return MatchType.PARTIAL_GENDER_LOOSE
    
    def execute(self, dtx_record: PatientRecord, pms_lookup: Dict[str, Any]) -> Optional[MatchResult]:
        # Iterate through PMS records to find partial matches
        for pms_key, pms_data in pms_lookup.items():
            if isinstance(pms_data, dict):
                pms_family = pms_data.get('last_name', '')
                pms_given = pms_data.get('first_name', '')
                pms_dob = pms_data.get('dob', '')
                
                # Check if PMS names are substrings of DTX names (ignore gender)
                if (is_partial_name_match(pms_family, dtx_record.family_name) and
                    is_partial_name_match(pms_given, dtx_record.given_name) and
                    normalize_date(pms_dob) == normalize_date(dtx_record.dob)):
                    
                    # Make sure this wasn't already matched by exact partial strategy
                    pms_sex = pms_data.get('gender', '')
                    if normalize_string(pms_sex) != normalize_string(dtx_record.sex):
                        return self._create_match_result(
                            pms_data, dtx_record,
                            {
                                'match_key': pms_key,
                                'strategy': 'partial_gender_loose',
                                'suffix_removal_detected': True,
                                'gender_mismatch_detected': True
                            }
                        )
        
        return None