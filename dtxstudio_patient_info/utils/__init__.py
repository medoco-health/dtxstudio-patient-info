"""Utility functions for clinical patient matching."""

# Import key functions for easier access
from .normalizers import normalize_string, normalize_date, normalize_gender
from .key_builders import (
    create_exact_match_key,
    create_loose_match_key,
    create_name_only_match_key,
    create_flipped_match_key,
    create_composite_keys
)
from .italian_cf import extract_gender_from_codice_fiscale, validate_codice_fiscale_format
from .date_similarity import calculate_date_similarity, is_fuzzy_date_match

__all__ = [
    'normalize_string',
    'normalize_date', 
    'normalize_gender',
    'create_exact_match_key',
    'create_loose_match_key',
    'create_name_only_match_key',
    'create_flipped_match_key',
    'create_composite_keys',
    'extract_gender_from_codice_fiscale',
    'validate_codice_fiscale_format',
    'calculate_date_similarity',
    'is_fuzzy_date_match'
]