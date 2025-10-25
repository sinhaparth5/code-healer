import json
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError
from utils.logger import get_logger

logger = get_logger(__name__)


class SageMakerClient:
    def __init__(self, region_name: str = "us-east-1"):
        self.runtime_client = boto3.client("sagemaker-runtime", region_name=region_name)
        self.client = boto3.client("sagemaker", region_name=region_name)

    def invoke_llm(
        self,
        endpoint_name: str,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs
    ) -> Optional[str]:
        try:
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    **kwargs
                }
            }
            
            response = self.runtime_client.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType="application/json",
                Body=json.dumps(payload)
            )
            
            result = json.loads(response["Body"].read().decode())
            
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "")
            elif isinstance(result, dict):
                return result.get("generated_text", "")
            
            return str(result)
        except ClientError as e:
            logger.error(f"Failed to invoke LLM endpoint: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error invoking LLM: {e}")
            return None

    def generate_embeddings(
        self,
        endpoint_name: str,
        texts: List[str]
    ) -> Optional[List[List[float]]]:
        try:
            payload = {
                "inputs": texts
            }
            
            response = self.runtime_client.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType="application/json",
                Body=json.dumps(payload)
            )
            
            result = json.loads(response["Body"].read().decode())
            
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "embeddings" in result:
                return result["embeddings"]
            
            logger.warning(f"Unexpected embedding response format: {type(result)}")
            return None
        except ClientError as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating embeddings: {e}")
            return None

    def analyze_error_log(
        self,
        llm_endpoint: str,
        error_log: str,
        system_state: Dict[str, Any],
        recent_changes: List[str]
    ) -> Optional[Dict[str, Any]]:
        prompt = f"""You are a senior DevOps engineer analyzing a deployment failure.

Error Context:
- Error Log: {error_log[:2000]}
- System State: {json.dumps(system_state, indent=2)[:1000]}
- Recent Changes: {', '.join(recent_changes[:5])}

Analyze this failure and provide:
1. Root cause (be specific)
2. Is this auto-fixable? (yes/no with justification)
3. If fixable: Exact remediation steps
4. If not fixable: Investigation steps for on-call engineer
5. Confidence score (0-100%)

Format as JSON with fields: root_cause, fixable, steps, confidence, reasoning
"""
        
        response = self.invoke_llm(
            llm_endpoint,
            prompt,
            max_tokens=1024,
            temperature=0.3
        )
        
        if not response:
            return None
        
        try:
            result = self._extract_json_from_response(response)
            return result
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {
                "root_cause": response[:500],
                "fixable": False,
                "steps": [],
                "confidence": 0,
                "reasoning": "Failed to parse structured response"
            }

    def classify_failure(
        self,
        llm_endpoint: str,
        error_message: str,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        categories = ["CONFIG", "AUTH", "RESOURCE", "DEPENDENCY", "DRIFT"]
        
        prompt = f"""Classify this deployment failure into one of these categories: {', '.join(categories)}

Error: {error_message[:1000]}
Context: {json.dumps(context, indent=2)[:500]}

Respond with JSON: {{"category": "CATEGORY", "subcategory": "specific type", "confidence": 0.0-1.0}}
"""
        
        response = self.invoke_llm(
            llm_endpoint,
            prompt,
            max_tokens=256,
            temperature=0.1
        )
        
        if not response:
            return None
        
        try:
            return self._extract_json_from_response(response)
        except Exception as e:
            logger.error(f"Failed to classify failure: {e}")
            return None

    def generate_fix_pr_description(
        self,
        llm_endpoint: str,
        incident_details: Dict[str, Any],
        fix_applied: str
    ) -> Optional[str]:
        prompt = f"""Generate a clear PR description for an automated fix.

Incident: {json.dumps(incident_details, indent=2)}
Fix Applied: {fix_applied}

Create a concise PR description with:
1. Problem summary
2. Root cause
3. Solution implemented
4. Testing recommendations

Keep it professional and under 500 words.
"""
        
        return self.invoke_llm(
            llm_endpoint,
            prompt,
            max_tokens=512,
            temperature=0.5
        )

    def summarize_slack_solutions(
        self,
        llm_endpoint: str,
        slack_messages: List[Dict[str, Any]],
        current_error: str
    ) -> Optional[str]:
        messages_text = "\n\n".join([
            f"Channel: {msg['channel']}, User: {msg.get('user', {}).get('name', 'unknown')}\n{msg['text']}"
            for msg in slack_messages[:5]
        ])
        
        prompt = f"""Summarize relevant solutions from these Slack discussions for the current error.

Current Error: {current_error[:500]}

Slack Discussions:
{messages_text}

Provide a concise summary of applicable solutions with step-by-step instructions.
"""
        
        return self.invoke_llm(
            llm_endpoint,
            prompt,
            max_tokens=1024,
            temperature=0.3
        )

    def get_endpoint_status(self, endpoint_name: str) -> Optional[str]:
        try:
            response = self.client.describe_endpoint(EndpointName=endpoint_name)
            return response["EndpointStatus"]
        except ClientError as e:
            logger.error(f"Failed to get endpoint status: {e}")
            return None

    def invoke_async(
        self,
        endpoint_name: str,
        input_location: str,
        output_location: str
    ) -> Optional[str]:
        try:
            response = self.runtime_client.invoke_endpoint_async(
                EndpointName=endpoint_name,
                InputLocation=input_location
            )
            return response.get("OutputLocation")
        except ClientError as e:
            logger.error(f"Failed to invoke async endpoint: {e}")
            return None

    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        import re
        
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        
        return json.loads(response)

    def batch_invoke_llm(
        self,
        endpoint_name: str,
        prompts: List[str],
        **kwargs
    ) -> List[Optional[str]]:
        results = []
        for prompt in prompts:
            result = self.invoke_llm(endpoint_name, prompt, **kwargs)
            results.append(result)
        return results

    def batch_generate_embeddings(
        self,
        endpoint_name: str,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.generate_embeddings(endpoint_name, batch)
            if embeddings:
                all_embeddings.extend(embeddings)
            else:
                all_embeddings.extend([[0.0] * 768] * len(batch))
        
        return all_embeddings