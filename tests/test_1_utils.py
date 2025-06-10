import unittest
from dtxstudio_patient_info1.utils import normalize_string


class TestNormalizeString(unittest.TestCase):
    """Test the normalize_string function, especially accent removal."""

    def test_accent_removal(self):
        """Test that accents and diacritical marks are properly removed."""
        # Spanish names
        self.assertEqual(normalize_string("José"), "jose")
        self.assertEqual(normalize_string("Jose"), "jose")
        self.assertEqual(normalize_string("Andrés"), "andres")
        self.assertEqual(normalize_string("Andres"), "andres")

        # French names
        self.assertEqual(normalize_string("François"), "francois")
        self.assertEqual(normalize_string("Francois"), "francois")
        self.assertEqual(normalize_string("Élise"), "elise")
        self.assertEqual(normalize_string("Elise"), "elise")

        # German names
        self.assertEqual(normalize_string("Müller"), "muller")
        self.assertEqual(normalize_string("Muller"), "muller")
        self.assertEqual(normalize_string("Jürgen"), "jurgen")
        self.assertEqual(normalize_string("Jurgen"), "jurgen")

        # Italian names
        self.assertEqual(normalize_string("Niccolò"), "niccolo")
        self.assertEqual(normalize_string("Niccolo"), "niccolo")

    def test_mixed_accents_and_cases(self):
        """Test names with mixed accents and different cases."""
        self.assertEqual(normalize_string("JOSÉ"), "jose")
        self.assertEqual(normalize_string("josé"), "jose")
        self.assertEqual(normalize_string("JoSé"), "jose")

    def test_spaces_and_apostrophes(self):
        """Test that spaces and apostrophes are still removed."""
        self.assertEqual(normalize_string("O'Connor"), "oconnor")
        self.assertEqual(normalize_string("Van Der Berg"), "vanderberg")
        self.assertEqual(normalize_string("D'Angelo"), "dangelo")

    def test_combined_accents_spaces_apostrophes(self):
        """Test names with accents, spaces, and apostrophes combined."""
        self.assertEqual(normalize_string("José María"), "josemaria")
        self.assertEqual(normalize_string("O'Reilly"), "oreilly")
        self.assertEqual(normalize_string(
            "François D'Aubigny"), "francoisdaubigny")

    def test_empty_and_none(self):
        """Test edge cases with empty strings."""
        self.assertEqual(normalize_string(""), "")
        self.assertEqual(normalize_string("   "), "")

    def test_numbers_and_special_chars(self):
        """Test that numbers and other characters are preserved."""
        self.assertEqual(normalize_string("Smith2"), "smith2")
        self.assertEqual(normalize_string("Jean-Claude"), "jean-claude")


if __name__ == '__main__':
    unittest.main()
