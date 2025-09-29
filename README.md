
# K8s & Weaviate Metrics

This Bash script automates the collection of Kubernetes and Weaviate metrics, stores the results in an outputs directory, and packages them into a ZIP archive.


**Prerequisites**
- Bash shell
- Python 3 installed
- Permissions to read Kubernetes resources and pod logs

### Installation
Before running the script, install the required Python packages:
```bash
pip install -r requriements.txt
```

### Required (set in `.env`)
```bash
# Weaviate HTTP connection
WEAVIATE_HTTP_HOST=""
WEAVIATE_HTTP_PORT=""
WEAVIATE_HTTP_SECURE=""

# Weaviate gRPC connection
WEAVIATE_GRPC_HOST=""
WEAVIATE_GRPC_PORT=""
WEAVIATE_GRPC_SECURE=""

AUTH_API_KEY="XXXXXX"

# Output directory
OUTPUT_DIR="./outputs"

# Kubernetes-specific variables
NAMESPACE=""
STATEFULSET_NAME=""
RELEASE_NAME=""
POD_NAME=""
LOG_LINES=""
```

**Package Outputs**
```bash
zip -r "$ZIP_NAME" outputs/
```
- Compresses the outputs directory into a ZIP file.
- Default ZIP file: `k8s-weaviate-metrics.zip`.


### Usage Example
### Run with default ZIP name
```bash
./run_scripts.sh
```

**Output**
- `outputs/` directory with all collected metrics in separate files.
- Compressed ZIP file containing all collected metrics.
