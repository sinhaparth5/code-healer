"""
AWS Lambda handler for CodeHealer webhook processing

This handler:
1. Receives webhook events from GitHub Actions, ArgoCD, Kubernetes, etc.
2. Validates and parses the event
3. Routes to CodeHealer agent for automated remediation
4. Returns appropriate response to webhook sender
"""

import json
import os
import asyncio
from typing import Dict, Any, Optional
import hmac
import hashlib

from utils.logger import get_logger, setup_lambda_logging
from utils.config import config
from agent import CodeHealerAgent

logger = get_logger(__name__)

# Global agent singleton
agent: Optional[CodeHealerAgent] = None


def get_agent() -> CodeHealerAgent:
    """
    Get or create the CodeHealer agent singleton
    
    Returns:
        Initialized CodeHealer agent
    """
    global agent
    
    if agent is None:
        # Validate required configuration
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logger.warning("GITHUB_TOKEN not configured - GitHub integration disabled")
        
        slack_token = os.getenv("SLACK_TOKEN")
        if not slack_token:
            logger.warning("SLACK_TOKEN not configured - Slack notifications disabled")
        
        # Build comprehensive configuration
        agent_config = {
            "github": {
                "token": github_token or ""
            },
            "argocd": {
                "server_url": os.getenv("ARGOCD_SERVER_URL", ""),
                "token": os.getenv("ARGOCD_TOKEN", ""),
                "verify_ssl": os.getenv("ARGOCD_VERIFY_SSL", "true").lower() == "true"
            },
            "slack": {
                "token": slack_token or "",
                "notification_channel": os.getenv("SLACK_NOTIFICATION_CHANNEL", "#alerts"),
                "search_channels": os.getenv("SLACK_SEARCH_CHANNELS", "devops,alerts,incidents").split(","),
                "time_window_days": int(os.getenv("SLACK_TIME_WINDOW_DAYS", "180")),
                "max_results": int(os.getenv("SLACK_MAX_RESULTS", "20"))
            },
            "llm": config.get_llm_config(),
            "confidence_thresholds": {
                "production": float(os.getenv("CONFIDENCE_THRESHOLD_PROD", "0.92")),
                "staging": float(os.getenv("CONFIDENCE_THRESHOLD_STAGING", "0.85")),
                "development": float(os.getenv("CONFIDENCE_THRESHOLD_DEV", "0.75")),
                "default": float(os.getenv("CONFIDENCE_THRESHOLD_DEFAULT", "0.85"))
            },
            "vector_db": {
                "similarity_threshold": float(os.getenv("VECTOR_SIMILARITY_THRESHOLD", "0.75")),
                "max_results": int(os.getenv("VECTOR_MAX_RESULTS", "10"))
            },
            "embedding": {
                "endpoint": os.getenv("EMBEDDING_ENDPOINT", "")
            },
            "remediation": {
                "confidence_thresholds": {
                    "production": float(os.getenv("CONFIDENCE_THRESHOLD_PROD", "0.92")),
                    "staging": float(os.getenv("CONFIDENCE_THRESHOLD_STAGING", "0.85")),
                    "development": float(os.getenv("CONFIDENCE_THRESHOLD_DEV", "0.75")),
                    "default": float(os.getenv("CONFIDENCE_THRESHOLD_DEFAULT", "0.85"))
                },
                "risk_factors": {
                    "production_environment": 0.3,
                    "cross_service_impact": 0.25,
                    "config_changes": 0.15,
                    "resource_scaling": 0.20,
                    "credential_updates": 0.10
                }
            },
            "approval": {
                "rules": {
                    "production_always": os.getenv("APPROVAL_PROD_ALWAYS", "true").lower() == "true",
                    "high_risk_always": os.getenv("APPROVAL_HIGH_RISK", "true").lower() == "true",
                    "low_confidence_threshold": float(os.getenv("APPROVAL_LOW_CONF_THRESHOLD", "0.9"))
                }
            },
            "feedback": {
                "learning_rate": float(os.getenv("FEEDBACK_LEARNING_RATE", "0.1")),
                "min_sample_size": int(os.getenv("FEEDBACK_MIN_SAMPLES", "10")),
                "pattern_threshold": float(os.getenv("FEEDBACK_PATTERN_THRESHOLD", "0.7")),
                "deprecation_threshold": float(os.getenv("FEEDBACK_DEPRECATION_THRESHOLD", "0.3"))
            },
            "event_processing": {
                "environment_patterns": {
                    "production": ["prod", "production", "main", "master"],
                    "staging": ["stage", "staging", "stg"],
                    "development": ["dev", "develop", "development"]
                }
            }
        }
        
        try:
            agent = CodeHealerAgent(agent_config)
            logger.info("CodeHealer agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize CodeHealer agent: {e}", exc_info=True)
            raise
    
    return agent


