"""
Match key builders for clinical patient matching.

This module provides functions to build normalized matching keys
for different types of patient record comparisons.
"""

from typing import List
from .normalizers import normalize_string, normalize_date, normalize_gender


def create_exact_match_key(family_name: str, given_name: str, sex: str, dob: str) -> str:
    """
    Create a normalized key for exact patient matching.
    
    Args:
        family_name: Patient's family name
        given_name: Patient's given name
        sex: Patient's gender/sex
        dob: Patient's date of birth
        
    Returns:
        Normalized matching key
    """
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}|{normalize_gender(sex)}|{normalize_date(dob)}"


def create_loose_match_key(family_name: str, given_name: str, dob: str) -> str:
    """
    Create a normalized key for loose matching (without gender).
    
    Args:
        family_name: Patient's family name
        given_name: Patient's given name
        dob: Patient's date of birth
        
    Returns:
        Normalized matching key without gender
    """
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}|{normalize_date(dob)}"


def create_name_only_match_key(family_name: str, given_name: str) -> str:
    """
    Create a normalized key for name-only matching (for fuzzy date matching).
    
    Args:
        family_name: Patient's family name
        given_name: Patient's given name
        
    Returns:
        Normalized name-only matching key
    """
    return f"{normalize_string(family_name)}|{normalize_string(given_name)}"


def create_flipped_match_key(family_name: str, given_name: str, sex: str, dob: str) -> str:
    """
    Create a normalized key for matching patients with flipped names.
    
    Args:
        family_name: Patient's family name (will be used as given name in key)
        given_name: Patient's given name (will be used as family name in key)
        sex: Patient's gender/sex
        dob: Patient's date of birth
        
    Returns:
        Normalized matching key with flipped names
    """
    return f"{normalize_string(given_name)}|{normalize_string(family_name)}|{normalize_gender(sex)}|{normalize_date(dob)}"


def create_flipped_loose_match_key(family_name: str, given_name: str, dob: str) -> str:
    """
    Create a normalized key for loose matching with flipped names (without gender).
    
    Args:
        family_name: Patient's family name (will be used as given name in key)
        given_name: Patient's given name (will be used as family name in key)
        dob: Patient's date of birth
        
    Returns:
        Normalized matching key with flipped names, without gender
    """
    return f"{normalize_string(given_name)}|{normalize_string(family_name)}|{normalize_date(dob)}"


def create_flipped_name_only_key(family_name: str, given_name: str) -> str:
    """
    Create a normalized key for name-only matching with flipped names.
    
    Args:
        family_name: Patient's family name (will be used as given name in key)
        given_name: Patient's given name (will be used as family name in key)
        
    Returns:
        Normalized name-only matching key with flipped names
    """
    return f"{normalize_string(given_name)}|{normalize_string(family_name)}"


def create_composite_keys(family_name: str, given_name: str, sex: str, dob: str) -> dict:
    """
    Create all possible matching keys for a patient record.
    
    This generates the complete set of keys needed for hierarchical matching:
    - Exact matching keys
    - Loose matching keys (without gender)
    - Name-only keys (for fuzzy date matching)
    - Flipped name variations
    
    Args:
        family_name: Patient's family name
        given_name: Patient's given name
        sex: Patient's gender/sex
        dob: Patient's date of birth
        
    Returns:
        Dictionary with all matching keys
    """
    return {
        # Standard keys
        'exact': create_exact_match_key(family_name, given_name, sex, dob),
        'loose': create_loose_match_key(family_name, given_name, dob),
        'name_only': create_name_only_match_key(family_name, given_name),
        
        # Flipped name keys
        'flipped_exact': create_flipped_match_key(family_name, given_name, sex, dob),
        'flipped_loose': create_flipped_loose_match_key(family_name, given_name, dob),
        'flipped_name_only': create_flipped_name_only_key(family_name, given_name)
    }


def build_search_keys(dtx_record: dict) -> List[str]:
    """
    Build all possible search keys for a DTX record.
    
    Args:
        dtx_record: DTX patient record dictionary
        
    Returns:
        List of search keys in priority order
    """
    family_name = dtx_record.get('family_name', '')
    given_name = dtx_record.get('given_name', '')
    sex = dtx_record.get('sex', '')
    dob = dtx_record.get('dob', '')
    
    keys = create_composite_keys(family_name, given_name, sex, dob)
    
    # Return keys in priority order for matching
    return [
        keys['exact'],           # Priority 1: Exact match
        keys['loose'],           # Priority 2: Loose match (no gender)
        keys['flipped_exact'],   # Priority 3: Flipped exact match
        keys['flipped_loose'],   # Priority 4: Flipped loose match
        keys['name_only'],       # Priority 5: Name-only (for fuzzy date)
        keys['flipped_name_only'] # Priority 6: Flipped name-only (for fuzzy date)
    ]


def validate_key_components(family_name: str, given_name: str, sex: str, dob: str) -> dict:
    """
    Validate the components used to build matching keys.
    
    Args:
        family_name: Patient's family name
        given_name: Patient's given name
        sex: Patient's gender/sex
        dob: Patient's date of birth
        
    Returns:
        Dictionary with validation results
    """
    validation = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Check for required fields
    if not family_name or not family_name.strip():
        validation['valid'] = False
        validation['errors'].append('Family name is required')
    
    if not given_name or not given_name.strip():
        validation['valid'] = False
        validation['errors'].append('Given name is required')
    
    if not dob or not dob.strip():
        validation['valid'] = False
        validation['errors'].append('Date of birth is required')
    
    # Check for data quality issues
    if sex and normalize_gender(sex) not in ['MALE', 'FEMALE']:
        validation['warnings'].append(f'Unrecognized gender value: {sex}')
    
    # Check date format
    normalized_dob = normalize_date(dob) if dob else ''
    if dob and normalized_dob == dob and '-' not in dob:
        validation['warnings'].append('Date of birth may not be in standard format')
    
    return validation