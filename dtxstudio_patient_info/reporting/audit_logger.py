"""
Clinical audit and reporting for patient matching operations.

Provides HIPAA-compliant audit logging and quality metrics
for clinical environments.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..core.patient_matcher import SessionStatistics
from ..core.matching_strategies import MatchResult


class ClinicalAuditLogger:
    """
    HIPAA-compliant audit logging for clinical patient matching.
    
    Provides structured logging suitable for clinical audit trails
    and regulatory compliance requirements.
    """
    
    def __init__(self, logger_name: str = "clinical_matching"):
        """
        Initialize clinical audit logger.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = logging.getLogger(logger_name)
        self.session_start_time = datetime.now()
    
    def log_match_decision(self, match_result: MatchResult, dtx_patient_id: str = "") -> None:
        """
        Log a patient matching decision for audit trail.
        
        Args:
            match_result: Result of matching operation
            dtx_patient_id: DTX patient identifier (for audit trail)
        """
        if not match_result.match_found:
            self.logger.info(f"NO_MATCH - DTX Patient {dtx_patient_id} - No suitable match found")
            return
        
        log_level = logging.WARNING if match_result.clinical_warnings else logging.INFO
        
        log_parts = []
        
        # Add clinical warnings as prefix
        if match_result.clinical_warnings:
            log_parts.append(" - ".join(match_result.clinical_warnings))
        
        # Add basic match info
        pms_data = match_result.pms_data or {}
        patient_name = f"{pms_data.get('first_name', '')} {pms_data.get('last_name', '')}"
        log_parts.append(f"MATCH - Patient: {patient_name}")
        log_parts.append(f"Strategy: {match_result.match_type.value}")
        log_parts.append(f"Confidence: {match_result.confidence_score:.1%}")
        
        # Add corrections
        if match_result.corrections_needed:
            log_parts.append(f"Corrections: {', '.join(match_result.corrections_needed)}")
        
        # Add manual review flag
        if match_result.requires_manual_review:
            log_parts.append("REQUIRES_MANUAL_REVIEW")
        
        self.logger.log(log_level, " - ".join(log_parts))
    
    def log_session_summary(self, stats: SessionStatistics) -> None:
        """
        Log summary statistics for the matching session.
        
        Args:
            stats: Session statistics to log
        """
        session_duration = datetime.now() - self.session_start_time
        
        self.logger.info(f"MATCHING_SESSION_COMPLETE - Duration: {session_duration}")
        self.logger.info(f"TOTAL_PROCESSED: {stats.total_processed}")
        self.logger.info(f"AUTO_MATCHED: {stats.auto_matched}")
        self.logger.info(f"MANUAL_REVIEW: {stats.manual_review_required}")
        self.logger.info(f"NO_MATCHES: {stats.no_matches}")
        
        if stats.match_type_counts:
            self.logger.info("MATCH_TYPE_DISTRIBUTION:")
            for match_type, count in sorted(stats.match_type_counts.items()):
                self.logger.info(f"  {match_type}: {count}")
        
        if stats.confidence_distribution:
            self.logger.info("CONFIDENCE_DISTRIBUTION:")
            for conf_range, count in sorted(stats.confidence_distribution.items()):
                self.logger.info(f"  {conf_range}: {count}")


