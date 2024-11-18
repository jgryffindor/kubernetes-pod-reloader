# image-checker 

A python script and container to dynamically check pod image digest against a remote and restart the pod if different. 



## Configuration 

#### 
- ImagePullPolicy must be set to always
- The container must be running as a sidecar container to the pod you wish to watch for changes.

### Required ENV Vars 
- Set to inform the watcher container which container to watch

```
IMAGE_CHECKER_WATCH_CONTAINER="container-name-in-pod"
```

Optional env vars 
- set a different container image repo url if not using dockerhub: 

```
IMAGE_CHECKER_REGISTRY_URL="https://domain.com"
```

## Development 
```
docker build --platform linux/amd64 -t repo/image-checker:latest . --push
```

## Kubernetes Configuration 
Mount the container into a pod you wish to watch with a service account containing the necessary permissions:

```
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: image-checker-sa
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: image-checker-role
  namespace: default
rules:
  - apiGroups: ["apps"]
    resources: ["deployments","replicasets"]
    verbs: ["get", "patch", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: image-checker-rolebinding
  namespace: default
subjects:
  - kind: ServiceAccount
    name: image-checker-sa
    namespace: manifest
roleRef:
  kind: Role
  name: image-checker-role
  apiGroup: rbac.authorization.k8s.io
```