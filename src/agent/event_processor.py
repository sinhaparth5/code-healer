import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger
from agent.core_agent import IncidentEvent

logger = get_logger(__name__)

class EventSource(Enum):
    GITHUB_ACTIONS = "github_actions"
    ARGOCD = "argocd"
    KUBERNETES = "kubernetes"
    PROMETHEUS = "prometheus"
    JENKINS = "jenkins"
    UNKNOWN = "unknown"

class EventSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class ParsedEventMetadata:
    """Metadata extracted from raw event"""
    source: EventSource
    event_type: str
    severity: EventSeverity
    environment: str
    service: str
    component: str
    namespace: Optional[str]
    repository: Optional[str]
    workflow_id: Optional[str]
    application_name: Optional[str]

class EventProcessor:
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.event_config = config.get("event_processing", {})
        
        self.environment_patterns = self.event_config.get("environment_patterns", {
            "production": ["prod", "production", "main", "master"],
            "staging": ["stage", "staging", "stg"],
            "development": ["dev", "develop", "development"]
        })
        
        self.service_patterns = [
            r'(?:service|app|application)[/\s-]+([a-zA-Z0-9-]+)',
            r'([a-zA-Z0-9-]+)[-_](?:service|svc)',
            r'(?:^|/)([a-zA-Z0-9-]+)-(?:deployment|deploy)'
        ]
        
        logger.info("EventProcessor initialized")

    async def process_webhook_event(
        self, 
        raw_event: Dict[str, Any], 
        headers: Dict[str, str],
        incident_id: str
    ) -> Optional[IncidentEvent]:
        """
        Process raw webhook event into normalized IncidentEvent
        
        Args:
            raw_event: Raw webhook payload
            headers: HTTP headers from webhook
            incident_id: Unique incident identifier
            
        Returns:
            Normalized IncidentEvent or None if not a failure event
        """
        try:
            logger.info(f"Processing webhook event for incident: {incident_id}")
            
            event_source = self._identify_event_source(raw_event, headers)
            if event_source == EventSource.UNKNOWN:
                logger.warning(f"Unknown event source for incident {incident_id}")
                return None
            
            is_failure = self._is_failure_event(raw_event, event_source)
            if not is_failure:
                logger.info(f"Event {incident_id} is not a failure event")
                return None
            
            metadata = self._extract_event_metadata(raw_event, event_source)
            
            error_log = await self._extract_error_logs(raw_event, event_source, metadata)
            
            system_state = await self._gather_system_state(raw_event, event_source, metadata)
            
            incident = IncidentEvent(
                incident_id=incident_id,
                timestamp=datetime.utcnow(),
                source=event_source.value,
                severity=metadata.severity.value,
                failure_type=self._classify_failure_type(raw_event, event_source),
                context=self._build_context(metadata),
                error_log=error_log,
                system_state=system_state,
                raw_event=raw_event
            )
            
            logger.info(f"Successfully processed event {incident_id}: "
                       f"{event_source.value}/{metadata.service}")
            
            return incident
            
        except Exception as e:
            logger.error(f"Failed to process webhook event {incident_id}: {e}")
            return None

    def _identify_event_source(
        self, 
        raw_event: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> EventSource:
        """Identify the source platform of the webhook event"""
        
        user_agent = headers.get("user-agent", "").lower()
        if "github" in user_agent:
            return EventSource.GITHUB_ACTIONS
        
        if "workflow_run" in raw_event and "repository" in raw_event:
            return EventSource.GITHUB_ACTIONS
        
        if "application" in raw_event and raw_event.get("type") == "application":
            return EventSource.ARGOCD
        
        if "kind" in raw_event and raw_event.get("apiVersion"):
            return EventSource.KUBERNETES
        
        if "alerts" in raw_event or raw_event.get("receiver"):
            return EventSource.PROMETHEUS
        
        if "build" in raw_event and "jenkins" in str(raw_event).lower():
            return EventSource.JENKINS
        
        return EventSource.UNKNOWN

    def _is_failure_event(self, raw_event: Dict[str, Any], source: EventSource) -> bool:
        """Determine if this event represents a failure"""
        
        if source == EventSource.GITHUB_ACTIONS:
            workflow_run = raw_event.get("workflow_run", {})
            return (
                workflow_run.get("status") == "completed" and
                workflow_run.get("conclusion") in ["failure", "cancelled", "timed_out"]
            )
        
        elif source == EventSource.ARGOCD:
            application = raw_event.get("application", {})
            health_status = application.get("status", {}).get("health", {}).get("status")
            sync_status = application.get("status", {}).get("sync", {}).get("status")
            return health_status in ["Degraded", "Missing"] or sync_status == "OutOfSync"
        
        elif source == EventSource.KUBERNETES:
            event_type = raw_event.get("type", "")
            reason = raw_event.get("reason", "")
            return (
                event_type == "Warning" or
                reason in ["Failed", "FailedScheduling", "FailedMount", "Unhealthy"]
            )
        
        elif source == EventSource.PROMETHEUS:
            alerts = raw_event.get("alerts", [])
            return any(alert.get("status") == "firing" for alert in alerts)
        
        elif source == EventSource.JENKINS:
            build = raw_event.get("build", {})
            return build.get("status") in ["FAILURE", "ABORTED", "UNSTABLE"]
        
        return False

    def _extract_event_metadata(
        self, 
        raw_event: Dict[str, Any], 
        source: EventSource
    ) -> ParsedEventMetadata:
        """Extract structured metadata from raw event"""
        
        if source == EventSource.GITHUB_ACTIONS:
            return self._extract_github_metadata(raw_event)
        elif source == EventSource.ARGOCD:
            return self._extract_argocd_metadata(raw_event)
        elif source == EventSource.KUBERNETES:
            return self._extract_kubernetes_metadata(raw_event)
        elif source == EventSource.PROMETHEUS:
            return self._extract_prometheus_metadata(raw_event)
        elif source == EventSource.JENKINS:
            return self._extract_jenkins_metadata(raw_event)
        else:
            return self._extract_default_metadata(raw_event, source)

    def _extract_github_metadata(self, raw_event: Dict[str, Any]) -> ParsedEventMetadata:
        """Extract metadata from GitHub Actions event"""
        workflow_run = raw_event.get("workflow_run", {})
        repository = raw_event.get("repository", {})
        
        repo_name = repository.get("name", "unknown")
        workflow_name = workflow_run.get("name", "unknown")
        branch = workflow_run.get("head_branch", "")
        
        environment = self._infer_environment(branch)
        
        severity = EventSeverity.CRITICAL if environment == "production" else EventSeverity.HIGH
        
        return ParsedEventMetadata(
            source=EventSource.GITHUB_ACTIONS,
            event_type="workflow_failure",
            severity=severity,
            environment=environment,
            service=repo_name,
            component=workflow_name,
            namespace=None,
            repository=repository.get("full_name"),
            workflow_id=str(workflow_run.get("id", "")),
            application_name=None
        )

    def _extract_argocd_metadata(self, raw_event: Dict[str, Any]) -> ParsedEventMetadata:
        """Extract metadata from ArgoCD event"""
        application = raw_event.get("application", {})
        metadata = application.get("metadata", {})
        status = application.get("status", {})
        
        app_name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", "default")
        
        environment = self._infer_environment(f"{namespace} {app_name}")
        
        health_status = status.get("health", {}).get("status", "")
        severity = EventSeverity.CRITICAL if health_status == "Degraded" else EventSeverity.HIGH
        
        return ParsedEventMetadata(
            source=EventSource.ARGOCD,
            event_type="application_degraded",
            severity=severity,
            environment=environment,
            service=app_name,
            component=app_name,
            namespace=namespace,
            repository=status.get("sync", {}).get("revision", ""),
            workflow_id=None,
            application_name=app_name
        )

    def _extract_kubernetes_metadata(self, raw_event: Dict[str, Any]) -> ParsedEventMetadata:
        """Extract metadata from Kubernetes event"""
        involved_object = raw_event.get("involvedObject", {})
        metadata = raw_event.get("metadata", {})
        
        object_name = involved_object.get("name", "unknown")
        namespace = involved_object.get("namespace", "default")
        kind = involved_object.get("kind", "unknown")
        
        service_name = self._extract_service_name(object_name)
        
        environment = self._infer_environment(namespace)
        
        reason = raw_event.get("reason", "")
        severity = EventSeverity.CRITICAL if reason in ["Failed", "Unhealthy"] else EventSeverity.HIGH
        
        return ParsedEventMetadata(
            source=EventSource.KUBERNETES,
            event_type=f"{kind.lower()}_failure",
            severity=severity,
            environment=environment,
            service=service_name,
            component=f"{kind}/{object_name}",
            namespace=namespace,
            repository=None,
            workflow_id=None,
            application_name=None
        )

    def _extract_prometheus_metadata(self, raw_event: Dict[str, Any]) -> ParsedEventMetadata:
        """Extract metadata from Prometheus alert"""
        alerts = raw_event.get("alerts", [])
        if not alerts:
            return self._extract_default_metadata(raw_event, EventSource.PROMETHEUS)
        
        alert = alerts[0] 
        labels = alert.get("labels", {})
        
        service_name = labels.get("service", labels.get("job", "unknown"))
        namespace = labels.get("namespace", "default")
        alertname = labels.get("alertname", "unknown")
        
        environment = self._infer_environment(f"{namespace} {service_name}")
        
        severity_label = labels.get("severity", "high").lower()
        severity_map = {
            "critical": EventSeverity.CRITICAL,
            "high": EventSeverity.HIGH,
            "medium": EventSeverity.MEDIUM,
            "low": EventSeverity.LOW
        }
        severity = severity_map.get(severity_label, EventSeverity.HIGH)
        
        return ParsedEventMetadata(
            source=EventSource.PROMETHEUS,
            event_type="alert_firing",
            severity=severity,
            environment=environment,
            service=service_name,
            component=alertname,
            namespace=namespace,
            repository=None,
            workflow_id=None,
            application_name=None
        )

    def _extract_jenkins_metadata(self, raw_event: Dict[str, Any]) -> ParsedEventMetadata:
        build = raw_event.get("build", {})
        
        job_name = build.get("full_displayName", build.get("displayName", "unknown"))
        build_number = str(build.get("number", ""))
        
        service_name = self._extract_service_name(job_name)
        
        environment = self._infer_environment(job_name)
        
        return ParsedEventMetadata(
            source=EventSource.JENKINS,
            event_type="build_failure",
            severity=EventSeverity.HIGH,
            environment=environment,
            service=service_name,
            component=f"{job_name}#{build_number}",
            namespace=None,
            repository=None,
            workflow_id=None,
            application_name=None
        )

    def _extract_default_metadata(
        self, 
        raw_event: Dict[str, Any], 
        source: EventSource
    ) -> ParsedEventMetadata:
        """Extract default metadata for unknown event types"""
        return ParsedEventMetadata(
            source=source,
            event_type="unknown_failure",
            severity=EventSeverity.MEDIUM,
            environment="unknown",
            service="unknown",
            component="unknown",
            namespace=None,
            repository=None,
            workflow_id=None,
            application_name=None
        )

    def _infer_environment(self, text: str) -> str:
        """Infer environment from text (branch, namespace, etc.)"""
        if not text:
            return "unknown"
        
        text = text.lower()
        
        for env, patterns in self.environment_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return env
        
        return "unknown"

    def _extract_service_name(self, text: str) -> str:
        """Extract service name using regex patterns"""
        if not text:
            return "unknown"
        
        for pattern in self.service_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1)
        
        parts = text.split('-')
        if len(parts) > 1:
            return parts[0]
        
        return text

    async def _extract_error_logs(
        self, 
        raw_event: Dict[str, Any], 
        source: EventSource, 
        metadata: ParsedEventMetadata
    ) -> str:
        """Extract detailed error logs from the event"""
        
        if source == EventSource.GITHUB_ACTIONS:
            return await self._extract_github_error_logs(raw_event, metadata)
        elif source == EventSource.ARGOCD:
            return self._extract_argocd_error_logs(raw_event)
        elif source == EventSource.KUBERNETES:
            return self._extract_kubernetes_error_logs(raw_event)
        elif source == EventSource.PROMETHEUS:
            return self._extract_prometheus_error_logs(raw_event)
        elif source == EventSource.JENKINS:
            return self._extract_jenkins_error_logs(raw_event)
        else:
            return json.dumps(raw_event, indent=2)

    async def _extract_github_error_logs(
        self, 
        raw_event: Dict[str, Any], 
        metadata: ParsedEventMetadata
    ) -> str:
        """Extract GitHub Actions error logs"""
        workflow_run = raw_event.get("workflow_run", {})
        
        error_info = f"""GitHub Actions Workflow Failure
Repository: {metadata.repository}
Workflow: {metadata.component}
Branch: {workflow_run.get('head_branch', 'unknown')}
Status: {workflow_run.get('status', 'unknown')}
Conclusion: {workflow_run.get('conclusion', 'unknown')}
Run ID: {metadata.workflow_id}
URL: {workflow_run.get('html_url', 'N/A')}

Commit: {workflow_run.get('head_sha', 'unknown')}
Message: {workflow_run.get('head_commit', {}).get('message', 'N/A')}
"""
        
        return error_info

    def _extract_argocd_error_logs(self, raw_event: Dict[str, Any]) -> str:
        """Extract ArgoCD error logs"""
        application = raw_event.get("application", {})
        status = application.get("status", {})
        
        error_info = f"""ArgoCD Application Failure
Application: {application.get('metadata', {}).get('name', 'unknown')}
Namespace: {application.get('metadata', {}).get('namespace', 'unknown')}

Health Status: {status.get('health', {}).get('status', 'unknown')}
Health Message: {status.get('health', {}).get('message', 'N/A')}

Sync Status: {status.get('sync', {}).get('status', 'unknown')}
Sync Revision: {status.get('sync', {}).get('revision', 'unknown')}

Conditions:
"""
        
        conditions = status.get("conditions", [])
        for condition in conditions:
            error_info += f"- {condition.get('type', 'Unknown')}: {condition.get('message', 'N/A')}\n"
        
        resources = status.get("resources", [])
        if resources:
            error_info += "\nResource Status:\n"
            for resource in resources[:10]:  
                health = resource.get("health", {}).get("status", "Unknown")
                sync_status = resource.get("status", "Unknown")
                name = resource.get("name", "Unknown")
                kind = resource.get("kind", "Unknown")
                error_info += f"- {kind}/{name}: Health={health}, Sync={sync_status}\n"
        
        return error_info

    def _extract_kubernetes_error_logs(self, raw_event: Dict[str, Any]) -> str:
        """Extract Kubernetes event error logs"""
        involved_object = raw_event.get("involvedObject", {})
        
        error_info = f"""Kubernetes Event
Object: {involved_object.get('kind', 'unknown')}/{involved_object.get('name', 'unknown')}
Namespace: {involved_object.get('namespace', 'default')}
Reason: {raw_event.get('reason', 'unknown')}
Type: {raw_event.get('type', 'unknown')}

Message: {raw_event.get('message', 'N/A')}

First Occurrence: {raw_event.get('firstTimestamp', 'unknown')}
Last Occurrence: {raw_event.get('lastTimestamp', 'unknown')}
Count: {raw_event.get('count', 1)}

Source: {raw_event.get('source', {}).get('component', 'unknown')}
"""
        
        return error_info

    def _extract_prometheus_error_logs(self, raw_event: Dict[str, Any]) -> str:
        """Extract Prometheus alert error logs"""
        alerts = raw_event.get("alerts", [])
        
        error_info = "Prometheus Alert(s) Firing\n\n"
        
        for alert in alerts:
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            
            error_info += f"""Alert: {labels.get('alertname', 'Unknown')}
Severity: {labels.get('severity', 'unknown')}
Status: {alert.get('status', 'unknown')}

Labels:
"""
            for key, value in labels.items():
                error_info += f"  {key}: {value}\n"
            
            error_info += "\nAnnotations:\n"
            for key, value in annotations.items():
                error_info += f"  {key}: {value}\n"
            
            error_info += f"\nStarts At: {alert.get('startsAt', 'unknown')}\n"
            error_info += f"Generator URL: {alert.get('generatorURL', 'N/A')}\n\n"
        
        return error_info

    def _extract_jenkins_error_logs(self, raw_event: Dict[str, Any]) -> str:
        """Extract Jenkins build error logs"""
        build = raw_event.get("build", {})
        
        error_info = f"""Jenkins Build Failure
Job: {build.get('fullDisplayName', 'unknown')}
Build Number: {build.get('number', 'unknown')}
Status: {build.get('status', 'unknown')}
Result: {build.get('result', 'unknown')}

Duration: {build.get('duration', 'unknown')}ms
Estimated Duration: {build.get('estimatedDuration', 'unknown')}ms

URL: {build.get('url', 'N/A')}

Parameters:
"""
        
        actions = build.get("actions", [])
        for action in actions:
            if "parameters" in action:
                for param in action["parameters"]:
                    name = param.get("name", "unknown")
                    value = param.get("value", "N/A")
                    error_info += f"  {name}: {value}\n"
        
        return error_info

    async def _gather_system_state(
        self, 
        raw_event: Dict[str, Any], 
        source: EventSource, 
        metadata: ParsedEventMetadata
    ) -> Dict[str, Any]:
        """Gather additional system state information"""
        
        system_state = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_source": source.value,
            "raw_event_size": len(json.dumps(raw_event)),
            "recent_changes": [],
            "resource_utilization": {},
            "dependencies_status": {}
        }
        
        if source == EventSource.GITHUB_ACTIONS:
            workflow_run = raw_event.get("workflow_run", {})
            system_state.update({
                "github_run_attempt": workflow_run.get("run_attempt", 1),
                "github_previous_attempt_url": workflow_run.get("previous_attempt_url"),
                "github_actor": workflow_run.get("actor", {}).get("login", "unknown")
            })
        
        elif source == EventSource.ARGOCD:
            application = raw_event.get("application", {})
            operation = application.get("status", {}).get("operationState", {})
            system_state.update({
                "argocd_sync_policy": application.get("spec", {}).get("syncPolicy", {}),
                "argocd_operation_phase": operation.get("phase"),
                "argocd_operation_message": operation.get("message")
            })
        
        elif source == EventSource.KUBERNETES:
            system_state.update({
                "k8s_api_version": raw_event.get("apiVersion"),
                "k8s_cluster_name": raw_event.get("clusterName", "unknown"),
                "k8s_event_time": raw_event.get("eventTime")
            })
        
        return system_state

    def _classify_failure_type(self, raw_event: Dict[str, Any], source: EventSource) -> str:
        """Classify the type of failure for initial categorization"""
        
        if source == EventSource.GITHUB_ACTIONS:
            workflow_run = raw_event.get("workflow_run", {})
            conclusion = workflow_run.get("conclusion", "")
            if conclusion == "timed_out":
                return "timeout"
            elif conclusion == "cancelled":
                return "cancelled"
            else:
                return "workflow_failure"
        
        elif source == EventSource.ARGOCD:
            application = raw_event.get("application", {})
            sync_status = application.get("status", {}).get("sync", {}).get("status")
            health_status = application.get("status", {}).get("health", {}).get("status")
            
            if sync_status == "OutOfSync":
                return "sync_failure"
            elif health_status == "Degraded":
                return "health_failure"
            else:
                return "application_failure"
        
        elif source == EventSource.KUBERNETES:
            reason = raw_event.get("reason", "")
            if "scheduling" in reason.lower():
                return "scheduling_failure"
            elif "mount" in reason.lower():
                return "mount_failure"
            elif "health" in reason.lower():
                return "health_failure"
            else:
                return "resource_failure"
        
        elif source == EventSource.PROMETHEUS:
            return "metric_alert"
        
        elif source == EventSource.JENKINS:
            return "build_failure"
        
        else:
            return "unknown_failure"

    def _build_context(self, metadata: ParsedEventMetadata) -> Dict[str, Any]:
        """Build context dictionary from metadata"""
        return {
            "environment": metadata.environment,
            "service": metadata.service,
            "component": metadata.component,
            "namespace": metadata.namespace,
            "repository": metadata.repository,
            "workflow_id": metadata.workflow_id,
            "application_name": metadata.application_name,
            "event_type": metadata.event_type
        }

    def validate_webhook_signature(
        self, 
        payload: bytes, 
        signature: str, 
        secret: str
    ) -> bool:
        """Validate webhook signature for security"""
        import hmac
        import hashlib
        
        try:
            expected_signature = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Signature validation failed: {e}")
            return False

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get event processing statistics"""
        return {
            "events_processed": 0,
            "by_source": {source.value: 0 for source in EventSource},
            "by_severity": {severity.value: 0 for severity in EventSeverity},
            "processing_errors": 0,
            "average_processing_time_ms": 0.0
        }