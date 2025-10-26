import json
import re
import asyncio
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from utils.logger import get_logger
from utils.config import config
from agent.core_agent import FailureCategory, Fixability, FailureAnalysis, IncidentEvent

logger = get_logger(__name__)

@dataclass 
class ErrorPattern:
    """Predefined error pattern for quick classification"""
    pattern: str
    category: FailureCategory
    subcategory: str
    fixability: Fixability
    confidence_boost: float

class FailureAnalyzer:
    """
    Analyzes deployment failures using LLM and pattern matching
    
    Implements the failure taxonomy from the research paper:
    - Category I: Configuration Errors (40% of failures)
    - Category II: Authentication & Authorization (25%)
    - Category III: Resource Constraints (20%)
    - Category IV: Dependency Failures (10%) 
    - Category V: Environmental Drift (5%)
    """
    
    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        if config_override is None:
            llm_config = config.get_llm_config()
            config_override = {"llm": llm_config}
        
        self.config = config_override
        self.error_patterns = self._load_error_patterns()
        
        self.llm_config = self.config.get("llm", {})
        self.model_name = self.llm_config.get("model", "llama-3.1-nemotron-8b")
        self.max_tokens = self.llm_config.get("max_tokens", 2048)
        self.temperature = self.llm_config.get("temperature", 0.1)
        
        self.api_key = self.llm_config.get("api_key", "")
        self.api_type = self.llm_config.get("type", "nvidia_nim")
        self.api_endpoint = self.llm_config.get("endpoint", "")
        
        if self.api_type == "nvidia_nim" and self.api_endpoint:
            if not self.api_endpoint.endswith("/chat/completions"):
                self.api_endpoint = self.api_endpoint.rstrip("/") + "/chat/completions"
        
        logger.info(f"FailureAnalyzer initialized with provider: {self.api_type}, model: {self.model_name}")

    def _load_error_patterns(self) -> List[ErrorPattern]:
        """Load predefined error patterns for quick classification"""
        patterns = [
            ErrorPattern(
                pattern=r"(?i)(yaml|json|yml).*(syntax|parse|invalid|malformed|indent)",
                category=FailureCategory.CONFIG,
                subcategory="syntax_error",
                fixability=Fixability.AUTO,
                confidence_boost=0.20
            ),
            ErrorPattern(
                pattern=r"(?i)(secret|configmap|volume|pvc).*(not found|does not exist|missing)",
                category=FailureCategory.CONFIG,
                subcategory="reference_error", 
                fixability=Fixability.AUTO,
                confidence_boost=0.18
            ),
            ErrorPattern(
                pattern=r"(?i)(image|tag|docker).*(not found|pull.*failed|does not exist|401|403)",
                category=FailureCategory.CONFIG,
                subcategory="image_reference_error",
                fixability=Fixability.AUTO,
                confidence_boost=0.17
            ),
            ErrorPattern(
                pattern=r"(?i)(field|property|attribute).*(required|missing|invalid|unknown)",
                category=FailureCategory.CONFIG,
                subcategory="validation_error",
                fixability=Fixability.AUTO,
                confidence_boost=0.16
            ),
            
            ErrorPattern(
                pattern=r"(?i)(unauthorized|forbidden|access denied|authentication failed|401|403)",
                category=FailureCategory.AUTH,
                subcategory="permission_error",
                fixability=Fixability.AUTO,
                confidence_boost=0.15
            ),
            ErrorPattern(
                pattern=r"(?i)(token|credential|certificate|key).*(expired|invalid|revoked|not found)",
                category=FailureCategory.AUTH,
                subcategory="expired_credentials",
                fixability=Fixability.AUTO,
                confidence_boost=0.17
            ),
            ErrorPattern(
                pattern=r"(?i)(rbac|role|permission|policy).*(denied|insufficient|missing)",
                category=FailureCategory.AUTH,
                subcategory="rbac_error",
                fixability=Fixability.AUTO,
                confidence_boost=0.14
            ),
            
            ErrorPattern(
                pattern=r"(?i)(oomkilled|out of memory|memory limit|memory.*exceeded)",
                category=FailureCategory.RESOURCE,
                subcategory="memory_limit",
                fixability=Fixability.AUTO,
                confidence_boost=0.19
            ),
            ErrorPattern(
                pattern=r"(?i)(cpu.*throttl|cpu.*limit|resource.*quota|quota.*exceeded)",
                category=FailureCategory.RESOURCE,
                subcategory="compute_limit",
                fixability=Fixability.AUTO,
                confidence_boost=0.16
            ),
            ErrorPattern(
                pattern=r"(?i)(disk.*full|storage.*exceeded|space.*unavailable|no.*space)",
                category=FailureCategory.RESOURCE,
                subcategory="storage_limit",
                fixability=Fixability.AUTO,
                confidence_boost=0.15
            ),
            ErrorPattern(
                pattern=r"(?i)(pending|unschedulable|insufficient.*resources|node.*capacity)",
                category=FailureCategory.RESOURCE,
                subcategory="scheduling_failure",
                fixability=Fixability.AUTO,
                confidence_boost=0.13
            ),
            
            ErrorPattern(
                pattern=r"(?i)(connection.*timeout|network.*timeout|dial.*timeout|i/o timeout)",
                category=FailureCategory.DEPENDENCY,
                subcategory="network_timeout",
                fixability=Fixability.RETRY,
                confidence_boost=0.12
            ),
            ErrorPattern(
                pattern=r"(?i)(connection.*refused|connection.*reset|network.*unreachable)",
                category=FailureCategory.DEPENDENCY,
                subcategory="network_failure",
                fixability=Fixability.RETRY,
                confidence_boost=0.11
            ),
            ErrorPattern(
                pattern=r"(?i)(service.*unavailable|endpoint.*unreachable|502|503|504)",
                category=FailureCategory.DEPENDENCY,
                subcategory="service_unavailable",
                fixability=Fixability.RETRY,
                confidence_boost=0.10
            ),
            ErrorPattern(
                pattern=r"(?i)(dns.*resolution|name.*not.*resolved|no such host)",
                category=FailureCategory.DEPENDENCY,
                subcategory="dns_failure",
                fixability=Fixability.RETRY,
                confidence_boost=0.09
            ),
            
            ErrorPattern(
                pattern=r"(?i)(state.*inconsistent|drift.*detected|configuration.*drift)",
                category=FailureCategory.DRIFT,
                subcategory="state_inconsistency",
                fixability=Fixability.INVESTIGATE,
                confidence_boost=0.08
            ),
            ErrorPattern(
                pattern=r"(?i)(version.*mismatch|api.*version|schema.*migration)",
                category=FailureCategory.DRIFT,
                subcategory="version_drift",
                fixability=Fixability.INVESTIGATE,
                confidence_boost=0.07
            )
        ]
        
        return patterns

    async def analyze_failure(self, incident: IncidentEvent) -> Optional[FailureAnalysis]:
        """
        Comprehensive failure analysis using multiple approaches:
        1. Fetch detailed logs from GitHub/ArgoCD/Kubernetes
        2. Use LLM for dynamic error detection and categorization
        3. Apply pattern matching as fallback
        4. Determine fixability and confidence
        
        Args:
            incident: Normalized incident event
            
        Returns:
            FailureAnalysis with categorization and remediation guidance
        """
        try:
            logger.info(f"Starting comprehensive failure analysis for {incident.incident_id}")
            
            # Step 1: Fetch detailed logs from source
            detailed_logs = await self._fetch_detailed_logs(incident)
            
            # Step 2: Enhanced pattern matching with detailed logs
            pattern_match = self._pattern_match_analysis(incident, detailed_logs)
            
            # Step 3: LLM analysis with enhanced context
            llm_analysis = await self._llm_analysis(incident, detailed_logs)
            
            # Step 4: Combine analyses intelligently
            final_analysis = self._combine_analyses(incident, pattern_match, llm_analysis)
            
            # Step 5: Extract affected components and recent changes
            affected_components = self._extract_affected_components(incident)
            recent_changes = await self._gather_recent_changes(incident)
            
            final_analysis.affected_components = affected_components
            final_analysis.recent_changes = recent_changes
            
            logger.info(f"Failure analysis completed for {incident.incident_id}: "
                       f"{final_analysis.primary_category.value} (confidence: {final_analysis.confidence:.2f})")
            
            return final_analysis
            
        except Exception as e:
            logger.error(f"Failure analysis failed for {incident.incident_id}: {e}")
            return None

    async def _fetch_detailed_logs(self, incident: IncidentEvent) -> str:
        """Fetch detailed logs from the source platform"""
        try:
            if incident.source == "github_actions":
                return await self._fetch_github_logs(incident)
            elif incident.source == "argocd":
                return await self._fetch_argocd_logs(incident)
            elif incident.source == "kubernetes":
                return await self._fetch_kubernetes_logs(incident)
            else:
                return incident.error_log
        except Exception as e:
            logger.warning(f"Failed to fetch detailed logs: {e}")
            return incident.error_log

    async def _fetch_github_logs(self, incident: IncidentEvent) -> str:
        """Fetch GitHub Actions workflow logs with enhanced context"""
        try:
            raw_event = incident.raw_event
            if "workflow_run" not in raw_event:
                return incident.error_log
            
            workflow_run = raw_event["workflow_run"]
            repo_info = raw_event.get("repository", {})
            
            # Construct GitHub API URLs for detailed log fetching
            repo_full_name = repo_info.get("full_name", "")
            run_id = workflow_run.get("id")
            
            if not repo_full_name or not run_id:
                return incident.error_log
            
            # Enhanced error context with GitHub-specific details
            enhanced_logs = f"""
=== GITHUB WORKFLOW FAILURE ANALYSIS ===
Repository: {repo_full_name}
Workflow: {workflow_run.get('name', 'Unknown')}
Run ID: {run_id}
Branch: {workflow_run.get('head_branch', 'Unknown')}
Conclusion: {workflow_run.get('conclusion', 'Unknown')}
Event: {workflow_run.get('event', 'Unknown')}
Started: {workflow_run.get('created_at', 'Unknown')}
Commit SHA: {workflow_run.get('head_sha', 'Unknown')[:8]}

=== WORKFLOW CONTEXT ===
Pull Request: {workflow_run.get('pull_requests', [])}
Actor: {workflow_run.get('triggering_actor', {}).get('login', 'Unknown')}
URL: {workflow_run.get('html_url', 'Unknown')}

=== ERROR DETAILS ===
{incident.error_log}

=== SYSTEM STATE ===
{json.dumps(incident.system_state, indent=2) if incident.system_state else 'No system state available'}
"""
            
            # TODO: Implement actual GitHub API log fetching
            # This would use GitHub API to get job logs, step details, etc.
            
            return enhanced_logs
            
        except Exception as e:
            logger.error(f"Failed to fetch GitHub logs: {e}")
            return incident.error_log

    async def _fetch_argocd_logs(self, incident: IncidentEvent) -> str:
        """Fetch ArgoCD application logs with enhanced context"""
        try:
            raw_event = incident.raw_event
            if "application" not in raw_event:
                return incident.error_log
            
            app = raw_event["application"]
            metadata = app.get("metadata", {})
            status = app.get("status", {})
            
            enhanced_logs = f"""
=== ARGOCD APPLICATION FAILURE ANALYSIS ===
Application: {metadata.get('name', 'Unknown')}
Namespace: {metadata.get('namespace', 'Unknown')}
Project: {metadata.get('labels', {}).get('project', 'Unknown')}

=== SYNC STATUS ===
Status: {status.get('sync', {}).get('status', 'Unknown')}
Revision: {status.get('sync', {}).get('revision', 'Unknown')[:8]}
Message: {status.get('sync', {}).get('message', 'No sync message')}

=== HEALTH STATUS ===
Status: {status.get('health', {}).get('status', 'Unknown')}
Message: {status.get('health', {}).get('message', 'No health message')}

=== OPERATION STATUS ===
{json.dumps(status.get('operationState', {}), indent=2) if status.get('operationState') else 'No operation status'}

=== ORIGINAL ERROR ===
{incident.error_log}
"""
            return enhanced_logs
            
        except Exception as e:
            logger.error(f"Failed to fetch ArgoCD logs: {e}")
            return incident.error_log

    async def _fetch_kubernetes_logs(self, incident: IncidentEvent) -> str:
        """Fetch Kubernetes pod/resource logs with enhanced context"""
        try:
            raw_event = incident.raw_event
            involved_object = raw_event.get("involvedObject", {})
            
            enhanced_logs = f"""
=== KUBERNETES EVENT FAILURE ANALYSIS ===
Resource Kind: {involved_object.get('kind', 'Unknown')}
Resource Name: {involved_object.get('name', 'Unknown')}
Namespace: {involved_object.get('namespace', 'Unknown')}
API Version: {involved_object.get('apiVersion', 'Unknown')}

=== EVENT DETAILS ===
Type: {raw_event.get('type', 'Unknown')}
Reason: {raw_event.get('reason', 'Unknown')}
Message: {raw_event.get('message', 'No message')}
Count: {raw_event.get('count', 1)}
First Timestamp: {raw_event.get('firstTimestamp', 'Unknown')}
Last Timestamp: {raw_event.get('lastTimestamp', 'Unknown')}

=== SOURCE COMPONENT ===
Component: {raw_event.get('source', {}).get('component', 'Unknown')}
Host: {raw_event.get('source', {}).get('host', 'Unknown')}

=== ORIGINAL ERROR ===
{incident.error_log}
"""
            return enhanced_logs
            
        except Exception as e:
            logger.error(f"Failed to fetch Kubernetes logs: {e}")
            return incident.error_log

    async def analyze_failure(self, incident: IncidentEvent) -> Optional[FailureAnalysis]:
        """
        Main failure analysis method with enhanced log fetching and LLM integration
        """
        try:
            logger.info(f"Starting enhanced analysis for incident: {incident.incident_id}")
            
            # Step 1: Fetch detailed logs from source platforms
            detailed_logs = await self._fetch_detailed_logs(incident)
            
            # Step 2: Perform pattern matching analysis with detailed logs
            pattern_analysis = self._pattern_match_analysis(incident, detailed_logs)
            
            # Step 3: Generate comprehensive LLM analysis  
            llm_analysis = await self._llm_analysis(incident, detailed_logs, pattern_analysis)
            
            # Step 4: Combine analyses with confidence weighting
            final_analysis = self._combine_analyses(incident, pattern_analysis, llm_analysis)
            
            if final_analysis:
                logger.info(f"Analysis complete for {incident.incident_id}: "
                           f"{final_analysis.primary_category.value}/{final_analysis.subcategory} "
                           f"(confidence: {final_analysis.confidence:.2f}, fixability: {final_analysis.fixability.value})")
            
            return final_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze incident {incident.incident_id}: {e}")
            return self._create_fallback_analysis(incident)

    def _pattern_match_analysis(self, incident: IncidentEvent, detailed_logs: str = None) -> Optional[Dict[str, Any]]:
        """Perform comprehensive pattern matching against known error signatures"""
        # Use detailed logs if available, otherwise fall back to incident error log
        error_text = (detailed_logs or incident.error_log).lower()
        
        best_match = None
        best_confidence = 0.0
        matched_patterns = []
        
        # Check all patterns and collect matches
        for pattern in self.error_patterns:
            match = re.search(pattern.pattern, error_text)
            if match:
                confidence = 0.6 + pattern.confidence_boost
                
                # Boost confidence if pattern appears multiple times
                match_count = len(re.findall(pattern.pattern, error_text))
                if match_count > 1:
                    confidence += min(0.1, match_count * 0.02)
                
                # Boost confidence for GitHub-specific patterns
                if incident.source == "github_actions" and "workflow" in pattern.subcategory:
                    confidence += 0.05
                
                # Boost confidence for Kubernetes-specific patterns  
                if incident.source == "kubernetes" and "pod" in pattern.subcategory:
                    confidence += 0.05
                
                matched_patterns.append((pattern, confidence, match.group(0)))
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = pattern
        
        if best_match:
            # Enhanced reasoning with matched text
            matched_text = next(
                (match[2] for match in matched_patterns if match[0] == best_match), 
                "pattern"
            )
            
            logger.info(f"Pattern match found: {best_match.subcategory} "
                       f"(confidence: {best_confidence:.2f}, matched: '{matched_text[:50]}...')")
            
            return {
                "category": best_match.category,
                "subcategory": best_match.subcategory,
                "fixability": best_match.fixability,
                "confidence": best_confidence,
                "reasoning": f"Pattern match: {best_match.subcategory} - Found '{matched_text[:100]}'",
                "source": "pattern_matching",
                "matched_patterns": len(matched_patterns),
                "matched_text": matched_text
            }
        
        logger.debug("No pattern matches found in logs")
        return None

    async def _llm_analysis(self, incident: IncidentEvent, detailed_logs: str = None) -> Optional[Dict[str, Any]]:
        """Perform enhanced LLM-based analysis using llama-3.1-nemotron-8b with detailed logs"""
        try:
            if not self.api_key:
                logger.warning("No API key configured, skipping LLM analysis")
                return None
            
            # Use detailed logs for more comprehensive analysis
            logs_to_analyze = detailed_logs or incident.error_log
            
            prompt = self._build_enhanced_analysis_prompt(incident, logs_to_analyze)
            response = await self._call_llm(prompt)
            
            if response:
                parsed_response = self._parse_llm_response(response)
                if parsed_response:
                    parsed_response["source"] = "llm_analysis"
                    # Boost confidence for LLM analysis with detailed logs
                    if detailed_logs:
                        parsed_response["confidence"] = min(0.95, parsed_response.get("confidence", 0.7) + 0.1)
                    return parsed_response
            
            return None
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return None

    def _build_enhanced_analysis_prompt(self, incident: IncidentEvent, detailed_logs: str) -> str:
        """Build comprehensive analysis prompt with enhanced context for llama-3.1-nemotron-8b"""
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an expert DevOps engineer specializing in deployment failure analysis and automated remediation. Your expertise includes:

