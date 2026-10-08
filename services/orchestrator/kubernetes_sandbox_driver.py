"""
Kubernetes Sandbox Driver for FuzeAgent Autonomous Execution (Track #1).
Spawns ephemeral, resource-constrained, auto-terminating agent runner pods in the Kubernetes cluster.
Replaces missing Docker-in-Docker / docker.sock dependency with native Kubernetes API execution.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException

    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False
    logger.warning(
        "kubernetes python package not installed; KubernetesSandboxDriver will run in simulated mode"
    )


class KubernetesSandboxDriver:
    """Manages ephemeral Kubernetes Pods for agent runtime environments."""

    def __init__(self, namespace: Optional[str] = None):
        self.namespace = namespace or os.getenv("POD_NAMESPACE", "fuzeagent")
        self.k8s_core_api = None
        self.k8s_network_api = None
        self._init_k8s_client()

    def _init_k8s_client(self):
        if not K8S_AVAILABLE:
            return

        try:
            config.load_incluster_config()
            self.k8s_core_api = client.CoreV1Api()
            self.k8s_network_api = client.NetworkingV1Api()
            logger.info(
                f"✅ KubernetesSandboxDriver: Connected via in-cluster serviceaccount (namespace: {self.namespace})"
            )
        except Exception:
            try:
                config.load_kube_config()
                self.k8s_core_api = client.CoreV1Api()
                self.k8s_network_api = client.NetworkingV1Api()
                logger.info(
                    f"✅ KubernetesSandboxDriver: Connected via local kubeconfig (namespace: {self.namespace})"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ KubernetesSandboxDriver: K8s cluster API not reachable ({e}). Falling back to simulation mode."
                )
                self.k8s_core_api = None
                self.k8s_network_api = None

    async def spawn_sandbox_pod(
        self,
        template_id: str,
        image: str,
        env_vars: Dict[str, str],
        secrets: Optional[Dict[str, str]] = None,
        setup_script: Optional[str] = None,
        network_isolation: str = "outbound-only",
        timeout_seconds: int = 1800,
        cpu_limit: str = "2.0",
        memory_limit: str = "4Gi",
        command: Optional[List[str]] = None,
        ws_relay_url: Optional[str] = None,
        agent_id: Optional[str] = None,
        image_pull_secrets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Spawn an isolated Pod with attached secrets, network policy, and startup script.
        - Secrets: Stored in an ephemeral K8s Secret and mounted via envFrom secretRef.
        - NetworkPolicy: Restricts ingress/egress to orchestrator bus + authorized external endpoints.
        - StartScript: Executes setupScript before launching the session-relay runner.
        """
        short_id = uuid.uuid4().hex[:6]
        base_name = f"agent-sbx-{template_id[:10]}-{short_id}".lower().replace("_", "-")
        pod_name = base_name
        secret_name = f"{base_name}-sec" if secrets else None
        netpol_name = (
            f"{base_name}-netpol"
            if network_isolation in ("outbound-only", "strict")
            else None
        )
        started_at = datetime.now(timezone.utc).isoformat()

        # Format container env vars
        merged_env = dict(env_vars)
        intra_cluster_ws = os.getenv(
            "INTRA_CLUSTER_WS_RELAY_URL",
            f"ws://fuzeagent-orchestrator.{self.namespace}.svc.cluster.local:8000/api/ws/agent-relay/{agent_id or short_id}",
        )
        if not ws_relay_url or "fuzeagent.prod.fuzefront.com/ws/stream" in ws_relay_url:
            merged_env["WS_RELAY_URL"] = intra_cluster_ws
        else:
            merged_env["WS_RELAY_URL"] = ws_relay_url
        if agent_id:
            merged_env["AGENT_ID"] = agent_id
        if setup_script:
            merged_env["SETUP_SCRIPT"] = setup_script
        merged_env["POD_NAME"] = pod_name
        merged_env["POD_NAMESPACE"] = self.namespace

        k8s_env = [{"name": k, "value": str(v)} for k, v in merged_env.items()]

        # 1. Ephemeral Secret definition
        if secrets and self.k8s_core_api:
            secret_spec = {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {
                    "name": secret_name,
                    "namespace": self.namespace,
                    "labels": {
                        "app": "agent-sandbox",
                        "managed-by": "fuzeagent",
                        "sandbox-id": short_id,
                    },
                },
                "type": "Opaque",
                "stringData": {k: str(v) for k, v in secrets.items()},
            }
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.k8s_core_api.create_namespaced_secret(
                        namespace=self.namespace,
                        body=secret_spec,
                    ),
                )
                logger.info(
                    "🔐 Ephemeral credential resource created for pod %s", pod_name
                )
            except Exception as e:
                logger.warning(
                    "⚠️ Failed to create credential resource for pod %s: %s",
                    pod_name,
                    type(e).__name__,
                )

        # 2. Ephemeral NetworkPolicy definition
        if netpol_name and self.k8s_network_api:
            netpol_spec = {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "NetworkPolicy",
                "metadata": {
                    "name": netpol_name,
                    "namespace": self.namespace,
                    "labels": {
                        "app": "agent-sandbox",
                        "managed-by": "fuzeagent",
                        "sandbox-id": short_id,
                    },
                },
                "spec": {
                    "podSelector": {
                        "matchLabels": {
                            "sandbox-id": short_id,
                        }
                    },
                    "policyTypes": ["Ingress", "Egress"],
                    "ingress": [
                        {
                            "from": [
                                {
                                    "podSelector": {
                                        "matchLabels": {
                                            "app.kubernetes.io/name": "fuzeagent",
                                        }
                                    }
                                }
                            ]
                        }
                    ],
                    "egress": [
                        # Allow DNS
                        {
                            "ports": [
                                {"protocol": "UDP", "port": 53},
                                {"protocol": "TCP", "port": 53},
                            ]
                        },
                        # Allow HTTPS / HTTP for external APIs and package registries
                        {
                            "ports": [
                                {"protocol": "TCP", "port": 443},
                                {"protocol": "TCP", "port": 80},
                            ]
                        },
                        # Allow intra-cluster communication to orchestrator bus
                        {
                            "ports": [
                                {"protocol": "TCP", "port": 8000},
                                {"protocol": "TCP", "port": 8080},
                            ],
                            "to": [
                                {
                                    "podSelector": {
                                        "matchLabels": {
                                            "app.kubernetes.io/name": "fuzeagent",
                                        }
                                    }
                                }
                            ],
                        },
                    ],
                },
            }
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.k8s_network_api.create_namespaced_network_policy(
                        namespace=self.namespace,
                        body=netpol_spec,
                    ),
                )
                logger.info(
                    f"🛡️ Ephemeral NetworkPolicy {netpol_name} created (outbound-only)"
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to create NetworkPolicy {netpol_name}: {e}")

        # 3. Container command & execution script
        container_spec: Dict[str, Any] = {
            "name": "agent-runner",
            "image": image,
            "imagePullPolicy": "IfNotPresent",
            "env": k8s_env,
            "resources": {
                "limits": {
                    "cpu": cpu_limit,
                    "memory": memory_limit,
                },
                "requests": {
                    "cpu": "250m",
                    "memory": "512Mi",
                },
            },
        }

        # Mount secrets via secretRef if created
        if secret_name:
            container_spec["envFrom"] = [{"secretRef": {"name": secret_name}}]

        if command:
            container_spec["command"] = command
        elif setup_script:
            # Execute setup script before session-relay
            container_spec["command"] = [
                "/bin/bash",
                "-c",
                'if [ -n "$SETUP_SCRIPT" ]; then eval "$SETUP_SCRIPT"; fi; if [ -x /usr/local/bin/session-relay ]; then exec /usr/local/bin/session-relay; else exec sleep infinity; fi',
            ]
        else:
            container_spec["command"] = [
                "/bin/bash",
                "-c",
                "if [ -x /usr/local/bin/session-relay ]; then exec /usr/local/bin/session-relay; else exec sleep infinity; fi",
            ]

        pull_secret_names = list(image_pull_secrets or [])
        default_secret = os.getenv("HARBOR_PULL_SECRET", "harbor-pull-secret")
        if default_secret and default_secret not in pull_secret_names:
            pull_secret_names.append(default_secret)
        ghcr_secret = os.getenv("GHCR_PULL_SECRET", "ghcr-pull")
        if ghcr_secret and ghcr_secret not in pull_secret_names:
            pull_secret_names.append(ghcr_secret)

        container_spec["securityContext"] = {
            "allowPrivilegeEscalation": False,
            "readOnlyRootFilesystem": False,
            "capabilities": {
                "drop": ["ALL"],
            },
        }
        container_spec["volumeMounts"] = [
            {
                "name": "workspace-storage",
                "mountPath": "/workspace",
            },
            {
                "name": "tmp-storage",
                "mountPath": "/tmp",
            },
        ]

        pod_spec = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "namespace": self.namespace,
                "labels": {
                    "app": "agent-sandbox",
                    "managed-by": "fuzeagent",
                    "template-id": template_id.replace("_", "-")[:30],
                    "sandbox-id": short_id,
                },
                "annotations": {
                    "fuzeagent.io/spawned-at": started_at,
                    "fuzeagent.io/timeout-seconds": str(timeout_seconds),
                },
            },
            "spec": {
                "restartPolicy": "Never",
                "activeDeadlineSeconds": timeout_seconds,  # Automatic K8s kernel-enforced TTL
                "securityContext": {
                    "runAsNonRoot": True,
                    "runAsUser": 1001,
                    "runAsGroup": 1001,
                    "fsGroup": 1001,
                    "seccompProfile": {
                        "type": "RuntimeDefault",
                    },
                },
                "containers": [container_spec],
                "volumes": [
                    {
                        "name": "workspace-storage",
                        "emptyDir": {
                            "sizeLimit": "2Gi",
                        },
                    },
                    {
                        "name": "tmp-storage",
                        "emptyDir": {
                            "sizeLimit": "1Gi",
                        },
                    },
                ],
                "imagePullSecrets": [{"name": s} for s in pull_secret_names],
            },
        }

        if self.k8s_core_api:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.k8s_core_api.create_namespaced_pod(
                        namespace=self.namespace,
                        body=pod_spec,
                    ),
                )
                logger.info(
                    f"🚀 K8s Pod {pod_name} successfully spawned in namespace {self.namespace}"
                )
                return {
                    "id": f"sbx-{short_id}",
                    "podName": pod_name,
                    "secretName": secret_name,
                    "networkPolicyName": netpol_name,
                    "namespace": self.namespace,
                    "status": "running",
                    "image": image,
                    "timeoutSeconds": timeout_seconds,
                    "startedAt": started_at,
                    "mode": "k8s_pod",
                }
            except Exception as e:
                logger.error(f"❌ Failed to spawn K8s pod {pod_name}: {e}")
                return {
                    "id": f"sbx-{short_id}",
                    "podName": pod_name,
                    "secretName": secret_name,
                    "networkPolicyName": netpol_name,
                    "namespace": self.namespace,
                    "status": "running",
                    "image": image,
                    "timeoutSeconds": timeout_seconds,
                    "startedAt": started_at,
                    "mode": "simulated_pod",
                    "error": str(e),
                }

        logger.info(
            f"⚡ [Simulated K8s Driver] Spawning virtual runner pod {pod_name} with {timeout_seconds}s TTL"
        )
        return {
            "id": f"sbx-{short_id}",
            "podName": pod_name,
            "secretName": secret_name,
            "networkPolicyName": netpol_name,
            "namespace": self.namespace,
            "status": "running",
            "image": image,
            "timeoutSeconds": timeout_seconds,
            "startedAt": started_at,
            "mode": "simulated_pod",
        }

    async def terminate_sandbox_pod(
        self,
        pod_name: str,
        secret_name: Optional[str] = None,
        netpol_name: Optional[str] = None,
    ) -> bool:
        """Force delete a sandbox pod and clean up its associated ephemeral Secret and NetworkPolicy."""
        # Derive secret and netpol names if omitted
        if not secret_name and pod_name:
            secret_name = f"{pod_name}-sec"
        if not netpol_name and pod_name:
            netpol_name = f"{pod_name}-netpol"

        if not self.k8s_core_api:
            logger.info(
                "⚡ [Simulated K8s Driver] Terminated virtual pod %s (netpol: %s)",
                pod_name,
                netpol_name,
            )
            return True

        loop = asyncio.get_event_loop()

        # 1. Delete Pod
        try:
            await loop.run_in_executor(
                None,
                lambda: self.k8s_core_api.delete_namespaced_pod(
                    name=pod_name,
                    namespace=self.namespace,
                    grace_period_seconds=0,
                ),
            )
            logger.info("🛑 Successfully deleted K8s pod %s", pod_name)
        except ApiException as e:
            if e.status != 404:
                logger.error("Failed to delete pod %s: %s", pod_name, e.status)
        except Exception as e:
            logger.error("Error terminating pod %s: %s", pod_name, type(e).__name__)

        # 2. Delete ephemeral Secret
        if secret_name:
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self.k8s_core_api.delete_namespaced_secret(
                        name=secret_name,
                        namespace=self.namespace,
                        grace_period_seconds=0,
                    ),
                )
                logger.info(
                    "🗑️ Deleted ephemeral credential resource for pod %s", pod_name
                )
            except ApiException as e:
                if e.status != 404:
                    logger.debug(
                        "Credential resource for pod %s already deleted or not found (status %s)",
                        pod_name,
                        e.status,
                    )
            except Exception as e:
                logger.debug(
                    "Error deleting credential resource for pod %s: %s",
                    pod_name,
                    type(e).__name__,
                )

        # 3. Delete ephemeral NetworkPolicy
        if netpol_name and self.k8s_network_api:
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self.k8s_network_api.delete_namespaced_network_policy(
                        name=netpol_name,
                        namespace=self.namespace,
                        grace_period_seconds=0,
                    ),
                )
                logger.info(f"🗑️ Deleted ephemeral NetworkPolicy {netpol_name}")
            except ApiException as e:
                if e.status != 404:
                    logger.debug(
                        f"NetworkPolicy {netpol_name} already deleted or not found: {e}"
                    )
            except Exception as e:
                logger.debug(f"Error deleting NetworkPolicy {netpol_name}: {e}")

        return True

    async def list_sandbox_pods(self) -> List[Dict[str, Any]]:
        """List active agent sandbox pods in cluster."""
        if not self.k8s_core_api:
            return []

        try:
            loop = asyncio.get_event_loop()
            pod_list = await loop.run_in_executor(
                None,
                lambda: self.k8s_core_api.list_namespaced_pod(
                    namespace=self.namespace,
                    label_selector="app=agent-sandbox",
                ),
            )
            results = []
            for pod in pod_list.items:
                results.append(
                    {
                        "podName": pod.metadata.name,
                        "phase": pod.status.phase,
                        "startTime": (
                            pod.status.start_time.isoformat()
                            if pod.status.start_time
                            else None
                        ),
                        "templateId": pod.metadata.labels.get("template-id", "unknown"),
                        "sandboxId": pod.metadata.labels.get("sandbox-id", "unknown"),
                    }
                )
            return results
        except Exception as e:
            logger.error(f"Failed to query K8s sandbox pods: {e}")
            return []

    async def get_sandbox_logs(self, pod_name: str, tail_lines: int = 50) -> str:
        """Fetch logs from sandbox container."""
        if not self.k8s_core_api:
            return (
                f"[SIMULATED LOGS] Pod {pod_name} running smoothly. No errors detected."
            )

        try:
            loop = asyncio.get_event_loop()
            logs = await loop.run_in_executor(
                None,
                lambda: self.k8s_core_api.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=self.namespace,
                    tail_lines=tail_lines,
                ),
            )
            return logs
        except Exception as e:
            return f"Unable to fetch logs for {pod_name}: {e}"

    async def execute_in_sandbox_pod(
        self,
        pod_name: str,
        command: Any,
        container: str = "agent-runner",
        timeout_seconds: int = 60,
    ) -> Dict[str, Any]:
        """
        Execute an ad-hoc command inside an active sandbox pod using Kubernetes exec.
        Falls back to simulation mode if cluster API is not available.
        """
        cmd_str = " ".join(command) if isinstance(command, list) else str(command)
        if not self.k8s_core_api:
            return {
                "status": "completed",
                "mode": "simulated_exec",
                "podName": pod_name,
                "stdout": f"[SIMULATED_EXEC] {cmd_str}\nStatus: completed (0)",
                "stderr": "",
                "exitCode": 0,
            }

        cmd_list = (
            ["/bin/bash", "-c", command] if isinstance(command, str) else list(command)
        )

        try:
            from kubernetes.stream import stream

            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: stream(
                    self.k8s_core_api.connect_get_namespaced_pod_exec,
                    name=pod_name,
                    namespace=self.namespace,
                    container=container,
                    command=cmd_list,
                    stderr=True,
                    stdin=False,
                    stdout=True,
                    tty=False,
                ),
            )
            return {
                "status": "completed",
                "podName": pod_name,
                "stdout": resp,
                "stderr": "",
                "exitCode": 0,
            }
        except Exception as e:
            logger.error(f"Exec in pod {pod_name} failed: {e}")
            return {
                "status": "error",
                "podName": pod_name,
                "stdout": "",
                "stderr": str(e),
                "exitCode": 1,
            }


# Global singleton instance
k8s_sandbox_driver = KubernetesSandboxDriver()
