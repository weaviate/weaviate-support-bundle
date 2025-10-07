from kubernetes import client, config
import yaml
import base64
import gzip
import json
import os
from loguru import logger
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_complete_release_info(release_name, namespace="default"):
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        secrets = v1.list_namespaced_secret(namespace)
        secret_name = None
        
        for secret in secrets.items:
            if secret.metadata.name.startswith(f"sh.helm.release.v1.{release_name}."):
                secret_name = secret.metadata.name
                break
        
        if not secret_name:
            raise ValueError(f"No Helm release found for {release_name} in namespace {namespace}")
        
        secret = v1.read_namespaced_secret(secret_name, namespace)
        release_data = secret.data["release"]
        
        decoded_data = base64.b64decode(release_data).decode('utf-8')
        decompressed = gzip.decompress(base64.b64decode(decoded_data))
        release_info = json.loads(decompressed.decode('utf-8'))
        
        return release_info
    
    except Exception as e:
        logger.error(f"Error accessing release information: {e}")
        return None
    
def extract_all_release_data(release_info):

    if not release_info:
        return None
    
    data = {}
    
    data['metadata'] = {
        'name': release_info.get('name'),
        'namespace': release_info.get('namespace'),
        'version': release_info.get('version'),
        'status': release_info.get('info', {}).get('status'),
        'description': release_info.get('info', {}).get('description'),
        'first_deployed': release_info.get('info', {}).get('first_deployed'),
        'last_deployed': release_info.get('info', {}).get('last_deployed'),
        'deleted': release_info.get('info', {}).get('deleted'),
        'notes': release_info.get('info', {}).get('notes')
    }
    
    data['chart'] = {
        'name': release_info.get('chart', {}).get('metadata', {}).get('name'),
        'version': release_info.get('chart', {}).get('metadata', {}).get('version'),
        'description': release_info.get('chart', {}).get('metadata', {}).get('description'),
        'api_version': release_info.get('chart', {}).get('metadata', {}).get('apiVersion'),
        'app_version': release_info.get('chart', {}).get('metadata', {}).get('appVersion'),
        'type': release_info.get('chart', {}).get('metadata', {}).get('type'),
        'dependencies': release_info.get('chart', {}).get('metadata', {}).get('dependencies', [])
    }
    
    data['config'] = {
        'raw_values': release_info.get('config', {}),
        'computed_values': release_info.get('chart', {}).get('values', {})
    }
    
    data['manifest'] = {
        'raw_manifest': release_info.get('manifest'),
        'resources': parse_manifest_resources(release_info.get('manifest', ''))
    }
    
    data['version_info'] = {
        'current_revision': release_info.get('version'),
        'previous_revisions': get_previous_revisions(release_name, namespace)
    }
    
    return data

def parse_manifest_resources(manifest_yaml):

    resources = []
    if manifest_yaml:
        documents = manifest_yaml.split('---')
        for doc in documents:
            doc = doc.strip()
            if doc:
                try:
                    resource = yaml.safe_load(doc)
                    if resource and 'kind' in resource:
                        resources.append({
                            'kind': resource.get('kind'),
                            'name': resource.get('metadata', {}).get('name'),
                            'namespace': resource.get('metadata', {}).get('namespace'),
                            'api_version': resource.get('apiVersion')
                        })
                except yaml.YAMLError:
                    continue
    return resources

def get_previous_revisions(release_name, namespace):

    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        
        secrets = v1.list_namespaced_secret(namespace)
        revisions = []
        
        for secret in secrets.items:
            if secret.metadata.name.startswith(f"sh.helm.release.v1.{release_name}."):
                revision = {
                    'secret_name': secret.metadata.name,
                    'revision_number': int(secret.metadata.labels.get('version', '0')),
                    'created': secret.metadata.creation_timestamp,
                    'status': secret.metadata.labels.get('status', 'unknown')
                }
                revisions.append(revision)

        return sorted(revisions, key=lambda x: x['revision_number'])
    
    except Exception as e:
        logger.error(f"Error getting revisions: {e}")
        return []


