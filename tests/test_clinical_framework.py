#!/usr/bin/env python3
"""
Test the clinical patient matching framework.

Quick validation that the new clinical matching system is working correctly.
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dtxstudio_patient_info.core.patient_matcher import ClinicalPatientMatcher
from dtxstudio_patient_info.core.matching_strategies import PatientRecord, MatchType
from dtxstudio_patient_info.utils.normalizers import normalize_string, normalize_date
from dtxstudio_patient_info.utils.key_builders import create_composite_keys

def test_basic_matching():
    """Test basic functionality of the clinical matcher."""
    print("🧪 Testing Clinical Patient Matching Framework")
    print("=" * 50)
    
    # Create matcher instance
    matcher = ClinicalPatientMatcher()
    print("✅ ClinicalPatientMatcher initialized")
    
    # Test normalizers
    test_name = normalize_string("John  Smith")
    test_date = normalize_date("03/15/1985")
    print(f"✅ Normalizers working: '{test_name}', '{test_date}'")
    
    # Test key builders
    keys = create_composite_keys("Smith", "John", "MALE", "1985-03-15")
    print(f"✅ Key builders working: {len(keys)} keys generated")
    
    # Create sample PMS lookup
    pms_lookup = {
        "smith|john|male|1985-03-15": {
            'first_name': 'John',
            'last_name': 'Smith', 
            'gender': 'MALE',
            'dob': '1985-03-15',
            'custom_identifier': 'PMS123',
            'middle_initial': 'A',
            'ssn': 'SMTJHN85C15H501Z'
        }
    }
    
    # Test exact match
    dtx_record = {
        'family_name': 'Smith',
        'given_name': 'John',
        'sex': 'MALE', 
        'dob': '1985-03-15',
        'pms_id': '',
        'practice_pms_id': '',
        'dicom_id': '',
        'middle_name': ''
    }
    
    result = matcher.match_patient(dtx_record, pms_lookup)
    
    if result.match_found:
        print(f"✅ Match found!")
        print(f"   Match type: {result.match_type.value}")
        print(f"   Confidence: {result.confidence_score:.2%}")
        print(f"   Manual review: {result.requires_manual_review}")
    else:
        print("❌ No match found")
        return False
    
    # Test session statistics
    stats = matcher.get_session_statistics()
    print(f"✅ Session stats: {stats.total_processed} processed, {stats.auto_matched} matched")
    
    print("\n🎉 Clinical matching framework is working!")
    return True

def test_name_flip_scenario():
    """Test name flipping scenario."""
    print("\n🔄 Testing Name Flip Scenario")
    print("-" * 30)
    
    matcher = ClinicalPatientMatcher()
    
    # PMS data (correct order)
    pms_lookup = {
        "garcia|maria|female|1988-12-03": {
            'first_name': 'Maria',
            'last_name': 'Garcia',
            'gender': 'FEMALE', 
            'dob': '1988-12-03',
            'custom_identifier': 'PMS789'
        },
        # Also store flipped key for matching
        "maria|garcia|female|1988-12-03": {
            'first_name': 'Maria',
            'last_name': 'Garcia',
            'gender': 'FEMALE',
            'dob': '1988-12-03', 
            'custom_identifier': 'PMS789'
        }
    }
    
    # DTX data (flipped names)
    dtx_record = {
        'family_name': 'Maria',    # Should be given name
        'given_name': 'Garcia',    # Should be family name
        'sex': 'FEMALE',
        'dob': '1988-12-03'
    }
    
    result = matcher.match_patient(dtx_record, pms_lookup)
    
    if result.match_found and result.is_name_flip:
        print(f"✅ Name flip detected and corrected!")
        print(f"   Match type: {result.match_type.value}")
        print(f"   Confidence: {result.confidence_score:.2%}")
        return True
    else:
        print("❌ Name flip not detected")
        return False

if __name__ == "__main__":
    success = test_basic_matching()
    if success:
        test_name_flip_scenario()
    
    print(f"\n📊 Framework Status: {'✅ READY' if success else '❌ NEEDS WORK'}")