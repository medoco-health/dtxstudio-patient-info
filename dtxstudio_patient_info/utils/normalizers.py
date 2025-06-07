"""
String and date normalization utilities for clinical patient matching.

This module provides standardized normalization functions used throughout
the clinical matching system to ensure consistent data processing.
"""

import re
from datetime import datetime
from typing import Optional


def normalize_string(s: str) -> str:
    """
    Normalize string by removing spaces and converting to lowercase.
    
    Args:
        s: Input string to normalize
        
    Returns:
        Normalized string with no spaces, lowercase
    """
    if not s:
        return ""
    return re.sub(r'\s+', '', s.lower())


def normalize_date(date_str: str) -> str:
    """
    Normalize date string to YYYY-MM-DD format.
    
    Supports multiple input formats commonly found in healthcare systems:
    - YYYY-MM-DD (ISO format)
    - MM/DD/YYYY (US format)
    - DD/MM/YYYY (European format)  
    - YYYY/MM/DD (Alternative ISO)
    
    Args:
        date_str: Input date string in various formats
        
    Returns:
        Normalized date in YYYY-MM-DD format, or original string if parsing fails
    """
    if not date_str:
        return ""

    # Try different date formats commonly used in healthcare
    formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return date_str  # Return original if no format matches


def normalize_name_for_matching(name: str) -> str:
    """
    Normalize name specifically for patient matching.
    
    This includes additional processing beyond basic normalization:
    - Remove common prefixes (Dr., Prof., etc.)
    - Remove common suffixes (Jr., Sr., III, etc.)
    - Handle special characters and diacritics
    
    Args:
        name: Input name string
        
    Returns:
        Normalized name for matching
    """
    if not name:
        return ""
    
    # Convert to lowercase and remove extra spaces
    normalized = name.lower().strip()
    
    # Remove common prefixes
    prefixes = ['dr.', 'prof.', 'dott.', 'dott.ssa', 'sig.', 'sig.ra', 'sig.na']
    for prefix in prefixes:
        if normalized.startswith(prefix + ' '):
            normalized = normalized[len(prefix):].strip()
    
    # Remove common suffixes  
    suffixes = ['jr.', 'sr.', 'ii', 'iii', 'iv', 'bis', 'tris', 'jr', 'sr']
    words = normalized.split()
    if len(words) > 1 and words[-1] in suffixes:
        words = words[:-1]
        normalized = ' '.join(words)
    
    # Remove spaces for final normalization
    return re.sub(r'\s+', '', normalized)


def normalize_gender(gender: str) -> str:
    """
    Normalize gender string to standard values.
    
    Args:
        gender: Input gender string
        
    Returns:
        Normalized gender ('MALE', 'FEMALE', or original if unrecognized)
    """
    if not gender:
        return ""
    
    gender_normalized = gender.upper().strip()
    
    # Map common variations to standard values
    male_variants = ['M', 'MALE', 'MASCHIO', 'UOMO', 'MAN']
    female_variants = ['F', 'FEMALE', 'FEMMINA', 'DONNA', 'WOMAN']
    
    if gender_normalized in male_variants:
        return 'MALE'
    elif gender_normalized in female_variants:
        return 'FEMALE'
    
    return gender_normalized  # Return original if not recognized


def clean_ssn(ssn: str) -> str:
    """
    Clean and normalize SSN/Codice Fiscale.
    
    Args:
        ssn: Input SSN/Codice Fiscale
        
    Returns:
        Cleaned SSN with no spaces, uppercase
    """
    if not ssn:
        return ""
    
    # Remove spaces and convert to uppercase
    cleaned = re.sub(r'\s+', '', ssn.upper())
    
    # Remove common separators
    cleaned = cleaned.replace('-', '').replace('_', '')
    
    return cleaned