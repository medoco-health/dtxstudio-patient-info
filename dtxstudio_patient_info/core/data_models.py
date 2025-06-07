"""
Clinical Patient Matching Data Models

This module defines the core data structures and types used throughout the
clinical patient matching system, following healthcare informatics standards.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class MatchType(Enum):
    """Types of patient matches based on clinical confidence levels."""
    GOLD_STANDARD = "GOLD_STANDARD"                    # 100% confidence
    EXACT_GENDER_LOOSE = "EXACT_GENDER_LOOSE"          # 98% confidence
    FLIPPED_EXACT = "FLIPPED_EXACT"                    # 97% confidence
    FLIPPED_GENDER_LOOSE = "FLIPPED_GENDER_LOOSE"      # 90% confidence
    PARTIAL_EXACT = "PARTIAL_EXACT"                    # 85% confidence
    PARTIAL_GENDER_LOOSE = "PARTIAL_GENDER_LOOSE"      # 75% confidence
    EXACT_FUZZY_DOB = "EXACT_FUZZY_DOB"               # 72% confidence
    FLIPPED_FUZZY_DOB = "FLIPPED_FUZZY_DOB"           # 65% confidence
    PARTIAL_FUZZY_DOB = "PARTIAL_FUZZY_DOB"           # 55% confidence
    NO_MATCH = "NO_MATCH"                             # 0% confidence


class ConfidenceLevel(Enum):
    """Clinical confidence levels for patient matching."""
    GOLD_STANDARD = "GOLD_STANDARD"        # 100% - Auto-match
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"    # 95-99% - Auto-match with warning
    MODERATE_CONFIDENCE = "MODERATE_CONFIDENCE"  # 80-95% - Auto-match with review
    ACCEPTABLE_CONFIDENCE = "ACCEPTABLE_CONFIDENCE"  # 70-80% - Auto-match with audit
    MANUAL_REVIEW = "MANUAL_REVIEW"        # 50-70% - Requires manual review
    NO_MATCH = "NO_MATCH"                  # <50% - No match


@dataclass
class PatientRecord:
    """Standardized patient record for matching."""
    family_name: str
    given_name: str
    sex: str
    dob: str
    pms_id: Optional[str] = None
    practice_pms_id: Optional[str] = None
    dicom_id: Optional[str] = None
    middle_name: Optional[str] = None
    custom_identifier: Optional[str] = None
    middle_initial: Optional[str] = None
    ssn: Optional[str] = None  # Codice Fiscale

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'family_name': self.family_name,
            'given_name': self.given_name,
            'sex': self.sex,
            'dob': self.dob,
            'pms_id': self.pms_id,
            'practice_pms_id': self.practice_pms_id,
            'dicom_id': self.dicom_id,
            'middle_name': self.middle_name,
            'custom_identifier': self.custom_identifier,
            'middle_initial': self.middle_initial,
            'ssn': self.ssn
        }


@dataclass
class MatchResult:
    """Result of patient matching operation."""
    match_found: bool
    pms_data: Optional[PatientRecord]
    confidence_score: float
    match_type: MatchType
    requires_manual_review: bool
    match_details: Dict[str, Any]

    # Clinical correction flags
    is_gender_mismatch: bool = False
    is_date_correction: bool = False
    is_name_flip: bool = False
    is_partial_match: bool = False
    is_pms_gender_error: bool = False

    def get_confidence_level(self) -> ConfidenceLevel:
        """Get clinical confidence level based on score."""
        if self.confidence_score >= 1.0:
            return ConfidenceLevel.GOLD_STANDARD
        elif self.confidence_score >= 0.95:
            return ConfidenceLevel.HIGH_CONFIDENCE
        elif self.confidence_score >= 0.80:
            return ConfidenceLevel.MODERATE_CONFIDENCE
        elif self.confidence_score >= 0.70:
            return ConfidenceLevel.ACCEPTABLE_CONFIDENCE
        elif self.confidence_score >= 0.50:
            return ConfidenceLevel.MANUAL_REVIEW
        else:
            return ConfidenceLevel.NO_MATCH


@dataclass
class MatchingStrategy:
    """Definition of a patient matching strategy."""
    name: str
    rules: List[str]
    confidence: float
    priority: int
    description: str

    def __post_init__(self):
        """Validate strategy configuration."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.priority < 1:
            raise ValueError("Priority must be >= 1")


@dataclass
class SessionStatistics:
    """Statistics for a matching session."""
    total_processed: int = 0
    auto_matched: int = 0
    manual_review_required: int = 0
    no_matches: int = 0

    # Match type distribution
    gold_standard_matches: int = 0
    high_confidence_matches: int = 0
    moderate_confidence_matches: int = 0
    acceptable_confidence_matches: int = 0

    # Correction type distribution
    gender_corrections: int = 0
    date_corrections: int = 0
    name_flips: int = 0
    partial_name_matches: int = 0
    pms_gender_errors: int = 0

    def get_match_rate(self) -> float:
        """Calculate overall match rate."""
        if self.total_processed == 0:
            return 0.0
        return (self.auto_matched + self.manual_review_required) / self.total_processed

    def get_auto_match_rate(self) -> float:
        """Calculate automatic match rate."""
        if self.total_processed == 0:
            return 0.0
        return self.auto_matched / self.total_processed