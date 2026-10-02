"""
Kaniko In-Cluster Kubernetes Job Builder for FuzeAgent.
Spawns rootless, unprivileged Kaniko Jobs to assemble and push agent container images
to Harbor or GHCR without Docker-in-Docker daemons.
"""

import logging
import os
import uuid
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class KanikoBuilder:
    def __init__(self, namespace: Optional[str] = None):
        self.namespace = namespace or os.environ.get("POD_NAMESPACE", "default")
        self.in_cluster = os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")
        self.k8s_batch_client = None
        self.k8s_core_client = None
        self._init_client()

    def _init_client(self):
        try:
            from kubernetes import client, config
            if self.in_cluster:
                config.load_incluster_config()
            else:
                config.load_kube_config()
            self.k8s_batch_client = client.BatchV1Api()
            self.k8s_core_client = client.CoreV1Api()
            logger.info("Kubernetes client initialized successfully for KanikoBuilder.")
        except Exception as e:
            logger.warning(f"Could not initialize Kubernetes client (dev/local fallback active): {e}")

    async def build_image(self, template_id: str, dockerfile: str, destination_image: str) -> Dict[str, Any]:
        """
        Creates a temporary ConfigMap containing the Dockerfile, then creates a batch/v1 Job
        running Kaniko to build and push the image.
        """
        job_id = f"kaniko-{template_id[:8]}-{uuid.uuid4().hex[:6]}"
        config_map_name = f"dockerfile-{job_id}"

        if not self.k8s_batch_client or not self.k8s_core_client:
            logger.info(f"[DEV MOCK] Simulated Kaniko build job '{job_id}' for image '{destination_image}'.")
            return {
                "status": "building",
                "jobId": job_id,
                "destination": destination_image,
                "mode": "simulated_local"
            }

        try:
            from kubernetes import client

            # 1. Create ConfigMap with the Dockerfile
            cm_body = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(
                    name=config_map_name,
                    namespace=self.namespace,
                    labels={"app.kubernetes.io/managed-by": "fuzeagent-kaniko"}
                ),
                data={"Dockerfile": dockerfile}
            )
            self.k8s_core_client.create_namespaced_config_map(
                namespace=self.namespace,
                body=cm_body
            )

            # 2. Create the Kaniko batch/v1 Job
            job_body = client.V1Job(
                metadata=client.V1ObjectMeta(
                    name=job_id,
                    namespace=self.namespace,
                    labels={"app.kubernetes.io/name": "kaniko-builder", "template-id": template_id}
                ),
                spec=client.V1JobSpec(
                    ttl_seconds_after_finished=600,
                    backoff_limit=1,
                    template=client.V1PodTemplateSpec(
                        metadata=client.V1ObjectMeta(labels={"app.kubernetes.io/name": "kaniko-builder"}),
                        spec=client.V1PodSpec(
                            restart_policy="Never",
                            containers=[
                                client.V1Container(
                                    name="kaniko",
                                    image="gcr.io/kaniko-project/executor:v1.23.2-debug",
                                    args=[
                                        "--dockerfile=/workspace/Dockerfile",
                                        "--context=dir:///workspace",
                                        f"--destination={destination_image}",
                                        "--cache=true"
                                    ],
                                    volume_mounts=[
                                        client.V1VolumeMount(name="dockerfile-storage", mount_path="/workspace"),
                                        client.V1VolumeMount(name="registry-creds", mount_path="/kaniko/.docker")
                                    ],
                                    resources=client.V1ResourceRequirements(
                                        requests={"cpu": "500m", "memory": "1Gi"},
                                        limits={"cpu": "2000m", "memory": "4Gi"}
                                    )
                                )
                            ],
                            volumes=[
                                client.V1Volume(
                                    name="dockerfile-storage",
                                    config_map=client.V1ConfigMapVolumeSource(name=config_map_name)
                                ),
                                client.V1Volume(
                                    name="registry-creds",
                                    secret=client.V1SecretVolumeSource(
                                        secret_name=os.environ.get("REGISTRY_SECRET_NAME", "harbor-registry-creds"),
                                        items=[client.V1KeyToPath(key=".dockerconfigjson", path="config.json")]
                                    )
                                )
                            ]
                        )
                    )
                )
            )

            created_job = self.k8s_batch_client.create_namespaced_job(
                namespace=self.namespace,
                body=job_body
            )

            logger.info(f"Successfully launched Kaniko Job '{job_id}' in namespace '{self.namespace}'.")
            return {
                "status": "building",
                "jobId": job_id,
                "destination": destination_image,
                "mode": "k8s_job"
            }

        except Exception as e:
            logger.error(f"Failed to launch Kaniko build job in K8s: {e}")
            raise e

kaniko_builder = KanikoBuilder()
