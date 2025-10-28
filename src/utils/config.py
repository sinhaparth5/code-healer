import os
from typing import Optional
from pydantic_settings import BaseSettings

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

class Config(BaseSettings):
    # AWS Configuration
    aws_region: str = os.getenv('AWS_REGION', 'us-east-1')
    
    # GitHub Integration
    github_token_secret_arn: str = os.getenv('GITHUB_TOKEN_SECRET_ARN', '')
    slack_token_secret_arn: str = os.getenv('SLACK_TOKEN_SECRET_ARN', '')
    github_webhook_secret: str = os.getenv('GITHUB_WEBHOOK_SECRET', '')
    github_repo: str = os.getenv('GITHUB_REPO', '')
    github_branch: str = os.getenv('GITHUB_BRANCH', 'develop')
    
    # Slack Integration
    slack_channel_id: str = os.getenv('SLACK_CHANNEL_ID', '')
    slack_senior_dev_id: str = os.getenv('SLACK_SENIOR_DEV_ID', '')
    
    # LLM/AI Configuration
    openai_api_key: str = os.getenv('OPENAI_API_KEY', '')
    openai_model: str = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    openai_max_tokens: int = int(os.getenv('OPENAI_MAX_TOKENS', '1024'))
    openai_temperature: float = float(os.getenv('OPENAI_TEMPERATURE', '0.1'))
    
    # NVIDIA NIM Configuration
    nvidia_nim_api_key: str = os.getenv('NVIDIA_NIM_API_KEY', '')
    nvidia_nim_endpoint: str = os.getenv('NVIDIA_NIM_ENDPOINT', 'https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions')
    nvidia_nim_model: str = os.getenv('NVIDIA_NIM_MODEL', 'llama-3.1-nemotron-8b')
    
    # NVIDIA NIM Embedding Configuration
    nvidia_nim_embedding_api_key: str = os.getenv('NVIDIA_NIM_EMBEDDING_API_KEY', '')
    nvidia_nim_embedding_endpoint: str = os.getenv('NVIDIA_NIM_EMBEDDING_ENDPOINT', 'https://integrate.api.nvidia.com/v1/embeddings')
    nvidia_nim_embedding_model: str = os.getenv('NVIDIA_NIM_EMBEDDING_MODEL', 'nvidia/nv-embedqa-e5-v5')
    
    # LLM Provider Selection ('openai', 'nvidia_nim', 'sagemaker')
    llm_provider: str = os.getenv('LLM_PROVIDER', 'openai')
    llm_fallback_enabled: bool = os.getenv('LLM_FALLBACK_ENABLED', 'true').lower() == 'true'
    llm_timeout_seconds: int = int(os.getenv('LLM_TIMEOUT_SECONDS', '30'))
    
    # SageMaker Configuration (for AWS hosted models)
    sagemaker_llama_endpoint: str = os.getenv('SAGEMAKER_LLAMA_ENDPOINT', '')
    sagemaker_embedding_endpoint: str = os.getenv('SAGEMAKER_EMBEDDING_ENDPOINT', '')
    
    # Vector Database / Search
    opensearch_endpoint: str = os.getenv('OPENSEARCH_ENDPOINT', '')
    opensearch_index: str = os.getenv('OPENSEARCH_INDEX', 'code_fixes')
    
    # Data Storage
    dynamodb_table_name: str = os.getenv('DYNAMODB_TABLE_NAME', '')
    
    # Analysis Configuration
    confidence_threshold_high: int = int(os.getenv('CONFIDENCE_THRESHOLD_HIGH', '85'))
    confidence_threshold_medium: int = int(os.getenv('CONFIDENCE_THRESHOLD_MEDIUM', '60'))
    
    # Performance Limits
    max_file_size_kb: int = int(os.getenv('MAX_FILE_SIZE_KB', '500'))
    analysis_timeout_seconds: int = int(os.getenv('ANALYSIS_TIMEOUT_SECONDS', '300'))
    
    # Feature Flags
    enable_auto_fix: bool = os.getenv('ENABLE_AUTO_FIX', 'true').lower() == 'true'
    enable_slack_notifications: bool = os.getenv('ENABLE_SLACK_NOTIFICATIONS', 'true').lower() == 'true'
    enable_llm_analysis: bool = os.getenv('ENABLE_LLM_ANALYSIS', 'true').lower() == 'true'
    
    # Logging
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    
    def get_embedding_config(self) -> dict:
        """Get embedding configuration for NVIDIA NIM"""
        return {
            "nvidia_nim": {
                "url": self.nvidia_nim_embedding_endpoint,
                "api_key": self.nvidia_nim_embedding_api_key or self.nvidia_nim_api_key,  
                "model": self.nvidia_nim_embedding_model
            }
        }

    def get_llm_config(self) -> dict:
        """Get LLM configuration for the selected provider"""
        if self.llm_provider == "openai":
            return {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "endpoint": "https://api.openai.com/v1/chat/completions",
                "type": "openai",
                "max_tokens": self.openai_max_tokens,
                "temperature": self.openai_temperature,
                "timeout": self.llm_timeout_seconds
            }
        elif self.llm_provider == "nvidia_nim":
            return {
                "api_key": self.nvidia_nim_api_key,
                "model": self.nvidia_nim_model,
                "endpoint": self.nvidia_nim_endpoint,
                "type": "nvidia_nim",
                "max_tokens": self.openai_max_tokens,
                "temperature": self.openai_temperature,
                "timeout": self.llm_timeout_seconds
            }
        elif self.llm_provider == "sagemaker":
            return {
                "api_key": "",  # Uses IAM for auth
                "model": "llama-3.1",
                "endpoint": self.sagemaker_llama_endpoint,
                "type": "sagemaker",
                "max_tokens": self.openai_max_tokens,
                "temperature": self.openai_temperature,
                "timeout": self.llm_timeout_seconds
            }
        else:
            # Fallback to pattern matching only
            return {
                "api_key": "",
                "model": "fallback",
                "endpoint": "",
                "type": "fallback",
                "max_tokens": 0,
                "temperature": 0.0,
                "timeout": 0
            }

    class Config:
        case_sensitive = False

config = Config()
