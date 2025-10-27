import json
import os
import hmac
import hashlib
import logging
import asyncio
from typing import Dict, Any

from codehealer_agent import CodeHealerAgent
from utils.config import config

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

_agent = None

def get_agent() -> CodeHealerAgent:
    global _agent
    if _agent is None:
        _agent = CodeHealerAgent(config)
    return _agent

def verify_signature(event: Dict[str, Any]) -> bool:
    signature = event.get('headers', {}).get('X-Hub-Signature-256', '').lower()
    body = event.get('body', '')
    secret = os.getenv('GITHUB_WEBHOOK_SECRET', '')
    
    if not (secret and signature):
        return False
    
    expected = 'sha256=' + hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)

def create_response(status_code: int, message: str, data: Dict = None) -> Dict[str, Any]:
    body = {'message': message, **(data or {})}
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json', 'X-CodeHealer-Version': '1.0.0'},
        'body': json.dumps(body)
    }

def process_github_workflow(body: Dict[str, Any]) -> Dict[str, Any]:
    workflow_run = body.get('workflow_run', {})
    action = body.get('action', '')
    conclusion = workflow_run.get('conclusion', '')
    
    if action != 'completed' or conclusion != 'failure':
        logger.info(f"Ignoring workflow: action={action}, conclusion={conclusion}")
        return create_response(200, "Event ignored: Not a failure")
    
    logger.info(f"Processing failure: {workflow_run.get('name')} in {body.get('repository', {}).get('full_name')}")
    result = asyncio.run(get_agent().process_failure_event(body))
    
    return create_response(200, "Failure processed", {
        'incident_id': result.get('incident_id'),
        'automated': result.get('automated', False),
        'status': result.get('status')
    })

def process_argocd_event(body: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Processing ArgoCD event")
    result = asyncio.run(get_agent().process_failure_event(body))
    return create_response(200, "ArgoCD event processed", {'incident_id': result.get('incident_id')})

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(f"Request ID: {context.request_id}")
    
    try:
        if not verify_signature(event):
            logger.error('Signature verification failed')
            return create_response(401, "Unauthorized: Invalid signature")
        
        body = json.loads(event.get('body', '{}'))
        headers = event.get('headers', {})
        github_event = headers.get('X-GitHub-Event', headers.get('x-github-event', ''))
        
        if github_event == 'ping':
            return create_response(200, "pong", {"zen": body.get("zen", "")})
        
        if github_event == 'workflow_run':
            return process_github_workflow(body)
        
        if 'application' in body:
            return process_argocd_event(body)
        
        logger.warning(f"Unsupported event type: {github_event}")
        return create_response(200, "Event type not monitored")
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return create_response(400, "Invalid JSON payload")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return create_response(500, f"Internal server error: {str(e)}")
