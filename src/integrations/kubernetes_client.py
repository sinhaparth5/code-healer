from typing import Dict, List, Optional, Any
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from utils.logger import get_logger

logger = get_logger(__name__)

class KubernetesClient:
    def __init__(self, kubeconfig: Optional[str] = None, context: Optional[str] = None):
        try:
            if kubeconfig:
                config.load_kube_config(config_file=kubeconfig, context=context)
            else:
                config.load_incluster_config()
            
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.batch_v1 = client.BatchV1Api()
            self.autoscaling_v1 = client.AutoscalingV1Api()
            self.networking_v1 = client.NetworkingV1Api()
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise

    def get_pod(self, name: str, namespace: str) -> Optional[Dict[str, Any]]:
        try:
            pod = self.core_v1.read_namespaced_pod(name, namespace)
            return self._serialize_pod(pod)
        except ApiException as e:
            logger.error(f"Failed to get pod {name}: {e}")
            return None

    def list_pods(
        self,
        namespace: str,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace,
                label_selector=label_selector,
                field_selector=field_selector
            )
            return [self._serialize_pod(pod) for pod in pods.items]
        except ApiException as e:
            logger.error(f"Failed to list pods: {e}")
            return []

    def get_pod_logs(
        self,
        name: str,
        namespace: str,
        container: Optional[str] = None,
        tail_lines: Optional[int] = None,
        previous: bool = False
    ) -> Optional[str]:
        try:
            return self.core_v1.read_namespaced_pod_log(
                name,
                namespace,
                container=container,
                tail_lines=tail_lines,
                previous=previous
            )
        except ApiException as e:
            logger.error(f"Failed to get pod logs: {e}")
            return None

    def get_pod_events(self, name: str, namespace: str) -> List[Dict[str, Any]]:
        try:
            events = self.core_v1.list_namespaced_event(
                namespace,
                field_selector=f"involvedObject.name={name}"
            )
            return [self._serialize_event(event) for event in events.items]
        except ApiException as e:
            logger.error(f"Failed to get pod events: {e}")
            return []

    def delete_pod(self, name: str, namespace: str, grace_period: int = 30) -> bool:
        try:
            self.core_v1.delete_namespaced_pod(
                name,
                namespace,
                grace_period_seconds=grace_period
            )
            logger.info(f"Deleted pod {name} in namespace {namespace}")
            return True
        except ApiException as e:
            logger.error(f"Failed to delete pod: {e}")
            return False

    def get_deployment(self, name: str, namespace: str) -> Optional[Dict[str, Any]]:
        try:
            deployment = self.apps_v1.read_namespaced_deployment(name, namespace)
            return self._serialize_deployment(deployment)
        except ApiException as e:
            logger.error(f"Failed to get deployment {name}: {e}")
            return None

    def patch_deployment(
        self,
        name: str,
        namespace: str,
        patch: Dict[str, Any]
    ) -> bool:
        try:
            self.apps_v1.patch_namespaced_deployment(name, namespace, patch)
            logger.info(f"Patched deployment {name} in namespace {namespace}")
            return True
        except ApiException as e:
            logger.error(f"Failed to patch deployment: {e}")
            return False

    def scale_deployment(self, name: str, namespace: str, replicas: int) -> bool:
        patch = {
            "spec": {
                "replicas": replicas
            }
        }
        return self.patch_deployment(name, namespace, patch)

    def update_deployment_resources(
        self,
        name: str,
        namespace: str,
        container_name: str,
        cpu_limit: Optional[str] = None,
        memory_limit: Optional[str] = None,
        cpu_request: Optional[str] = None,
        memory_request: Optional[str] = None
    ) -> bool:
        deployment = self.get_deployment(name, namespace)
        if not deployment:
            return False
        
        containers = deployment["spec"]["template"]["spec"]["containers"]
        for container in containers:
            if container["name"] == container_name:
                resources = container.get("resources", {})
                limits = resources.get("limits", {})
                requests = resources.get("requests", {})
                
                if cpu_limit:
                    limits["cpu"] = cpu_limit
                if memory_limit:
                    limits["memory"] = memory_limit
                if cpu_request:
                    requests["cpu"] = cpu_request
                if memory_request:
                    requests["memory"] = memory_request
                
                resources["limits"] = limits
                resources["requests"] = requests
                container["resources"] = resources
                break
        
        patch = {"spec": {"template": {"spec": {"containers": containers}}}}
        return self.patch_deployment(name, namespace, patch)

    def restart_deployment(self, name: str, namespace: str) -> bool:
        import datetime
        patch = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": datetime.datetime.utcnow().isoformat()
                        }
                    }
                }
            }
        }
        return self.patch_deployment(name, namespace, patch)

    def get_configmap(self, name: str, namespace: str) -> Optional[Dict[str, Any]]:
        try:
            cm = self.core_v1.read_namespaced_config_map(name, namespace)
            return {"name": cm.metadata.name, "data": cm.data}
        except ApiException as e:
            logger.error(f"Failed to get configmap: {e}")
            return None

    def update_configmap(self, name: str, namespace: str, data: Dict[str, str]) -> bool:
        try:
            cm = self.core_v1.read_namespaced_config_map(name, namespace)
            cm.data = data
            self.core_v1.patch_namespaced_config_map(name, namespace, cm)
            logger.info(f"Updated configmap {name} in namespace {namespace}")
            return True
        except ApiException as e:
            logger.error(f"Failed to update configmap: {e}")
            return False

    def get_secret(self, name: str, namespace: str) -> Optional[Dict[str, Any]]:
        try:
            secret = self.core_v1.read_namespaced_secret(name, namespace)
            return {
                "name": secret.metadata.name,
                "data": {k: v.decode() if v else "" for k, v in (secret.data or {}).items()}
            }
        except ApiException as e:
            logger.error(f"Failed to get secret: {e}")
            return None

    def update_secret(self, name: str, namespace: str, data: Dict[str, str]) -> bool:
        try:
            import base64
            secret = self.core_v1.read_namespaced_secret(name, namespace)
            secret.data = {k: base64.b64encode(v.encode()).decode() for k, v in data.items()}
            self.core_v1.patch_namespaced_secret(name, namespace, secret)
            logger.info(f"Updated secret {name} in namespace {namespace}")
            return True
        except ApiException as e:
            logger.error(f"Failed to update secret: {e}")
            return False

    def get_service(self, name: str, namespace: str) -> Optional[Dict[str, Any]]:
        try:
            svc = self.core_v1.read_namespaced_service(name, namespace)
            return {
                "name": svc.metadata.name,
                "type": svc.spec.type,
                "cluster_ip": svc.spec.cluster_ip,
                "ports": [{"port": p.port, "target_port": p.target_port} for p in svc.spec.ports]
            }
        except ApiException as e:
            logger.error(f"Failed to get service: {e}")
            return None

    def get_namespace_resource_quota(self, namespace: str) -> Optional[Dict[str, Any]]:
        try:
            quotas = self.core_v1.list_namespaced_resource_quota(namespace)
            if quotas.items:
                quota = quotas.items[0]
                return {
                    "hard": quota.status.hard,
                    "used": quota.status.used
                }
            return None
        except ApiException as e:
            logger.error(f"Failed to get resource quota: {e}")
            return None

    def get_node_resources(self, node_name: str) -> Optional[Dict[str, Any]]:
        try:
            node = self.core_v1.read_node(node_name)
            return {
                "capacity": node.status.capacity,
                "allocatable": node.status.allocatable
            }
        except ApiException as e:
            logger.error(f"Failed to get node resources: {e}")
            return None

    def _serialize_pod(self, pod) -> Dict[str, Any]:
        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "conditions": [
                {"type": c.type, "status": c.status, "reason": c.reason}
                for c in (pod.status.conditions or [])
            ],
            "container_statuses": [
                {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "state": self._get_container_state(cs.state)
                }
                for cs in (pod.status.container_statuses or [])
            ]
        }

    def _serialize_deployment(self, deployment) -> Dict[str, Any]:
        return {
            "name": deployment.metadata.name,
            "namespace": deployment.metadata.namespace,
            "replicas": deployment.spec.replicas,
            "ready_replicas": deployment.status.ready_replicas or 0,
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": c.name,
                                "image": c.image,
                                "resources": {
                                    "limits": c.resources.limits or {},
                                    "requests": c.resources.requests or {}
                                } if c.resources else {}
                            }
                            for c in deployment.spec.template.spec.containers
                        ]
                    }
                }
            }
        }

    def _serialize_event(self, event) -> Dict[str, Any]:
        return {
            "type": event.type,
            "reason": event.reason,
            "message": event.message,
            "count": event.count,
            "first_timestamp": event.first_timestamp.isoformat() if event.first_timestamp else None,
            "last_timestamp": event.last_timestamp.isoformat() if event.last_timestamp else None
        }

    def _get_container_state(self, state) -> Dict[str, Any]:
        if state.running:
            return {"state": "running", "started_at": state.running.started_at.isoformat()}
        elif state.waiting:
            return {"state": "waiting", "reason": state.waiting.reason}
        elif state.terminated:
            return {
                "state": "terminated",
                "reason": state.terminated.reason,
                "exit_code": state.terminated.exit_code
            }
        return {"state": "unknown"}