# Cloud deployment

Build and push the backend and frontend images, replacing the placeholder image names in `kubernetes.yaml`. Build the frontend with `NEXT_PUBLIC_API_URL` set to the public API origin. Use managed PostgreSQL, Redis and S3-compatible object storage; do not deploy stateful development containers for production.

Create `storycast-secrets` with `GEMINI_API_KEY`, `HF_TOKEN`, and any S3 credentials. Replace the example database and Redis endpoints in the ConfigMap. Apply the migration Job and wait for it to complete before deploying the API/workers:

```sh
kubectl apply -f deploy/kubernetes.yaml
kubectl wait --for=condition=complete job/storycast-migrate --timeout=180s
```

Terminate TLS at a cloud load balancer or ingress, restrict API CORS to the frontend origin, and use workload identity instead of long-lived S3 keys where supported. This project intentionally has no authentication and should not be exposed directly to the public internet.
