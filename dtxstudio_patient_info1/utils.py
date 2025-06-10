"""
File: utils.py
Author: amagni@medoco.health
Date: 2025-06-10
"""


import re
from typing import Optional
from datetime import datetime


def normalize_string(s: str) -> str:
    """Normalize string by removing spaces, apostrophes and converting to lowercase."""
    if not s:
        return ""
    # Remove spaces and apostrophes, then convert to lowercase
    return re.sub(r"[\s']+", '', s.lower())


def normalize_date(date_str: str) -> str:
    """Normalize date string to YYYY-MM-DD format."""
    if not date_str:
        return ""

    # Try different date formats
    formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return date_str  # Return original if no format matches


def calculate_digit_similarity(date1: str, date2: str) -> float:
    """
    Calculate similarity between two dates based on digit differences.
    Returns a score from 0.0 (completely different) to 1.0 (identical).
    """
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

    matches = 0
    partial_matches = 0

    for i in range(len(digits1)):
        d1, d2 = digits1[i], digits2[i]
        if d1 == d2:
            matches += 1
        elif d1 in similar_digits.get(d2, []) or d2 in similar_digits.get(d1, []):
            partial_matches += 1

    # Calculate similarity score
    total_positions = len(digits1)
    similarity = (matches + 0.5 * partial_matches) / total_positions

    return similarity


def is_partial_name_match(pms_name: str, dtx_name: str) -> bool:
    """
    Check if PMS name is a substring of DTX name (case insensitive).
    This handles cases where DTX has suffixes like 'BIS', 'TRIS', etc.

    Args:
        pms_name: Name from PMS (shorter, without suffix)
        dtx_name: Name from DTX (potentially with suffix)

    Returns:
        True if PMS name matches the beginning of DTX name
    """
    if not pms_name or not dtx_name:
        return False

    pms_normalized = normalize_string(pms_name)
    dtx_normalized = normalize_string(dtx_name)

    # PMS name should be at the start of DTX name
    return dtx_normalized.startswith(pms_normalized) and len(pms_normalized) > 0


def is_fuzzy_date_match(date1: str, date2: str, threshold: float = 0.75) -> bool:
    """
    Check if two dates are similar enough to be considered a fuzzy match.

    Args:
        date1: First date string
        date2: Second date string
        threshold: Minimum similarity score (0.75 means 75% similarity)

    Returns:
        True if dates are similar enough to be considered a match
    """
    similarity = calculate_digit_similarity(date1, date2)
    return similarity >= threshold


def is_partial_name_word_match(name1: str, name2: str) -> bool:
    """Check if names have partial word matches in both directions.

    Returns True if any word in name1 is found in name2,
    OR if any word in name2 is found in name1.

    Examples:
    - "mark leo" vs "mark" → True (mark found in both)
    - "leo" vs "mark leo" → True (leo found in both)
    - "john michael" vs "mike" → False (no common words)
    - "smith jones" vs "smith" → True (smith found in both)
    """
    if not name1.strip() or not name2.strip():
        return False

    # Normalize and split names into words
    name1_words = set(normalize_string(word)
                      for word in name1.split() if word.strip())
    name2_words = set(normalize_string(word)
                      for word in name2.split() if word.strip())

    # Check if there's any intersection between the word sets
    return bool(name1_words & name2_words)


def extract_gender_from_codice_fiscale(ssn: str) -> Optional[str]:
    """
    Extract gender from Italian codice fiscale (SSN).

    Args:
        ssn: The codice fiscale string

    Returns:
        'MALE' for male, 'FEMALE' for female, None if invalid or can't determine
    """
    if not ssn or len(ssn) < 11:
        return None

    try:
        # Get chars 10-11 (0-based indexing: chars 9-10)
        day_chars = ssn[9:11]
        day_number = int(day_chars)

        # For females, day is encoded with +40 offset
        if 41 <= day_number <= 71:
            return 'FEMALE'  # Female (day - 40 gives actual day 1-31)
        elif 1 <= day_number <= 31:
            return 'MALE'  # Male (actual day)
        else:
            return None  # Invalid day

    except (ValueError, IndexError):
        return None
