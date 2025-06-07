
#!/usr/bin/env python3
"""
Unit tests for patient_info_updater.py
"""

from patient_info_updater import extract_gender_from_codice_fiscale
import unittest
import sys
import os

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestExtractGenderFromCodiceFiscale(unittest.TestCase):
    """Test cases for extract_gender_from_codice_fiscale function."""

    def setUp(self):
        """Set up test data."""
        # Valid test cases from existing test file
        self.VALID_MALE_CF = "LTLLWO80D02H501V"    # day is 02
        self.VALID_FEMALE_CF = "SKSKVI80L43H501M"  # day is 03 (43-40)

        # Additional test cases for edge conditions
        self.MALE_CF_DAY_01 = "RSSMRA85A01H501Z"   # day is 01
        self.MALE_CF_DAY_31 = "RSSMRA85A31H501Z"   # day is 31
        self.FEMALE_CF_DAY_41 = "RSSMRA85A41H501Z"  # day is 01 (41-40)
        self.FEMALE_CF_DAY_71 = "RSSMRA85A71H501Z"  # day is 31 (71-40)

    def test_valid_male_codice_fiscale(self):
        """Test extraction of male gender from valid codice fiscale."""
        result = extract_gender_from_codice_fiscale(self.VALID_MALE_CF)
        self.assertEqual(
            result, 'MALE', f"Expected 'MALE' for male CF: {self.VALID_MALE_CF}")

    def test_valid_female_codice_fiscale(self):
        """Test extraction of female gender from valid codice fiscale."""
        result = extract_gender_from_codice_fiscale(self.VALID_FEMALE_CF)
        self.assertEqual(
            result, 'FEMALE', f"Expected 'FEMALE' for female CF: {self.VALID_FEMALE_CF}")

    def test_male_edge_cases(self):
        """Test male gender extraction for edge cases (day 01 and 31)."""
        # Test day 01
        result = extract_gender_from_codice_fiscale(self.MALE_CF_DAY_01)
        self.assertEqual(
            result, 'MALE', f"Expected 'MALE' for male CF with day 01: {self.MALE_CF_DAY_01}")

        # Test day 31
        result = extract_gender_from_codice_fiscale(self.MALE_CF_DAY_31)
        self.assertEqual(
            result, 'MALE', f"Expected 'MALE' for male CF with day 31: {self.MALE_CF_DAY_31}")

    def test_female_edge_cases(self):
        """Test female gender extraction for edge cases (day 41 and 71)."""
        # Test day 41 (day 01 + 40)
        result = extract_gender_from_codice_fiscale(self.FEMALE_CF_DAY_41)
        self.assertEqual(
            result, 'FEMALE', f"Expected 'FEMALE' for female CF with day 41: {self.FEMALE_CF_DAY_41}")

        # Test day 71 (day 31 + 40)
        result = extract_gender_from_codice_fiscale(self.FEMALE_CF_DAY_71)
        self.assertEqual(
            result, 'FEMALE', f"Expected 'FEMALE' for female CF with day 71: {self.FEMALE_CF_DAY_71}")

    def test_invalid_inputs(self):
        """Test function behavior with invalid inputs."""
        # Test None input
        result = extract_gender_from_codice_fiscale(None)
        self.assertIsNone(result, "Expected None for None input")

        # Test empty string
        result = extract_gender_from_codice_fiscale("")
        self.assertIsNone(result, "Expected None for empty string")

        # Test too short string
        result = extract_gender_from_codice_fiscale("SHORTCF")
        self.assertIsNone(
            result, "Expected None for string shorter than 11 characters")

    def test_invalid_day_values(self):
        """Test function behavior with invalid day values."""
        # Test day 00 (invalid)
        invalid_cf_00 = "RSSMRA85A00H501Z"
        result = extract_gender_from_codice_fiscale(invalid_cf_00)
        self.assertIsNone(
            result, f"Expected None for invalid day 00: {invalid_cf_00}")

        # Test day 32 (invalid for male)
        invalid_cf_32 = "RSSMRA85A32H501Z"
        result = extract_gender_from_codice_fiscale(invalid_cf_32)
        self.assertIsNone(
            result, f"Expected None for invalid day 32: {invalid_cf_32}")

        # Test day 40 (invalid boundary)
        invalid_cf_40 = "RSSMRA85A40H501Z"
        result = extract_gender_from_codice_fiscale(invalid_cf_40)
        self.assertIsNone(
            result, f"Expected None for invalid day 40: {invalid_cf_40}")

        # Test day 72 (invalid for female)
        invalid_cf_72 = "RSSMRA85A72H501Z"
        result = extract_gender_from_codice_fiscale(invalid_cf_72)
        self.assertIsNone(
            result, f"Expected None for invalid day 72: {invalid_cf_72}")

    def test_non_numeric_day_characters(self):
        """Test function behavior with non-numeric characters in day position."""
        # Test with letters in day position
        invalid_cf_letters = "RSSMRA85AAH501Z"
        result = extract_gender_from_codice_fiscale(invalid_cf_letters)
        self.assertIsNone(
            result, f"Expected None for non-numeric day: {invalid_cf_letters}")

        # Test with special characters in day position
        invalid_cf_special = "RSSMRA85A**H501Z"
        result = extract_gender_from_codice_fiscale(invalid_cf_special)
        self.assertIsNone(
            result, f"Expected None for special chars in day: {invalid_cf_special}")

    def test_codice_fiscale_exactly_11_chars(self):
        """Test function with codice fiscale that is exactly 11 characters."""
        # Valid 11-char CF (minimum length)
        valid_11_char_male = "RSSMRA85A02"
        result = extract_gender_from_codice_fiscale(valid_11_char_male)
        self.assertEqual(
            result, 'MALE', f"Expected 'MALE' for 11-char male CF: {valid_11_char_male}")

        valid_11_char_female = "RSSMRA85A42"
        result = extract_gender_from_codice_fiscale(valid_11_char_female)
        self.assertEqual(
            result, 'FEMALE', f"Expected 'FEMALE' for 11-char female CF: {valid_11_char_female}")


if __name__ == '__main__':
    unittest.main()