if __name__ == "__main__":
  release_name = os.getenv("RELEASE_NAME", "weaviate")
  namespace = os.getenv("NAMESPACE", "weaviate")

  release_info = get_complete_release_info(release_name, namespace)
  #logger.info(type(release_info)) # type is dict
  #logger.info(list(release_info.keys())) # will shows top level keys

  if release_info:
    pass
    all_data = extract_all_release_data(release_info)
    
    logger.info("=== RELEASE METADATA ===")
    logger.info(f"Name: {all_data['metadata']['name']}")
    logger.info(f"Namespace: {all_data['metadata']['namespace']}")
    logger.info(f"Status: {all_data['metadata']['status']}")
    logger.info(f"Version: {all_data['metadata']['version']}")
    logger.info(f"First deployed: {all_data['metadata']['first_deployed']}")
    logger.info(f"Last deployed: {all_data['metadata']['last_deployed']}")

    logger.info("\n=== CHART INFORMATION ===")
    logger.info(f"Chart: {all_data['chart']['name']}-{all_data['chart']['version']}")
    logger.info(f"App version: {all_data['chart']['app_version']}")
    logger.info(f"Description: {all_data['chart']['description']}")
    
    logger.info("\n=== DEPLOYED RESOURCES ===")
    for resource in all_data['manifest']['resources']:
        logger.info(f"{resource['kind']}: {resource['name']}")

    export_data = {
        "metadata": {
            "name": all_data["metadata"]["name"],
            "namespace": all_data["metadata"]["namespace"],
            "status": all_data["metadata"]["status"],
            "version": all_data["metadata"]["version"],
            "first_deployed": all_data["metadata"]["first_deployed"],
            "last_deployed": all_data["metadata"]["last_deployed"]
        },
        "chart": {
            "name": all_data["chart"]["name"],
            "version": all_data["chart"]["version"],
            "app_version": all_data["chart"]["app_version"],
            "description": all_data["chart"]["description"]
        },
        "resources": all_data["manifest"]["resources"],
        "revision_history": [
            {
                "revision_number": rev["revision_number"],
                "status": rev["status"],
                "created": str(rev["created"]) 
            }
            for rev in all_data["version_info"]["previous_revisions"]
        ]
    }

    # logger.info("\n=== CONFIGURATION VALUES ===")
    # logger.info(yaml.dump(all_data['config']['raw_values'], default_flow_style=False))
    
    # logger.info("=== Rendered Template for Helm Chart ===")
    # logger.info(release_info.get('manifest'))

    logger.info("\n=== REVISION HISTORY ===")
    for revision in all_data['version_info']['previous_revisions']:
        logger.info(f"Revision {revision['revision_number']}: {revision['status']} at {revision['created']}")

    
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")
    SAVED_DIR = os.path.join(OUTPUT_DIR, "k8smetrics")
    output_dir = os.path.join(SAVED_DIR, f"helm_{release_name}")
    # output_dir = f"helm_{release_name}"#_{datetime.now().strftime('%Y%m%d')}"
    os.makedirs(output_dir, exist_ok=True)


    json_file = os.path.join(output_dir, "release_summary.json")
    with open(json_file, "w") as f:
        json.dump(export_data, f, indent=4)


    values = yaml.dump(all_data['config']['raw_values'], default_flow_style=False)
    cleaned_values = values.replace('\\n', '\n')
    parsed_values = yaml.safe_load(cleaned_values)
    with open(os.path.join(output_dir, 'values.yaml'), 'w') as f:
        yaml.dump(parsed_values, f, default_flow_style=False, sort_keys=False)

    manifest=release_info.get('manifest')
    with open(os.path.join(output_dir, 'templates.yaml'), 'w') as f:
        f.write(manifest)

    logger.info(f"\nFiles saved to: {output_dir}/")
    logger.info(f"  - values.yaml")
    logger.info(f"  - templates.yaml")

    
