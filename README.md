# Glasgow FastAPI 🚀

A FastAPI application designed for the Glasgow GitOps learning project, featuring automated CI/CD deployment to Kubernetes via ArgoCD.
Admin API

## 🛠️ Development

### Local Development Setup

```bash
# Install dependencies
uv sync

# Run locally with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access the API
curl http://localhost:8000/
curl http://localhost:8000/docs  # Swagger UI
```

### Environment Variables

The application expects the environment variables defined in core/config.py


## 🐳 Docker

### Manual Docker Build

```bash
# Build the image
docker build -t glasgow-fastapi .

# Run locally
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:password@host:5432/db \
  -e MINIO_ENDPOINT=host:9000 \
  -e MINIO_ACCESS_KEY=admin \
  -e MINIO_SECRET_KEY=password123 \
  glasgow-fastapi

# Test the container
curl http://localhost:8000/health
```

### Docker Hub Integration

This repository is configured with **automated Docker Hub builds** via GitHub Actions.
The new images are picked up by ArgoCD and deployed.


#### 📋 Manual Trigger

You can manually trigger the build workflow:

1. Go to **Actions** tab in GitHub
2. Select **"Build and Push to Docker Hub"**
3. Click **"Run workflow"**


## 🔧 GitOps Integration

This application is deployed using **GitOps principles**:

### Repository Structure
```
glasgow-fastapi/           # This repo (application code)
├── app/
│   └── main.py           # FastAPI application
├── Dockerfile            # Container definition
├── requirements.txt      # Dependencies
└── .github/workflows/    # CI/CD automation

glasgow-gitops/           # Infrastructure repo
├── components/fastapi/   # Kubernetes manifests
└── argocd/apps/         # ArgoCD applications
```


## 🧪 Testing


### Kubernetes Testing
```bash
# Port forward to service
kubectl port-forward svc/fastapi-service -n fastapi-prod 8081:8000

# Test through ingress (if configured)
curl http://api.glasgow.local/health
```

## 🔍 Troubleshooting

### Common Issues

#### Image Pull Errors
```bash
# Check if image exists on Docker Hub
docker pull hatchikin/glasgow-fastapi:latest

# Check Kubernetes events
kubectl describe pod -n fastapi-prod
```

#### Database Connection Issues
```bash
# Check database connectivity
kubectl logs -n fastapi-prod deployment/fastapi

# Test database service
kubectl get svc -n postgres-prod
```

#### MinIO Connection Issues
```bash
# Check MinIO service
kubectl get svc -n minio-prod

# Verify MinIO credentials in ConfigMap
kubectl get configmap fastapi-config -n fastapi-prod -o yaml
```

### Version Management

For production deployments, consider using specific version tags:

```bash
# Tag with version
docker build -t hatchikin/glasgow-fastapi:v1.2.3 .
docker push hatchikin/glasgow-fastapi:v1.2.3

# Update GitOps repo with specific version
# Edit components/fastapi/base/deployment.yaml
image: hatchikin/glasgow-fastapi:v1.2.3
```
