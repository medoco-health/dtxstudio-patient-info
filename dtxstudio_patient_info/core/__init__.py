"""Core clinical matching framework."""

# Import main classes for easier access
from .data_models import (
    MatchType, 
    ConfidenceLevel, 
    PatientRecord, 
    MatchResult, 
    MatchingStrategy,
    SessionStatistics
)
from .confidence_scoring import ConfidenceCalculator

__all__ = [
    'MatchType',
    'ConfidenceLevel', 
    'PatientRecord',
    'MatchResult',
    'MatchingStrategy',
    'SessionStatistics',
    'ConfidenceCalculator'
]