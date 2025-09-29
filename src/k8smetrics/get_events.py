
import os
import json
from loguru import logger
from kubernetes import client, config
from dotenv import load_dotenv

from src.utils import save_results_to_json


load_dotenv()

NAMESPACE = os.getenv("NAMESPACE", "weaviate")


try:
    config.load_kube_config()
except Exception as e:
    logger.error(f"Error loading kubeconfig: {e}")
    exit(1)

v1 = client.CoreV1Api()

def get_namespace_events(namespace: str):
    events = v1.list_namespaced_event(namespace)
    event_list = []

    for event in events.items:
        event_info = {
            "reason": event.reason,
            "message": event.message,
            "type": event.type,
            "involved_object": f"{event.involved_object.kind}/{event.involved_object.name}",
            "timestamp": str(event.last_timestamp) if event.last_timestamp else None
        }
        event_list.append(event_info)
        logger.info(f"Event: {event.type} - {event.reason}: {event.message} on {event_info['involved_object']}")

    return event_list

if __name__ == "__main__":
    
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
    SAVED_DIR = os.path.join(OUTPUT_DIR, "k8smetrics")
    os.makedirs(SAVED_DIR, exist_ok=True)
    SAVED_PATH = os.path.join(SAVED_DIR, "k8s_events.json")

    event_data = get_namespace_events(NAMESPACE)
    save_results_to_json(event_data, SAVED_PATH)