def parse_event_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and validate the event body
    
    Args:
        event: Lambda event
        
    Returns:
        Parsed payload dictionary
    """
    body = event.get("body", "{}")
    
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in event body: {e}")
            return {}
    
    return body


def identify_event_source(event: Dict[str, Any], payload: Dict[str, Any]) -> str:
    """
    Identify the source of the webhook event
    
    Args:
        event: Lambda event with headers
        payload: Parsed webhook payload
        
    Returns:
        Event source identifier (github_actions, argocd, kubernetes, etc.)
    """
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    user_agent = headers.get("user-agent", "").lower()
    
    # GitHub Actions
    if "github" in user_agent or "workflow_run" in payload:
        return "github_actions"
    
    # ArgoCD
    if "application" in payload and payload.get("type") == "application":
        return "argocd"
    
    # Kubernetes
    if "kind" in payload and payload.get("apiVersion"):
        return "kubernetes"
    
    # Prometheus
    if "alerts" in payload or payload.get("receiver"):
        return "prometheus"
    
    # Jenkins
    if "build" in payload and "jenkins" in str(payload).lower():
        return "jenkins"
    
    return "unknown"


def is_failure_event(payload: Dict[str, Any], source: str) -> bool:
    """
    Check if the event represents a failure
    
    Args:
        payload: Webhook payload
        source: Event source identifier
        
    Returns:
        True if this is a failure event, False otherwise
    """
    if source == "github_actions":
        workflow_run = payload.get("workflow_run", {})
        return (
            workflow_run.get("status") == "completed" and
            workflow_run.get("conclusion") in ["failure", "cancelled", "timed_out"]
        )
    
    elif source == "argocd":
        application = payload.get("application", {})
        health_status = application.get("status", {}).get("health", {}).get("status")
        sync_status = application.get("status", {}).get("sync", {}).get("status")
        return health_status in ["Degraded", "Missing"] or sync_status == "OutOfSync"
    
    elif source == "kubernetes":
        event_type = payload.get("type", "")
        reason = payload.get("reason", "")
        return (
            event_type == "Warning" or
            reason in ["Failed", "FailedScheduling", "FailedMount", "Unhealthy", "OOMKilled"]
        )
    
    elif source == "prometheus":
        alerts = payload.get("alerts", [])
        return any(alert.get("status") == "firing" for alert in alerts)
    
    elif source == "jenkins":
        build = payload.get("build", {})
        return build.get("status") in ["FAILURE", "ABORTED", "UNSTABLE"]
    
    return False


def verify_webhook_signature(event: Dict[str, Any], body: str, source: str) -> bool:
    """
    Verify webhook signature for security
    
    Args:
        event: Lambda event with headers
        body: Raw request body
        source: Event source
        
    Returns:
        True if signature is valid or verification is disabled
    """
    if source != "github_actions":
        # Only GitHub Actions signature verification implemented
        return True
    
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    signature = headers.get("x-hub-signature-256", "")
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    
    if not secret:
        logger.warning("GITHUB_WEBHOOK_SECRET not configured - skipping signature verification")
        return True
    
    if not signature:
        logger.warning("No signature header found in GitHub webhook")
        return False
    
    expected_signature = "sha256=" + hmac.new(
        secret.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()
    
    is_valid = hmac.compare_digest(signature, expected_signature)
    
    if not is_valid:
        logger.error("Invalid webhook signature")
    
    return is_valid


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main AWS Lambda handler for CodeHealer webhook events
    
    Args:
        event: API Gateway event containing webhook payload
        context: Lambda context object
        
    Returns:
        API Gateway response with status and body
    """
    # Setup logging
    setup_lambda_logging()
    
    request_id = getattr(context, 'request_id', 'unknown')
    logger.info(f"Received webhook event", extra={
        "request_id": request_id,
        "source_ip": event.get("requestContext", {}).get("identity", {}).get("sourceIp")
    })
    
    try:
        # Get raw body for signature verification
        raw_body = event.get("body", "{}")
        
        # Parse event payload
        payload = parse_event_body(event)
        
        if not payload:
            logger.error("Empty or invalid payload")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid payload"})
            }
        
        # Identify event source
        source = identify_event_source(event, payload)
        logger.info(f"Identified event source: {source}")
        
        if source == "unknown":
            logger.warning("Unknown event source, ignoring")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Unknown event source"})
            }
        
        # Verify webhook signature
        if not verify_webhook_signature(event, raw_body, source):
            logger.error("Webhook signature verification failed")
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Invalid signature"})
            }
        
        # Check if this is a failure event
        if not is_failure_event(payload, source):
            logger.info(f"Event is not a failure, ignoring")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Event processed (not a failure)"})
            }
        
        # Get CodeHealer agent
        agent = get_agent()
        
        # Process the failure event asynchronously
        logger.info(f"Processing failure event from {source}")
        result = asyncio.run(agent.process_failure_event(payload))
        
        # Log result
        logger.info(f"Failure processing complete", extra={
            "incident_id": result.get("incident_id"),
            "status": result.get("status"),
            "automated": result.get("automated")
        })
        
        # Return success response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "status": result.get("status", "error"),
                "incident_id": result.get("incident_id"),
                "automated": result.get("automated", False),
                "message": "Failure event processed successfully"
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda handler failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "status": "error",
                "error": str(e),
                "message": "Internal server error"
            })
        }


# For local testing
if __name__ == "__main__":
    # Mock GitHub Actions failure event
    test_event = {
        "body": json.dumps({
            "workflow_run": {
                "id": 12345,
                "status": "completed",
                "conclusion": "failure",
                "name": "CI",
                "head_branch": "main"
            },
            "repository": {
                "name": "test-repo",
                "full_name": "org/test-repo",
                "owner": {"login": "org"}
            }
        }),
        "headers": {
            "user-agent": "GitHub-Hookshot/abc123"
        }
    }
    
    class MockContext:
        request_id = "test-123"
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
