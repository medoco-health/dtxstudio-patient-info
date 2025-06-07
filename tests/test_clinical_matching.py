"""
Comprehensive test suite for the clinical matching framework.

Tests all matching strategies, edge cases, and clinical data quality scenarios.
"""

from dtxstudio_patient_info.utils.italian_cf import extract_gender_from_codice_fiscale, validate_codice_fiscale_gender
from dtxstudio_patient_info.utils.key_builders import create_exact_match_key, create_flipped_exact_key
from dtxstudio_patient_info.utils.normalizers import normalize_string, normalize_date, is_partial_name_match
from dtxstudio_patient_info.core.data_models import PatientRecord, MatchType
from dtxstudio_patient_info.core.patient_matcher import ClinicalPatientMatcher
import unittest
from typing import Dict, Any
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestClinicalPatientMatcher(unittest.TestCase):
    """Test suite for the main clinical patient matcher."""

    def setUp(self):
        """Set up test fixtures."""
        self.matcher = ClinicalPatientMatcher()

        # Sample PMS data for testing
        self.sample_pms_data = {
            # Perfect match case
            "smith|john|male|1990-01-15": {
                "first_name": "John",
                "last_name": "Smith",
                "gender": "Male",
                "dob": "1990-01-15",
                "pms_id": "PMS001"
            },

            # Gender mismatch case
            "doe|jane|female|1985-03-22": {
                "first_name": "Jane",
                "last_name": "Doe",
                "gender": "Female",
                "dob": "1985-03-22",
                "pms_id": "PMS002"
            },

            # Flipped names case
            "brown|mary|female|1992-07-08": {
                "first_name": "Mary",
                "last_name": "Brown",
                "gender": "Female",
                "dob": "1992-07-08",
                "pms_id": "PMS003"
            },

            # Case for partial matching (DTX has suffix)
            "johnson|robert|male|1988-12-03": {
                "first_name": "Robert",
                "last_name": "Johnson",
                "gender": "Male",
                "dob": "1988-12-03",
                "pms_id": "PMS004"
            }
        }

    def test_gold_standard_match(self):
        """Test perfect exact matching (100% confidence)."""
        dtx_record = PatientRecord(
            family_name="Smith",
            given_name="John",
            sex="Male",
            dob="1990-01-15",
            source_system="dtx"
        )

        result = self.matcher.match_patient(dtx_record, self.sample_pms_data)

        self.assertTrue(result.match_found)
        self.assertEqual(result.match_type, MatchType.GOLD_STANDARD)
        self.assertEqual(result.confidence_score, 1.0)
        self.assertFalse(result.requires_manual_review)
        self.assertEqual(result.pms_data["pms_id"], "PMS001")

    def test_exact_names_gender_loose(self):
        """Test exact names with gender flexibility."""
        # Create case where gender differs but names/DOB match
        pms_data_gender_diff = self.sample_pms_data.copy()
        pms_data_gender_diff["smith|john|female|1990-01-15"] = {
            "first_name": "John",
            "last_name": "Smith",
            "gender": "Female",  # Different gender
            "dob": "1990-01-15",
            "pms_id": "PMS001"
        }

        dtx_record = PatientRecord(
            family_name="Smith",
            given_name="John",
            sex="Male",  # Different from PMS
            dob="1990-01-15",
            source_system="dtx"
        )

        result = self.matcher.match_patient(dtx_record, pms_data_gender_diff)

        self.assertTrue(result.match_found)
        self.assertEqual(result.match_type, MatchType.EXACT_GENDER_LOOSE)
        self.assertEqual(result.confidence_score, 0.98)

    def test_flipped_names_exact(self):
        """Test flipped name matching."""
        dtx_record = PatientRecord(
            family_name="Mary",  # Flipped: should be Brown
            given_name="Brown",  # Flipped: should be Mary
            sex="Female",
            dob="1992-07-08",
            source_system="dtx"
        )

        result = self.matcher.match_patient(dtx_record, self.sample_pms_data)

        self.assertTrue(result.match_found)
        self.assertEqual(result.match_type, MatchType.FLIPPED_EXACT)
        self.assertEqual(result.confidence_score, 0.97)
        self.assertIn("name_flip_detected", result.match_details)

    def test_partial_names_exact(self):
        """Test partial name matching (DTX has suffixes)."""
        # Add partial match case to PMS data
        pms_data_partial = self.sample_pms_data.copy()
        pms_data_partial["wilson|james|male|1985-06-12"] = {
            "first_name": "James",
            "last_name": "Wilson",
            "gender": "Male",
            "dob": "1985-06-12",
            "pms_id": "PMS005"
        }

        dtx_record = PatientRecord(
            family_name="Wilson BIS",  # DTX has suffix
            given_name="James TRIS",   # DTX has suffix
            sex="Male",
            dob="1985-06-12",
            source_system="dtx"
        )

        result = self.matcher.match_patient(dtx_record, pms_data_partial)

        self.assertTrue(result.match_found)
        self.assertEqual(result.match_type, MatchType.PARTIAL_EXACT)
        self.assertEqual(result.confidence_score, 0.85)
        self.assertIn("suffix_removal_detected", result.match_details)

    def test_no_match_found(self):
        """Test case where no match is found."""
        dtx_record = PatientRecord(
            family_name="NoMatch",
            given_name="Person",
            sex="Unknown",
            dob="2000-01-01",
            source_system="dtx"
        )

        result = self.matcher.match_patient(dtx_record, self.sample_pms_data)

        self.assertFalse(result.match_found)
        self.assertEqual(result.match_type, MatchType.NO_MATCH)
        self.assertEqual(result.confidence_score, 0.0)
        self.assertIsNone(result.pms_data)

    def test_match_from_dict(self):
        """Test convenience method for dictionary input."""
        dtx_dict = {
            'family_name': 'Smith',
            'given_name': 'John',
            'sex': 'Male',
            'dob': '1990-01-15'
        }

        result = self.matcher.match_from_dict(dtx_dict, self.sample_pms_data)

        self.assertTrue(result.match_found)
        self.assertEqual(result.match_type, MatchType.GOLD_STANDARD)

    def test_session_statistics(self):
        """Test session statistics tracking."""
        # Reset statistics
        self.matcher.reset_statistics()

        # Run several matches
        test_records = [
            PatientRecord("Smith", "John", "Male",
                          "1990-01-15", source_system="dtx"),
            PatientRecord("Doe", "Jane", "Female",
                          "1985-03-22", source_system="dtx"),
            PatientRecord("NoMatch", "Person", "Unknown",
                          "2000-01-01", source_system="dtx")
        ]

        for record in test_records:
            self.matcher.match_patient(record, self.sample_pms_data)

        stats = self.matcher.get_session_statistics()

        self.assertEqual(stats.total_processed, 3)
        self.assertEqual(stats.auto_matched, 2)  # Smith and Doe
        self.assertEqual(stats.no_matches, 1)    # NoMatch


