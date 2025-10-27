import json
import os
import asyncio
from typing import Dict, Any, Optional
from utils.logger import get_logger, setup_lamdba_logging
from utils.config import config
from agent import CodeHealerAgent

logger = get_logger(__name__)
agent: Optional[CodeHealerAgent] = None

def get_agent() -> CodeHealerAgent:
    global agent
    if agent is None:
        agent_config = {
            "github": {
                "token": os.getenv("GITHUB_TOKEN", "")
            },
            "argocd": {
                "server_url": os.getenv("ARGOCD_SERVER_URL", ""),
                "token": os.getenv("ARGOCD_TOKEN", ""),
                "verify_ssl": os.getenv("ARGOCD_VERIFY_SSL", "true").lower() == "true"
            },
            "slack": {
                "token": os.getenv("SLACK_TOKEN", ""),
                "notification_channel": os.getenv("SLACK_NOTIFICATION_CHANNEL", "#alerts")
            },
            "llm": config.get_llm_config(),
            "confidence_threshold": {
                "production": float(os.getenv("CONFIDENCE_THRESHOLD_PROD", "0.92")),
                "staging": float(os.getenv("CONFIDENCE_THRESHOLD_STAGING", "0.85")),
                "development": float(os.getenv("CONFIDENCE_THRESHOLD_DEV", "0.75")),
                "default": float(os.getenv("CONFIDENCE_THRESHOLD_DEFAULT", "0.85"))
            }
        }
        agent = CodeHealerAgent(agent_config)
    return agent

def parse_event_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body", "{}")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in event body")
            return {}
    return body

def indentity_event_source(event: Dict[str, Any], payload: Dict[str, Any]) -> str:
    headers= event.get("headers", {})
    user_agent = headers.get("user-agent", "").lower()

    if "github" in user_agent or "workflow_run" in payload:
        return "github_actions"
    elif "application" in payload and payload.get("type") == "application":
        return "argocd"
    elif "kind" in payload and payload.get("apiVersion"):
        return "kubernetes"
    return "unknown"

def is_failure_event(payload: Dict[str, Any], source: str) -> bool:
    if source == "github_actions":
        workflow_run = payload.get("workflow_run", {})
        return (
            workflow_run.get("status") == "completed" and
            workflow_run.get("conclusion") in ["failure", "cancelled", "timed_out"]
        )