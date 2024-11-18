
Set env var on the pod to indicate which container digest to check:
```
HUB_IMAGE_PATH='jgriffin555/manifest-app/tags/latest'
```

```
docker build --platform linux/amd64 -t jgriffin555/manifest-image-checker:latest . --push
```