def generate_clinical_quality_report(stats: SessionStatistics, 
                                   manual_review_queue: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Generate a clinical data quality report.
    
    Args:
        stats: Session statistics
        manual_review_queue: List of cases requiring manual review
        
    Returns:
        Formatted clinical quality report
    """
    report_lines = []
    
    # Header
    report_lines.extend([
        "=" * 70,
        "CLINICAL PATIENT MATCHING QUALITY REPORT",
        "=" * 70,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ])
    
    # Overall Statistics
    total = stats.total_processed
    if total > 0:
        auto_match_rate = (stats.auto_matched / total) * 100
        review_rate = (stats.manual_review_required / total) * 100
        no_match_rate = (stats.no_matches / total) * 100
        
        report_lines.extend([
            "OVERALL PERFORMANCE METRICS:",
            f"  Total records processed: {total:,}",
            f"  Automatic matches: {stats.auto_matched:,} ({auto_match_rate:.1f}%)",
            f"  Manual review required: {stats.manual_review_required:,} ({review_rate:.1f}%)",
            f"  No matches found: {stats.no_matches:,} ({no_match_rate:.1f}%)",
            ""
        ])
        
        # Data Quality Assessment
        if auto_match_rate >= 85:
            quality_assessment = "EXCELLENT - High quality data with minimal issues"
        elif auto_match_rate >= 70:
            quality_assessment = "GOOD - Acceptable data quality with some corrections needed"
        elif auto_match_rate >= 50:
            quality_assessment = "FAIR - Moderate data quality issues requiring attention"
        else:
            quality_assessment = "POOR - Significant data quality issues requiring investigation"
        
        report_lines.extend([
            f"DATA QUALITY ASSESSMENT: {quality_assessment}",
            ""
        ])
    
    # Match Type Distribution
    if stats.match_type_counts:
        report_lines.extend([
            "MATCH TYPE DISTRIBUTION:",
        ])
        for match_type, count in sorted(stats.match_type_counts.items(), 
                                      key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            report_lines.append(f"  {match_type}: {count:,} ({percentage:.1f}%)")
        report_lines.append("")
    
    # Confidence Distribution
    if stats.confidence_distribution:
        report_lines.extend([
            "CONFIDENCE SCORE DISTRIBUTION:",
        ])
        for conf_range, count in sorted(stats.confidence_distribution.items()):
            percentage = (count / total * 100) if total > 0 else 0
            report_lines.append(f"  {conf_range}: {count:,} ({percentage:.1f}%)")
        report_lines.append("")
    
    # Manual Review Queue
    if manual_review_queue:
        report_lines.extend([
            f"MANUAL REVIEW QUEUE ({len(manual_review_queue)} items):",
            "-" * 50
        ])
        
        for i, item in enumerate(manual_review_queue[:10], 1):  # Show first 10
            dtx_data = item.get('dtx_record', {})
            match_result = item.get('match_result', {})
            
            name = f"{dtx_data.get('given_name', '')} {dtx_data.get('family_name', '')}"
            match_type = match_result.get('match_type', {}).get('value', 'UNKNOWN') if hasattr(match_result.get('match_type', {}), 'value') else str(match_result.get('match_type', 'UNKNOWN'))
            confidence = match_result.get('confidence_score', 0.0)
            reason = item.get('reason', 'Unknown')
            
            report_lines.append(f"{i:2d}. {name} | {match_type} | {confidence:.1%} | {reason}")
        
        if len(manual_review_queue) > 10:
            report_lines.append(f"    ... and {len(manual_review_queue) - 10} more items")
        
        report_lines.append("")
    
    # Clinical Recommendations
    report_lines.extend([
        "CLINICAL RECOMMENDATIONS:",
    ])
    
    if stats.manual_review_required > 0:
        report_lines.append(f"• Review {stats.manual_review_required} cases requiring manual verification")
    
    if stats.no_matches > 0:
        no_match_rate = (stats.no_matches / total * 100) if total > 0 else 0
        if no_match_rate > 10:
            report_lines.append("• High unmatched rate suggests data quality investigation needed")
    
    # Check for specific data quality issues
    gold_standard_count = stats.match_type_counts.get('GOLD_STANDARD', 0)
    if total > 0 and (gold_standard_count / total) < 0.5:
        report_lines.append("• Consider data standardization efforts to improve exact match rates")
    
    if 'PARTIAL_EXACT' in stats.match_type_counts or 'PARTIAL_GENDER_LOOSE' in stats.match_type_counts:
        report_lines.append("• DTX system contains name suffixes - consider suffix normalization")
    
    if 'FLIPPED_EXACT' in stats.match_type_counts or 'FLIPPED_GENDER_LOOSE' in stats.match_type_counts:
        report_lines.append("• Name field mapping inconsistency detected between systems")
    
    report_lines.extend([
        "",
        "=" * 70
    ])
    
    return "\n".join(report_lines)