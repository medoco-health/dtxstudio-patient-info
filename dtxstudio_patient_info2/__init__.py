"""
Clinical Patient Matching Framework v2

This is a complete rewrite of the dtxstudio_patient_info1 package, mainly done
in vibe coding. However, this is incomplete and not yet ready for production
use.

A clinical informatics-based patient matching system following evidence-based
practices from peer-reviewed literature for healthcare data integration.

References:
- Fellegi-Sunter Model for record linkage
- Grannis et al. (2019): "Analysis of identifier performance for patient matching"
- Karimi et al. (2011): "Patient name matching in healthcare"
- HL7 FHIR Patient Matching specifications
"""

from .core.patient_matcher import ClinicalPatientMatcher
from .core.data_models import MatchingStrategy, MatchResult, MatchType, ConfidenceLevel
from .core.confidence_scoring import ConfidenceCalculator
from .utils.normalizers import normalize_string, normalize_date
from .utils.italian_cf import extract_gender_from_codice_fiscale

__version__ = "1.0.0"
__author__ = "Clinical Informatics Team"

__all__ = [
    'ClinicalPatientMatcher',
    'MatchingStrategy', 
    'MatchResult',
    'MatchType',
    'ConfidenceLevel',
    'ConfidenceCalculator',
    'normalize_string',
    'normalize_date',
    'extract_gender_from_codice_fiscale'
]