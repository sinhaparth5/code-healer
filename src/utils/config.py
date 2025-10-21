import os
from typing import Optional
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    aws_region: str = os.getenv('AWS_REGION', 'us-east-1')
    
    github_token_secret_arn: str = os.getenv('GITHUB_TOKEN_SECRET_ARN', '')
    slack_token_secret_arn: str = os.getenv('SLACK_TOKEN_SECRET_ARN', '')
    github_webhook_secret: str = os.getenv('GITHUB_WEBHOOK_SECRET', '')
    github_repo: str = os.getenv('GITHUB_REPO', '')
    github_branch: str = os.getenv('GITHUB_BRANCH', 'develop')
    
    slack_channel_id: str = os.getenv('SLACK_CHANNEL_ID', '')
    slack_senior_dev_id: str = os.getenv('SLACK_SENIOR_DEV_ID', '')
    
    sagemaker_llama_endpoint: str = os.getenv('SAGEMAKER_LLAMA_ENDPOINT', '')
    sagemaker_embedding_endpoint: str = os.getenv('SAGEMAKER_EMBEDDING_ENDPOINT', '')
    
    opensearch_endpoint: str = os.getenv('OPENSEARCH_ENDPOINT', '')
    opensearch_index: str = os.getenv('OPENSEARCH_INDEX', 'code_fixes')
    
    dynamodb_table_name: str = os.getenv('DYNAMODB_TABLE_NAME', '')
    
    confidence_threshold_high: int = int(os.getenv('CONFIDENCE_THRESHOLD_HIGH', '85'))
    confidence_threshold_medium: int = int(os.getenv('CONFIDENCE_THRESHOLD_MEDIUM', '60'))
    
    max_file_size_kb: int = int(os.getenv('MAX_FILE_SIZE_KB', '500'))
    analysis_timeout_seconds: int = int(os.getenv('ANALYSIS_TIMEOUT_SECONDS', '300'))
    
    enable_auto_fix: bool = os.getenv('ENABLE_AUTO_FIX', 'true').lower() == 'true'
    enable_slack_notifications: bool = os.getenv('ENABLE_SLACK_NOTIFICATIONS', 'true').lower() == 'true'
    
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    
    class Config:
        case_sensitive = False

config = Config()
