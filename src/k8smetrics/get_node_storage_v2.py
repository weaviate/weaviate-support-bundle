
import os
from loguru import logger
from kubernetes import client, config
from kubernetes.stream import stream

from src.utils import save_results_to_json





def get_node_stats_using_client():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    
    nodes = v1.list_node()
    for node in nodes.items:
        node_name = node.metadata.name
        logger.info(f"Getting stats for node: {node_name}")
        
        try:
            path = f"/api/v1/nodes/{node_name}/proxy/stats/summary"
            response = v1.api_client.call_api(
                path, 
                'GET', 
                auth_settings=['BearerToken'],
                response_type='object'
            )
            
            data = response[0]
            node_info = process_node_data(node_name, data)

            return node_info
            
        except client.exceptions.ApiException as e:
            logger.error(f"Error accessing node {node_name}: {e}")


def process_node_data(node_name, data):
    fs_stats = data["node"]["fs"]

    capacity_bytes = fs_stats["capacityBytes"]
    used_bytes = fs_stats["usedBytes"]
    inode_used = fs_stats["inodesUsed"]
    inode_total = fs_stats["inodes"]

    capacity_gb = capacity_bytes / (1024 ** 3)
    used_gb = used_bytes / (1024 ** 3)

    node_info = {
        "node": node_name,
        "filesystem": {
            "capacity_gb": round(capacity_gb, 2),
            "used_gb": round(used_gb, 2),
            "inodes": {
                "used": inode_used,
                "total": inode_total,
                "percent_used": round(inode_used / inode_total * 100, 2)
            }
        },
        "pods_ephemeral_storage": []
    }


    for pod in data.get("pods", []):
        pod_name = pod["podRef"]["name"]
        pod_namespace = pod["podRef"]["namespace"]
        ephemeral = pod.get("ephemeral-storage", {})
        if ephemeral:
            node_info["pods_ephemeral_storage"].append({
                "namespace": pod_namespace,
                "pod": pod_name,
                "used_bytes": ephemeral.get("usedBytes"),
                "capacity_bytes": ephemeral.get("capacityBytes")
            })

    return node_info


        
if __name__ == "__main__":
    
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
    SAVED_DIR = os.path.join(OUTPUT_DIR, "k8smetrics")
    os.makedirs(SAVED_DIR, exist_ok=True)
    SAVED_PATH = os.path.join(SAVED_DIR, "k8s_storage_v2.json")
    storage_node_info = get_node_stats_using_client()

    save_results_to_json(storage_node_info, SAVED_PATH)



