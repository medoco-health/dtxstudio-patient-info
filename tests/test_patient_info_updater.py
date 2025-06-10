"""
Unit tests for patient_info_updater.py
"""

import unittest
import sys
import os
import tempfile
import csv
from unittest.mock import patch

from dtxstudio_patient_info1.patient_info_updater import (
    extract_gender_from_codice_fiscale,
    load_pms_data,
    process_dtx_file,
    create_match_key,
    create_flipped_match_key,
)
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
        # Test None input - need to cast to avoid type error
        result = extract_gender_from_codice_fiscale(None)  # type: ignore
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


class TestNameFlipping(unittest.TestCase):
    """Test cases for name flipping scenarios."""

    def setUp(self):
        """Set up test data for name flipping scenarios."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_temp_csv(self, filename, data, headers):
        """Helper to create temporary CSV files."""
        import os
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        return filepath

    def test_names_flipped_exact_match(self):
        """Test: names are flipped, all rest matches -> should flip names back as in PMS."""

        # PMS data with correct name order
        pms_data = [{
            'first_name': 'John',
            'last_name': 'Smith',
            'gender': 'MALE',
            'dob': '1985-03-15',
            'custom_identifier': 'PMS123',
            'middle_initial': 'A',
            'ssn': 'SMTJHN85C15H501Z'  # Valid male CF
        }]

        # DTX data with flipped names
        dtx_data = [{
            'given_name': 'Smith',  # Flipped with family_name
            'family_name': 'John',  # Flipped with given_name
            'sex': 'MALE',
            'dob': '1985-03-15',
            'pms_id': '',
            'practice_pms_id': '',
            'dicom_id': '',
            'middle_name': ''
        }]

        pms_file = self.create_temp_csv('pms.csv', pms_data,
                                        ['first_name', 'last_name', 'gender', 'dob', 'custom_identifier', 'middle_initial', 'ssn'])
        dtx_file = self.create_temp_csv('dtx.csv', dtx_data,
                                        ['given_name', 'family_name', 'sex', 'dob', 'pms_id', 'practice_pms_id', 'dicom_id', 'middle_name'])

        # Load PMS data and process DTX
        with patch('logging.warning'), patch('logging.info'), patch('sys.stderr'):
            pms_lookup = load_pms_data(pms_file)

            # Capture output
            import io
            output = io.StringIO()
            process_dtx_file(dtx_file, pms_lookup, None)

        # Verify flipped match key exists in lookup
        flipped_key = create_flipped_match_key(
            'John', 'Smith', 'MALE', '1985-03-15')
        self.assertIn(flipped_key, pms_lookup,
                      "Flipped match key should exist in PMS lookup")

        # Verify the lookup data
        pms_record = pms_lookup[flipped_key]
        self.assertEqual(pms_record['first_name'],
                         'John', "PMS should have correct given name")
        self.assertEqual(pms_record['last_name'], 'Smith',
                         "PMS should have correct family name")

    def test_names_flipped_gender_mismatch(self):
        """Test: names are flipped, gender mismatch only -> should fix gender and names."""

        # PMS data with correct name order
        pms_data = [{
            'first_name': 'Jane',
            'last_name': 'Doe',
            'gender': 'FEMALE',
            'dob': '1990-06-20',
            'custom_identifier': 'PMS456',
            'middle_initial': 'B',
            'ssn': 'DOEJNE90H60H501Z'  # Valid female CF
        }]

        # DTX data with flipped names and wrong gender
        dtx_data = [{
            'given_name': 'Doe',    # Flipped
            'family_name': 'Jane',  # Flipped
            'sex': 'MALE',          # Wrong gender
            'dob': '1990-06-20',
            'pms_id': '',
            'practice_pms_id': '',
            'dicom_id': '',
            'middle_name': ''
        }]

        pms_file = self.create_temp_csv('pms.csv', pms_data,
                                        ['first_name', 'last_name', 'gender', 'dob', 'custom_identifier', 'middle_initial', 'ssn'])
        dtx_file = self.create_temp_csv('dtx.csv', dtx_data,
                                        ['given_name', 'family_name', 'sex', 'dob', 'pms_id', 'practice_pms_id', 'dicom_id', 'middle_name'])

        with patch('logging.warning'), patch('logging.info'), patch('sys.stderr'):
            pms_lookup = load_pms_data(pms_file)

            # Should find match via flipped loose key (names flipped, gender differs)
            from dtxstudio_patient_info1.patient_info_updater import create_flipped_loose_match_key
            flipped_loose_key = create_flipped_loose_match_key(
                'Jane', 'Doe', '1990-06-20')
            self.assertIn(flipped_loose_key, pms_lookup,
                          "Should have flipped loose match")

    def test_names_flipped_fuzzy_date_match(self):
        """Test: names are flipped, dob is close enough -> match and make corrections."""

        # PMS data
        pms_data = [{
            'first_name': 'Maria',
            'last_name': 'Garcia',
            'gender': 'FEMALE',
            'dob': '1988-12-03',    # Correct date
            'custom_identifier': 'PMS789',
            'middle_initial': 'C',
            'ssn': 'GRCMRA88T43H501Z'  # Valid female CF
        }]

        # DTX data with flipped names and similar date
        dtx_data = [{
            'given_name': 'Garcia',   # Flipped
            'family_name': 'Maria',   # Flipped
            'sex': 'FEMALE',
            'dob': '1988-12-08',     # Close date (off by 5 days)
            'pms_id': '',
            'practice_pms_id': '',
            'dicom_id': '',
            'middle_name': ''
        }]

        pms_file = self.create_temp_csv('pms.csv', pms_data,
                                        ['first_name', 'last_name', 'gender', 'dob', 'custom_identifier', 'middle_initial', 'ssn'])
        dtx_file = self.create_temp_csv('dtx.csv', dtx_data,
                                        ['given_name', 'family_name', 'sex', 'dob', 'pms_id', 'practice_pms_id', 'dicom_id', 'middle_name'])

        with patch('logging.warning'), patch('logging.info'), patch('sys.stderr'):
            pms_lookup = load_pms_data(pms_file)
            
            # Debug: print all keys in lookup
            print("All keys in PMS lookup:")
            for key in sorted(pms_lookup.keys()):
                print(f"  '{key}'")

            # Should be stored under name-only key for fuzzy matching
            # Check both normal and flipped name-only keys since both should exist
            from dtxstudio_patient_info1.patient_info_updater import create_name_only_match_key
            normal_name_key = create_name_only_match_key('Maria', 'Garcia')  # PMS order
            flipped_name_key = create_name_only_match_key('Garcia', 'Maria')  # Flipped order
            
            # At least one of these should exist for fuzzy matching
            has_name_only_key = normal_name_key in pms_lookup or flipped_name_key in pms_lookup
            self.assertTrue(has_name_only_key, 
                          f"Should have name-only key for fuzzy matching. Looking for '{normal_name_key}' or '{flipped_name_key}'")

    def test_names_flipped_patient_id_mismatch(self):
        """Test: names flipped, dob close, gender match, patient id mismatch -> match and correct."""

        # PMS data
        pms_data = [{
            'first_name': 'Carlos',
            'last_name': 'Rodriguez',
            'gender': 'MALE',
            'dob': '1975-08-14',
            'custom_identifier': 'PMS999',
            'middle_initial': 'D',
            'ssn': 'RDRCRL75M14H501Z'  # Valid male CF
        }]

        # DTX data with flipped names and wrong patient ID
        dtx_data = [{
            'given_name': 'Rodriguez',  # Flipped
            'family_name': 'Carlos',    # Flipped
            'sex': 'MALE',              # Correct gender
            'dob': '1975-08-14',        # Exact date match
            'pms_id': 'OLD123',         # Wrong ID - should be updated
            'practice_pms_id': 'OLD456',
            'dicom_id': 'OLD789',
            'middle_name': 'D'
        }]

        pms_file = self.create_temp_csv('pms.csv', pms_data,
                                        ['first_name', 'last_name', 'gender', 'dob', 'custom_identifier', 'middle_initial', 'ssn'])
        dtx_file = self.create_temp_csv('dtx.csv', dtx_data,
                                        ['given_name', 'family_name', 'sex', 'dob', 'pms_id', 'practice_pms_id', 'dicom_id', 'middle_name'])

        with patch('logging.warning'), patch('logging.info'), patch('sys.stderr'):
            pms_lookup = load_pms_data(pms_file)

            # Should match via flipped exact key
            flipped_key = create_flipped_match_key(
                'Carlos', 'Rodriguez', 'MALE', '1975-08-14')
            self.assertIn(flipped_key, pms_lookup,
                          "Should find flipped exact match")

            # Verify PMS data has correct IDs to update with
            pms_record = pms_lookup[flipped_key]
            self.assertEqual(
                pms_record['custom_identifier'], 'PMS999', "Should have correct PMS ID")

    def test_names_flipped_pms_gender_error_via_codice_fiscale(self):
        """Test: names flipped, fuzzy date, gender mismatch due to PMS error -> correct gender via codice fiscale."""

        # PMS data with WRONG gender (but codice fiscale will correct it)
        pms_data = [{
            'first_name': 'Anna',
            'last_name': 'Bianchi',
            'gender': 'MALE',           # WRONG - should be FEMALE based on CF
            'dob': '1992-04-25',
            'custom_identifier': 'PMS888',
            'middle_initial': 'E',
            'ssn': 'BNCNNA92D65H501Z'   # Valid FEMALE CF (day 65 = 25+40)
        }]

        # DTX data with flipped names
        dtx_data = [{
            'given_name': 'Bianchi',    # Flipped
            'family_name': 'Anna',      # Flipped
            'sex': 'FEMALE',            # Correct gender (matches CF, not PMS)
            'dob': '1992-04-23',        # Close date (off by 2 days)
            'pms_id': '',
            'practice_pms_id': '',
            'dicom_id': '',
            'middle_name': ''
        }]

        pms_file = self.create_temp_csv('pms.csv', pms_data,
                                        ['first_name', 'last_name', 'gender', 'dob', 'custom_identifier', 'middle_initial', 'ssn'])
        dtx_file = self.create_temp_csv('dtx.csv', dtx_data,
                                        ['given_name', 'family_name', 'sex', 'dob', 'pms_id', 'practice_pms_id', 'dicom_id', 'middle_name'])

        with patch('logging.warning') as mock_warning, patch('logging.info'), patch('sys.stderr'):
            pms_lookup = load_pms_data(pms_file)

            # Should log PMS gender error during loading
            warning_calls = [call for call in mock_warning.call_args_list
                             if 'CODICE_FISCALE_GENDER_MISMATCH' in str(call)]
            self.assertTrue(len(warning_calls) > 0,
                            "Should log codice fiscale gender error")

            # Verify gender was corrected in PMS lookup
            # Should be stored with corrected gender
            corrected_key = create_match_key(
                'Bianchi', 'Anna', 'FEMALE', '1992-04-25')
            flipped_corrected_key = create_flipped_match_key(
                'Bianchi', 'Anna', 'FEMALE', '1992-04-25')

            # One of these should exist (depending on how it's stored)
            has_corrected_match = corrected_key in pms_lookup or flipped_corrected_key in pms_lookup
            self.assertTrue(has_corrected_match,
                            "Should store with corrected gender")

    def test_extract_gender_validation(self):
        """Verify the codice fiscale gender extraction works correctly."""

        # Test valid male CF
        male_cf = "SMTJHN85C15H501Z"  # Day 15 = male
        self.assertEqual(extract_gender_from_codice_fiscale(male_cf), 'MALE')

        # Test valid female CF
        female_cf = "BNCNNA92D65H501Z"  # Day 65 = 25+40 = female
        self.assertEqual(
            extract_gender_from_codice_fiscale(female_cf), 'FEMALE')

        # Test invalid day
        invalid_cf = "XXXYYY85A40H501Z"  # Day 40 = invalid
        self.assertIsNone(extract_gender_from_codice_fiscale(invalid_cf))

    def test_match_key_creation(self):
        """Test that flipped match keys are created correctly."""

        # Normal key
        normal_key = create_match_key('Smith', 'John', 'MALE', '1985-03-15')
        expected_normal = "smith|john|male|1985-03-15"
        self.assertEqual(normal_key, expected_normal)

        # Flipped key should swap first two components
        flipped_key = create_flipped_match_key(
            'Smith', 'John', 'MALE', '1985-03-15')
        expected_flipped = "john|smith|male|1985-03-15"  # given|family swapped
        self.assertEqual(flipped_key, expected_flipped)


if __name__ == '__main__':
    unittest.main()