class TestNormalizers(unittest.TestCase):
    """Test suite for data normalization utilities."""

    def test_normalize_string(self):
        """Test string normalization."""
        self.assertEqual(normalize_string("John Smith"), "johnsmith")
        self.assertEqual(normalize_string("  MARY  JANE  "), "maryjane")
        self.assertEqual(normalize_string(""), "")
        self.assertEqual(normalize_string("O'Connor"), "o'connor")

    def test_normalize_date(self):
        """Test date normalization."""
        self.assertEqual(normalize_date("1990-01-15"), "1990-01-15")
        self.assertEqual(normalize_date("01/15/1990"), "1990-01-15")
        self.assertEqual(normalize_date("15/01/1990"), "1990-01-15")
        self.assertEqual(normalize_date("invalid"), "invalid")

    def test_is_partial_name_match(self):
        """Test partial name matching."""
        # Standard cases
        self.assertTrue(is_partial_name_match("John", "John BIS"))
        self.assertTrue(is_partial_name_match("Smith", "Smith TRIS"))
        self.assertFalse(is_partial_name_match("John", "Jane"))
        self.assertFalse(is_partial_name_match("", "John"))

        # Case insensitive
        self.assertTrue(is_partial_name_match("john", "JOHN BIS"))
        self.assertTrue(is_partial_name_match("SMITH", "smith tris"))


