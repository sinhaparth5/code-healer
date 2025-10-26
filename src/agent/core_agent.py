import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger
from utils.config import config
from integrations.github_client import GitHubClient
from integrations.argocd_client import ArgoCDClient
from integrations.slack_client import SlackClient

logger = get_logger(__name__)

class FailureCategory(Enum):
    CONFIG = "config"
    AUTH = "auth"
    RESOURCE = "resource"
    DEPENDENCY = "dependency"
    DRIFT = "drift"

class Fixability(Enum):
    AUTO = "auto"
    RETRY = "retry"
    INVESTIGATE = "investigate"

class ResolutionSource(Enum):
    SLACK = "slack"
    VECTOR_DB = "vector_db"
    LLM_ANALYSIS = "llm_analysis"

@dataclass
class IncidentEvent:
    incident_id: str
    timestamp: datetime
    source: str
    severity: str
    failure_type: str
    context: Dict[str, Any]
    error_log: str
    system_state: Dict[str, Any]
    raw_event: Dict[str, Any]

@dataclass
class FailureAnalysis:
    incident_id: str
    primary_category: FailureCategory
    subcategory: str
    root_cause: str
    fixability: Fixability
    confidence: float
    reasoning: str
    affected_components: List[str]
    recent_changes: List[Dict[str, Any]]

@dataclass
class ResolutionCandidate:
    resolution_id: str
    source: ResolutionSource
    description: str
    steps: List[str]
    confidence: float
    success_rate: float
    last_used: Optional[datetime]
    environment_match: bool
    code_changes: List[Dict[str, Any]]
    estimated_duration: int

@dataclass
class RemediationResult:
    incident_id: str
    remediation_id: str
    action_taken: str
    outcome: str
    confidence_at_execution: float
    resolution_time_seconds: int
    human_intervention_required: bool
    rollback_performed: bool
    details: Dict[str, Any]

