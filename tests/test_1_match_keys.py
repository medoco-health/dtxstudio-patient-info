"""
Unit tests for match_keys.py module
Tests all key generation functions and their matching logic
"""

import unittest
from dtxstudio_patient_info.match_keys import (
    create_match_key_exact,
    create_match_key_no_gender,
    create_match_key_name_only,
    create_match_key_flipped_names,
    create_match_key_no_gender_flipped_names,
    create_match_key_no_suffix,
)


class TestMatchKeys(unittest.TestCase):
    """Test cases for match key generation functions"""

    def setUp(self):
        """Set up test data"""
        self.test_family = "Smith"
        self.test_given = "John"
        self.test_sex = "Male"
        self.test_dob = "1990-01-01"

        # Test variations
        self.test_family_caps = "SMITH"
        self.test_given_caps = "JOHN"
        self.test_sex_short = "M"
        self.test_dob_alt_format = "01/01/1990"

        # Names with apostrophes and spaces
        self.test_family_apostrophe = "O'Connor"
        self.test_given_space = "Mary Ann"

        # Names with suffixes
        self.test_family_suffix = "Smith Jr."
        self.test_given_middle = "John Michael"

    def test_create_match_key_exact(self):
        """Test exact match key generation"""
        key = create_match_key_exact(
            self.test_family, self.test_given, self.test_sex, self.test_dob)
        expected = "smith|john|male|1990-01-01"
        self.assertEqual(key, expected)

        # Test case insensitive matching
        key_caps = create_match_key_exact(
            self.test_family_caps, self.test_given_caps, self.test_sex, self.test_dob)
        self.assertEqual(key, key_caps)

        # Test different date format
        key_alt_date = create_match_key_exact(
            self.test_family, self.test_given, self.test_sex, self.test_dob_alt_format)
        self.assertEqual(key, key_alt_date)

        # Test short sex format
        key_short_sex = create_match_key_exact(
            self.test_family, self.test_given, self.test_sex_short, self.test_dob)
        expected_short = "smith|john|m|1990-01-01"
        self.assertEqual(key_short_sex, expected_short)

    def test_apostrophe_normalization(self):
        """Test that apostrophes are ignored in name normalization"""
        key1 = create_match_key_exact("O'Connor", "John", "M", "1990-01-01")
        key2 = create_match_key_exact("OConnor", "John", "M", "1990-01-01")
        key3 = create_match_key_exact("O Connor", "John", "M", "1990-01-01")

        # All should be the same after normalization
        expected = "oconnor|john|m|1990-01-01"
        self.assertEqual(key1, expected)
        self.assertEqual(key2, expected)
        self.assertEqual(key3, expected)

    def test_space_normalization(self):
        """Test that spaces are ignored in name normalization"""
        key1 = create_match_key_exact(
            "Van Der Berg", "Mary Ann", "F", "1985-05-15")
        key2 = create_match_key_exact(
            "VanDerBerg", "MaryAnn", "F", "1985-05-15")

        expected = "vanderberg|maryann|f|1985-05-15"
        self.assertEqual(key1, expected)
        self.assertEqual(key2, expected)

    def test_create_match_key_no_gender(self):
        """Test match key without gender"""
        key = create_match_key_no_gender(
            self.test_family, self.test_given, self.test_dob)
        expected = "smith|john|1990-01-01"
        self.assertEqual(key, expected)

        # Should match regardless of sex differences
        key_male = create_match_key_exact(
            self.test_family, self.test_given, "Male", self.test_dob)
        key_female = create_match_key_exact(
            self.test_family, self.test_given, "Female", self.test_dob)
        key_no_gender = create_match_key_no_gender(
            self.test_family, self.test_given, self.test_dob)

        self.assertNotEqual(key_male, key_female)  # Different with gender
        # Same without gender
        self.assertEqual(key_no_gender, "smith|john|1990-01-01")

    def test_create_match_key_name_only(self):
        """Test name-only match key for fuzzy date matching"""
        key = create_match_key_name_only(self.test_family, self.test_given)
        expected = "smith|john"
        self.assertEqual(key, expected)

        # Should be same regardless of date
        key1 = create_match_key_name_only(self.test_family, self.test_given)
        key2 = create_match_key_name_only(self.test_family, self.test_given)
        self.assertEqual(key1, key2)

    def test_create_match_key_flipped_names(self):
        """Test flipped names match key"""
        key = create_match_key_flipped_names(
            self.test_family, self.test_given, self.test_sex, self.test_dob)
        expected = "john|smith|male|1990-01-01"  # given|family instead of family|given
        self.assertEqual(key, expected)

        # Should catch data entry errors where names are swapped
        normal_key = create_match_key_exact(
            "Smith", "John", "Male", "1990-01-01")
        flipped_key = create_match_key_flipped_names(
            "John", "Smith", "Male", "1990-01-01")

        self.assertEqual(normal_key, flipped_key)

    def test_create_match_key_no_gender_flipped_names(self):
        """Test flipped names without gender"""
        key = create_match_key_no_gender_flipped_names(
            self.test_family, self.test_given, self.test_dob)
        expected = "john|smith|1990-01-01"
        self.assertEqual(key, expected)

    def test_create_match_key_no_suffix(self):
        """Test partial name matching with suffixes"""
        # Test that function exists and works
        key = create_match_key_no_suffix(
            "Smith Jr.", "John Michael", "Male", "1990-01-01")
        expected = "smith|john|male|1990-01-01"
        self.assertEqual(key, expected)

        # Test matching simplified version
        key_simple = create_match_key_no_suffix(
            "Smith ", " John", "Male", "1990-01-01")
        expected_simple = "smith|john|male|1990-01-01"
        self.assertEqual(key_simple, expected_simple)

    def test_empty_inputs(self):
        """Test handling of empty or None inputs"""
        key = create_match_key_exact("", "", "", "")
        expected = "|||"
        self.assertEqual(key, expected)

        # Test None handling would depend on normalize_string implementation
        # Assuming it returns empty string for None

    def test_special_characters(self):
        """Test handling of special characters in names"""
        key = create_match_key_exact(
            "Müller-Schmidt", "José María", "Male", "1990-01-01")
        # Should handle special characters consistently
        self.assertIsInstance(key, str)
        self.assertIn("|", key)  # Should still have separators

    def test_different_date_formats(self):
        """Test that different date formats normalize to same result"""
        formats = [
            "1990-01-01",
            "01/01/1990",
            "1990/01/01"
        ]

        keys = []
        for date_format in formats:
            key = create_match_key_exact("Smith", "John", "Male", date_format)
            keys.append(key)

        # All should normalize to same key
        for i in range(1, len(keys)):
            self.assertEqual(
                keys[0], keys[i], f"Date format {formats[i]} didn't normalize correctly")

    def test_match_key_consistency(self):
        """Test that all functions are consistent in their behavior"""
        family, given, sex, dob = "Smith", "John", "Male", "1990-01-01"

        # Test that all functions return strings
        functions = [
            create_match_key_exact,
            create_match_key_flipped_names,
            create_match_key_no_suffix
        ]

        for func in functions:
            key = func(family, given, sex, dob)
            self.assertIsInstance(key, str)
            self.assertGreater(len(key), 0)
            self.assertIn("|", key)  # Should have separators

        # Test functions without gender
        functions_no_gender = [
            create_match_key_no_gender,
            create_match_key_no_gender_flipped_names,
        ]

        for func in functions_no_gender:
            key = func(family, given, dob)
            self.assertIsInstance(key, str)
            self.assertGreater(len(key), 0)
            self.assertIn("|", key)

        # Name only function
        key = create_match_key_name_only(family, given)
        self.assertIsInstance(key, str)
        self.assertGreater(len(key), 0)
        self.assertIn("|", key)


if __name__ == "__main__":
    unittest.main()
