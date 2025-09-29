
import os
import logging
import weaviate
from loguru import logger
from typing import Dict, Any
from dotenv import load_dotenv

from src.weaviatemetrics.wvc_client import make_connection
from src.utils import save_results_to_json, serialize



load_dotenv()



def get_all_collection_info(client: weaviate.Client) -> Dict[str, Any]:
    """Retrieve configuration of a specific collection."""
    try:
        configs = client.collections.list_all(simple=False)
        logger.info(f"Fetched configuration for all collection")
        # print(configs)
        return configs
    except Exception as e:
        logger.error(f"Failed to fetch collections info: {e}", exc_info=True)
        raise



if __name__ == "__main__":
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
    SAVED_DIR = os.path.join(OUTPUT_DIR, "weaviatemetrics")
    os.makedirs(SAVED_DIR, exist_ok=True)
    SAVED_PATH = os.path.join(SAVED_DIR, "collections_schema.json")

    client = make_connection()
    configs = get_all_collection_info(client)
    save_results_to_json(serialize(configs), SAVED_PATH)
    
    client.close()