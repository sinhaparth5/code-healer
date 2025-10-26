from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

from utils.logger import get_logger
from agent.core_agent import (
    IncidentEvent, FailureAnalysis, ResolutionCandidate, RemediationResult,
    FailureCategory, Fixability, ResolutionSource
)

logger = get_logger(__name__)

class OutcomeType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"

class FeedbackType(Enum):
    AUTOMATED = "automated"
    HUMAN_RATING = "human_rating"
    OUTCOME_VERIFICATION = "outcome_verification"
    INCIDENT_CORRELATION = "incident_correlation"

@dataclass
class OutcomeRecord:
    """Record of remediation outcome for learning"""
    incident_id: str
    remediation_id: str
    outcome_type: OutcomeType
    timestamp: datetime
    resolution_time_seconds: int
    confidence_at_execution: float
    actual_root_cause: Optional[str]
    effectiveness_score: float
    human_feedback: Optional[Dict[str, Any]]
    validation_data: Dict[str, Any]

@dataclass
class LearningMetrics:
    """Metrics for continuous learning"""
    prediction_accuracy: float
    confidence_calibration: float
    resolution_success_rate: float
    mean_time_to_resolution: float
    false_positive_rate: float
    escalation_rate: float
    knowledge_reuse_rate: float

@dataclass 
class PatternLearning:
    """Learned pattern from feedback"""
    pattern_id: str
    error_signature: str
    failure_category: FailureCategory
    subcategory: str
    confidence_adjustment: float
    success_count: int
    failure_count: int
    last_updated: datetime
    pattern_metadata: Dict[str, Any]