class TestKeyBuilders(unittest.TestCase):
    """Test suite for match key generation."""

    def test_create_exact_match_key(self):
        """Test exact match key creation."""
        key = create_exact_match_key("Smith", "John", "Male", "1990-01-15")
        self.assertEqual(key, "smith|john|male|1990-01-15")

    def test_create_flipped_exact_key(self):
        """Test flipped exact match key creation."""
        key = create_flipped_exact_key("Smith", "John", "Male", "1990-01-15")
        self.assertEqual(key, "john|smith|male|1990-01-15")

    def test_key_normalization(self):
        """Test that keys are properly normalized."""
        key1 = create_exact_match_key(
            "  Smith  ", "JOHN", "male", "1990-01-15")
        key2 = create_exact_match_key("smith", "john", "MALE", "1990-01-15")

        # Should be the same after normalization
        self.assertEqual(key1, key2)


class TestItalianCodiceFiscale(unittest.TestCase):
    """Test suite for Italian codice fiscale utilities."""

    def test_extract_gender_from_codice_fiscale(self):
        """Test gender extraction from codice fiscale."""
        # Male examples (day 01-31)
        self.assertEqual(extract_gender_from_codice_fiscale(
            "RSSMRA85A15H501Z"), "MALE")
        self.assertEqual(extract_gender_from_codice_fiscale(
            "BNCGVN70C01F205X"), "MALE")

        # Female examples (day 41-71, i.e., actual day + 40)
        self.assertEqual(extract_gender_from_codice_fiscale(
            "RSSMRA85A55H501Z"), "FEMALE")  # 55 = 15 + 40
        self.assertEqual(extract_gender_from_codice_fiscale(
            "BNCGVN70C41F205X"), "FEMALE")  # 41 = 01 + 40

        # Invalid cases
        self.assertIsNone(extract_gender_from_codice_fiscale(""))
        self.assertIsNone(extract_gender_from_codice_fiscale("SHORT"))
        self.assertIsNone(extract_gender_from_codice_fiscale(
            "INVALID99A99H501Z"))  # Day 99 invalid

    def test_validate_codice_fiscale_gender(self):
        """Test gender validation against codice fiscale."""
        # Valid cases
        is_valid, correction = validate_codice_fiscale_gender(
            "MALE", "RSSMRA85A15H501Z")
        self.assertTrue(is_valid)
        self.assertIsNone(correction)

        is_valid, correction = validate_codice_fiscale_gender(
            "FEMALE", "RSSMRA85A55H501Z")
        self.assertTrue(is_valid)
        self.assertIsNone(correction)

        # Invalid case - gender mismatch
        is_valid, correction = validate_codice_fiscale_gender(
            "FEMALE", "RSSMRA85A15H501Z")
        self.assertFalse(is_valid)
        self.assertEqual(correction, "MALE")

        # No SSN provided
        is_valid, correction = validate_codice_fiscale_gender("MALE", "")
        self.assertTrue(is_valid)  # Cannot validate without SSN
        self.assertIsNone(correction)