class CodeHealerAgent:
    """
    Main autonomous agent for deployment failure resolution
    
    Orchestrates the complete flow:
    1. Event ingestion and normalization
    2. Failure analysis using LLM
    3. Knowledge retrieval from multiple sources
    4. Confidence-based remediation decision
    5. Automated fix execution
    6. Outcome tracking and learning
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.incident_history = {}
        self.active_incidents = {}
        
        self._init_clients()
        self._init_agent_components()
        
        logger.info("CodeHealer Agent initialized")

    def _init_clients(self):
        try:
            if github_token := self.config.get("github", {}).get("token"):
                self.github_client = GitHubClient(github_token)
                logger.info("GitHub client initialized")
            
            argocd_config = self.config.get("argocd", {})
            if argocd_config.get("server_url") and argocd_config.get("token"):
                self.argocd_client = ArgoCDClient(
                    argocd_config["server_url"],
                    argocd_config["token"],
                    verify_ssl=argocd_config.get("verify_ssl", True)
                )
                logger.info("ArgoCD client initialized")
            
            if slack_token := self.config.get("slack", {}).get("token"):
                self.slack_client = SlackClient(slack_token)
                logger.info("Slack client initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            raise

    def _init_agent_components(self):
        try:
            from .event_processor import EventProcessor
            from .failure_analyzer import FailureAnalyzer
            from .knowledge_retriever import KnowledgeRetriever
            from .remediation_coordinator import RemediationCoordinator
            from .feedback_system import FeedbackSystem
            
            self.event_processor = EventProcessor(self.config)
            self.failure_analyzer = FailureAnalyzer(self.config)
            self.knowledge_retriever = KnowledgeRetriever(
                self.config, 
                slack_client=getattr(self, 'slack_client', None)
            )
            self.remediation_coordinator = RemediationCoordinator(
                self.config,
                github_client=getattr(self, 'github_client', None),
                argocd_client=getattr(self, 'argocd_client', None)
            )
            self.feedback_system = FeedbackSystem(self.config)
            
            logger.info("Agent components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent components: {e}")
            raise

    async def process_failure_event(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for processing deployment failure events
        
        Args:
            raw_event: Raw webhook event from GitHub Actions, ArgoCD, etc.
            
        Returns:
            Processing result with incident details and actions taken
        """
        incident_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Processing failure event: {incident_id}")
            
            incident = await self._normalize_event(raw_event, incident_id)
            if not incident:
                return {"status": "error", "message": "Failed to normalize event"}
            
            self.active_incidents[incident_id] = incident
            
            analysis = await self._analyze_failure(incident)
            if not analysis:
                return {"status": "error", "message": "Failed to analyze failure"}
            
            resolution_candidates = await self._retrieve_solutions(incident, analysis)
            
            remediation_decision = await self._make_remediation_decision(
                incident, analysis, resolution_candidates
            )
            
            remediation_result = None
            if remediation_decision["should_remediate"]:
                remediation_result = await self._execute_remediation(
                    incident, analysis, remediation_decision["selected_resolution"]
                )
            
            await self._update_tracking(incident, analysis, remediation_result)
            
            await self._send_notifications(incident, analysis, remediation_result)
            
            if incident_id in self.active_incidents:
                self.incident_history[incident_id] = self.active_incidents.pop(incident_id)
            
            return {
                "status": "success",
                "incident_id": incident_id,
                "analysis": analysis,
                "remediation_result": remediation_result,
                "automated": remediation_result is not None
            }
            
        except Exception as e:
            logger.error(f"Error processing failure event {incident_id}: {e}")
            if incident_id in self.active_incidents:
                del self.active_incidents[incident_id]
            return {"status": "error", "message": str(e), "incident_id": incident_id}

    async def _normalize_event(self, raw_event: Dict[str, Any], incident_id: str) -> Optional[IncidentEvent]:
        try:
            headers = {}
            incident = await self.event_processor.process_webhook_event(
                raw_event, headers, incident_id
            )
            return incident
        except Exception as e:
            logger.error(f"Failed to normalize event: {e}")
            return None

    def _extract_context(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        context = {
            "environment": "unknown",
            "service": "unknown", 
            "component": "unknown",
            "namespace": None
        }
        
        if "workflow_run" in raw_event:
            workflow_run = raw_event["workflow_run"]
            context.update({
                "service": raw_event.get("repository", {}).get("name", "unknown"),
                "component": workflow_run.get("name", "unknown"),
                "environment": self._infer_environment_from_branch(
                    workflow_run.get("head_branch", "")
                )
            })
        
        elif "application" in raw_event:
            app = raw_event["application"]
            context.update({
                "service": app.get("metadata", {}).get("name", "unknown"),
                "namespace": app.get("metadata", {}).get("namespace"),
                "environment": self._infer_environment_from_namespace(
                    app.get("metadata", {}).get("namespace", "")
                )
            })
        
        return context

    def _extract_error_log(self, raw_event: Dict[str, Any]) -> str:
        if "workflow_run" in raw_event:
            return f"GitHub Actions workflow failed: {raw_event.get('workflow_run', {}).get('conclusion', 'unknown')}"
        elif "application" in raw_event:
            return f"ArgoCD application sync failed: {raw_event.get('application', {}).get('status', {})}"
        else:
            return json.dumps(raw_event, indent=2)

    async def _gather_system_state(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_incidents": len(self.active_incidents),
            "recent_changes": [],
            "resource_utilization": {},
            "dependencies_status": {}
        }

    async def _analyze_failure(self, incident: IncidentEvent) -> Optional[FailureAnalysis]:
        return await self.failure_analyzer.analyze_failure(incident)

    async def _retrieve_solutions(
        self, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis
    ) -> List[ResolutionCandidate]:
        return await self.knowledge_retriever.retrieve_solutions(incident, analysis)

    async def _make_remediation_decision(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        candidates: List[ResolutionCandidate]
    ) -> Dict[str, Any]:
        logger.info(f"Making remediation decision for incident: {incident.incident_id}")
        
        if not candidates:
            return {"should_remediate": False, "reason": "No viable solutions found"}
        
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        best_candidate = candidates[0]
        
        min_confidence = self._get_min_confidence_threshold(incident.context.get("environment"))
        
        should_remediate = (
            best_candidate.confidence >= min_confidence and
            analysis.fixability == Fixability.AUTO
        )
        
        return {
            "should_remediate": should_remediate,
            "selected_resolution": best_candidate if should_remediate else None,
            "reason": f"Confidence {best_candidate.confidence:.2f} vs threshold {min_confidence:.2f}",
            "all_candidates": candidates
        }

    async def _execute_remediation(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution: ResolutionCandidate
    ) -> RemediationResult:
        return await self.remediation_coordinator.coordinate_remediation(
            incident, analysis, [resolution]
        )

    async def _update_tracking(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        remediation_result: Optional[RemediationResult]
    ):
        try:
            resolution = None
            if remediation_result and remediation_result.remediation_id != "none":
                resolution = ResolutionCandidate(
                    resolution_id=remediation_result.remediation_id,
                    source=ResolutionSource.LLM_ANALYSIS,  
                    description=remediation_result.action_taken,
                    steps=[],
                    confidence=remediation_result.confidence_at_execution,
                    success_rate=0.0,
                    last_used=None,
                    environment_match=True,
                    code_changes=[],
                    estimated_duration=0
                )
            
            await self.feedback_system.record_outcome(
                incident, analysis, resolution, remediation_result
            )
        except Exception as e:
            logger.error(f"Failed to update tracking: {e}")

    async def _send_notifications(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        remediation_result: Optional[RemediationResult]
    ):
        if not hasattr(self, 'slack_client'):
            return
        
        try:
            channel = self.config.get("slack", {}).get("notification_channel", "#alerts")
            
            if remediation_result:
                if remediation_result.outcome == "success":
                    action_text = f"Automatically resolved: {remediation_result.action_taken}"
                else:
                    action_text = f"Attempted fix failed: {remediation_result.action_taken}"
            else:
                action_text = "Escalating to human engineer for investigation"
            
            self.slack_client.send_incident_notification(
                channel=channel,
                incident_id=incident.incident_id,
                failure_type=analysis.primary_category.value,
                service=incident.context.get("service", "unknown"),
                error_summary=analysis.root_cause,
                automated_action=action_text
            )
            
        except Exception as e:
            logger.error(f"Failed to send notifications: {e}")

    def _get_min_confidence_threshold(self, environment: str) -> float:
        thresholds = self.config.get("confidence_thresholds", {})
        return thresholds.get(environment, thresholds.get("default", 0.85))

    def _infer_environment_from_branch(self, branch: str) -> str:
        branch = branch.lower()
        if "prod" in branch or "main" in branch or "master" in branch:
            return "production"
        elif "stag" in branch or "staging" in branch:
            return "staging"
        elif "dev" in branch or "develop" in branch:
            return "development"
        else:
            return "unknown"

    def _infer_environment_from_namespace(self, namespace: str) -> str:
        if not namespace:
            return "unknown"
        namespace = namespace.lower()
        if "prod" in namespace:
            return "production"
        elif "stag" in namespace:
            return "staging"
        elif "dev" in namespace:
            return "development"
        else:
            return "unknown"

    async def get_incident_status(self, incident_id: str) -> Optional[Dict[str, Any]]:
        if incident_id in self.active_incidents:
            return {
                "status": "active",
                "incident": self.active_incidents[incident_id]
            }
        elif incident_id in self.incident_history:
            return {
                "status": "completed",
                "incident": self.incident_history[incident_id]
            }
        else:
            return None

    async def list_active_incidents(self) -> List[Dict[str, Any]]:
        return list(self.active_incidents.values())

    async def get_agent_health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "active_incidents": len(self.active_incidents),
            "total_processed": len(self.incident_history),
            "clients_initialized": {
                "github": hasattr(self, 'github_client'),
                "argocd": hasattr(self, 'argocd_client'),
                "slack": hasattr(self, 'slack_client')
            }
        }