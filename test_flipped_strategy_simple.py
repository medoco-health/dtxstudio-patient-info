#!/usr/bin/env python3
"""
Test script for FlippedNamesFuzzyDateStrategy to verify it's working correctly.
"""

from dtxstudio_patient_info.utils.key_builders import create_flipped_name_only_key
from dtxstudio_patient_info.strategies.probabilistic import FlippedNamesFuzzyDateStrategy
from dtxstudio_patient_info.core.data_models import PatientRecord, MatchType
import sys
import os

# Add project root to path
sys.path.insert(0, '/home/afm/src/medoco/dtxstudio-patient-info')


def test_flipped_names_fuzzy_date():
    """Test the FlippedNamesFuzzyDateStrategy functionality."""
    print("🧪 Testing FlippedNamesFuzzyDateStrategy...")

    # Create test PMS lookup data
    pms_lookup = {
        # Normal name order in PMS
        "smith|john": {
            'last_name': 'Smith',
            'first_name': 'John',
            'gender': 'MALE',
            'dob': '1990-06-15',
            'custom_identifier': 'PMS123',
            'middle_initial': '',
            'ssn': 'SMTJHN90H15F205Z'
        }
    }

    # Create DTX record with flipped names and fuzzy date
    dtx_record = PatientRecord(
        family_name='John',     # Flipped - should be Smith
        given_name='Smith',     # Flipped - should be John
        sex='MALE',
        dob='1990-06-16',       # Off by one day (fuzzy match)
        dicom_id='DTX789'
    )

    # Test the strategy
    strategy = FlippedNamesFuzzyDateStrategy()

    print(
        f"📋 DTX Record: {dtx_record.given_name} {dtx_record.family_name}, {dtx_record.sex}, {dtx_record.dob}")
    print(f"📋 PMS Record: John Smith, MALE, 1990-06-15")
    print(
        f"🔍 Looking for flipped name key: {create_flipped_name_only_key(dtx_record.family_name, dtx_record.given_name)}")

    # Execute strategy
    result = strategy.execute(dtx_record, pms_lookup)

    if result and result.match_found:
        print("✅ Match found!")
        print(f"   Confidence: {result.confidence_score}")
        print(f"   Match Type: {result.match_type}")
        print(f"   Manual Review Required: {result.requires_manual_review}")
        print(f"   Name Flip Detected: {result.is_name_flip}")
        print(f"   Date Correction: {result.is_date_correction}")
        if hasattr(result.pms_data, 'given_name'):
            print(
                f"   Matched PMS Data: {result.pms_data.given_name} {result.pms_data.family_name}")
        else:
            print(f"   Matched PMS Data: {result.pms_data}")
        return True
    else:
        print("❌ No match found")
        print("   This might indicate the strategy needs more work")
        return False


def test_strategy_properties():
    """Test strategy properties."""
    print("\n🔧 Testing strategy properties...")

    strategy = FlippedNamesFuzzyDateStrategy()

    print(f"   Name: {strategy.name}")
    print(f"   Confidence Score: {strategy.confidence_score}")
    print(f"   Match Type: {strategy.match_type}")

    assert strategy.confidence_score == 0.65
    assert strategy.match_type == MatchType.FLIPPED_FUZZY_DOB
    print("✅ Properties are correct")


if __name__ == "__main__":
    print("🚀 FlippedNamesFuzzyDateStrategy Test Suite")
    print("=" * 50)

    # Test strategy properties
    test_strategy_properties()

    # Test actual matching
    success = test_flipped_names_fuzzy_date()

    print("\n" + "=" * 50)
    if success:
        print("🎉 FlippedNamesFuzzyDateStrategy is working correctly!")
    else:
        print("⚠️  FlippedNamesFuzzyDateStrategy needs further implementation")

    print("✅ Test completed - original PatientRecord error should be fixed")
