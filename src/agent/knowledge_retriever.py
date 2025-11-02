import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import hashlib

from utils.logger import get_logger
from utils.config import config
from agent.core_agent import (
    IncidentEvent, FailureAnalysis, ResolutionCandidate, 
    ResolutionSource
)

logger = get_logger(__name__)

@dataclass
class VectorSearchResult:
    """Result from vector database search"""
    incident_id: str
    similarity_score: float
    resolution_steps: List[str]
    success_rate: float
    environment: str
    last_applied: datetime
    metadata: Dict[str, Any]

@dataclass
class SlackSolution:
    """Solution extracted from Slack conversations"""
    message_id: str
    channel: str
    author: str
    timestamp: datetime
    solution_text: str
    code_blocks: List[str]
    thread_context: List[str]
    social_proof_score: float
    relevance_score: float

class KnowledgeRetriever:
    """
    Multi-source knowledge retrieval system implementing RAG for incident resolution
    
    Sources prioritized by reliability:
    1. Slack Solutions (team-validated, 95% confidence baseline)
    2. Vector DB Patterns (past successes, 85% confidence baseline)  
    3. LLM Analysis (novel failures, 60-80% confidence baseline)
    """
    
    def __init__(self, config_dict: Dict[str, Any] = None, slack_client=None):
        if config_dict is None:
            self.config = {
                "slack": {},
                "vector_db": {},
                "embedding": config.get_embedding_config()
            }
        else:
            self.config = config_dict
            # Ensure embedding config is available
            if "embedding" not in self.config:
                self.config["embedding"] = config.get_embedding_config()
        
        self.slack_client = slack_client
        self.vector_client = None
        self.embedding_client = None
        
        self.slack_config = self.config.get("slack", {})
        self.vector_config = self.config.get("vector_db", {})
        self.embedding_config = self.config.get("embedding", {})
        
        self.max_slack_results = self.slack_config.get("max_results", 20)
        self.max_vector_results = self.vector_config.get("max_results", 10)
        self.slack_time_window_days = self.slack_config.get("time_window_days", 180)
        self.vector_similarity_threshold = self.vector_config.get("similarity_threshold", 0.75)
        
        self.confidence_baselines = {
            ResolutionSource.SLACK: 0.90,
            ResolutionSource.VECTOR_DB: 0.80,
            ResolutionSource.LLM_ANALYSIS: 0.65
        }
        
        logger.info("KnowledgeRetriever initialized with NVIDIA NIM embedding support")

    async def retrieve_solutions(
        self, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis
    ) -> List[ResolutionCandidate]:
        """
        Retrieve potential solutions from all knowledge sources
        
        Args:
            incident: The incident to find solutions for
            analysis: Analysis results from FailureAnalyzer
            
        Returns:
            List of resolution candidates ranked by confidence
        """
        try:
            logger.info(f"Retrieving solutions for incident: {incident.incident_id}")
            
            # Check for similar LLM solutions first (fastest)
            similar_llm_solutions = await self.retrieve_similar_llm_solutions(analysis, max_results=3)
            
            slack_task = self._search_slack_solutions(incident, analysis)
            vector_task = self._search_vector_database(incident, analysis)
            llm_task = self._generate_llm_solutions(incident, analysis)
            
            slack_solutions, vector_results, llm_solutions = await asyncio.gather(
                slack_task, vector_task, llm_task, return_exceptions=True
            )
            
            if isinstance(slack_solutions, Exception):
                logger.error(f"Slack search failed: {slack_solutions}")
                slack_solutions = []
            
            if isinstance(vector_results, Exception):
                logger.error(f"Vector search failed: {vector_results}")
                vector_results = []
                
            if isinstance(llm_solutions, Exception):
                logger.error(f"LLM generation failed: {llm_solutions}")
                llm_solutions = []
            
            candidates = []
            
            # Add cached LLM solutions with high confidence
            for cached_solution in similar_llm_solutions:
                candidate = self._cached_llm_to_candidate(cached_solution, incident, analysis)
                if candidate:
                    candidates.append(candidate)
            
            for slack_solution in slack_solutions:
                candidate = self._slack_to_candidate(slack_solution, incident, analysis)
                if candidate:
                    candidates.append(candidate)
            
            for vector_result in vector_results:
                candidate = self._vector_to_candidate(vector_result, incident, analysis)
                if candidate:
                    candidates.append(candidate)
            
            for llm_solution in llm_solutions:
                candidate = self._llm_to_candidate(llm_solution, incident, analysis)
                if candidate:
                    candidates.append(candidate)
            
            candidates = self._deduplicate_candidates(candidates)
            candidates.sort(key=lambda x: x.confidence, reverse=True)
            
            logger.info(f"Retrieved {len(candidates)} solution candidates for {incident.incident_id}")
            return candidates
            
        except Exception as e:
            logger.error(f"Failed to retrieve solutions for {incident.incident_id}: {e}")
            return []

    async def _search_slack_solutions(
        self, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis
    ) -> List[SlackSolution]:
        """Search Slack for validated solutions"""
        if not self.slack_client:
            return []
        
        try:
            # Extract keywords from error and analysis
            error_keywords = self._extract_error_keywords(incident.error_log, analysis)
            
            # Search for solutions in configured channels
            channels = self.slack_config.get("search_channels", ["devops", "alerts", "incidents"])
            
            solutions = self.slack_client.search_for_solutions(
                error_keywords=error_keywords,
                channels=channels,
                time_window_days=self.slack_time_window_days
            )
            
            # Convert to SlackSolution objects
            slack_solutions = []
            for solution in solutions:
                slack_solutions.append(SlackSolution(
                    message_id=solution.get("permalink", ""),
                    channel=solution.get("channel", ""),
                    author=solution.get("user", {}).get("name", ""),
                    timestamp=datetime.fromtimestamp(float(solution.get("timestamp", 0))),
                    solution_text=solution.get("text", ""),
                    code_blocks=solution.get("code_blocks", []),
                    thread_context=[msg["text"] for msg in solution.get("thread_messages", [])],
                    social_proof_score=self._calculate_social_proof(solution),
                    relevance_score=solution.get("relevance_score", 0.0)
                ))
            
            logger.info(f"Found {len(slack_solutions)} Slack solutions")
            return slack_solutions
            
        except Exception as e:
            logger.error(f"Slack search failed: {e}")
            return []

    async def _search_vector_database(
        self, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis
    ) -> List[VectorSearchResult]:
        """Search vector database for similar past incidents"""
        try:
            # Generate embedding for current incident
            incident_embedding = await self._generate_embedding(incident, analysis)
            if not incident_embedding:
                return []
            
            # Perform k-NN search (placeholder - will integrate with OpenSearch)
            vector_results = await self._vector_knn_search(
                embedding=incident_embedding,
                k=self.max_vector_results,
                filters={
                    "environment": incident.context.get("environment"),
                    "category": analysis.primary_category.value,
                    "success_rate_threshold": 0.7
                }
            )
            
            logger.info(f"Found {len(vector_results)} vector database matches")
            return vector_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _generate_llm_solutions(
        self, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis
    ) -> List[Dict[str, Any]]:
        """Generate novel solutions using LLM for unknown failures"""
        try:
            # Only generate LLM solutions for low-confidence analysis or novel failures
            if analysis.confidence > 0.8:
                return []
            
            prompt = self._build_solution_generation_prompt(incident, analysis)
            response = await self._call_solution_llm(prompt)
            
            if response:
                solutions = self._parse_llm_solutions(response)
                logger.info(f"Generated {len(solutions)} LLM solutions")
                return solutions
            
            return []
            
        except Exception as e:
            logger.error(f"LLM solution generation failed: {e}")
            return []

    def _extract_error_keywords(self, error_log: str, analysis: FailureAnalysis) -> List[str]:
        """Extract relevant keywords for search"""
        keywords = []
        
        # Add category and subcategory
        keywords.append(analysis.primary_category.value)
        keywords.append(analysis.subcategory)
        
        # Extract technical terms from error log
        import re
        
        # Common deployment-related terms
        patterns = [
            r'\b(deployment|pod|service|ingress|configmap|secret)\b',
            r'\b(timeout|failed|error|exception)\b',
            r'\b(k8s|kubernetes|docker|image)\b',
            r'\b(github|actions|workflow|pipeline)\b',
            r'\b(argocd|helm|kustomize)\b'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, error_log.lower())
            keywords.extend(matches)
        
        # Remove duplicates and return
        return list(set(keywords))

    def _calculate_social_proof(self, slack_message: Dict[str, Any]) -> float:
        """Calculate social proof score based on Slack engagement"""
        score = 0.0
        
        # Base score for having a solution
        score += 10.0
        
        # Thread activity
        thread_count = len(slack_message.get("thread_messages", []))
        score += min(thread_count * 2, 20.0)  # Cap at 20 points
        
        # Author reputation (if available)
        user_info = slack_message.get("user", {})
        if user_info.get("is_admin"):
            score += 15.0
        
        # Code blocks (indicates technical solution)
        code_block_count = len(slack_message.get("code_blocks", []))
        score += min(code_block_count * 5, 25.0)  # Cap at 25 points
        
        # Normalize to 0-1 range
        return min(score / 100.0, 1.0)

    async def _generate_embedding(
        self, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis
    ) -> Optional[List[float]]:
        """Generate embedding for incident using NVIDIA Embedding NIM"""
        try:
            # Combine incident and analysis into search text
            search_text = f"""
            Error: {incident.error_log}
            Category: {analysis.primary_category.value}
            Subcategory: {analysis.subcategory}
            Root Cause: {analysis.root_cause}
            Environment: {incident.context.get('environment', 'unknown')}
            Service: {incident.context.get('service', 'unknown')}
            """
            
            # Call embedding service (placeholder)
            embedding = await self._call_embedding_service(search_text)
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def _call_embedding_service(self, text: str) -> Optional[List[float]]:
        """Call NVIDIA Embedding NIM service"""
        try:
            import aiohttp
            
            nim_config = self.embedding_config.get("nvidia_nim", {})
            nim_url = nim_config.get("url", "https://integrate.api.nvidia.com/v1/embeddings")
            api_key = nim_config.get("api_key")
            model = nim_config.get("model", "nvidia/nv-embedqa-e5-v5")
            
            if not api_key:
                logger.warning("NVIDIA NIM API key not configured, falling back to mock embeddings")
                import random
                return [random.random() for _ in range(768)]
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            payload = {
                "input": [text],
                "model": model,
                "encoding_format": "float",
                "extra_body": {
                    "truncate": "END"
                }
            }
            
            timeout = aiohttp.ClientTimeout(total=30) 
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(nim_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if "data" in result and len(result["data"]) > 0:
                            embedding = result["data"][0].get("embedding", [])
                            if embedding:
                                logger.info(f"Generated embedding with dimension: {len(embedding)}")
                                return embedding
                            else:
                                logger.error("No embedding found in NIM response")
                        else:
                            logger.error("Invalid response format from NVIDIA NIM")
                    else:
                        error_text = await response.text()
                        logger.error(f"NVIDIA NIM API error {response.status}: {error_text}")
            
            logger.warning("Falling back to mock embeddings due to API failure")
            import random
            return [random.random() for _ in range(768)]
            
        except ImportError:
            logger.warning("aiohttp not available, falling back to mock embeddings")
            await asyncio.sleep(0.1)  
            import random
            return [random.random() for _ in range(768)]
            
        except Exception as e:
            logger.error(f"Failed to call NVIDIA NIM embedding service: {e}")
            import random
            return [random.random() for _ in range(768)]

    async def _vector_knn_search(
        self, 
        embedding: List[float], 
        k: int, 
        filters: Dict[str, Any]
    ) -> List[VectorSearchResult]:
        """Perform k-NN search in vector database"""
        # Placeholder implementation - will integrate with OpenSearch
        await asyncio.sleep(0.2)  # Simulate search
        
        # Return mock results for development
        results = []
        for i in range(min(k, 3)):  # Return up to 3 mock results
            results.append(VectorSearchResult(
                incident_id=f"past-incident-{i}",
                similarity_score=0.85 - (i * 0.05),
                resolution_steps=[
                    f"Mock resolution step 1 for result {i}",
                    f"Mock resolution step 2 for result {i}"
                ],
                success_rate=0.9 - (i * 0.1),
                environment=filters.get("environment", "unknown"),
                last_applied=datetime.utcnow() - timedelta(days=i * 10),
                metadata={"source": "vector_db", "category": filters.get("category")}
            ))
        
        return results

    def _build_solution_generation_prompt(
        self, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis
    ) -> str:
        """Build prompt for LLM solution generation"""
        prompt = f"""You are a senior DevOps engineer generating solutions for a deployment failure.

Incident Details:
- ID: {incident.incident_id}
- Source: {incident.source}
- Environment: {incident.context.get('environment')}
- Service: {incident.context.get('service')}

Failure Analysis:
- Category: {analysis.primary_category.value}
- Subcategory: {analysis.subcategory}
- Root Cause: {analysis.root_cause}
- Fixability: {analysis.fixability.value}

Error Log:
```
{incident.error_log}
```

Generate 2-3 potential solutions for this failure. For each solution provide:

1. "description": Brief description of the solution
2. "steps": Detailed step-by-step instructions
3. "confidence": Your confidence in this solution (0.0-1.0)
4. "estimated_duration": Time to implement in minutes
5. "prerequisites": Any prerequisites or checks needed
6. "rollback_plan": How to rollback if the solution fails
7. "environment_restrictions": Any environment-specific considerations

Focus on practical, actionable solutions that can be automated.
Be specific about commands, API calls, and configuration changes.

Respond with a JSON array of solutions:"""

        return prompt

    async def _call_solution_llm(self, prompt: str) -> Optional[str]:
        """Call LLM for solution generation"""
        # Placeholder implementation - will integrate with NVIDIA NIM
        await asyncio.sleep(0.8)  # Simulate API call
        
        # Mock response for development
        mock_solutions = [
            {
                "description": "Retry workflow with exponential backoff",
                "steps": [
                    "Wait 60 seconds for transient issue to resolve",
                    "Re-trigger the workflow via GitHub API",
                    "Monitor execution for success"
                ],
                "confidence": 0.7,
                "estimated_duration": 5,
                "prerequisites": ["GitHub API access", "Workflow is in failed state"],
                "rollback_plan": "Cancel retry if it fails again",
                "environment_restrictions": "Safe for all environments"
            },
            {
                "description": "Update configuration to fix syntax error",
                "steps": [
                    "Clone repository to temporary location",
                    "Fix YAML syntax error in workflow file",
                    "Validate syntax with yamllint",
                    "Create pull request with fix",
                    "Auto-merge if confidence > 95%"
                ],
                "confidence": 0.85,
                "estimated_duration": 8,
                "prerequisites": ["Repository write access", "YAML syntax error identified"],
                "rollback_plan": "Revert commit if workflow still fails",
                "environment_restrictions": "Requires manual approval for production"
            }
        ]
        
        return json.dumps(mock_solutions)

    def _parse_llm_solutions(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM solution response"""
        try:
            solutions = json.loads(response)
            
            # Validate each solution
            valid_solutions = []
            for solution in solutions:
                if self._validate_solution_format(solution):
                    valid_solutions.append(solution)
            
            return valid_solutions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM solutions: {e}")
            return []

    def _validate_solution_format(self, solution: Dict[str, Any]) -> bool:
        """Validate solution has required fields"""
        required_fields = ["description", "steps", "confidence", "estimated_duration"]
        return all(field in solution for field in required_fields)

    def _cached_llm_to_candidate(
        self, 
        cached_solution: Dict[str, Any], 
        incident: IncidentEvent, 
        analysis: FailureAnalysis
    ) -> Optional[ResolutionCandidate]:
        """Convert cached LLM solution to resolution candidate"""
        try:
            # Extract steps from cached solution
            steps = cached_solution.get('resolution_steps', [])
            if not steps:
                # Fallback to fix actions
                fix_actions = cached_solution.get('fix_actions', [])
                steps = [f"Apply fix: {action}" for action in fix_actions]
            
            # Calculate boosted confidence based on reuse success
            base_confidence = self.confidence_baselines[ResolutionSource.LLM_ANALYSIS]
            similarity_boost = cached_solution.get('similarity_score', 0) * 0.1  # Up to 10% boost
            success_boost = cached_solution.get('success_rate', 0) * 0.05  # Up to 5% boost
            
            confidence = min(base_confidence + similarity_boost + success_boost, 0.95)
            
            return ResolutionCandidate(
                resolution_id=self._generate_resolution_id(cached_solution['signature'][:16]),
                source=ResolutionSource.LLM_ANALYSIS,
                description=f"Cached LLM solution (reused {cached_solution.get('reuse_count', 0)} times)",
                steps=steps,
                confidence=confidence,
                estimated_duration=cached_solution.get('estimated_fix_time', 'Unknown'),
                success_indicators=[
                    "Configuration files updated successfully",
                    "Application deployment successful",
                    "No recurring errors in logs"
                ],
                rollback_instructions=[
                    "Revert file changes using git",
                    "Redeploy previous working version"
                ],
                metadata={
                    "cached_solution": True,
                    "original_incident": cached_solution.get('incident_id'),
                    "reuse_count": cached_solution.get('reuse_count', 0),
                    "success_rate": cached_solution.get('success_rate', 1.0),
                    "solution_signature": cached_solution.get('signature'),
                    "tags": cached_solution.get('tags', [])
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to convert cached LLM solution: {e}")
            return None

    def _slack_to_candidate(
        self, 
        slack_solution: SlackSolution, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis
    ) -> Optional[ResolutionCandidate]:
        """Convert Slack solution to resolution candidate"""
        try:
            # Extract steps from solution text and code blocks
            steps = []
            
            # Add code blocks as steps
            for code_block in slack_solution.code_blocks:
                steps.append(f"Execute: {code_block}")
            
            # Add solution text as description step
            if slack_solution.solution_text:
                steps.append(f"Context: {slack_solution.solution_text}")
            
            # Calculate confidence based on social proof and relevance
            base_confidence = self.confidence_baselines[ResolutionSource.SLACK]
            social_boost = slack_solution.social_proof_score * 0.05  # Up to 5% boost
            relevance_boost = slack_solution.relevance_score * 0.01  # Up to 1% boost
            
            confidence = min(base_confidence + social_boost + relevance_boost, 0.98)
            
            return ResolutionCandidate(
                resolution_id=self._generate_resolution_id(slack_solution.message_id),
                source=ResolutionSource.SLACK,
                description=f"Slack solution from #{slack_solution.channel}",
                steps=steps,
                confidence=confidence,
                success_rate=0.95,  # High for peer-validated solutions
                last_used=slack_solution.timestamp,
                environment_match=True,  # Slack solutions are environment-agnostic
                code_changes=[],
                estimated_duration=10  # Default for Slack solutions
            )
            
        except Exception as e:
            logger.error(f"Failed to convert Slack solution: {e}")
            return None

    def _vector_to_candidate(
        self, 
        vector_result: VectorSearchResult, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis
    ) -> Optional[ResolutionCandidate]:
        """Convert vector DB result to resolution candidate"""
        try:
            # Calculate confidence based on similarity and success rate
            base_confidence = self.confidence_baselines[ResolutionSource.VECTOR_DB]
            similarity_boost = (vector_result.similarity_score - 0.75) * 0.2  # Boost for high similarity
            success_boost = (vector_result.success_rate - 0.7) * 0.1  # Boost for high success rate
            
            confidence = min(base_confidence + similarity_boost + success_boost, 0.95)
            
            # Environment matching
            environment_match = (
                vector_result.environment == incident.context.get("environment") or
                vector_result.environment == "all"
            )
            
            return ResolutionCandidate(
                resolution_id=self._generate_resolution_id(vector_result.incident_id),
                source=ResolutionSource.VECTOR_DB,
                description=f"Solution from similar incident (similarity: {vector_result.similarity_score:.2f})",
                steps=vector_result.resolution_steps,
                confidence=confidence,
                success_rate=vector_result.success_rate,
                last_used=vector_result.last_applied,
                environment_match=environment_match,
                code_changes=[],
                estimated_duration=15  # Default for vector DB solutions
            )
            
        except Exception as e:
            logger.error(f"Failed to convert vector result: {e}")
            return None

    def _llm_to_candidate(
        self, 
        llm_solution: Dict[str, Any], 
        incident: IncidentEvent, 
        analysis: FailureAnalysis
    ) -> Optional[ResolutionCandidate]:
        """Convert LLM solution to resolution candidate"""
        try:
            # Use LLM-provided confidence, capped for safety
            llm_confidence = min(float(llm_solution["confidence"]), 0.8)
            base_confidence = self.confidence_baselines[ResolutionSource.LLM_ANALYSIS]
            
            confidence = min(base_confidence, llm_confidence)
            
            return ResolutionCandidate(
                resolution_id=self._generate_resolution_id(f"llm-{incident.incident_id}"),
                source=ResolutionSource.LLM_ANALYSIS,
                description=llm_solution["description"],
                steps=llm_solution["steps"],
                confidence=confidence,
                success_rate=0.6,  # Conservative estimate for novel solutions
                last_used=None,
                environment_match=True,  # LLM considers environment context
                code_changes=[],
                estimated_duration=llm_solution["estimated_duration"]
            )
            
        except Exception as e:
            logger.error(f"Failed to convert LLM solution: {e}")
            return None

    def _deduplicate_candidates(self, candidates: List[ResolutionCandidate]) -> List[ResolutionCandidate]:
        """Remove duplicate resolution candidates"""
        seen_hashes = set()
        unique_candidates = []
        
        for candidate in candidates:
            # Create hash based on steps content
            content_hash = hashlib.md5(
                json.dumps(candidate.steps, sort_keys=True).encode()
            ).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_candidates.append(candidate)
        
        return unique_candidates

    def _generate_resolution_id(self, source_id: str) -> str:
        """Generate unique resolution ID"""
        return hashlib.sha256(
            f"{source_id}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

    async def store_successful_resolution(
        self, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis, 
        resolution: ResolutionCandidate,
        outcome: str
    ):
        """Store successful resolution in vector database for future retrieval"""
        try:
            if outcome == "success":
                # Generate embedding and store in vector DB
                embedding = await self._generate_embedding(incident, analysis)
                if embedding:
                    await self._store_in_vector_db(incident, analysis, resolution, embedding)
                    logger.info(f"Stored successful resolution for {incident.incident_id}")
                
                # Store LLM-specific solutions for reuse
                if resolution.source == ResolutionSource.LLM_ANALYSIS:
                    await self._store_llm_solution(incident, analysis, resolution)
            
        except Exception as e:
            logger.error(f"Failed to store resolution: {e}")

    async def _store_llm_solution(
        self, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis, 
        resolution: ResolutionCandidate
    ):
        """Store LLM solution with enhanced metadata for reuse"""
        try:
            # Create solution signature for similarity matching
            solution_signature = self._create_solution_signature(analysis, resolution)
            
            # Enhanced solution record
            solution_record = {
                "incident_id": incident.incident_id,
                "signature": solution_signature,
                "category": analysis.primary_category.value,
                "subcategory": analysis.subcategory,
                "confidence": analysis.confidence,
                "summary": analysis.summary,
                "fix_actions": getattr(analysis, 'fix_actions', []),
                "affected_files": getattr(analysis, 'affected_files', []),
                "estimated_fix_time": getattr(analysis, 'estimated_fix_time', 'Unknown'),
                "resolution_steps": resolution.steps,
                "environment": incident.metadata.get('environment', 'unknown'),
                "repository": incident.metadata.get('repository', 'unknown'),
                "success_indicators": resolution.success_indicators,
                "timestamp": datetime.now().isoformat(),
                "reuse_count": 0,
                "success_rate": 1.0,  # Initial success rate
                "tags": self._extract_solution_tags(analysis, resolution)
            }
            
            # Store in local cache for immediate reuse
            await self._cache_llm_solution(solution_record)
            
            # Store in persistent storage (vector DB or dedicated LLM solution store)
            if self.vector_client:
                await self._store_llm_solution_persistent(solution_record)
                
            logger.info(f"Stored LLM solution with signature: {solution_signature[:16]}...")
            
        except Exception as e:
            logger.error(f"Failed to store LLM solution: {e}")

    def _create_solution_signature(self, analysis: FailureAnalysis, resolution: ResolutionCandidate) -> str:
        """Create unique signature for solution matching"""
        signature_components = [
            analysis.primary_category.value,
            analysis.subcategory,
            str(sorted(analysis.indicators)),
            str(sorted(getattr(analysis, 'fix_actions', []))),
            str(sorted(getattr(analysis, 'affected_files', [])))
        ]
        
        signature_text = "|".join(signature_components)
        return hashlib.sha256(signature_text.encode()).hexdigest()

    def _extract_solution_tags(self, analysis: FailureAnalysis, resolution: ResolutionCandidate) -> List[str]:
        """Extract searchable tags from solution"""
        tags = [
            analysis.primary_category.value.lower(),
            analysis.subcategory.lower()
        ]
        
        # Add tags based on fix actions
        fix_actions = getattr(analysis, 'fix_actions', [])
        for action in fix_actions:
            if 'yaml' in action.lower():
                tags.append('yaml-fix')
            if 'config' in action.lower():
                tags.append('config-fix')
            if 'image' in action.lower():
                tags.append('image-fix')
            if 'environment' in action.lower():
                tags.append('env-fix')
        
        # Add file type tags
        affected_files = getattr(analysis, 'affected_files', [])
        for file_path in affected_files:
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                tags.append('yaml-file')
            elif file_path.endswith('.json'):
                tags.append('json-file')
            elif 'deployment' in file_path.lower():
                tags.append('deployment-file')
            elif 'service' in file_path.lower():
                tags.append('service-file')
        
        return list(set(tags))  # Remove duplicates

    async def _cache_llm_solution(self, solution_record: Dict[str, Any]):
        """Cache LLM solution in memory for immediate reuse"""
        try:
            # Initialize cache if not exists
            if not hasattr(self, '_llm_solution_cache'):
                self._llm_solution_cache = {}
            
            signature = solution_record['signature']
            self._llm_solution_cache[signature] = solution_record
            
            # Limit cache size (keep most recent 100 solutions)
            if len(self._llm_solution_cache) > 100:
                oldest_signature = min(
                    self._llm_solution_cache.keys(),
                    key=lambda k: self._llm_solution_cache[k]['timestamp']
                )
                del self._llm_solution_cache[oldest_signature]
                
        except Exception as e:
            logger.error(f"Failed to cache LLM solution: {e}")

    async def _store_llm_solution_persistent(self, solution_record: Dict[str, Any]):
        """Store LLM solution in persistent storage"""
        # Placeholder for vector DB storage of LLM solutions
        # In production, this would integrate with OpenSearch or similar
        pass

    async def retrieve_similar_llm_solutions(
        self, 
        analysis: FailureAnalysis, 
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve similar LLM solutions from cache and storage"""
        try:
            similar_solutions = []
            
            # Search in memory cache first
            if hasattr(self, '_llm_solution_cache'):
                for signature, solution in self._llm_solution_cache.items():
                    similarity_score = self._calculate_solution_similarity(analysis, solution)
                    if similarity_score > 0.7:  # High similarity threshold
                        solution_copy = solution.copy()
                        solution_copy['similarity_score'] = similarity_score
                        similar_solutions.append(solution_copy)
            
            # Sort by similarity and reuse success
            similar_solutions.sort(
                key=lambda x: (x['similarity_score'] * x['success_rate']),
                reverse=True
            )
            
            return similar_solutions[:max_results]
            
        except Exception as e:
            logger.error(f"Failed to retrieve similar LLM solutions: {e}")
            return []

    def _calculate_solution_similarity(self, analysis: FailureAnalysis, solution: Dict[str, Any]) -> float:
        """Calculate similarity between current analysis and stored solution"""
        try:
            score = 0.0
            
            # Category match (40% weight)
            if analysis.primary_category.value == solution['category']:
                score += 0.4
            
            # Subcategory match (30% weight)
            if analysis.subcategory == solution['subcategory']:
                score += 0.3
            
            # Indicator overlap (20% weight)
            current_indicators = set(analysis.indicators)
            solution_tags = set(solution.get('tags', []))
            if current_indicators and solution_tags:
                overlap = len(current_indicators.intersection(solution_tags))
                total = len(current_indicators.union(solution_tags))
                score += 0.2 * (overlap / total) if total > 0 else 0
            
            # Confidence similarity (10% weight)
            confidence_diff = abs(analysis.confidence - solution['confidence'])
            score += 0.1 * (1 - confidence_diff)
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Failed to calculate solution similarity: {e}")
            return 0.0

    async def update_solution_success_rate(self, solution_signature: str, success: bool):
        """Update success rate of a reused solution"""
        try:
            # Update in cache
            if hasattr(self, '_llm_solution_cache') and solution_signature in self._llm_solution_cache:
                solution = self._llm_solution_cache[solution_signature]
                solution['reuse_count'] += 1
                
                # Update success rate using exponential moving average
                alpha = 0.3  # Learning rate
                current_success = 1.0 if success else 0.0
                solution['success_rate'] = (
                    alpha * current_success + 
                    (1 - alpha) * solution['success_rate']
                )
                
                logger.info(f"Updated solution success rate: {solution['success_rate']:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to update solution success rate: {e}")

    async def _store_in_vector_db(
        self, 
        incident: IncidentEvent, 
        analysis: FailureAnalysis, 
        resolution: ResolutionCandidate,
        embedding: List[float]
    ):
        """Store resolution in vector database"""
        # Placeholder implementation - will integrate with OpenSearch
        pass

    def get_retrieval_statistics(self) -> Dict[str, Any]:
        """Get knowledge retrieval statistics"""
        return {
            "sources_enabled": {
                "slack": self.slack_client is not None,
                "vector_db": self.vector_client is not None,
                "llm": True
            },
            "search_parameters": {
                "slack_time_window_days": self.slack_time_window_days,
                "vector_similarity_threshold": self.vector_similarity_threshold,
                "max_results_per_source": {
                    "slack": self.max_slack_results,
                    "vector_db": self.max_vector_results
                }
            },
            "confidence_baselines": {
                source.value: baseline 
                for source, baseline in self.confidence_baselines.items()
            }
        }