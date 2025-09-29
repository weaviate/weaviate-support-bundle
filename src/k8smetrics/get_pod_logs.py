import os
from loguru import logger
from kubernetes import client, config
from dotenv import load_dotenv

from src.utils import save_results_to_json

load_dotenv()

NAMESPACE = os.getenv("NAMESPACE", "weaviate")
POD_NAME = os.getenv("POD_NAME", "weaviate-0")

LOG_LINES = os.getenv("LOG_LINES", "7")

try:
    config.load_kube_config()
except Exception as e:
    logger.error(f"Error loading kubeconfig: {e}")
    exit(1)

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()


def get_pod_logs_by_name(pod_name, namespace):
    """Fetch logs for a specific pod."""
    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace
        )
        logger.info(logs)
    except client.exceptions.ApiException as e:
        logger.error(f"Error fetching logs for pod {pod_name}: {e}")
        return None


def list_pods_with_logs():
    """List all pods and collect their logs."""
    try:
      pods = v1.list_pod_for_all_namespaces(watch=False) 
      for pod in pods.items:
        pod_name = pod.metadata.name
        namespace = pod.metadata.namespace
        pod_ip = pod.status.pod_ip
        node_name = pod.spec.node_name

        logger.info(f"Name: {pod_name}, Namespace: {namespace}, IP: {pod_ip}, Node: {node_name}")

        #Retrieve and print logs for each container in the pod
        for container in pod.spec.containers:
          container_name = container.name
          logger.info(f"Logs for container {container_name}:")
          try:
              logs = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, container=container_name, tail_lines=LOG_LINES)
              logger.info(logs)

          except Exception as e:
              logger.error(f"Error getting logs for pod {pod_name}, container {container_name}: {e}")
    except Exception as e:
        logger.error(f"Error listing pods logs: {e}")


if __name__ == "__main__":
    logger.info("Starting pod log collection...")
    
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
    SAVED_DIR = os.path.join(OUTPUT_DIR, "k8smetrics")
    os.makedirs(SAVED_DIR, exist_ok=True)
    LOG_SAVED_PATH = os.path.join(SAVED_DIR, "pod.log")
    logger.add(LOG_SAVED_PATH, level="INFO")

    get_pod_logs_by_name(POD_NAME, NAMESPACE)
    pods_data = list_pods_with_logs()
    logger.info("Pod log collection finished.")
