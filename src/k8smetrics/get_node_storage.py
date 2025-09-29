import os
import requests
from loguru import logger

from src.utils import save_results_to_json


# my node name is docker-desktop
KUBELET_SUMMARY_URL = os.getenv('KUBELET_SUMMARY_URL', "http://127.0.0.1:8001/api/v1/nodes/minikube/proxy/stats/summary")


def get_node_ephemeral_storage():
    result = {}

    try:
        response = requests.get(KUBELET_SUMMARY_URL)
        response.raise_for_status()
        data = response.json()

        node_name = data["node"]["nodeName"]
        fs_stats = data["node"]["fs"]

        capacity_bytes = fs_stats["capacityBytes"]
        used_bytes = fs_stats["usedBytes"]
        inode_used = fs_stats["inodesUsed"]
        inode_total = fs_stats["inodes"]

        capacity_gb = capacity_bytes / (1024 ** 3)
        used_gb = used_bytes / (1024 ** 3)

        # Node info
        result["node"] = {
            "name": node_name,
            "ephemeral_storage": {
                "capacity_gb": round(capacity_gb, 2),
                "used_gb": round(used_gb, 2),
                "inodes_used": inode_used,
                "inodes_total": inode_total,
                "inodes_percent_used": round(inode_used / inode_total * 100, 2)
            }
        }

        # Pods info
        result["pods"] = []
        for pod in data.get("pods", []):
            pod_name = pod["podRef"]["name"]
            pod_namespace = pod["podRef"]["namespace"]
            ephemeral = pod.get("ephemeral-storage", {})

            pod_info = {
                "namespace": pod_namespace,
                "name": pod_name,
                "used_bytes": ephemeral.get("usedBytes"),
                "capacity_bytes": ephemeral.get("capacityBytes")
            }

            result["pods"].append(pod_info)

        return results

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching summary API: {e}")

if __name__ == "__main__":
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
    SAVED_DIR = os.path.join(OUTPUT_DIR, "k8smetrics")
    os.makedirs(SAVED_DIR, exist_ok=True)
    SAVED_PATH = os.path.join(SAVED_DIR, "k8s_storage.json")

    storage_info = get_node_ephemeral_storage()
    save_results_to_json(storage_info, SAVED_PATH)

    

