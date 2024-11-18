import logging
import time
import requests
import os
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load Kubernetes in-cluster config
config.load_incluster_config()
core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

# Environment variables
container_name = os.getenv('IMAGE_CHECKER_WATCH_CONTAINER')

if not container_name:
    raise ValueError("Environment variable 'IMAGE_CHECKER_WATCH_CONTAINER' is not set.")

def get_current_namespace():
    """
    Reads the namespace of the current pod from the service account token location.
    """
    with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace') as f:
        return f.read().strip()

def get_current_pod_name():
    """
    Gets the name of the current pod using the Downward API through the Kubernetes client.
    """
    with open('/etc/hostname') as f:
        return f.read().strip()

def get_deployment_name_from_pod(pod_name, namespace):
    """
    Extracts the deployment name from the ownerReferences of the current pod.
    """
    pod = core_v1.read_namespaced_pod(pod_name, namespace)
    for owner in pod.metadata.owner_references:
        if owner.kind == "ReplicaSet":
            replicaset_name = owner.name
            replicaset = apps_v1.read_namespaced_replica_set(replicaset_name, namespace)
            for owner in replicaset.metadata.owner_references:
                if owner.kind == "Deployment":
                    return owner.name
    raise ValueError("Deployment not found for pod.")

def get_deployment_selector(deployment_name, namespace):
    """
    Retrieves the label selector for the deployment.
    """
    deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
    selector = deployment.spec.selector.match_labels
    return ",".join([f"{k}={v}" for k, v in selector.items()])

def get_running_pod(deployment_selector, namespace):
    """
    Retrieves the first running pod for the deployment based on its label selector.
    """
    pods = core_v1.list_namespaced_pod(namespace, label_selector=deployment_selector)
    for pod in pods.items:
        if pod.status.phase == "Running":
            return pod
    raise RuntimeError("No running pod found for the deployment.")

def get_image_digest_from_pod(pod, container_name):
    """
    Extracts the image digest from the running pod's containerStatuses field for the specified container.
    """
    logging.info(f"Checking pod: {pod.metadata.name}")
    
    for container_status in pod.status.container_statuses:
        if container_status.name == container_name:
            image_id = container_status.image_id  # Format: docker-pullable://<image>@<digest>
            if "@" in image_id:
                return image_id.split("@")[-1]  # Extract the digest after '@'
    raise RuntimeError(f"Image digest not found for container '{container_name}' in the pod's containerStatuses.")

def get_docker_hub_url(deployment_name, namespace):
    """
    Constructs the Docker Hub URL for the image based on the deployment's container image.
    """
    deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
    container_image = deployment.spec.template.spec.containers[0].image

    # Parse image into repository, image name, and tag
    if "@" in container_image:
        repo_image, digest = container_image.split("@")
        tag = digest  # Use the digest if tag isn't present
    elif ":" in container_image:
        repo_image, tag = container_image.split(":")
    else:
        repo_image, tag = container_image, "latest"  # Default to "latest" if no tag specified

    # Docker Hub expects URL in {repo}/{image}/tags/{tag}
    if "/" not in repo_image:
        repo_image = f"library/{repo_image}"  # Assume "library" namespace for official images

    return f"https://registry.hub.docker.com/v2/repositories/{repo_image}/tags/{tag}"

namespace = get_current_namespace()
pod_name = get_current_pod_name()
deployment_name = get_deployment_name_from_pod(pod_name, namespace)

while True:
    try:
        logging.info(f"Checking image digest for deployment: {deployment_name}")
        docker_hub_url = get_docker_hub_url(deployment_name, namespace)
        logging.info(f"Docker Hub URL: {docker_hub_url}")

        # Get the latest digest from Docker Hub
        response = requests.get(docker_hub_url)
        response.raise_for_status()
        latest_digest = response.json()["images"][0]["digest"]
        
        # Get deployment selector and find the running pod
        deployment_selector = get_deployment_selector(deployment_name, namespace)
        pod = get_running_pod(deployment_selector, namespace)
        
        # Get the image digest
        current_digest = get_image_digest_from_pod(pod, container_name)
        logging.info(f"Current image digest: {current_digest}")

        # Compare and trigger redeployment if needed
        if current_digest != latest_digest:
            logging.info(f"New image detected: {latest_digest}. Triggering redeployment...")
            deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
            deployment.spec.template.metadata.annotations = {
                "force-redeploy": str(time.time())  # Use annotation to trigger new pod
            }
            apps_v1.patch_namespaced_deployment(deployment_name, namespace, deployment)
        else:
            logging.info(f"Image up-to-date: {current_digest}")

    except ApiException as e:
        logging.error(f"Kubernetes API error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        time.sleep(300)  # Check every 5 minutes
        
        
        
        
        
        