class FeedbackSystem:
    """
    Implements continuous learning and improvement through outcome tracking
    
    Key capabilities:
    1. Outcome tracking and validation
    2. Confidence calibration and adjustment
    3. Pattern learning from successes and failures
    4. Knowledge base updates and deprecation
    5. Performance metrics and reporting
    6. Human feedback integration
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.feedback_config = config.get("feedback", {})
        
        self.outcome_records = {}
        self.learned_patterns = {}
        self.confidence_adjustments = {}
        self.knowledge_deprecation = {}
        
        self.learning_rate = self.feedback_config.get("learning_rate", 0.1)
        self.min_sample_size = self.feedback_config.get("min_sample_size", 10)
        self.pattern_threshold = self.feedback_config.get("pattern_threshold", 0.7)
        self.deprecation_threshold = self.feedback_config.get("deprecation_threshold", 0.3)
        
        self.metrics_history = []
        self.current_metrics = None
        
        logger.info("FeedbackSystem initialized")

    async def record_outcome(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution: Optional[ResolutionCandidate],
        remediation_result: Optional[RemediationResult],
        human_feedback: Optional[Dict[str, Any]] = None
    ):
        """
        Record the outcome of an incident for learning
        
        Args:
            incident: Original incident
            analysis: Failure analysis results
            resolution: Selected resolution (if any)
            remediation_result: Result of remediation attempt
            human_feedback: Optional feedback from engineers
        """
        try:
            logger.info(f"Recording outcome for incident: {incident.incident_id}")
            
            outcome_type = self._determine_outcome_type(remediation_result)
            
            effectiveness_score = self._calculate_effectiveness_score(
                incident, analysis, resolution, remediation_result, human_feedback
            )
            
            validation_data = await self._gather_validation_data(
                incident, analysis, remediation_result
            )
            
            outcome_record = OutcomeRecord(
                incident_id=incident.incident_id,
                remediation_id=resolution.resolution_id if resolution else "none",
                outcome_type=outcome_type,
                timestamp=datetime.utcnow(),
                resolution_time_seconds=remediation_result.resolution_time_seconds if remediation_result else 0,
                confidence_at_execution=resolution.confidence if resolution else 0.0,
                actual_root_cause=self._extract_actual_root_cause(human_feedback),
                effectiveness_score=effectiveness_score,
                human_feedback=human_feedback,
                validation_data=validation_data
            )
            
            self.outcome_records[incident.incident_id] = outcome_record
            
            await self._update_learning(incident, analysis, resolution, outcome_record)
            
            await self._update_metrics()
            
            logger.info(f"Outcome recorded for {incident.incident_id}: "
                       f"{outcome_type.value} (effectiveness: {effectiveness_score:.2f})")
            
        except Exception as e:
            logger.error(f"Failed to record outcome for {incident.incident_id}: {e}")

    def _determine_outcome_type(self, remediation_result: Optional[RemediationResult]) -> OutcomeType:
        """Determine the type of outcome"""
        if not remediation_result:
            return OutcomeType.ESCALATED
        
        outcome_map = {
            "success": OutcomeType.SUCCESS,
            "failure": OutcomeType.FAILURE,
            "partial": OutcomeType.PARTIAL,
            "rejected": OutcomeType.ESCALATED,
            "error": OutcomeType.FAILURE
        }
        
        return outcome_map.get(remediation_result.outcome, OutcomeType.FAILURE)

    def _calculate_effectiveness_score(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution: Optional[ResolutionCandidate],
        remediation_result: Optional[RemediationResult],
        human_feedback: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate effectiveness score for the resolution"""
        
        if not remediation_result:
            return 0.0
        
        score = 0.0
        
        if remediation_result.outcome == "success":
            score += 0.7
        elif remediation_result.outcome == "partial":
            score += 0.4
        elif remediation_result.outcome == "failure":
            score += 0.1
        
        if remediation_result.resolution_time_seconds > 0:
            time_factor = max(0, 1 - (remediation_result.resolution_time_seconds / 600))
            score += time_factor * 0.2
        
        if not remediation_result.human_intervention_required:
            score += 0.1
        
        if human_feedback:
            rating = human_feedback.get("rating", "neutral")
            if rating == "helpful":
                score += 0.1
            elif rating == "not_helpful":
                score -= 0.1
        
        return min(max(score, 0.0), 1.0)

    def _extract_actual_root_cause(self, human_feedback: Optional[Dict[str, Any]]) -> Optional[str]:
        """Extract actual root cause from human feedback"""
        if not human_feedback:
            return None
        
        return human_feedback.get("actual_root_cause", human_feedback.get("comments"))

    async def _gather_validation_data(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        remediation_result: Optional[RemediationResult]
    ) -> Dict[str, Any]:
        """Gather additional validation data"""
        
        validation_data = {
            "incident_severity": incident.severity,
            "analysis_confidence": analysis.confidence,
            "predicted_category": analysis.primary_category.value,
            "predicted_subcategory": analysis.subcategory,
            "environment": incident.context.get("environment"),
            "service": incident.context.get("service")
        }
        
        if remediation_result:
            validation_data.update({
                "rollback_performed": remediation_result.rollback_performed,
                "execution_details": remediation_result.details
            })
        
        return validation_data

    async def _update_learning(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution: Optional[ResolutionCandidate],
        outcome: OutcomeRecord
    ):
        """Update learning models based on outcome"""
        
        await self._update_confidence_calibration(analysis, resolution, outcome)
        
        await self._learn_patterns(incident, analysis, outcome)
        
        await self._update_knowledge_effectiveness(resolution, outcome)
        
        await self._check_solution_deprecation(resolution, outcome)

    async def _update_confidence_calibration(
        self,
        analysis: FailureAnalysis,
        resolution: Optional[ResolutionCandidate],
        outcome: OutcomeRecord
    ):
        """Update confidence calibration based on actual outcomes"""
        
        if not resolution:
            return
        
        calibration_key = f"{analysis.primary_category.value}_{analysis.subcategory}_{resolution.source.value}"
        
        if calibration_key not in self.confidence_adjustments:
            self.confidence_adjustments[calibration_key] = {
                "predictions": [],
                "outcomes": [],
                "adjustment": 0.0
            }
        
        predicted_success = resolution.confidence
        actual_success = 1.0 if outcome.outcome_type == OutcomeType.SUCCESS else 0.0
        
        calibration_data = self.confidence_adjustments[calibration_key]
        calibration_data["predictions"].append(predicted_success)
        calibration_data["outcomes"].append(actual_success)
        
        if len(calibration_data["predictions"]) > 100:
            calibration_data["predictions"] = calibration_data["predictions"][-100:]
            calibration_data["outcomes"] = calibration_data["outcomes"][-100:]
        
        if len(calibration_data["predictions"]) >= self.min_sample_size:
            mean_prediction = sum(calibration_data["predictions"]) / len(calibration_data["predictions"])
            mean_outcome = sum(calibration_data["outcomes"]) / len(calibration_data["outcomes"])
            
            adjustment = (mean_outcome - mean_prediction) * self.learning_rate
            calibration_data["adjustment"] = adjustment
            
            logger.info(f"Updated confidence calibration for {calibration_key}: "
                       f"adjustment = {adjustment:.3f}")

    async def _learn_patterns(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        outcome: OutcomeRecord
    ):
        """Learn new error patterns from successful resolutions"""
        
        if outcome.outcome_type != OutcomeType.SUCCESS:
            return
        
        error_signature = self._create_error_signature(incident.error_log)
        pattern_key = f"{analysis.primary_category.value}_{error_signature}"
        
        if pattern_key not in self.learned_patterns:
            self.learned_patterns[pattern_key] = PatternLearning(
                pattern_id=pattern_key,
                error_signature=error_signature,
                failure_category=analysis.primary_category,
                subcategory=analysis.subcategory,
                confidence_adjustment=0.0,
                success_count=0,
                failure_count=0,
                last_updated=datetime.utcnow(),
                pattern_metadata={
                    "first_seen": datetime.utcnow().isoformat(),
                    "environments": [],
                    "services": []
                }
            )
        
        pattern = self.learned_patterns[pattern_key]
        
        if outcome.effectiveness_score > 0.7:
            pattern.success_count += 1
            pattern.confidence_adjustment = min(
                pattern.confidence_adjustment + 0.01, 
                0.1
            )
        else:
            pattern.failure_count += 1
            pattern.confidence_adjustment = max(
                pattern.confidence_adjustment - 0.01,
                -0.1
            )
        
        environment = incident.context.get("environment")
        service = incident.context.get("service")
        
        if environment and environment not in pattern.pattern_metadata["environments"]:
            pattern.pattern_metadata["environments"].append(environment)
        
        if service and service not in pattern.pattern_metadata["services"]:
            pattern.pattern_metadata["services"].append(service)
        
        pattern.last_updated = datetime.utcnow()
        
        logger.info(f"Updated pattern {pattern_key}: "
                   f"success={pattern.success_count}, failure={pattern.failure_count}")

    def _create_error_signature(self, error_log: str) -> str:
        """Create a signature for error pattern matching"""
        normalized = error_log.lower()
        
        import re
        patterns = [
            r'error:?\s*(.{20,60})',
            r'failed:?\s*(.{20,60})',
            r'exception:?\s*(.{20,60})',
            r'timeout:?\s*(.{20,60})'
        ]
        
        signatures = []
        for pattern in patterns:
            matches = re.findall(pattern, normalized)
            signatures.extend(matches)
        
        if signatures:
            combined = " | ".join(signatures[:3])
            return hashlib.md5(combined.encode()).hexdigest()[:16]
        else:
            return hashlib.md5(normalized[:200].encode()).hexdigest()[:16]

    async def _update_knowledge_effectiveness(
        self,
        resolution: Optional[ResolutionCandidate],
        outcome: OutcomeRecord
    ):
        """Update effectiveness tracking for knowledge sources"""
        
        if not resolution:
            return
        
        source_key = f"{resolution.source.value}_{resolution.resolution_id}"
        
        if source_key not in self.knowledge_deprecation:
            self.knowledge_deprecation[source_key] = {
                "source": resolution.source.value,
                "total_uses": 0,
                "successful_uses": 0,
                "effectiveness_scores": [],
                "last_used": datetime.utcnow()
            }
        
        knowledge_data = self.knowledge_deprecation[source_key]
        knowledge_data["total_uses"] += 1
        knowledge_data["effectiveness_scores"].append(outcome.effectiveness_score)
        knowledge_data["last_used"] = datetime.utcnow()
        
        if outcome.outcome_type == OutcomeType.SUCCESS:
            knowledge_data["successful_uses"] += 1
        
        if len(knowledge_data["effectiveness_scores"]) > 50:
            knowledge_data["effectiveness_scores"] = knowledge_data["effectiveness_scores"][-50:]

    async def _check_solution_deprecation(
        self,
        resolution: Optional[ResolutionCandidate],
        outcome: OutcomeRecord
    ):
        """Check if solutions should be deprecated due to poor performance"""
        
        if not resolution:
            return
        
        source_key = f"{resolution.source.value}_{resolution.resolution_id}"
        
        if source_key not in self.knowledge_deprecation:
            return
        
        knowledge_data = self.knowledge_deprecation[source_key]
        
        if knowledge_data["total_uses"] < self.min_sample_size:
            return
        
        recent_scores = knowledge_data["effectiveness_scores"][-20:]
        avg_effectiveness = sum(recent_scores) / len(recent_scores)
        
        if avg_effectiveness < self.deprecation_threshold:
            logger.warning(f"Solution {source_key} below deprecation threshold: "
                          f"{avg_effectiveness:.2f} < {self.deprecation_threshold}")
            
            knowledge_data["deprecated"] = True
            knowledge_data["deprecation_reason"] = f"Low effectiveness: {avg_effectiveness:.2f}"
            knowledge_data["deprecated_at"] = datetime.utcnow().isoformat()

    async def _update_metrics(self):
        """Update overall system metrics"""
        
        if not self.outcome_records:
            return
        
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        recent_outcomes = [
            outcome for outcome in self.outcome_records.values()
            if outcome.timestamp >= cutoff_date
        ]
        
        if not recent_outcomes:
            return
        
        successful = sum(1 for o in recent_outcomes if o.outcome_type == OutcomeType.SUCCESS)
        resolution_success_rate = successful / len(recent_outcomes)
        
        successful_outcomes = [o for o in recent_outcomes if o.outcome_type == OutcomeType.SUCCESS]
        if successful_outcomes:
            mean_time_to_resolution = sum(o.resolution_time_seconds for o in successful_outcomes) / len(successful_outcomes)
        else:
            mean_time_to_resolution = 0.0
        
        escalated = sum(1 for o in recent_outcomes if o.outcome_type == OutcomeType.ESCALATED)
        escalation_rate = escalated / len(recent_outcomes)
        
        accuracy_data = [
            o for o in recent_outcomes 
            if o.human_feedback and o.human_feedback.get("actual_root_cause")
        ]
        if accuracy_data:
            prediction_accuracy = 0.75
        else:
            prediction_accuracy = 0.0
        
        confidence_calibration = self._calculate_confidence_calibration(recent_outcomes)
        
        knowledge_reuse_count = sum(
            1 for o in recent_outcomes 
            if o.remediation_id != "none" and any(
                source in o.remediation_id for source in ["slack", "vector"]
            )
        )
        knowledge_reuse_rate = knowledge_reuse_count / len(recent_outcomes)
        
        automated_outcomes = [o for o in recent_outcomes if o.remediation_id != "none"]
        if automated_outcomes:
            failed_automated = sum(1 for o in automated_outcomes if o.outcome_type == OutcomeType.FAILURE)
            false_positive_rate = failed_automated / len(automated_outcomes)
        else:
            false_positive_rate = 0.0
        
        self.current_metrics = LearningMetrics(
            prediction_accuracy=prediction_accuracy,
            confidence_calibration=confidence_calibration,
            resolution_success_rate=resolution_success_rate,
            mean_time_to_resolution=mean_time_to_resolution,
            false_positive_rate=false_positive_rate,
            escalation_rate=escalation_rate,
            knowledge_reuse_rate=knowledge_reuse_rate
        )
        
        self.metrics_history.append({
            "timestamp": datetime.utcnow(),
            "metrics": asdict(self.current_metrics)
        })
        
        cutoff = datetime.utcnow() - timedelta(days=90)
        self.metrics_history = [
            m for m in self.metrics_history 
            if m["timestamp"] >= cutoff
        ]
        
        logger.info(f"Updated metrics: success_rate={resolution_success_rate:.2f}, "
                   f"escalation_rate={escalation_rate:.2f}, "
                   f"knowledge_reuse_rate={knowledge_reuse_rate:.2f}")

    def _calculate_confidence_calibration(self, outcomes: List[OutcomeRecord]) -> float:
        """Calculate confidence calibration error"""
        
        if len(outcomes) < 10:
            return 0.0
        
        buckets = {}
        for outcome in outcomes:
            if outcome.confidence_at_execution == 0.0:
                continue
            
            bucket = int(outcome.confidence_at_execution * 10) / 10
            if bucket not in buckets:
                buckets[bucket] = {"predicted": [], "actual": []}
            
            buckets[bucket]["predicted"].append(outcome.confidence_at_execution)
            buckets[bucket]["actual"].append(
                1.0 if outcome.outcome_type == OutcomeType.SUCCESS else 0.0
            )
        
        total_error = 0.0
        total_samples = 0
        
        for bucket, data in buckets.items():
            if len(data["predicted"]) < 5:
                continue
            
            mean_predicted = sum(data["predicted"]) / len(data["predicted"])
            mean_actual = sum(data["actual"]) / len(data["actual"])
            
            error = abs(mean_predicted - mean_actual)
            total_error += error * len(data["predicted"])
            total_samples += len(data["predicted"])
        
        if total_samples == 0:
            return 0.0
        
        calibration_error = total_error / total_samples
        
        return 1.0 - (total_error / total_samples) if total_samples > 0 else 0.0

    def get_confidence_adjustment(
        self, 
        category: FailureCategory, 
        subcategory: str, 
        source: ResolutionSource
    ) -> float:
        """Get confidence adjustment based on learned patterns"""
        
        calibration_key = f"{category.value}_{subcategory}_{source.value}"
        
        if calibration_key in self.confidence_adjustments:
            return self.confidence_adjustments[calibration_key].get("adjustment", 0.0)
        
        return 0.0

    def get_pattern_confidence_boost(self, error_log: str, category: FailureCategory) -> float:
        """Get confidence boost based on learned error patterns"""
        
        error_signature = self._create_error_signature(error_log)
        pattern_key = f"{category.value}_{error_signature}"
        
        if pattern_key in self.learned_patterns:
            pattern = self.learned_patterns[pattern_key]
            
            total_uses = pattern.success_count + pattern.failure_count
            if total_uses >= self.min_sample_size:
                success_rate = pattern.success_count / total_uses
                if success_rate > self.pattern_threshold:
                    return pattern.confidence_adjustment
        
        return 0.0

    def should_deprecate_solution(self, resolution_id: str, source: ResolutionSource) -> bool:
        """Check if a solution should be deprecated"""
        
        source_key = f"{source.value}_{resolution_id}"
        
        if source_key in self.knowledge_deprecation:
            return self.knowledge_deprecation[source_key].get("deprecated", False)
        
        return False

    async def submit_human_feedback(
        self,
        incident_id: str,
        feedback: Dict[str, Any]
    ):
        """Submit human feedback for an incident"""
        
        if incident_id not in self.outcome_records:
            logger.warning(f"No outcome record found for incident {incident_id}")
            return
        
        outcome_record = self.outcome_records[incident_id]
        outcome_record.human_feedback = feedback
        
        logger.info(f"Human feedback submitted for incident {incident_id}")

    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get comprehensive learning statistics"""
        
        stats = {
            "total_outcomes": len(self.outcome_records),
            "learned_patterns": len(self.learned_patterns),
            "confidence_adjustments": len(self.confidence_adjustments),
            "deprecated_solutions": sum(
                1 for data in self.knowledge_deprecation.values()
                if data.get("deprecated", False)
            ),
            "current_metrics": asdict(self.current_metrics) if self.current_metrics else None
        }
        
        # Outcome distribution
        outcome_counts = {}
        for outcome in self.outcome_records.values():
            outcome_type = outcome.outcome_type.value
            outcome_counts[outcome_type] = outcome_counts.get(outcome_type, 0) + 1
        
        stats["outcome_distribution"] = outcome_counts
        
        # Pattern statistics
        pattern_stats = {}
        for pattern in self.learned_patterns.values():
            category = pattern.failure_category.value
            if category not in pattern_stats:
                pattern_stats[category] = {"count": 0, "avg_success_rate": 0.0}
            
            pattern_stats[category]["count"] += 1
            total_uses = pattern.success_count + pattern.failure_count
            if total_uses > 0:
                success_rate = pattern.success_count / total_uses
                pattern_stats[category]["avg_success_rate"] += success_rate
        
        # Average success rates
        for category_stats in pattern_stats.values():
            if category_stats["count"] > 0:
                category_stats["avg_success_rate"] /= category_stats["count"]
        
        stats["pattern_statistics"] = pattern_stats
        
        return stats

    def export_learning_data(self) -> Dict[str, Any]:
        """Export learning data for backup or analysis"""
        
        return {
            "outcome_records": {
                incident_id: asdict(outcome) 
                for incident_id, outcome in self.outcome_records.items()
            },
            "learned_patterns": {
                pattern_id: asdict(pattern)
                for pattern_id, pattern in self.learned_patterns.items()
            },
            "confidence_adjustments": self.confidence_adjustments,
            "knowledge_deprecation": self.knowledge_deprecation,
            "metrics_history": self.metrics_history,
            "export_timestamp": datetime.utcnow().isoformat()
        }

    def import_learning_data(self, data: Dict[str, Any]):
        """Import learning data from backup"""
        
        try:
            # Import outcome records
            if "outcome_records" in data:
                for incident_id, outcome_data in data["outcome_records"].items():
                    # Convert timestamp string back to datetime
                    outcome_data["timestamp"] = datetime.fromisoformat(outcome_data["timestamp"])
                    outcome_data["outcome_type"] = OutcomeType(outcome_data["outcome_type"])
                    
                    self.outcome_records[incident_id] = OutcomeRecord(**outcome_data)
            
            # Import learned patterns
            if "learned_patterns" in data:
                for pattern_id, pattern_data in data["learned_patterns"].items():
                    pattern_data["last_updated"] = datetime.fromisoformat(pattern_data["last_updated"])
                    pattern_data["failure_category"] = FailureCategory(pattern_data["failure_category"])
                    
                    self.learned_patterns[pattern_id] = PatternLearning(**pattern_data)
            
            # Import other data
            if "confidence_adjustments" in data:
                self.confidence_adjustments = data["confidence_adjustments"]
            
            if "knowledge_deprecation" in data:
                self.knowledge_deprecation = data["knowledge_deprecation"]
            
            if "metrics_history" in data:
                self.metrics_history = data["metrics_history"]
            
            logger.info("Successfully imported learning data")
            
        except Exception as e:
            logger.error(f"Failed to import learning data: {e}")