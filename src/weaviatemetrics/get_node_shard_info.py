
import os
import json
import weaviate
from loguru import logger
from dotenv import load_dotenv
from typing import Dict, Any, List

from src.weaviatemetrics.wvc_client import make_connection
from src.utils import save_results_to_json

load_dotenv()


def get_shards_info(client: weaviate.Client) -> List[Any]:
    """Retrieve detailed shard info from the cluster."""
    try:
        return client.cluster.nodes(output="verbose")
    except Exception as e:
        logger.error(f"Failed to fetch shard info: {e}", exc_info=True)
        raise


def process_shards_data(node_info: List[Any]) -> Dict[str, Any]:
    """Process shard and node data into structured format."""
    node_data, shard_data, collection_shard_counts, readonly_shards = [], [], [], []

    for node in node_info:
        logger.info(f"Processing node: {node.name}")

        # Node-level data
        node_data.append({
            "Node Name": node.name,
            "Git Hash": node.git_hash,
            "Version": node.version,
            "Status": node.status,
            "Object Count (Stats)": node.stats.object_count,
            "Shard Count (Stats)": node.stats.shard_count,
        })

        collection_counts = {}

        # Shard-level data
        for shard in node.shards:
            shard_info = {
                "Node Name": node.name,
                "Class": shard.collection,
                "Shard Name": shard.name,
                "Shard Replica": getattr(shard, "replica", None),
                "Object Count": shard.object_count,
                "Index Status": shard.vector_indexing_status,
                "Vector Queue Length": shard.vector_queue_length,
                "Compressed": shard.compressed,
                "Loaded": shard.loaded,
            }
            shard_data.append(shard_info)

            if shard.vector_indexing_status == "READONLY":
                readonly_shards.append(shard_info)

            # Count shards per collection per node
            collection_counts[shard.collection] = collection_counts.get(shard.collection, 0) + 1

        for collection, count in collection_counts.items():
            collection_shard_counts.append({
                "Node Name": node.name,
                "Collection": collection,
                "Shard Count": count,
            })

    return {
        "node_data": node_data,
        "shard_data": shard_data,
        "collection_shard_data": collection_shard_counts,
        "readonly_shards": readonly_shards,
    }


if __name__ == "__main__":
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
    SAVED_DIR = os.path.join(OUTPUT_DIR, "weaviatemetrics")
    os.makedirs(SAVED_DIR, exist_ok=True)
    SAVED_PATH = os.path.join(SAVED_DIR, "weaviate_node_shard_info.json")

    client = make_connection()
    node_info = get_shards_info(client)
    results = process_shards_data(node_info)
    save_results_to_json(results, SAVED_PATH)
    
    client.close()
