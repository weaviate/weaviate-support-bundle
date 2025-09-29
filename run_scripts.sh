#!/bin/bash
set -e  # stop on first error

# Make current directory available for Python imports
export PYTHONPATH=.

# Default zip name if not provided
if [ -z "$ZIP_NAME" ]; then
  ZIP_NAME="k8s-weaviate-metrics.zip"
fi

mkdir -p outputs

echo ">>> Running Getting Env"
python -m src.k8smetrics.get_env

echo ">>> Running Getting Events"
python -m src.k8smetrics.get_events

echo ">>> Running Getting helm release details"
python -m src.k8smetrics.get_helm_release_details

echo ">>> Running getting node details"
python -m src.k8smetrics.get_node_details

echo ">>> Running getting node storage"
python -m src.k8smetrics.get_node_storage_v2

echo ">>> Running getting pod logs"
python -m src.k8smetrics.get_pod_logs

echo ">>> Running getting collection info"
python -m src.weaviatemetrics.get_collection_info

echo ">>> Running getting node shard info"
python -m src.weaviatemetrics.get_node_shard_info

echo ">>> Zipping outputs into $ZIP_NAME"
zip -r "$ZIP_NAME" outputs/

echo ">>> Done! Created $ZIP_NAME"
