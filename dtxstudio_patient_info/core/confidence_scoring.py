"""
Clinical confidence scoring for patient matching.

This module implements evidence-based confidence scoring algorithms
based on clinical informatics research and healthcare data quality standards.
"""

from typing import Dict, List, Tuple
from .matching_strategies import MatchType, ConfidenceLevel, MatchResult
import logging


class ConfidenceCalculator:
    """
    Calculates confidence scores for patient matches based on clinical criteria.
    
    References:
    - Grannis et al. (2019): Statistical approaches to patient matching
    - Christen (2012): Data matching concepts and techniques
    """
    
    def __init__(self):
        """Initialize confidence calculator with clinical thresholds."""
        # Clinical confidence thresholds based on healthcare standards
        self.confidence_thresholds = {
            MatchType.GOLD_STANDARD: 1.00,
            MatchType.EXACT_GENDER_LOOSE: 0.98,
            MatchType.FLIPPED_EXACT: 0.97,
            MatchType.FLIPPED_GENDER_LOOSE: 0.90,
            MatchType.PARTIAL_EXACT: 0.85,
            MatchType.PARTIAL_GENDER_LOOSE: 0.75,
            MatchType.EXACT_FUZZY_DOB: 0.72,
            MatchType.FLIPPED_FUZZY_DOB: 0.65,
            MatchType.PARTIAL_FUZZY_DOB: 0.55,
            MatchType.NO_MATCH: 0.00
        }
        
        # Adjustment factors for clinical corrections
        self.correction_factors = {
            'gender_mismatch': -0.05,        # Gender correction reduces confidence
            'date_correction': -0.03,        # Date correction reduces confidence  
            'name_flip': -0.02,              # Name flip reduces confidence slightly
            'partial_match': -0.10,          # Partial matching reduces confidence more
            'pms_gender_error': 0.02,        # CF validation increases confidence
            'codice_fiscale_validation': 0.05  # CF validation increases confidence
        }
        
        self.logger = logging.getLogger(__name__)
    
    def calculate_base_confidence(self, match_type: MatchType) -> float:
        """Get base confidence score for match type."""
        return self.confidence_thresholds.get(match_type, 0.0)
    
    def calculate_adjusted_confidence(self, 
                                    base_confidence: float,
                                    corrections: Dict[str, bool]) -> float:
        """
        Calculate adjusted confidence score based on clinical corrections.
        
        Args:
            base_confidence: Base confidence from match type
            corrections: Dictionary of correction flags
            
        Returns:
            Adjusted confidence score (0.0 to 1.0)
        """
        adjusted_confidence = base_confidence
        
        # Apply correction factors
        for correction_type, is_present in corrections.items():
            if is_present and correction_type in self.correction_factors:
                factor = self.correction_factors[correction_type]
                adjusted_confidence += factor
                
                self.logger.debug(
                    f"Applied {correction_type} adjustment: {factor:+.3f} "
                    f"(confidence: {base_confidence:.3f} -> {adjusted_confidence:.3f})"
                )
        
        # Ensure confidence stays within bounds
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))
        
        return adjusted_confidence
    
    def calculate_fuzzy_date_confidence(self, 
                                      date1: str, 
                                      date2: str,
                                      base_confidence: float = 0.72) -> float:
        """
        Calculate confidence for fuzzy date matching.
        
        Uses Levenshtein distance and date similarity algorithms
        from clinical informatics literature.
        """
        from ..utils.normalizers import normalize_date
        from ..utils.date_similarity import calculate_date_similarity
        
        norm_date1 = normalize_date(date1)
        norm_date2 = normalize_date(date2)
        
        if norm_date1 == norm_date2:
            return base_confidence  # Exact date match
        
        # Calculate date similarity score
        similarity_score = calculate_date_similarity(norm_date1, norm_date2)
        
        # Adjust confidence based on date similarity
        # High similarity (>0.8) = minor reduction
        # Medium similarity (0.6-0.8) = moderate reduction  
        # Low similarity (<0.6) = major reduction
        if similarity_score >= 0.8:
            adjustment = -0.05
        elif similarity_score >= 0.6:
            adjustment = -0.15
        else:
            adjustment = -0.25
        
        adjusted_confidence = base_confidence + adjustment
        
        self.logger.debug(
            f"Fuzzy date matching: {date1} vs {date2} "
            f"(similarity: {similarity_score:.3f}, "
            f"confidence: {base_confidence:.3f} -> {adjusted_confidence:.3f})"
        )
        
        return max(0.0, min(1.0, adjusted_confidence))
    
    def calculate_partial_name_confidence(self,
                                        pms_name: str,
                                        dtx_name: str, 
                                        base_confidence: float = 0.85) -> float:
        """
        Calculate confidence for partial name matching.
        
        Accounts for suffix variations (BIS, TRIS, JR, etc.)
        """
        from ..utils.normalizers import normalize_string
        
        pms_norm = normalize_string(pms_name)
        dtx_norm = normalize_string(dtx_name)
        
        # Calculate coverage ratio
        if len(pms_norm) == 0 or len(dtx_norm) == 0:
            return 0.0
        
        coverage_ratio = len(pms_norm) / len(dtx_norm)
        
        # Adjust confidence based on coverage
        # High coverage (>0.8) = minor reduction
        # Medium coverage (0.6-0.8) = moderate reduction
        # Low coverage (<0.6) = major reduction
        if coverage_ratio >= 0.8:
            adjustment = -0.05
        elif coverage_ratio >= 0.6:
            adjustment = -0.10
        else:
            adjustment = -0.20
        
        adjusted_confidence = base_confidence + adjustment
        
        self.logger.debug(
            f"Partial name matching: '{pms_name}' vs '{dtx_name}' "
            f"(coverage: {coverage_ratio:.3f}, "
            f"confidence: {base_confidence:.3f} -> {adjusted_confidence:.3f})"
        )
        
        return max(0.0, min(1.0, adjusted_confidence))
    
    def requires_manual_review(self, confidence_score: float) -> bool:
        """Determine if match requires manual review based on confidence."""
        return confidence_score < 0.70
    
    def get_confidence_level(self, confidence_score: float) -> ConfidenceLevel:
        """Get clinical confidence level from numeric score."""
        if confidence_score >= 1.0:
            return ConfidenceLevel.GOLD_STANDARD
        elif confidence_score >= 0.95:
            return ConfidenceLevel.HIGH_CONFIDENCE
        elif confidence_score >= 0.80:
            return ConfidenceLevel.MODERATE_CONFIDENCE
        elif confidence_score >= 0.70:
            return ConfidenceLevel.ACCEPTABLE_CONFIDENCE
        elif confidence_score >= 0.50:
            return ConfidenceLevel.MANUAL_REVIEW
        else:
            return ConfidenceLevel.NO_MATCH