- Kubernetes and container orchestration troubleshooting
- CI/CD pipeline failures (GitHub Actions, ArgoCD, Jenkins)  
- Infrastructure configuration and resource management
- Network, authentication, and security issues
- Cloud platform integration problems

Your task is to analyze deployment failures and provide structured remediation guidance with specific, actionable solutions.

ANALYSIS FRAMEWORK:
1. CATEGORIZE the failure into one of these types:
   - CONFIG: Configuration errors, YAML syntax, missing resources
   - AUTH: Authentication, authorization, credential issues  
   - RESOURCE: Memory, CPU, storage constraints
   - DEPENDENCY: External service failures, network connectivity
   - DRIFT: Environment inconsistencies, version mismatches

2. DETERMINE FIXABILITY:
   - AUTO: Can be automatically fixed with high confidence
   - RETRY: Transient issue, retry might resolve
   - INVESTIGATE: Requires human analysis

3. PROVIDE specific fix actions when possible:
   - Exact configuration changes needed
   - Commands to run
   - Resources to update
   - Files to modify

RESPOND ONLY with valid JSON in this exact format:
{{
    "category": "CONFIG|AUTH|RESOURCE|DEPENDENCY|DRIFT",
    "subcategory": "specific_error_type",
    "confidence": 0.85,
    "fixability": "AUTO|RETRY|INVESTIGATE", 
    "reasoning": "detailed analysis explanation",
    "root_cause": "specific root cause identified",
    "fix_actions": [
        "specific action 1",
        "specific action 2"
    ],
    "affected_files": ["file1.yaml", "file2.json"],
    "estimated_fix_time": "5 minutes"
}}