class TestClinicalScenarios(unittest.TestCase):
    """Test suite for realistic clinical data scenarios."""

    def setUp(self):
        """Set up clinical test scenarios."""
        self.matcher = ClinicalPatientMatcher()

        # Realistic Italian healthcare PMS data
        self.clinical_pms_data = {
            "rossi|mario|male|1975-03-12": {
                "first_name": "Mario",
                "last_name": "Rossi",
                "gender": "Male",
                "dob": "1975-03-12",
                "pms_id": "PMS001",
                "ssn": "RSSMRA75C12H501Z"
            },
            "bianchi|giulia|female|1988-07-25": {
                "first_name": "Giulia",
                "last_name": "Bianchi",
                "gender": "Female",
                "dob": "1988-07-25",
                "pms_id": "PMS002",
                "ssn": "BNCGLI88L65H501X"  # 65 = 25 + 40 for female
            }
        }

    def test_italian_suffix_scenario(self):
        """Test common Italian name suffix scenario."""
        # DTX often has suffixes like BIS, TRIS for multiple registrations
        dtx_record = PatientRecord(
            family_name="Rossi BIS",
            given_name="Mario TRIS",
            sex="Male",
            dob="1975-03-12",
            source_system="dtx"
        )

        result = self.matcher.match_patient(dtx_record, self.clinical_pms_data)

        self.assertTrue(result.match_found)
        self.assertEqual(result.match_type, MatchType.PARTIAL_EXACT)
        self.assertGreaterEqual(result.confidence_score, 0.85)

    def test_gender_data_quality_issue(self):
        """Test handling of gender data quality issues."""
        # Create scenario where DTX has wrong gender but names/DOB match
        clinical_data_wrong_gender = self.clinical_pms_data.copy()
        clinical_data_wrong_gender["rossi|mario|female|1975-03-12"] = {
            "first_name": "Mario",
            "last_name": "Rossi",
            "gender": "Female",  # Wrong gender in PMS
            "dob": "1975-03-12",
            "pms_id": "PMS001",
            "ssn": "RSSMRA75C12H501Z"  # SSN indicates MALE
        }

        dtx_record = PatientRecord(
            family_name="Rossi",
            given_name="Mario",
            sex="Male",  # Correct gender in DTX
            dob="1975-03-12",
            source_system="dtx"
        )

        result = self.matcher.match_patient(
            dtx_record, clinical_data_wrong_gender)

        self.assertTrue(result.match_found)
        self.assertEqual(result.match_type, MatchType.EXACT_GENDER_LOOSE)
        self.assertGreater(result.confidence_score, 0.95)

    def test_clinical_warnings_generation(self):
        """Test that clinical warnings are properly generated."""
        # Test with codice fiscale gender mismatch
        pms_data_cf_issue = {
            "test|patient|male|1990-01-15": {
                "first_name": "Patient",
                "last_name": "Test",
                "gender": "Male",
                "dob": "1990-01-15",
                "pms_id": "PMS999",
                "ssn": "TSTPNT90A55H501Z"  # 55 indicates FEMALE, but PMS says MALE
            }
        }

        dtx_record = PatientRecord(
            family_name="Test",
            given_name="Patient",
            sex="Male",
            dob="1990-01-15",
            source_system="dtx"
        )

        result = self.matcher.match_patient(dtx_record, pms_data_cf_issue)

        self.assertTrue(result.match_found)
        # Should have clinical warnings about codice fiscale mismatch
        self.assertTrue(len(result.clinical_warnings) > 0)


def run_clinical_matching_tests():
    """Run the complete test suite for clinical matching."""

    # Create test suite
    test_suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestClinicalPatientMatcher,
        TestNormalizers,
        TestKeyBuilders,
        TestItalianCodiceFiscale,
        TestClinicalScenarios
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print(f"\n{'='*70}")
    print("CLINICAL MATCHING TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print(f"\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")

    if result.errors:
        print(f"\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")

    success_rate = ((result.testsRun - len(result.failures) -
                    len(result.errors)) / result.testsRun) * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")

    return result.wasSuccessful()


if __name__ == "__main__":
    print("Starting Clinical Patient Matching Test Suite...")
    print("Testing all matching strategies, edge cases, and clinical scenarios.")
    print(f"{'='*70}")

    success = run_clinical_matching_tests()

    if success:
        print("\n✅ All tests passed! Clinical matching framework is ready for use.")
    else:
        print("\n❌ Some tests failed. Please review the output above.")
        sys.exit(1)
