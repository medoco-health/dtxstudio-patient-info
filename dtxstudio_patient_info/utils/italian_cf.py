"""
Italian Codice Fiscale utilities for clinical patient matching.

This module provides functions to validate and extract information from
Italian tax codes (Codice Fiscale) commonly used in Italian healthcare systems.
"""

import re
from typing import Optional


def extract_gender_from_codice_fiscale(ssn: str) -> Optional[str]:
    """
    Extract gender from Italian Codice Fiscale.

    The gender is encoded in the day of birth field:
    - Days 01-31: Male
    - Days 41-71: Female (day + 40)

    Args:
        ssn: Italian Codice Fiscale (16 characters)

    Returns:
        'MALE', 'FEMALE', or None if invalid/unrecognizable
    """
    if not ssn or len(ssn) < 11:
        return None

    try:
        # Extract day digits (positions 9-10, 0-indexed)
        day_str = ssn[9:11]

        # Check if day digits are numeric
        if not day_str.isdigit():
            return None

        day = int(day_str)

        # Determine gender based on day encoding
        if 1 <= day <= 31:
            return 'MALE'
        elif 41 <= day <= 71:
            return 'FEMALE'
        else:
            return None  # Invalid day value

    except (ValueError, IndexError):
        return None


def validate_codice_fiscale_format(cf: str) -> bool:
    """
    Validate basic format of Italian Codice Fiscale.

    Args:
        cf: Codice Fiscale to validate

    Returns:
        True if format is valid, False otherwise
    """
    if not cf or len(cf) != 16:
        return False

    # Basic pattern: 6 letters + 2 digits + 1 letter + 2 digits + 1 letter + 3 chars + 1 letter
    pattern = r'^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9A-Z]{3}[A-Z]$'

    return bool(re.match(pattern, cf.upper()))


def extract_birth_date_from_codice_fiscale(cf: str) -> Optional[str]:
    """
    Extract birth date from Italian Codice Fiscale.

    Args:
        cf: Italian Codice Fiscale

    Returns:
        Birth date in YYYY-MM-DD format, or None if extraction fails
    """
    if not validate_codice_fiscale_format(cf):
        return None

    try:
        cf_upper = cf.upper()

        # Extract year (positions 6-7)
        year_digits = cf_upper[6:8]

        # Extract month letter (position 8)
        month_letter = cf_upper[8]

        # Extract day (positions 9-10)
        day_str = cf_upper[9:11]

        # Convert month letter to number
        month_map = {
            'A': '01', 'B': '02', 'C': '03', 'D': '04', 'E': '05', 'H': '06',
            'L': '07', 'M': '08', 'P': '09', 'R': '10', 'S': '11', 'T': '12'
        }

        if month_letter not in month_map:
            return None

        month = month_map[month_letter]

        # Handle day (subtract 40 for females)
        day = int(day_str)
        if day > 40:
            day -= 40

        if not (1 <= day <= 31):
            return None

        # Determine century (assuming current century for recent dates)
        current_year = 2024
        year_2digit = int(year_digits)

        # If year is in the future relative to current year, assume previous century
        if year_2digit <= (current_year % 100):
            year = 2000 + year_2digit
        else:
            year = 1900 + year_2digit

        # Format as YYYY-MM-DD
        return f"{year:04d}-{month}-{day:02d}"

    except (ValueError, IndexError):
        return None


def is_codice_fiscale_gender_consistent(cf: str, declared_gender: str) -> bool:
    """
    Check if declared gender is consistent with Codice Fiscale.

    Args:
        cf: Italian Codice Fiscale
        declared_gender: Declared gender ('MALE' or 'FEMALE')

    Returns:
        True if consistent, False if inconsistent or undeterminable
    """
    cf_gender = extract_gender_from_codice_fiscale(cf)

    if not cf_gender:
        return True  # Cannot determine, assume consistent

    declared_normalized = declared_gender.upper().strip()

    return cf_gender == declared_normalized


def get_codice_fiscale_validation_info(cf: str) -> dict:
    """
    Get comprehensive validation information for Codice Fiscale.

    Args:
        cf: Italian Codice Fiscale

    Returns:
        Dictionary with validation results and extracted information
    """
    info = {
        'valid_format': False,
        'extracted_gender': None,
        'extracted_birth_date': None,
        'length_valid': False,
        'pattern_valid': False
    }

    if not cf:
        return info

    info['length_valid'] = len(cf) == 16
    info['pattern_valid'] = validate_codice_fiscale_format(cf)
    info['valid_format'] = info['length_valid'] and info['pattern_valid']

    if info['valid_format']:
        info['extracted_gender'] = extract_gender_from_codice_fiscale(cf)
        info['extracted_birth_date'] = extract_birth_date_from_codice_fiscale(
            cf)

    return info
