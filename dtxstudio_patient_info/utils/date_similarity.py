"""
Date similarity calculation for clinical patient matching.

This module implements date comparison algorithms used in healthcare
record linkage, including fuzzy date matching for OCR errors and typos.
"""

from datetime import datetime
from typing import Tuple


def calculate_date_similarity(date1: str, date2: str) -> float:
    """
    Calculate similarity between two dates using digit-level comparison.
    
    This handles common OCR errors and typos in healthcare data entry:
    - Digit transpositions (1985 vs 1895)
    - Similar-looking digits (0 vs 8, 1 vs l)
    - Single digit errors (05 vs 06)
    
    Args:
        date1: First date in YYYY-MM-DD format
        date2: Second date in YYYY-MM-DD format
        
    Returns:
        Similarity score from 0.0 (completely different) to 1.0 (identical)
    """
    from .normalizers import normalize_date
    
    if not date1 or not date2:
        return 0.0
    
    # Normalize dates to YYYY-MM-DD format
    norm_date1 = normalize_date(date1)
    norm_date2 = normalize_date(date2)
    
    if norm_date1 == norm_date2:
        return 1.0
    
    # Remove hyphens for digit comparison
    digits1 = norm_date1.replace('-', '')
    digits2 = norm_date2.replace('-', '')
    
    if len(digits1) != len(digits2) or len(digits1) != 8:
        return 0.0
    
    return calculate_digit_similarity(digits1, digits2)


def calculate_digit_similarity(digits1: str, digits2: str) -> float:
    """
    Calculate similarity between two digit strings.
    
    Uses a weighted scoring system that accounts for:
    - Exact matches (full score)
    - Visually similar digits (partial score) 
    - Position-based weighting (year > month > day)
    
    Args:
        digits1: First digit string (8 digits: YYYYMMDD)
        digits2: Second digit string (8 digits: YYYYMMDD)
        
    Returns:
        Similarity score from 0.0 to 1.0
    """
    if len(digits1) != len(digits2) or len(digits1) != 8:
        return 0.0
    
    # Define similar digits (visually or by proximity on keyboard)
    similar_digits = {
        '0': ['0', '8', 'o', 'O'],
        '1': ['1', 'l', 'I', '|'],
        '2': ['2', 'z', 'Z'],
        '3': ['3', '8'],
        '4': ['4', 'A'],
        '5': ['5', 'S', 's'],
        '6': ['6', 'G'],
        '7': ['7', 'T'],
        '8': ['8', '0', '3', 'B'],
        '9': ['9', 'g', 'q']
    }
    
    # Position weights: Year (4 digits) > Month (2 digits) > Day (2 digits)
    position_weights = [
        0.20, 0.20, 0.15, 0.15,  # Year positions (YYYY)
        0.10, 0.10,              # Month positions (MM)
        0.05, 0.05               # Day positions (DD)
    ]
    
    total_score = 0.0
    max_possible_score = sum(position_weights)
    
    for i in range(len(digits1)):
        d1, d2 = digits1[i], digits2[i]
        weight = position_weights[i]
        
        if d1 == d2:
            # Exact match
            total_score += weight
        elif d1 in similar_digits.get(d2, []) or d2 in similar_digits.get(d1, []):
            # Similar digit (partial credit)
            total_score += weight * 0.5
        # No credit for completely different digits
    
    return total_score / max_possible_score if max_possible_score > 0 else 0.0


def is_fuzzy_date_match(date1: str, date2: str, threshold: float = 0.8) -> bool:
    """
    Determine if two dates are a fuzzy match.
    
    Args:
        date1: First date string
        date2: Second date string  
        threshold: Minimum similarity score to consider a match
        
    Returns:
        True if dates are similar enough to be considered a match
    """
    similarity = calculate_date_similarity(date1, date2)
    return similarity >= threshold


def get_date_difference_days(date1: str, date2: str) -> int:
    """
    Calculate the difference in days between two dates.
    
    Args:
        date1: First date in YYYY-MM-DD format
        date2: Second date in YYYY-MM-DD format
        
    Returns:
        Absolute difference in days, or -1 if parsing fails
    """
    from .normalizers import normalize_date
    
    try:
        norm_date1 = normalize_date(date1)
        norm_date2 = normalize_date(date2)
        
        dt1 = datetime.strptime(norm_date1, '%Y-%m-%d')
        dt2 = datetime.strptime(norm_date2, '%Y-%m-%d')
        
        return abs((dt1 - dt2).days)
        
    except (ValueError, TypeError):
        return -1


def analyze_date_discrepancy(date1: str, date2: str) -> dict:
    """
    Analyze the type and magnitude of date discrepancy.
    
    Args:
        date1: First date
        date2: Second date
        
    Returns:
        Dictionary with analysis results
    """
    from .normalizers import normalize_date
    
    analysis = {
        'similarity_score': 0.0,
        'days_difference': -1,
        'discrepancy_type': 'unknown',
        'likely_cause': 'unknown'
    }
    
    analysis['similarity_score'] = calculate_date_similarity(date1, date2)
    analysis['days_difference'] = get_date_difference_days(date1, date2)
    
    # Analyze type of discrepancy
    if analysis['similarity_score'] >= 0.95:
        analysis['discrepancy_type'] = 'minimal'
        analysis['likely_cause'] = 'minor_typo'
    elif analysis['similarity_score'] >= 0.8:
        analysis['discrepancy_type'] = 'moderate'
        analysis['likely_cause'] = 'ocr_error'
    elif analysis['similarity_score'] >= 0.6:
        analysis['discrepancy_type'] = 'significant'
        analysis['likely_cause'] = 'transcription_error'
    else:
        analysis['discrepancy_type'] = 'major'
        analysis['likely_cause'] = 'different_dates'
    
    return analysis