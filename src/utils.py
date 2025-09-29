
import json
from enum import Enum
from loguru import logger
from typing import Any, Dict




def save_results_to_json(results: Dict[str, Any], filename: str) -> None:
    """Save results dictionary into a JSON file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        logger.info(f"Results saved to {filename}")
    except Exception as e:
        logger.error(f"Failed to save results to JSON: {e}", exc_info=True)
        raise


def serialize(obj):
    """
    Recursively convert objects into JSON-serializable types.
    """
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize(v) for v in obj]
    elif isinstance(obj, Enum):
        return obj.value
    elif hasattr(obj, "__dict__"):
        return serialize(obj.__dict__)
    else:
        return obj