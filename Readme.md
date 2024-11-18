# Kubernetes Pod Reloaded

A python script and container to dynamically check a pods container image digest against a remote image digest, and restart the pod if different. 



## Configuration 

#### 
- ImagePullPolicy must be set to always
- The container must be running as a sidecar container to the pod you wish to watch for changes.

### Required ENV Vars 
- Set to inform the watcher container which container to watch:

```
IMAGE_CHECKER_WATCH_CONTAINER="container-name-in-pod"
```

Optional env vars 
- (untested) set a different container image repo url if not using dockerhub: 

```
IMAGE_CHECKER_REGISTRY_URL="https://domain.com/api/v1/repository/"
```

## Development 
```
docker build --platform linux/amd64 -t repo/image-checker:latest . --push
```

## Kubernetes Configuration 
Mount the container into a pod you wish to watch with a service account containing the necessary permissions:

```
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-watched
  namespace: default
  labels:
    app: nginx-watched
spec:
  replicas: 1
  revisionHistoryLimit: 3
  selector:
    matchLabels:
      app: mnginx-watched
  template:
    metadata:
      labels:
        app: nginx-watched
    spec:
      serviceAccountName: image-checker-sa 
      containers:
      - name: main-container
        image: nginx:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 80
        resources:
          requests: 
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "2500m"
            memory: "4Gi"
        readinessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 5
          failureThreshold: 3
        livenessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
          failureThreshold: 3
      - name: image-checker
        imagePullPolicy: Always
        image: repo/image-checker:latest
        command: ["/bin/sh", "-c"]
        args: ["cd /app && python check.py"]
        env: 
        - name: IMAGE_CHECKER_WATCH_CONTAINER
          value: "main-container"
        resources:
          requests: 
            cpu: "100m"
            memory: "100Mi"
          limits:
            cpu: "250m"
            memory: "300Mi"

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