"""
Simple test script to verify FlippedNamesFuzzyDateStrategy functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dtxstudio_patient_info.strategies.probabilistic import FlippedNamesFuzzyDateStrategy
from dtxstudio_patient_info.core.data_models import PatientRecord, MatchType
from dtxstudio_patient_info.core.patient_matcher import ClinicalPatientMatcher

def test_strategy_properties():
    """Test basic strategy properties."""
    print("Testing FlippedNamesFuzzyDateStrategy properties...")
    
    strategy = FlippedNamesFuzzyDateStrategy()
    
    print(f"✓ Name: {strategy.name}")
    print(f"✓ Confidence: {strategy.confidence_score}")
    print(f"✓ Match Type: {strategy.match_type}")
    
    assert strategy.name == "Flipped Names with Fuzzy Date"
    assert strategy.confidence_score == 0.65
    assert strategy.match_type == MatchType.FLIPPED_FUZZY_DOB
    
    print("✓ All properties correct!")

def test_strategy_in_matcher():
    """Test that strategy is integrated in matcher."""
    print("\nTesting strategy integration...")
    
    matcher = ClinicalPatientMatcher()
    strategy_names = [s.__class__.__name__ for s in matcher.strategy_instances]
    
    print(f"Available strategies: {strategy_names}")
    
    assert 'FlippedNamesFuzzyDateStrategy' in strategy_names
    print("✓ FlippedNamesFuzzyDateStrategy is integrated!")
    
    # Find its position
    index = next(i for i, s in enumerate(matcher.strategy_instances) 
                 if s.__class__.__name__ == 'FlippedNamesFuzzyDateStrategy')
    print(f"✓ Strategy position: {index + 1} of {len(matcher.strategy_instances)}")

def test_simple_execution():
    """Test simple strategy execution."""
    print("\nTesting strategy execution...")
    
    strategy = FlippedNamesFuzzyDateStrategy()
    
    dtx_record = PatientRecord(
        family_name="Test",
        given_name="Patient",
        sex="MALE",
        dob="2000-01-01"
    )
    
    # Empty lookup should return None
    result = strategy.execute(dtx_record, {})
    assert result is None
    print("✓ Empty lookup returns None")
    
    print("✓ Strategy execution works!")

if __name__ == "__main__":
    print("=== FlippedNamesFuzzyDateStrategy Test ===")
    
    try:
        test_strategy_properties()
        test_strategy_in_matcher()
        test_simple_execution()
        
        print("\n🎉 All tests passed! FlippedNamesFuzzyDateStrategy is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)