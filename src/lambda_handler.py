import json
import os
import hmac
import hashlib
import logging
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

def verify_signature(event: Dict[str, Any]) -> bool:
    signature = event.get('headers', {}).get('X-Hub-Signature-256', '')
    body = event.get('body', '')
    secret = os.getenv('GITHUB_WEBHOOK_SECRET', '')

    if not secret or not signature:
        return False
    
    expected = 'sha256=' + hmac.new(
        secret.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)

def parse_webhook_payload(event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        body = event.get('body', '{}')
        return json.loads(body) if isinstance(body, str) else body
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise ValueError("Invalid JSON payload")

def validate_webhook_event(payload: Dict[str, Any], event: Dict[str, Any]) -> bool:
    required_fields = ['ref', 'repository', 'commits']
    github_event = event.get('headers', {}).get('X-GitHub-Event', '')

    if github_event != 'push':
        logger.warning(f"Unsupproted event: {github_event}")
        return False
    
    if not all(field in payload for field in required_fields):
        logger.error("Missing required fields in payload")
        return False

    branch = payload['ref'].split('/')[-1]
    target_branch = os.getenv('GITHUB_BRANCH', 'develop')

    if branch != target_branch:
        logger.info(f"Ignoring branch: {branch}")
        return False

    return True

def create_response(status_code: int, message: str, data: Dict = None) -> Dict[str, Any]:
    body = {'message': message}
    if data:
        body.update(data)

    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'X-CodeHealer-Version': '1.0.0'
        },
        'body': json.dumps(body)
    }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(f"Request ID: {context.request_id}")
    
    try:
        if not verify_signature(event):
            logger.error('Signature verification failed')
            return create_response(401, "Unauthorized: Invalid signature")

        payload = parse_webhook_payload(event)

        if not validate_webhook_event(payload, event):
            return create_response(200, "Event ignored")

        repo_name = payload['repository']['full_name']
        commits = payload['commits']
        branch = payload['ref'].split('/')[-1]

        logger.info(f"Processing {len(commits)} commits from {repo_name}:{branch}")

        results = {
            'repository': repo_name,
            'branch': branch,
            'commits_processed': len(commits),
            'status': 'queued'
        }

        return create_response(200, "Webhook received and queued", results)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return create_response(400, str(e))

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return create_response(500, "Internal server error")

