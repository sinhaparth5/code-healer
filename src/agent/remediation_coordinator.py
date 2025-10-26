import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger
from agent.core_agent import (
    IncidentEvent, FailureAnalysis, ResolutionCandidate, RemediationResult,
    FailureCategory, Fixability, ResolutionSource
)
from integrations.github_client import GitHubClient
from integrations.argocd_client import ArgoCDClient

logger = get_logger(__name__)

class RemediationAction(Enum):
    GITHUB_RERUN = "github_rerun"
    GITHUB_UPDATE_CONFIG = "github_update_config"
    GITHUB_UPDATE_SECRET = "github_update_secret"
    ARGOCD_SYNC = "argocd_sync"
    ARGOCD_UPDATE_MANIFEST = "argocd_update_manifest"
    KUBERNETES_SCALE = "kubernetes_scale"
    KUBERNETES_RESTART = "kubernetes_restart"
    WAIT_AND_RETRY = "wait_and_retry"
    ESCALATE_TO_HUMAN = "escalate_to_human"

class ApprovalStatus(Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

@dataclass
class RemediationPlan:
    """Plan for executing a remediation"""
    resolution_id: str
    actions: List[RemediationAction]
    approval_required: bool
    approval_status: ApprovalStatus
    risk_level: str
    rollback_plan: List[str]
    estimated_duration: int
    prerequisites: List[str]
    metadata: Dict[str, Any]

@dataclass
class ExecutionContext:
    """Context for remediation execution"""
    incident: IncidentEvent
    analysis: FailureAnalysis
    resolution: ResolutionCandidate
    plan: RemediationPlan
    start_time: datetime
    rollback_data: Dict[str, Any]

class RemediationCoordinator:
    """
    Coordinates automated remediation decisions and execution
    
    Implements the cost-benefit optimization from the research:
    - Automate fix F if E[C|F] < E[C|manual]
    - Considers confidence thresholds, environment, and risk levels
    - Provides rollback capabilities and approval workflows
    """
    
    def __init__(self, config: Dict[str, Any], github_client=None, argocd_client=None):
        self.config = config
        self.github_client = github_client
        self.argocd_client = argocd_client
        
        self.remediation_config = config.get("remediation", {})
        self.approval_config = config.get("approval", {})
        
        self.confidence_thresholds = self.remediation_config.get("confidence_thresholds", {
            "production": 0.92,
            "staging": 0.85,
            "development": 0.75,
            "default": 0.85
        })
        
        self.risk_factors = self.remediation_config.get("risk_factors", {
            "production_environment": 0.3,
            "cross_service_impact": 0.25,
            "config_changes": 0.15,
            "resource_scaling": 0.20,
            "credential_updates": 0.10
        })
        
        self.approval_rules = self.approval_config.get("rules", {
            "production_always": True,
            "high_risk_always": True,
            "low_confidence_threshold": 0.9,
            "resource_scaling_threshold": 2.0
        })
        
        self.active_remediations = {}
        self.remediation_history = {}
        
        logger.info("RemediationCoordinator initialized")

    async def coordinate_remediation(
        self, 
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution_candidates: List[ResolutionCandidate]
    ) -> Optional[RemediationResult]:
        """
        Main coordination method for automated remediation
        
        Args:
            incident: The incident to remediate
            analysis: Failure analysis results
            resolution_candidates: Potential solutions ranked by confidence
            
        Returns:
            RemediationResult if remediation was attempted, None otherwise
        """
        try:
            logger.info(f"Coordinating remediation for incident: {incident.incident_id}")
            
            if not resolution_candidates:
                logger.info(f"No resolution candidates for {incident.incident_id}")
                return None
            
            selected_resolution = await self._select_resolution(
                incident, analysis, resolution_candidates
            )
            
            if not selected_resolution:
                logger.info(f"No suitable resolution found for {incident.incident_id}")
                return None
            
            remediation_plan = await self._create_remediation_plan(
                incident, analysis, selected_resolution
            )
            
            should_proceed = await self._should_proceed_with_remediation(
                incident, analysis, selected_resolution, remediation_plan
            )
            
            if not should_proceed:
                logger.info(f"Remediation rejected for {incident.incident_id}")
                return self._create_rejection_result(incident, selected_resolution, "Risk too high")
            
            if remediation_plan.approval_required:
                approval_result = await self._handle_approval_workflow(
                    incident, analysis, selected_resolution, remediation_plan
                )
                if not approval_result:
                    return self._create_rejection_result(
                        incident, selected_resolution, "Approval required"
                    )
            
            remediation_result = await self._execute_remediation(
                incident, analysis, selected_resolution, remediation_plan
            )
            
            self.remediation_history[incident.incident_id] = {
                "incident": incident,
                "analysis": analysis,
                "resolution": selected_resolution,
                "plan": remediation_plan,
                "result": remediation_result
            }
            
            return remediation_result
            
        except Exception as e:
            logger.error(f"Remediation coordination failed for {incident.incident_id}: {e}")
            return self._create_error_result(incident, str(e))

    async def _select_resolution(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        candidates: List[ResolutionCandidate]
    ) -> Optional[ResolutionCandidate]:
        """Select the best resolution candidate"""
        
        min_confidence = self._get_min_confidence_threshold(incident.context.get("environment"))
        viable_candidates = [
            c for c in candidates 
            if c.confidence >= min_confidence and analysis.fixability == Fixability.AUTO
        ]
        
        if not viable_candidates:
            logger.info(f"No candidates meet confidence threshold {min_confidence}")
            return None
        
        scored_candidates = []
        for candidate in viable_candidates:
            score = self._calculate_candidate_score(incident, analysis, candidate)
            scored_candidates.append((score, candidate))
        
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        best_candidate = scored_candidates[0][1]
        
        logger.info(f"Selected resolution: {best_candidate.description} "
                   f"(confidence: {best_candidate.confidence:.2f})")
        
        return best_candidate

    def _calculate_candidate_score(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        candidate: ResolutionCandidate
    ) -> float:
        """Calculate overall score for a resolution candidate"""
        score = 0.0
        
        score += candidate.confidence * 0.6
        
        source_weights = {
            ResolutionSource.SLACK: 1.0,
            ResolutionSource.VECTOR_DB: 0.9,
            ResolutionSource.LLM_ANALYSIS: 0.7
        }
        score += source_weights.get(candidate.source, 0.5) * 0.2
        
        score += candidate.success_rate * 0.1
        
        if candidate.environment_match:
            score += 0.05
        
        if candidate.last_used:
            days_since_used = (datetime.utcnow() - candidate.last_used).days
            recency_factor = max(0, 1 - (days_since_used / 90))
            score += recency_factor * 0.05
        
        return score

    async def _create_remediation_plan(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution: ResolutionCandidate
    ) -> RemediationPlan:
        """Create detailed remediation plan"""
        
        actions = self._determine_remediation_actions(incident, analysis, resolution)
        
        risk_level = self._assess_risk_level(incident, analysis, resolution, actions)
        
        approval_required = self._requires_approval(incident, analysis, resolution, risk_level)
        
        rollback_plan = self._create_rollback_plan(incident, analysis, actions)
        
        estimated_duration = self._estimate_execution_duration(actions)
        
        prerequisites = self._identify_prerequisites(incident, analysis, actions)
        
        return RemediationPlan(
            resolution_id=resolution.resolution_id,
            actions=actions,
            approval_required=approval_required,
            approval_status=ApprovalStatus.NOT_REQUIRED if not approval_required else ApprovalStatus.PENDING,
            risk_level=risk_level,
            rollback_plan=rollback_plan,
            estimated_duration=estimated_duration,
            prerequisites=prerequisites,
            metadata={
                "incident_id": incident.incident_id,
                "analysis_confidence": analysis.confidence,
                "resolution_confidence": resolution.confidence,
                "created_at": datetime.utcnow().isoformat()
            }
        )

    def _determine_remediation_actions(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution: ResolutionCandidate
    ) -> List[RemediationAction]:
        """Determine specific actions needed for remediation"""
        actions = []
        
        if incident.source == "github_actions":
            if analysis.primary_category == FailureCategory.CONFIG:
                if "syntax" in analysis.subcategory.lower():
                    actions.append(RemediationAction.GITHUB_UPDATE_CONFIG)
                elif "secret" in analysis.subcategory.lower():
                    actions.append(RemediationAction.GITHUB_UPDATE_SECRET)
            elif analysis.primary_category == FailureCategory.DEPENDENCY:
                actions.append(RemediationAction.WAIT_AND_RETRY)
                actions.append(RemediationAction.GITHUB_RERUN)
            else:
                actions.append(RemediationAction.GITHUB_RERUN)
        
        elif incident.source == "argocd":
            if analysis.primary_category == FailureCategory.CONFIG:
                actions.append(RemediationAction.ARGOCD_UPDATE_MANIFEST)
            actions.append(RemediationAction.ARGOCD_SYNC)
        
        elif incident.source == "kubernetes":
            if analysis.primary_category == FailureCategory.RESOURCE:
                if "memory" in analysis.subcategory.lower():
                    actions.append(RemediationAction.KUBERNETES_SCALE)
                else:
                    actions.append(RemediationAction.KUBERNETES_RESTART)
        
        if not actions:
            actions.append(RemediationAction.ESCALATE_TO_HUMAN)
        
        return actions

    def _assess_risk_level(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution: ResolutionCandidate,
        actions: List[RemediationAction]
    ) -> str:
        """Assess risk level of the remediation"""
        risk_score = 0.0
        
        # Environment risk
        environment = incident.context.get("environment", "unknown")
        if environment == "production":
            risk_score += self.risk_factors["production_environment"]
        
        # Action-based risk
        high_risk_actions = [
            RemediationAction.GITHUB_UPDATE_CONFIG,
            RemediationAction.KUBERNETES_SCALE,
            RemediationAction.GITHUB_UPDATE_SECRET
        ]
        
        for action in actions:
            if action in high_risk_actions:
                if action == RemediationAction.KUBERNETES_SCALE:
                    risk_score += self.risk_factors["resource_scaling"]
                elif action == RemediationAction.GITHUB_UPDATE_CONFIG:
                    risk_score += self.risk_factors["config_changes"]
                elif action == RemediationAction.GITHUB_UPDATE_SECRET:
                    risk_score += self.risk_factors["credential_updates"]
        
        confidence_risk = (1.0 - resolution.confidence) * 0.2
        risk_score += confidence_risk
        
        if len(analysis.affected_components) > 1:
            risk_score += self.risk_factors["cross_service_impact"]
        
        if risk_score >= 0.7:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        else:
            return "low"

    def _requires_approval(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution: ResolutionCandidate,
        risk_level: str
    ) -> bool:
        """Determine if approval is required"""
        
        if (incident.context.get("environment") == "production" and 
            self.approval_rules.get("production_always", True)):
            return True
        
        if risk_level == "high" and self.approval_rules.get("high_risk_always", True):
            return True
        
        confidence_threshold = self.approval_rules.get("low_confidence_threshold", 0.9)
        if resolution.confidence < confidence_threshold:
            return True
        
        scaling_actions = [RemediationAction.KUBERNETES_SCALE]
        if any(action in scaling_actions for action in []):  
            return True
        
        return False

    def _create_rollback_plan(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        actions: List[RemediationAction]
    ) -> List[str]:
        """Create rollback plan for the remediation"""
        rollback_steps = []
        
        for action in actions:
            if action == RemediationAction.GITHUB_UPDATE_CONFIG:
                rollback_steps.append("Revert configuration file changes via Git")
                rollback_steps.append("Re-trigger workflow with reverted config")
            
            elif action == RemediationAction.GITHUB_UPDATE_SECRET:
                rollback_steps.append("Restore previous secret value")
                rollback_steps.append("Re-trigger workflow")
            
            elif action == RemediationAction.KUBERNETES_SCALE:
                rollback_steps.append("Scale back to original resource limits")
                rollback_steps.append("Monitor pod stability")
            
            elif action == RemediationAction.ARGOCD_UPDATE_MANIFEST:
                rollback_steps.append("Revert manifest changes in Git")
                rollback_steps.append("Trigger ArgoCD sync")
            
            elif action == RemediationAction.GITHUB_RERUN:
                rollback_steps.append("Cancel workflow run if still in progress")
            
        return rollback_steps

    def _estimate_execution_duration(self, actions: List[RemediationAction]) -> int:
        """Estimate execution duration in minutes"""
        duration_map = {
            RemediationAction.GITHUB_RERUN: 2,
            RemediationAction.GITHUB_UPDATE_CONFIG: 8,
            RemediationAction.GITHUB_UPDATE_SECRET: 3,
            RemediationAction.ARGOCD_SYNC: 5,
            RemediationAction.ARGOCD_UPDATE_MANIFEST: 10,
            RemediationAction.KUBERNETES_SCALE: 7,
            RemediationAction.KUBERNETES_RESTART: 5,
            RemediationAction.WAIT_AND_RETRY: 3,
            RemediationAction.ESCALATE_TO_HUMAN: 1
        }
        
        total_duration = sum(duration_map.get(action, 5) for action in actions)
        return total_duration

    def _identify_prerequisites(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        actions: List[RemediationAction]
    ) -> List[str]:
        """Identify prerequisites for remediation"""
        prerequisites = []
        
        for action in actions:
            if action in [RemediationAction.GITHUB_RERUN, RemediationAction.GITHUB_UPDATE_CONFIG]:
                prerequisites.append("GitHub API access token")
                prerequisites.append("Repository write permissions")
            
            elif action in [RemediationAction.ARGOCD_SYNC, RemediationAction.ARGOCD_UPDATE_MANIFEST]:
                prerequisites.append("ArgoCD API access")
                prerequisites.append("Application sync permissions")
            
            elif action in [RemediationAction.KUBERNETES_SCALE, RemediationAction.KUBERNETES_RESTART]:
                prerequisites.append("Kubernetes cluster access")
                prerequisites.append("Namespace resource permissions")
        
        return list(set(prerequisites))  

    async def _should_proceed_with_remediation(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution: ResolutionCandidate,
        plan: RemediationPlan
    ) -> bool:
        """Apply decision algorithm to determine if remediation should proceed"""
        
        cost_if_successful = 1.0  
        cost_if_failed = 50.0    
        cost_manual = 500.0      
        
        expected_cost_auto = (
            resolution.confidence * cost_if_successful + 
            (1 - resolution.confidence) * cost_if_failed
        )
        
        should_proceed = expected_cost_auto < cost_manual
        
        if plan.risk_level == "high" and resolution.confidence < 0.95:
            should_proceed = False
            logger.info(f"Rejecting high-risk remediation with confidence {resolution.confidence:.2f}")
        
        environment = incident.context.get("environment")
        if environment == "production" and resolution.confidence < self.confidence_thresholds["production"]:
            should_proceed = False
            logger.info(f"Rejecting production remediation below threshold")
        
        logger.info(f"Remediation decision for {incident.incident_id}: {should_proceed} "
                   f"(expected cost: {expected_cost_auto:.2f} vs manual: {cost_manual})")
        
        return should_proceed

    async def _handle_approval_workflow(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution: ResolutionCandidate,
        plan: RemediationPlan
    ) -> bool:
        """Handle approval workflow for high-risk remediations"""
        try:
        
            logger.info(f"Approval required for {incident.incident_id} (risk: {plan.risk_level})")
            
            await asyncio.sleep(1)
            
            environment = incident.context.get("environment")
            if environment in ["development", "staging"] and resolution.confidence > 0.9:
                plan.approval_status = ApprovalStatus.APPROVED
                logger.info(f"Auto-approved for {environment} environment")
                return True
            
            plan.approval_status = ApprovalStatus.PENDING
            logger.info(f"Manual approval required for {incident.incident_id}")
            return False
            
        except Exception as e:
            logger.error(f"Approval workflow failed: {e}")
            return False

    async def _execute_remediation(
        self,
        incident: IncidentEvent,
        analysis: FailureAnalysis,
        resolution: ResolutionCandidate,
        plan: RemediationPlan
    ) -> RemediationResult:
        """Execute the remediation plan"""
        
        start_time = datetime.utcnow()
        context = ExecutionContext(
            incident=incident,
            analysis=analysis,
            resolution=resolution,
            plan=plan,
            start_time=start_time,
            rollback_data={}
        )
        
        try:
            self.active_remediations[incident.incident_id] = context
            
            logger.info(f"Executing remediation for {incident.incident_id}")
            
            # Execute each action in the plan
            for action in plan.actions:
                success = await self._execute_action(action, context)
                if not success:
                    # Track failure for knowledge learning
                    await self._update_solution_success_tracking(resolution, False)
                    # Trigger rollback
                    await self._rollback_remediation(context)
                    return self._create_failure_result(
                        incident, resolution, f"Action {action.value} failed"
                    )
            
            # Verify remediation success
            verification_success = await self._verify_remediation_success(context)
            if not verification_success:
                # Track failure for knowledge learning
                await self._update_solution_success_tracking(resolution, False)
                await self._rollback_remediation(context)
                return self._create_failure_result(
                    incident, resolution, "Verification failed"
                )
            
            # Track success for knowledge learning
            context.auto_fix_successful = True
            await self._update_solution_success_tracking(resolution, True)
            
            end_time = datetime.utcnow()
            duration = int((end_time - start_time).total_seconds())
            
            logger.info(f"Remediation successful for {incident.incident_id} in {duration}s")
            
            return RemediationResult(
                incident_id=incident.incident_id,
                remediation_id=resolution.resolution_id,
                action_taken=resolution.description,
                outcome="success",
                confidence_at_execution=resolution.confidence,
                resolution_time_seconds=duration,
                human_intervention_required=False,
                rollback_performed=False,
                details={
                    "actions_executed": [action.value for action in plan.actions],
                    "execution_plan": plan.metadata
                }
            )
            
        except Exception as e:
            logger.error(f"Remediation execution failed: {e}")
            await self._rollback_remediation(context)
            return self._create_failure_result(incident, resolution, str(e))
        
        finally:
            if incident.incident_id in self.active_remediations:
                del self.active_remediations[incident.incident_id]

    async def _execute_action(self, action: RemediationAction, context: ExecutionContext) -> bool:
        """Execute a specific remediation action"""
        try:
            logger.info(f"Executing action: {action.value}")
            
            if action == RemediationAction.GITHUB_RERUN:
                return await self._execute_github_rerun(context)
            
            elif action == RemediationAction.GITHUB_UPDATE_CONFIG:
                return await self._execute_github_update_config(context)
            
            elif action == RemediationAction.GITHUB_UPDATE_SECRET:
                return await self._execute_github_update_secret(context)
            
            elif action == RemediationAction.ARGOCD_SYNC:
                return await self._execute_argocd_sync(context)
            
            elif action == RemediationAction.ARGOCD_UPDATE_MANIFEST:
                return await self._execute_argocd_update_manifest(context)
            
            elif action == RemediationAction.KUBERNETES_SCALE:
                return await self._execute_kubernetes_scale(context)
            
            elif action == RemediationAction.KUBERNETES_RESTART:
                return await self._execute_kubernetes_restart(context)
            
            elif action == RemediationAction.WAIT_AND_RETRY:
                return await self._execute_wait_and_retry(context)
            
            else:
                logger.warning(f"Unknown action: {action.value}")
                return False
            
        except Exception as e:
            logger.error(f"Action {action.value} failed: {e}")
            return False

    async def _execute_github_rerun(self, context: ExecutionContext) -> bool:
        """Execute GitHub workflow rerun"""
        if not self.github_client:
            return False
        
        # Extract workflow info from incident
        raw_event = context.incident.raw_event
        if "workflow_run" not in raw_event:
            return False
        
        workflow_run = raw_event["workflow_run"]
        repo_info = raw_event.get("repository", {})
        
        owner = repo_info.get("owner", {}).get("login")
        repo = repo_info.get("name")
        run_id = workflow_run.get("id")
        
        if not all([owner, repo, run_id]):
            logger.error("Missing GitHub workflow information")
            return False
        
        # Store rollback data
        context.rollback_data["github_run_id"] = run_id
        
        # Re-run the workflow
        success = self.github_client.rerun_workflow(owner, repo, run_id)
        if success:
            logger.info(f"Successfully re-triggered workflow {run_id}")
        
        return success

    async def _execute_github_update_config(self, context: ExecutionContext) -> bool:
        """Execute GitHub configuration update with automatic file fixes"""
        try:
            if not self.github_client:
                logger.error("GitHub client not available")
                return False
            
            # Extract fix information from analysis
            analysis = context.analysis
            fix_actions = getattr(analysis, 'fix_actions', [])
            affected_files = getattr(analysis, 'affected_files', [])
            
            if not fix_actions or not affected_files:
                logger.warning("No specific fix actions or affected files provided")
                return False
            
            # Get repository information from incident
            raw_event = context.incident.raw_event
            repo_info = raw_event.get("repository", {})
            repo_full_name = repo_info.get("full_name", "")
            
            if not repo_full_name:
                logger.error("Repository information not available")
                return False
            
            owner, repo = repo_full_name.split("/", 1)
            branch = raw_event.get("workflow_run", {}).get("head_branch", "main")
            
            logger.info(f"Starting automated fix for {repo_full_name} on branch {branch}")
            
            # Track changes for rollback
            context.rollback_data["github_changes"] = []
            
            success = True
            for file_path in affected_files:
                try:
                    # Get current file content
                    file_content = self.github_client.get_file_content(owner, repo, file_path, branch)
                    if not file_content:
                        logger.warning(f"Could not fetch content for {file_path}")
                        continue
                    
                    # Store original content for rollback
                    context.rollback_data["github_changes"].append({
                        "file_path": file_path,
                        "original_content": file_content,
                        "sha": self.github_client.get_file_sha(owner, repo, file_path, branch)
                    })
                    
                    # Apply automated fixes based on failure type
                    updated_content = await self._apply_automated_fixes(
                        file_content, file_path, analysis, fix_actions
                    )
                    
                    if updated_content and updated_content != file_content:
                        # Create commit with fix
                        commit_message = f"🤖 CodeHealer: Fix {analysis.subcategory} in {file_path}\n\nAutomated fix for incident: {context.incident.incident_id}\nCategory: {analysis.primary_category.value}\nConfidence: {analysis.confidence:.2f}"
                        
                        success = self.github_client.update_file(
                            owner, repo, file_path, updated_content, 
                            commit_message, branch,
                            context.rollback_data["github_changes"][-1]["sha"]
                        )
                        
                        if success:
                            logger.info(f"Successfully updated {file_path}")
                        else:
                            logger.error(f"Failed to update {file_path}")
                            success = False
                            break
                    else:
                        logger.info(f"No changes needed for {file_path}")
                        
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    success = False
                    break
            
            if success:
                logger.info(f"Successfully applied automated fixes to {len(affected_files)} files")
            
            return success
            
        except Exception as e:
            logger.error(f"GitHub config update failed: {e}")
            return False

    async def _apply_automated_fixes(self, content: str, file_path: str, analysis, fix_actions: list) -> str:
        """Apply specific automated fixes based on failure analysis"""
        try:
            updated_content = content
            
            # YAML/JSON syntax fixes
            if analysis.subcategory == "syntax_error" and file_path.endswith(('.yaml', '.yml')):
                updated_content = await self._fix_yaml_syntax(updated_content, fix_actions)
            
            # Configuration value fixes
            elif analysis.subcategory == "reference_error":
                updated_content = await self._fix_resource_references(updated_content, fix_actions)
            
            # Image reference fixes
            elif analysis.subcategory == "image_reference_error":
                updated_content = await self._fix_image_references(updated_content, fix_actions)
            
            # Environment variable fixes
            elif analysis.subcategory == "env_var_error":
                updated_content = await self._fix_env_variables(updated_content, fix_actions)
            
            # Apply any specific fix actions from LLM
            for action in fix_actions:
                if "replace" in action.lower():
                    updated_content = await self._apply_replacement_fix(updated_content, action)
                elif "add" in action.lower():
                    updated_content = await self._apply_addition_fix(updated_content, action)
                elif "remove" in action.lower():
                    updated_content = await self._apply_removal_fix(updated_content, action)
            
            return updated_content
            
        except Exception as e:
            logger.error(f"Failed to apply automated fixes: {e}")
            return content

    async def _fix_yaml_syntax(self, content: str, fix_actions: list) -> str:
        """Fix common YAML syntax errors"""
        try:
            import yaml
            
            # Try to parse and reformat
            try:
                parsed = yaml.safe_load(content)
                return yaml.dump(parsed, default_flow_style=False, sort_keys=False)
            except yaml.YAMLError as e:
                # Apply common fixes
                fixed_content = content
                
                # Fix indentation issues
                lines = fixed_content.split('\n')
                fixed_lines = []
                for line in lines:
                    # Fix common indentation problems
                    if line.strip() and not line.startswith(' ') and ':' in line:
                        if not line.startswith((' ', '-', '#')):
                            line = '  ' + line
                    fixed_lines.append(line)
                
                return '\n'.join(fixed_lines)
                
        except Exception as e:
            logger.error(f"YAML fix failed: {e}")
            return content

    async def _fix_resource_references(self, content: str, fix_actions: list) -> str:
        """Fix resource reference errors"""
        try:
            # Common resource reference fixes
            fixes = {
                'configMapRef': 'configMap',
                'secretRef': 'secret',
                'persistentVolumeClaimRef': 'persistentVolumeClaim'
            }
            
            for old_ref, new_ref in fixes.items():
                content = content.replace(old_ref, new_ref)
            
            return content
            
        except Exception as e:
            logger.error(f"Resource reference fix failed: {e}")
            return content

    async def _fix_image_references(self, content: str, fix_actions: list) -> str:
        """Fix Docker image reference errors"""
        try:
            # Add latest tag if missing
            import re
            
            # Find image references without tags
            image_pattern = r'(image:\s*)([a-zA-Z0-9._/-]+)(\s*$)'
            
            def add_latest_tag(match):
                prefix = match.group(1)
                image = match.group(2)
                suffix = match.group(3)
                
                if ':' not in image:
                    return f"{prefix}{image}:latest{suffix}"
                return match.group(0)
            
            return re.sub(image_pattern, add_latest_tag, content, flags=re.MULTILINE)
            
        except Exception as e:
            logger.error(f"Image reference fix failed: {e}")
            return content

    async def _apply_replacement_fix(self, content: str, action: str) -> str:
        """Apply replacement-based fixes from LLM analysis"""
        try:
            # Extract replacement instructions from action
            # Example: "Replace 'old_value' with 'new_value' in deployment.yaml"
            import re
            
            match = re.search(r"replace\s+'([^']+)'\s+with\s+'([^']+)'", action.lower())
            if match:
                old_value = match.group(1)
                new_value = match.group(2)
                return content.replace(old_value, new_value)
            
            return content
            
        except Exception as e:
            logger.error(f"Replacement fix failed: {e}")
            return content

    async def _apply_addition_fix(self, content: str, action: str) -> str:
        """Apply addition-based fixes from LLM analysis"""
        try:
            # Extract addition instructions from action
            # Example: "Add 'resources:' section to deployment.yaml"
            if 'resources:' in action.lower():
                # Add basic resource limits if missing
                if 'resources:' not in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'spec:' in line and 'containers:' in lines[i+1:i+5]:
                            # Find containers section and add resources
                            for j in range(i+1, min(len(lines), i+10)):
                                if 'image:' in lines[j]:
                                    indent = ' ' * (len(lines[j]) - len(lines[j].lstrip()))
                                    resource_lines = [
                                        f"{indent}resources:",
                                        f"{indent}  limits:",
                                        f"{indent}    memory: '1Gi'", 
                                        f"{indent}    cpu: '500m'",
                                        f"{indent}  requests:",
                                        f"{indent}    memory: '512Mi'",
                                        f"{indent}    cpu: '250m'"
                                    ]
                                    lines[j+1:j+1] = resource_lines
                                    break
                            break
                    return '\n'.join(lines)
            
            return content
            
        except Exception as e:
            logger.error(f"Addition fix failed: {e}")
            return content

    async def _apply_removal_fix(self, content: str, action: str) -> str:
        """Apply removal-based fixes from LLM analysis"""
        try:
            # Extract removal instructions from action
            # Example: "Remove duplicate 'apiVersion' line"
            if 'duplicate' in action.lower():
                lines = content.split('\n')
                seen_lines = set()
                unique_lines = []
                
                for line in lines:
                    stripped = line.strip()
                    if stripped and stripped not in seen_lines:
                        seen_lines.add(stripped)
                        unique_lines.append(line)
                    elif not stripped:  # Keep empty lines
                        unique_lines.append(line)
                
                return '\n'.join(unique_lines)
            
            return content
            
        except Exception as e:
            logger.error(f"Removal fix failed: {e}")
            return content

    async def _fix_env_variables(self, content: str, fix_actions: list) -> str:
        """Fix environment variable configuration errors"""
        try:
            # Add missing environment variables section
            if 'env:' not in content and any('env' in action.lower() for action in fix_actions):
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'image:' in line:
                        indent = ' ' * (len(line) - len(line.lstrip()))
                        env_lines = [
                            f"{indent}env:",
                            f"{indent}- name: DATABASE_URL",
                            f"{indent}  value: 'postgresql://localhost:5432/app'",
                            f"{indent}- name: REDIS_URL", 
                            f"{indent}  value: 'redis://localhost:6379'"
                        ]
                        lines[i+1:i+1] = env_lines
                        break
                return '\n'.join(lines)
            
            return content
            
        except Exception as e:
            logger.error(f"Environment variable fix failed: {e}")
            return content

    async def _execute_github_update_secret(self, context: ExecutionContext) -> bool:
        """Execute GitHub secret update"""
        await asyncio.sleep(1) 
        logger.info("GitHub secret update executed (placeholder)")
        return True

    async def _execute_argocd_sync(self, context: ExecutionContext) -> bool:
        """Execute ArgoCD application sync"""
        await asyncio.sleep(1)  
        logger.info("ArgoCD sync executed (placeholder)")
        return True

    async def _execute_argocd_update_manifest(self, context: ExecutionContext) -> bool:
        """Execute ArgoCD manifest update"""
        await asyncio.sleep(1)  
        logger.info("ArgoCD manifest update executed (placeholder)")
        return True

    async def _execute_kubernetes_scale(self, context: ExecutionContext) -> bool:
        """Execute Kubernetes resource scaling"""
        await asyncio.sleep(1) 
        logger.info("Kubernetes scaling executed (placeholder)")
        return True

    async def _execute_kubernetes_restart(self, context: ExecutionContext) -> bool:
        """Execute Kubernetes pod restart"""
        await asyncio.sleep(1)  
        logger.info("Kubernetes restart executed (placeholder)")
        return True

    async def _execute_wait_and_retry(self, context: ExecutionContext) -> bool:
        """Execute wait and retry for transient failures"""
        wait_time = 60  
        logger.info(f"Waiting {wait_time} seconds for transient issue to resolve")
        await asyncio.sleep(min(wait_time, 2))  
        return True

    async def _execute_slack_notify(self, context: ExecutionContext) -> bool:
        """Execute Slack notification with escalation support"""
        try:
            if not self.slack_client:
                logger.error("Slack client not available")
                return False

            analysis = context.analysis
            incident = context.incident
            
            # Determine escalation level based on analysis
            is_critical = analysis.confidence > 0.8 and analysis.primary_category in [
                FailureCategory.RESOURCE, FailureCategory.AUTH
            ]
            
            # Check if automatic fix was attempted and failed
            auto_fix_failed = hasattr(context, 'auto_fix_attempted') and not context.auto_fix_attempted
            
            # Determine notification type
            if is_critical or auto_fix_failed:
                return await self._send_escalation_notification(context, is_critical)
            else:
                return await self._send_status_notification(context)
                
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False

    async def _send_escalation_notification(self, context: ExecutionContext, is_critical: bool = False) -> bool:
        """Send escalation notification to senior developers"""
        try:
            analysis = context.analysis
            incident = context.incident
            
            # Prepare escalation message
            priority = "🚨 CRITICAL" if is_critical else "⚠️ HIGH PRIORITY"
            
            message = f"""{priority} - Manual Intervention Required

**Incident ID:** {incident.incident_id}
**Repository:** {incident.metadata.get('repository', 'Unknown')}
**Error Category:** {analysis.primary_category.value} - {analysis.subcategory}
**Confidence:** {analysis.confidence:.1%}

**Issue Summary:**
{analysis.summary}

**Recommended Actions:**
"""
            
            # Add fix actions if available
            fix_actions = getattr(analysis, 'fix_actions', [])
            if fix_actions:
                for i, action in enumerate(fix_actions, 1):
                    message += f"{i}. {action}\n"
            else:
                message += "Manual investigation required - specific actions not determined\n"
            
            # Add affected files
            affected_files = getattr(analysis, 'affected_files', [])
            if affected_files:
                message += f"\n**Affected Files:**\n"
                for file_path in affected_files[:5]:  # Limit to 5 files
                    message += f"- {file_path}\n"
                if len(affected_files) > 5:
                    message += f"- ... and {len(affected_files) - 5} more files\n"
            
            # Add timeline information
            estimated_fix_time = getattr(analysis, 'estimated_fix_time', 'Unknown')
            message += f"\n**Estimated Fix Time:** {estimated_fix_time}"
            
            # Add context links
            if incident.metadata.get('workflow_run_url'):
                message += f"\n**GitHub Workflow:** {incident.metadata['workflow_run_url']}"
            
            # Send to appropriate channel based on priority
            channel = "#dev-critical" if is_critical else "#dev-alerts"
            
            return await self.slack_client.send_message(
                channel=channel,
                message=message,
                thread_ts=None,
                metadata={
                    "incident_id": incident.incident_id,
                    "escalation_level": "critical" if is_critical else "high",
                    "requires_action": True
                }
            )
            
        except Exception as e:
            logger.error(f"Escalation notification failed: {e}")
            return False

    async def _send_status_notification(self, context: ExecutionContext) -> bool:
        """Send status notification for successful or low-priority issues"""
        try:
            analysis = context.analysis
            incident = context.incident
            
            # Check if auto-fix was successful
            auto_fix_success = getattr(context, 'auto_fix_successful', False)
            
            if auto_fix_success:
                status = "✅ RESOLVED"
                message = f"""{status} - Automatic Fix Applied

**Incident ID:** {incident.incident_id}
**Repository:** {incident.metadata.get('repository', 'Unknown')}
**Issue:** {analysis.subcategory}
**Resolution:** Automated configuration fix applied

**Changes Made:**
"""
                # Add rollback information
                github_changes = context.rollback_data.get("github_changes", [])
                for change in github_changes[:3]:  # Show first 3 changes
                    message += f"- Updated {change['file_path']}\n"
                
                if len(github_changes) > 3:
                    message += f"- ... and {len(github_changes) - 3} more files\n"
                
                message += f"\n**Verification:** Please verify the fix resolves the issue"
                
            else:
                status = "📊 DETECTED"
                message = f"""{status} - Issue Identified

**Incident ID:** {incident.incident_id}
**Repository:** {incident.metadata.get('repository', 'Unknown')}
**Issue:** {analysis.primary_category.value} - {analysis.subcategory}
**Confidence:** {analysis.confidence:.1%}

**Summary:** {analysis.summary}

**Status:** Monitoring for resolution or escalation
"""
            
            # Send to monitoring channel
            return await self.slack_client.send_message(
                channel="#dev-monitoring",
                message=message,
                thread_ts=None,
                metadata={
                    "incident_id": incident.incident_id,
                    "status": "resolved" if auto_fix_success else "monitoring",
                    "requires_action": False
                }
            )
            
        except Exception as e:
            logger.error(f"Status notification failed: {e}")
            return False

    async def _verify_remediation_success(self, context: ExecutionContext) -> bool:
        """Verify that the remediation was successful"""
        # Placeholder implementation - would check:
        # - Workflow status for GitHub Actions
        # - Application health for ArgoCD
        # - Pod status for Kubernetes
        await asyncio.sleep(0.5)  # Simulate verification
        logger.info("Remediation verification passed (placeholder)")
        return True

    async def _rollback_remediation(self, context: ExecutionContext):
        """Rollback the remediation if it failed"""
        try:
            logger.info(f"Rolling back remediation for {context.incident.incident_id}")
            
            # Execute rollback steps
            for step in context.plan.rollback_plan:
                logger.info(f"Rollback step: {step}")
                await asyncio.sleep(0.1)  # Simulate rollback work
            
            logger.info("Rollback completed")
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")

    def _get_min_confidence_threshold(self, environment: str) -> float:
        """Get minimum confidence threshold for environment"""
        return self.confidence_thresholds.get(
            environment, 
            self.confidence_thresholds["default"]
        )

    def _create_rejection_result(
        self, 
        incident: IncidentEvent, 
        resolution: ResolutionCandidate, 
        reason: str
    ) -> RemediationResult:
        """Create result for rejected remediation"""
        return RemediationResult(
            incident_id=incident.incident_id,
            remediation_id=resolution.resolution_id,
            action_taken="rejected",
            outcome="rejected",
            confidence_at_execution=resolution.confidence,
            resolution_time_seconds=0,
            human_intervention_required=True,
            rollback_performed=False,
            details={"rejection_reason": reason}
        )

    def _create_failure_result(
        self, 
        incident: IncidentEvent, 
        resolution: ResolutionCandidate, 
        error: str
    ) -> RemediationResult:
        """Create result for failed remediation"""
        return RemediationResult(
            incident_id=incident.incident_id,
            remediation_id=resolution.resolution_id,
            action_taken=resolution.description,
            outcome="failure",
            confidence_at_execution=resolution.confidence,
            resolution_time_seconds=0,
            human_intervention_required=True,
            rollback_performed=True,
            details={"error": error}
        )

    async def _update_solution_success_tracking(self, resolution: ResolutionCandidate, success: bool):
        """Update solution success tracking for learning"""
        try:
            # If this was a cached LLM solution, update its success rate
            if (resolution.source == ResolutionSource.LLM_ANALYSIS and 
                resolution.metadata.get('cached_solution')):
                
                solution_signature = resolution.metadata.get('solution_signature')
                if solution_signature and hasattr(self, 'knowledge_retriever'):
                    await self.knowledge_retriever.update_solution_success_rate(
                        solution_signature, success
                    )
                    logger.info(f"Updated cached solution success tracking: {success}")
            
            # Track auto-fix attempt for notification context
            if hasattr(self, '_current_context'):
                self._current_context.auto_fix_attempted = success
                
        except Exception as e:
            logger.error(f"Failed to update solution success tracking: {e}")

    def _create_error_result(self, incident: IncidentEvent, error: str) -> RemediationResult:
        """Create result for coordination error"""
        return RemediationResult(
            incident_id=incident.incident_id,
            remediation_id="error",
            action_taken="coordination_error",
            outcome="error",
            confidence_at_execution=0.0,
            resolution_time_seconds=0,
            human_intervention_required=True,
            rollback_performed=False,
            details={"error": error}
        )

    def get_remediation_statistics(self) -> Dict[str, Any]:
        """Get remediation statistics"""
        total_attempts = len(self.remediation_history)
        successful = sum(
            1 for entry in self.remediation_history.values()
            if entry["result"].outcome == "success"
        )
        
        return {
            "total_attempts": total_attempts,
            "successful_remediations": successful,
            "success_rate": successful / total_attempts if total_attempts > 0 else 0.0,
            "active_remediations": len(self.active_remediations),
            "confidence_thresholds": self.confidence_thresholds,
            "approval_rules": self.approval_rules
        }