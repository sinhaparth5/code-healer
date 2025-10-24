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
    
    def get_application(self, app_name: str) => Optional[Dict[str, Any]]:
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


