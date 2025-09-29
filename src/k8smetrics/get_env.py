# File: get_helm_release.py
import os
import yaml
import gzip
import base64
from loguru import logger
from typing import Dict, Any
from dotenv import load_dotenv
from kubernetes import client, config

from src.utils import save_results_to_json

load_dotenv()


NAMESPACE = os.getenv("NAMESPACE", "weaviate")
STATEFULSET_NAME = os.getenv("STATEFULSET_NAME", "weaviate")


try:
    config.load_kube_config()
except Exception as e:
    logger.error(f"Error loading kubeconfig: {e}")
    exit(1)

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()


def get_statefulset_resource_details(namespace: str, statefulset_name: str) -> Dict[str, Any]:

    try:
        statefulset = apps_v1.read_namespaced_stateful_set(statefulset_name, namespace)
        #logger.info(statefulset.spec.template.spec.containers)
        container = statefulset.spec.template.spec.containers[0]
        resources = container.resources or client.V1ResourceRequirements()
        env_vars = {env.name: env.value for env in (container.env or []) if env.value is not None}
        env_from = container.env_from or []

        details = {
            "namespace": namespace,
            "statefulset": statefulset_name,
            "requests": dict(resources.requests or {}),
            "limits": dict(resources.limits or {}),
            "env_vars": env_vars,
            "env_from": f"Env From (ConfigMaps/Secrets): {env_from}"
        }

        logger.info("=== StatefulSet Resource Details ===")
        logger.info(f"StatefulSet: {statefulset_name}")
        logger.info(f"Requests: {details['requests']}")
        logger.info(f"Limits: {details['limits']}")
        logger.info(f"Env Vars: {details['env_vars']}")
        if details["env_from"]:
            logger.info(f"Env From (ConfigMaps/Secrets): {details['env_from']}")

        return details
    except client.ApiException as e:
        logger.error(f"Error fetching StatefulSet: {e}")
        return {}


if __name__ == "__main__":
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
    SAVED_DIR = os.path.join(OUTPUT_DIR, "k8smetrics")
    os.makedirs(SAVED_DIR, exist_ok=True)
    SAVED_PATH = os.path.join(SAVED_DIR, "k8s_env_var.json")
    resource_details = get_statefulset_resource_details(NAMESPACE, STATEFULSET_NAME)

    save_results_to_json(resource_details,SAVED_PATH)
