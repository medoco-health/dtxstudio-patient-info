"""
Clinical Reporting Service

Service for generating clinical audit reports and statistics.
"""

import sys
from typing import List

from .data_models import SessionStatistics


class ClinicalReportingService:
    """Service for generating clinical reports and audit trails."""
    
    @staticmethod
    def generate_audit_report(stats: SessionStatistics, manual_review_queue: List[dict]):
        """Generate comprehensive clinical audit report."""
        print("\n" + "="*70, file=sys.stderr)
        print("CLINICAL PATIENT MATCHING AUDIT REPORT", file=sys.stderr)
        print("="*70, file=sys.stderr)
        
        ClinicalReportingService._print_overall_statistics(stats)
        ClinicalReportingService._print_confidence_distribution(stats)
        ClinicalReportingService._print_correction_types(stats)
        ClinicalReportingService._print_manual_review_queue(manual_review_queue)
    
    @staticmethod
    def _print_overall_statistics(stats: SessionStatistics):
        """Print overall statistics section."""
        print(f"\nOVERALL STATISTICS:", file=sys.stderr)
        print(f"Total records processed: {stats.total_processed:,}", file=sys.stderr)
        print(f"Automatic matches: {stats.auto_matched:,} ({stats.get_auto_match_rate():.1%})", file=sys.stderr)
        
        manual_review_rate = (stats.manual_review_required / stats.total_processed 
                            if stats.total_processed > 0 else 0)
        print(f"Manual review required: {stats.manual_review_required:,} ({manual_review_rate:.1%})", file=sys.stderr)
        
        no_match_rate = (stats.no_matches / stats.total_processed 
                        if stats.total_processed > 0 else 0)
        print(f"No matches found: {stats.no_matches:,} ({no_match_rate:.1%})", file=sys.stderr)
    
    @staticmethod
    def _print_confidence_distribution(stats: SessionStatistics):
        """Print confidence level distribution."""
        print(f"\nCONFIDENCE LEVEL DISTRIBUTION:", file=sys.stderr)
        print(f"  Gold standard (100%): {stats.gold_standard_matches:,}", file=sys.stderr)
        print(f"  High confidence (95-99%): {stats.high_confidence_matches:,}", file=sys.stderr)
        print(f"  Moderate confidence (80-95%): {stats.moderate_confidence_matches:,}", file=sys.stderr)
        print(f"  Acceptable confidence (70-80%): {stats.acceptable_confidence_matches:,}", file=sys.stderr)
    
    @staticmethod
    def _print_correction_types(stats: SessionStatistics):
        """Print correction type distribution."""
        print(f"\nCORRECTION TYPE DISTRIBUTION:", file=sys.stderr)
        print(f"  Gender corrections: {stats.gender_corrections:,}", file=sys.stderr)
        print(f"  Date corrections: {stats.date_corrections:,}", file=sys.stderr)
        print(f"  Name flips corrected: {stats.name_flips:,}", file=sys.stderr)
        print(f"  Partial name matches: {stats.partial_name_matches:,}", file=sys.stderr)
        print(f"  PMS gender errors corrected: {stats.pms_gender_errors:,}", file=sys.stderr)
    
    @staticmethod
    def _print_manual_review_queue(manual_review_queue: List[dict]):
        """Print manual review queue details."""
        if not manual_review_queue:
            return
            
        print(f"\nMANUAL REVIEW QUEUE ({len(manual_review_queue)} items):", file=sys.stderr)
        print("-" * 50, file=sys.stderr)
        
        for i, item in enumerate(manual_review_queue[:10], 1):
            dtx = item['dtx_record']
            result = item['match_result']
            print(f"{i:2d}. {dtx.get('given_name', ''):<15} {dtx.get('family_name', ''):<15} | "
                  f"Match: {result.match_type.value:<20} | "
                  f"Confidence: {result.confidence_score:.1%}", file=sys.stderr)
        
        if len(manual_review_queue) > 10:
            print(f"... and {len(manual_review_queue) - 10} more items", file=sys.stderr)
    
    @staticmethod
    def print_session_summary(stats: SessionStatistics):
        """Print final session summary."""
        print(f"\n🏥 Clinical processing complete!", file=sys.stderr)
        print(f"Match rate: {stats.get_match_rate():.1%} | "
              f"Auto-match rate: {stats.get_auto_match_rate():.1%}", file=sys.stderr)