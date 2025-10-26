import json
import time
from typing import Dict, List, Optional, Any
from github import Github, GithubException
import requests
from utils.logger import get_logger

logger = get_logger(__name__)

class GitHubClient:
    def __init__(self, token: str):
        self.client = Github(token)
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        })

    def get_workflow_run(self, owner: str, repo: str, run_id: int) -> Optional[Dict[str, Any]]:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            run = repository.get_workflow_run(run_id)
            return {
                "id": run.id,
                "status": run.status,
                "conclusion": run.conclusion,
                "html_url": run.html_url,
                "head_sha": run.head_sha,
                "head_branch": run.head_branch,
                "workflow_id": run.workflow_id,
                "created_at": run.created_at.isoformat(),
                "updated_at": run.updated_at.isoformat(),
            }
        except GithubException as e:
            logger.error(f"Failed to get workflow run: {e}")
            return None

    def get_workflow_logs(self, owner: str, repo: str, run_id: int) -> Optional[str]:
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
            response = self.session.get(url, allow_redirects=True)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to get workflow logs: {e}")
            return None

    def get_job_logs(self, owner: str, repo: str, job_id: str) -> Optional[str]:
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
            response = self.session.get(url)
            response.raise_for_status()
            jobs_data = response.json()
            return jobs_data.get("jobs", [])
        except Exception as e:
            logger.error(f"Failed to list workflow jobs: {e}")
            return []

    def rerun_workflow(self, owner: str, repo: str, run_id: int) -> bool:
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/rerun"
            response = self.session.post(url)
            response.raise_for_status()
            logger.info(f"Successfully triggered rerun for workflow run {run_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to rerun workflow: {e}")
            return False 

    def rerun_failed_jobs(self, owner: str, repo: str, run_id: int) -> bool:
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs"
            response = self.session.post(url)
            response.raise_for_status()
            logger.info(f"Successfully triggered rerun for failed jobs in run {run_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to rerun the failed jobs: {e}")
            return False

    def create_branch(self, owner: str, repo: str, branch_name: str, source_sha: str) -> bool:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            ref = f"refs/heads/{branch_name}"
            repository.create_git_ref(ref=ref, sha=source_sha)
            logger.info(f"Created branch {branch_name} from {source_sha}")
            return True
        except GithubException as e:
            logger.error(f"Failed to create branch: {e}")
            return False
        
    def get_file_sha(self, owner: str, repo: str, path: str, ref: str = "main") -> Optional[str]:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            file_content = repository.get_contents(path,ref=ref)
            return file_content.sha
        except GithubException as e:
            logger.error(f"Failed to get file SHA: {e}")
            return None

    def update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: Optional[str] = None
    ) -> bool:
        try: 
            repository = self.client.get_repo(f"{owner}/{repo}")
            if sha is None:
                file_content = repository.get_contents(path, ref=branch)
                sha = file_content.sha
            repository.update_file(
                path=path,
                message=message,
                content=content,
                sha=sha,
                branch=branch
            )
            logger.info(f"Updated file {path} in branch {branch}")
            return True
        except GithubException as e:
            logger.error(f"Failed to update file: {e}")
            return False

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str, 
        head: str,
        base: str
    ) -> Optional[Dict[str, Any]]:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            pr = repository.create_pull(
                title=title,
                body=body,
                head=head,
                base=base
            )
            logger.info(f"Created pull request #{pr.number}")
            return {
                "number": pr.number,
                "html_url": pr.html_url,
                "state": pr.state
            }
        except GithubException as e:
            logger.error(f"Failed to create pull request: {e}")
            return None

    def merge_pull_request(self, owner: str, repo: str, pull_number: int) -> bool:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            pr = repository.get_pull(pull_number)
            pr.merge()
            logger.info(f"Merged pull request #{pull_number}")
            return True
        except GithubException as e:
            logger.error(f"Failed to merge pull request: {e}")
            return False

    def update_secret(self, owner: str, repo: str, secret_name: str, secret_value: str) -> bool:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            public_key = repository.get_public_key()

            from nacl import encoding, public
            public_key_obj = public.PublicKey(public_key.key.encode(), encoding.Base64Encoder())
            sealed_box = public.SealedBox(public_key_obj)
            encrypted = sealed_box.encrypt(secret_value.encode())
            encrypted_value = encoding.Base64Encoder().encode(encrypted).decode()

            url = f"https://api.github.com/repos/{owner}/{repo}/actions/secrets/{secret_name}"
            response = self.session.put(url, json={
                "encrypted_value": encrypted_value,
                "key_id": public_key.key_id
            })
            response.raise_for_status()
            logger.info(f"Updated secret {secret_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update secret: {e}")
            return False

    def get_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> Optional[str]:
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            file_content = repository.get_contents(path, ref=ref)
            return file_content.decoded_content.decode()
        except GithubException as e:
            logger.error(f"Failed to get file content: {e}")
            return None

    def cancel_workflow_run(self, owner: str, repo: str, run_id: int) -> bool:
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/cancel"
            response = self.session.post(url)
            response.raise_for_status()
            logger.info(f"Cancelled workflow run {run_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel workflow: {e}")
            return False

    def get_workflow_run_artifacts(self, owner: str, repo: str, run_id: int) -> List[Dict[str, Any]]:
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json().get("artifacts", [])
        except Exception as e:
            logger.error(f"Failed to get artifacts: {e}")
            return []

    def wait_for_workflow_completion(
        self,
        owner: str,
        repo: str,
        run_id: int,
        timeout: int = 600,
        poll_interval: int = 10
    ) -> Optional[str]:
        start_time = time.time()
        while time.time() - start_time < timeout:
            run = self.get_workflow_run(owner, repo, run_id)
            if run and run.get("status") == "completed":
                return run.get("conclusion")
            time.sleep(poll_interval)
        logger.warning(f"Workflow run {run_id} did not complete within {timeout} seconds")
        return None
