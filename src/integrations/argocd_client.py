import requests
from typing import Dict, List, Optional, Any
from utils.logger import get_logger

logger = get_logger(__name__)

class ArgoCDClient:
    def __init__(self, server_url: str, token: str, verify_ssl: bool = True):
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        url = f"{self.server_url}/api/v1/{endpoint.lstrip('/')}"
        try:
            response = self.session.request(
                method,
                url,
                verify=self.verify_ssl,
                **kwargs
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            logger.error(f"ArgoCD API request failed: {e}")
            return None
    
    def get_application(self, app_name: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"applications/{app_name}")

    def list_applications(self, selector: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"selector": selector} if selector else {}
        result = self._request("GET", "applications", params=params)
        return result.get("items", []) if result else []

    def get_application_sync_status(self, app_name: str) -> Optional[Dict[str, Any]]:
        app = self.get_application(app_name)
        if app:
            return {
                "status": app.get("status", {}).get("sync", {}).get("status"),
                "revision": app.get("status", {}).get("sync", {}).get("revision"),
                "health": app.get("status", {}).get("health", {}).get("status"),
                "conditions": app.get("status", {}).get("conditions", [])
            }
        return None

    def sync_application(
            self,
            app_name: str,
            prune: bool = False,
            dry_run: bool = False,
            revision: Optional[str] = None
    ) -> bool:
        payload = {
            "prune": prune,
            "dryRun": dry_run,
        }
        if revision:
            payload["revision"] = revision

        result = self._request("POST", f"applications/{app_name}/sync", json=payload)
        if result:
            logger.info(f"Triggered sync for application {app_name}")
            return True
        return False
    
    def get_application_manifests(self, app_name: str, revision: Optional[str] = None) -> Optional[List[str]]:
        params = {"revision": revision} if revision else {}
        result = self._request("GET", f"applications/{app_name}/manifests", params=params)
        return result.get("manifests", []) if result else None
    
    def get_application_resources(self, app_name: str) -> List[Dict[str, Any]]:
        app = self.get_application(app_name)
        if app:
            return app.get("status", {}).get("resources", [])
        return []
    
    def get_resource_tree(self, app_name: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"applications/{app_name}/resource-tree")
    
    def delete_resource(
            self,
            app_name: str,
            resource_name: str,
            namespace: str,
            kind: str,
            group: Optional[str] = None
    ) -> bool:
        params = {
            "name": resource_name,
            "namespace": namespace,
            "kind": kind,
        }
        if group:
            params["group"] = group

        result = self._request("DELETE", f"applications/{app_name}/resource", params=params)
        if result is not None:
            logger.info(f"Deleted resource {kind}/{resource_name} from application {app_name}")
            return True
        return False
    
    def patch_resource(
            self,
            app_name: str,
            resource_name: str,
            namespace: str,
            kind: str,
            patch: Dict[str, Any],
            patch_type: str = "application/merge-patch+json"
    ) -> bool:
        params = {
            "name": resource_name,
            "namespace": namespace,
            "kind": kind,
            "patchType": patch_type
        }

        result = self._request(
            "POST",
            f"applications/{app_name}/resouce",
            params=params,
            json=patch
        )
        if result:
            logger.info(f"Patched resource {kind}/{resource_name} in application {app_name}")
            return True
        return False
    
    def rollback_application(self, app_name: str, revision: str) -> bool:
        payload = {"revision": revision}
        result = self._request("POST", f"applications/{app_name}/rollback", json=payload)
        if result:
            logger.info(f"Rolled back application {app_name} to revision {revision}")
            return True
        return False
    
    def get_application_events(self, app_name: str) -> List[Dict[str, Any]]:
        result = self._request("GET", f"applications/{app_name}/events")
        return result if result else []
    
    def update_application_spec(
            self,
            app_name: str,
            spec_updates: Dict[str, Any]
    ) -> bool:
        app = self.get_application(app_name)
        if not app:
            return False
        
        app["spec"].update(spec_updates)
        result = self._request("PUT", f"applications"/{app_name}, json=app)
        if result:
            logger.info(f"Updated application spec for {app_name}")
            return True
        return False
    
    def refresh_application(self, app_name: str, hard: bool = False) -> bool:
        payload = {"hardRefresh": hard}
        result = self._request("POST", f"applications/{app_name}/refresh", json=payload)
        if result is not None:
            logger.info(f"Refreshed application {app_name}")
            return True
        return False
    
    def terminate_operation(self, app_name: str) -> bool:
        result = self._request("DELETE", f"applications/{app_name}/operation")
        if result is not None:
            logger.info(f"Terminated operation for application {app_name}")
            return True
        return False
    
    def get_sync_windows(self, app_name: str) -> Optional[List[str, Any]]:
        result = self._request("GET", f"applications/{app_name}/syncwindows")
        return result if result else None
    
    def set_application_parameter(
            self,
            app_name: str,
            parameter_name: str,
            parameter_value: str
    ) -> bool:
        app = self.get_application(app_name)
        if not app:
            return False
        
        source = app.get("spec", {}).get("source", {})
        if "helm" not in source:
            source["helm"] = {"parameters": []}

        parameters = source["helm"]["parameters"]
        param_found = False
        for param in parameters:
            if param["name"] == parameter_name:
                param["value"] = parameter_value
                param_found = True
                break

        if not param_found:
            parameters.append({"name": parameter_name, "value": parameter_value})

        return self.update_application_spec(app_name, {"source": source})
    
    def wait_for_sync_completion(
            self,
            app_name: str, 
            timeout: int = 300,
            poll_interval: int = 5,
    ) -> Optional[str]:
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            sync_status = self.get_application_sync_status(app_name)
            if sync_status:
                status = sync_status.get("status")
                health = sync_status.get("health")

                if status == "Synced" and health in ["Healthy", "Progressing"]:
                    return health
                elif status == "OutOfSync":
                    logger.warning(f"Application {app_name} is out of sync")
                    return "OutOfSync"
            
            time.sleep(poll_interval)

        logger.warning(f"Sync did not complete within {timeout} seconds for {app_name}")
        return None