Focus on operational/infrastructure failures, not application source code bugs.<|eot_id|>

<|start_header_id|>user<|end_header_id|>
Analyze this deployment failure:

INCIDENT DETAILS:
- ID: {incident.incident_id}
- Source: {incident.source}
- Environment: {incident.context.get('environment', 'unknown')}
- Service: {incident.context.get('service', 'unknown')}
- Severity: {incident.severity}

DETAILED LOGS AND CONTEXT:
{detailed_logs}

SYSTEM STATE:
{json.dumps(incident.system_state, indent=2) if incident.system_state else 'No system state available'}

Provide a comprehensive analysis with specific remediation steps.<|eot_id|>"""
        
        return prompt

    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM service for analysis"""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._call_llm_sync, prompt
            )
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None

    def _call_llm_sync(self, prompt: str) -> Optional[str]:
        """Call LLM API synchronously based on provider type"""
        if self.api_type == "nvidia_nim":
            return self._call_nvidia_nim_sync(prompt)
        elif self.api_type == "openai":
            return self._call_openai_api_sync(prompt)
        else:
            logger.warning(f"Unsupported LLM provider: {self.api_type}")
            return None

    def _call_nvidia_nim_sync(self, prompt: str) -> Optional[str]:
        """Call NVIDIA NIM API for llama-3.1-nemotron-8b analysis"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            response = requests.post(
                self.api_endpoint, 
                headers=headers, 
                json=payload, 
                timeout=self.llm_config.get("timeout", 60)
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    return json_match.group(1)
                
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json_match.group(0)
                
                return content
            else:
                logger.error(f"NVIDIA NIM API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"NVIDIA NIM API request failed: {e}")
            return None

    def _call_openai_api_sync(self, prompt: str) -> Optional[str]:
        """Call OpenAI API for analysis"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name if "gpt" in self.model_name else "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a senior DevOps engineer specializing in deployment failure analysis. Respond with valid JSON only."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions", 
                headers=headers, 
                json=payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"OpenAI API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            return None

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse and validate enhanced LLM JSON response"""
        try:
            response = response.strip()
            
            # Extract JSON from code blocks
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            
            # Try to extract JSON from response text
            if not response.startswith('{'):
                json_start = response.find('{')
                json_end = response.rfind('}')
                if json_start != -1 and json_end != -1:
                    response = response[json_start:json_end+1]
            
            data = json.loads(response)
            
            # Required fields for enhanced analysis
            required_fields = ["category", "subcategory", "root_cause", "fixability", "confidence", "reasoning"]
            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field in LLM response: {field}")
                    return None
            
            # Validate enum values
            try:
                category = FailureCategory(data["category"].lower())
                fixability = Fixability(data["fixability"].lower())
            except ValueError as e:
                logger.error(f"Invalid enum value in LLM response: {e}")
                return None
            
            # Validate confidence
            confidence = float(data["confidence"])
            if not 0.0 <= confidence <= 1.0:
                logger.warning(f"Confidence value {confidence} out of range, clamping to [0,1]")
                confidence = max(0.0, min(1.0, confidence))
            
            # Build enhanced response with new fields
            parsed_response = {
                "category": category,
                "subcategory": data["subcategory"],
                "root_cause": data["root_cause"],
                "fixability": fixability,
                "confidence": confidence,
                "reasoning": data["reasoning"],
                "fix_actions": data.get("fix_actions", []),
                "affected_files": data.get("affected_files", []),
                "estimated_fix_time": data.get("estimated_fix_time", "unknown"),
                "auto_fix_steps": data.get("auto_fix_steps", []),
                "retry_strategy": data.get("retry_strategy", {}),
                "github_actions": data.get("github_actions", {}),
                "kubernetes_fixes": data.get("kubernetes_fixes", {}),
                "requires_approval": data.get("requires_approval", False)
            }
            
            logger.info(f"Successfully parsed LLM response: {category.value}/{data['subcategory']} "
                       f"(confidence: {confidence:.2f}, fixability: {fixability.value})")
            
            return parsed_response
            
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response}")
            return None

    def _combine_analyses(
        self, 
        incident: IncidentEvent,
        pattern_match: Optional[Dict[str, Any]], 
        llm_analysis: Optional[Dict[str, Any]]
    ) -> FailureAnalysis:
        """Combine pattern matching and LLM analysis results with intelligent weighting"""
        
        if pattern_match and llm_analysis:
            if pattern_match["category"] == llm_analysis["category"]:
                combined_confidence = min(
                    (pattern_match["confidence"] * 0.4) + (llm_analysis["confidence"] * 0.6) + 0.1,
                    1.0
                )
                logger.debug(f"Pattern and LLM analysis agree on category: {llm_analysis['category'].value}")
            else:
                combined_confidence = llm_analysis["confidence"] * 0.8
                logger.debug(f"Pattern and LLM analysis disagree: {pattern_match['category'].value} vs {llm_analysis['category'].value}")
            
            return FailureAnalysis(
                incident_id=incident.incident_id,
                primary_category=llm_analysis["category"],
                subcategory=llm_analysis["subcategory"],
                root_cause=llm_analysis["root_cause"],
                fixability=llm_analysis["fixability"],
                confidence=combined_confidence,
                reasoning=f"LLM analysis (conf: {llm_analysis['confidence']:.2f}) + Pattern match (conf: {pattern_match['confidence']:.2f}): {llm_analysis['reasoning']}",
                affected_components=[],
                recent_changes=[]
            )
        
        elif llm_analysis:
            return FailureAnalysis(
                incident_id=incident.incident_id,
                primary_category=llm_analysis["category"],
                subcategory=llm_analysis["subcategory"],
                root_cause=llm_analysis["root_cause"],
                fixability=llm_analysis["fixability"],
                confidence=llm_analysis["confidence"],
                reasoning=f"LLM analysis: {llm_analysis['reasoning']}",
                affected_components=[],
                recent_changes=[]
            )
        
        elif pattern_match:
            return FailureAnalysis(
                incident_id=incident.incident_id,
                primary_category=pattern_match["category"],
                subcategory=pattern_match["subcategory"],
                root_cause=f"Pattern-based classification: {pattern_match['reasoning']}",
                fixability=pattern_match["fixability"],
                confidence=pattern_match["confidence"],
                reasoning=f"Pattern matching: {pattern_match['reasoning']}",
                affected_components=[],
                recent_changes=[]
            )
        
        else:
            return self._create_fallback_analysis(incident)

    def _create_fallback_analysis(self, incident: IncidentEvent) -> FailureAnalysis:
        """Create fallback analysis when all other methods fail"""
        error_lower = incident.error_log.lower()
        
        if any(word in error_lower for word in ["yaml", "json", "syntax", "parse"]):
            category = FailureCategory.CONFIG
            subcategory = "syntax_error"
            fixability = Fixability.AUTO
            confidence = 0.6
        elif any(word in error_lower for word in ["unauthorized", "forbidden", "auth"]):
            category = FailureCategory.AUTH
            subcategory = "permission_error"
            fixability = Fixability.AUTO
            confidence = 0.55
        elif any(word in error_lower for word in ["memory", "oom", "resource"]):
            category = FailureCategory.RESOURCE
            subcategory = "resource_limit"
            fixability = Fixability.AUTO
            confidence = 0.5
        elif any(word in error_lower for word in ["timeout", "connection", "network"]):
            category = FailureCategory.DEPENDENCY
            subcategory = "network_failure"
            fixability = Fixability.RETRY
            confidence = 0.45
        else:
            category = FailureCategory.DEPENDENCY
            subcategory = "unknown_failure"
            fixability = Fixability.INVESTIGATE
            confidence = 0.3
        
        return FailureAnalysis(
            incident_id=incident.incident_id,
            primary_category=category,
            subcategory=subcategory,
            root_cause="Fallback analysis - unable to classify failure automatically",
            fixability=fixability,
            confidence=confidence,
            reasoning="Fallback rule-based analysis due to LLM unavailability",
            affected_components=[],
            recent_changes=[]
        )

    def _extract_affected_components(self, incident: IncidentEvent) -> List[str]:
        """Extract affected components using enhanced parsing"""
        components = set()
        
        context_components = [
            incident.context.get("component"),
            incident.context.get("service"),
            incident.context.get("namespace")
        ]
        components.update([c for c in context_components if c])
        
        error_text = incident.error_log
        
        k8s_patterns = [
            r"(?:pod|service|deployment|statefulset|daemonset|configmap|secret)[/\s]+([a-zA-Z0-9-_.]+)",
            r"(?:namespace)[/\s]+([a-zA-Z0-9-]+)",
            r"(?:container)[/\s]+([a-zA-Z0-9-_.]+)",
            r"(?:image)[/\s]+([a-zA-Z0-9-_./:]+)"
        ]
        
        github_patterns = [
            r"(?:workflow|job|step)[/\s]+([a-zA-Z0-9-_.]+)",
            r"(?:action)[/\s]+([a-zA-Z0-9-_./@]+)"
        ]
        
        argocd_patterns = [
            r"(?:application|project)[/\s]+([a-zA-Z0-9-_.]+)"
        ]
        
        all_patterns = k8s_patterns + github_patterns + argocd_patterns
        
        for pattern in all_patterns:
            matches = re.findall(pattern, error_text, re.IGNORECASE)
            components.update(matches)
        
        filtered_components = []
        for comp in components:
            if comp and len(comp) > 2 and not comp.isdigit():
                filtered_components.append(comp)
        
        return filtered_components[:10]  

    async def _gather_recent_changes(self, incident: IncidentEvent) -> List[Dict[str, Any]]:
        """Gather recent changes that might be related to the failure"""
        changes = []
        
        try:
            changes.append({
                "type": "incident",
                "timestamp": incident.timestamp.isoformat(),
                "description": f"Failure detected in {incident.source}",
                "component": incident.context.get("component", "unknown"),
                "severity": incident.severity
            })
                        
        except Exception as e:
            logger.error(f"Failed to gather recent changes: {e}")
        
        return changes

    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get failure analysis statistics"""
        return {
            "total_patterns": len(self.error_patterns),
            "pattern_categories": {
                category.value: len([p for p in self.error_patterns if p.category == category])
                for category in FailureCategory
            },
            "llm_provider": self.api_type,
            "llm_model": self.model_name,
            "api_configured": bool(self.api_key)
        }

    def update_error_patterns(self, new_patterns: List[ErrorPattern]):
        """Update error patterns from learning"""
        self.error_patterns.extend(new_patterns)
        logger.info(f"Added {len(new_patterns)} new error patterns")

    def validate_analysis(self, analysis: FailureAnalysis, actual_outcome: str) -> Dict[str, Any]:
        """Validate analysis against actual resolution outcome"""
        return {
            "analysis_id": analysis.incident_id,
            "predicted_category": analysis.primary_category.value,
            "predicted_fixability": analysis.fixability.value,
            "confidence": analysis.confidence,
            "actual_outcome": actual_outcome,
            "accuracy": actual_outcome == "success" and analysis.fixability in [Fixability.AUTO, Fixability.RETRY]
        }