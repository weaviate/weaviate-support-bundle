
import os
from loguru import logger
from kubernetes import client, config
from dotenv import load_dotenv

from src.utils import save_results_to_json


load_dotenv()

try:
    config.load_kube_config()
except Exception as e:
    logger.error(f"Error loading kubeconfig: {e}")
    exit(1)

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()


def get_node_details():
    nodes = v1.list_node()
    node_list = []

    logger.info("=== Cluster Node Details (Capacity) ===")
    for node in nodes.items:
        node_info = {
            "name": node.metadata.name,
            "capacity": {
                "cpu": node.status.capacity.get("cpu", "N/A"),
                "memory": node.status.capacity.get("memory", "N/A"),
                "pods": node.status.capacity.get("pods", "N/A")
            }
        } 
        node_list.append(node_info)

    return node_list


if __name__ == "__main__":
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
    SAVED_DIR = os.path.join(OUTPUT_DIR, "k8smetrics")
    os.makedirs(SAVED_DIR, exist_ok=True)
    SAVED_PATH = os.path.join(SAVED_DIR, "k8s_node.json")

    node_list = get_node_details()
    save_results_to_json(node_list, SAVED_PATH)