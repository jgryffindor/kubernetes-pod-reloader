import os
import logging
import time
import requests
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

config.load_incluster_config()
v1 = client.AppsV1Api()

namespace = "manifest"
hub_base_url = "https://registry.hub.docker.com/v2/repositories"

deployment_name = os.getenv('CHECKER_DEPLOYMENT_NAME')
hub_image_path = os.getenv('HUB_IMAGE_PATH', 'jgriffin555/manifest-app/tags/latest')
hub_url = f"{hub_base_url}/{hub_image_path}"

while True:
  try: 
    # Get current pod image digest
    deployment = v1.read_namespaced_deployment(deployment_name, namespace)
    current_image = deployment.spec.template.spec.containers[0].image
    logging.info(f"Current image: {current_image}")
    if "@" in current_image:
        current_digest = current_image.split("@")[-1]
    else:
        current_digest = current_image.split(":")[-1]
    logging.info(f"Current image digest: {current_digest}")

    # Check Docker Hub for latest digest
    logging.info(f"Checking {hub_url} for new image...")
    response = requests.get(hub_url)
    response.raise_for_status()
    latest_digest = response.json()["images"][0]["digest"]

    # Compare and trigger redeployment if neededx
    if current_digest != latest_digest:
        logging.info(f"New image detected: {latest_digest}. Triggering redeployment...")
        deployment.spec.template.metadata.annotations = {
            "force-redeploy": str(time.time())  # Use annotation to trigger new pod
        }
        v1.patch_namespaced_deployment(deployment_name, namespace, deployment)
    else:
        logging.info(f"Image up-to-date: {current_digest}")

  except ApiException as e:
      logging.error(f"Kubernetes API error: {e}")
  except requests.RequestException as e:
      logging.error(f"HTTP request error: {e}")
  except Exception as e:
      logging.error(f"Unexpected error: {e}")
  finally:
      # Add a maximum failure limit if needed to prevent infinite retries
      time.sleep(300)  # Check every 5 minutes
