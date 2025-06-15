# Glasgow FastAPI 🚀

A FastAPI application designed for the Glasgow GitOps learning project, featuring automated CI/CD deployment to Kubernetes via ArgoCD.

## 🏗️ Architecture

This application is part of a **GitOps microservices stack**:
- **FastAPI** (this repo) - Application code
- **PostgreSQL** - Database storage
- **MinIO** - Object storage
- **ArgoCD** - GitOps deployment
- **Traefik** - Ingress controller


## 🛠️ Development

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access the API
curl http://localhost:8000/
curl http://localhost:8000/docs  # Swagger UI
```

### Environment Variables

The application expects these environment variables:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/database
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password123
```

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

#### 🔄 Automated Workflow

Every push to `main` triggers:

1. **GitHub Actions** builds Docker image
2. **Image pushed** to `hatchikin/glasgow-fastapi:latest`
3. **Multiple tags** created automatically:
   - `hatchikin/glasgow-fastapi:latest`
   - `hatchikin/glasgow-fastapi:main`
   - `hatchikin/glasgow-fastapi:main-abc1234` (commit SHA)


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

### Deployment Flow

1. **Developer** pushes code changes
2. **GitHub Actions** builds new Docker image
3. **Image** pushed to Docker Hub with latest tag
4. **ArgoCD** detects configuration in GitOps repo
5. **Kubernetes** pulls new image and deploys

### Kubernetes Configuration

The application runs in Kubernetes with:
- **2 replicas** (production)
- **Resource limits**: 512Mi memory, 400m CPU
- **Health checks**: Liveness and readiness probes
- **Config injection**: Database and MinIO credentials via ConfigMap
- **Ingress**: External access via `api.glasgow.local`

## 🧪 Testing

### Local Testing
```bash
# Test health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/db
curl http://localhost:8000/health/minio

# Test bucket operations
curl -X POST http://localhost:8000/bucket/test-bucket
curl http://localhost:8000/buckets
```

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

## 🚀 Development Workflow

### Making Changes

1. **Edit code** in `app/main.py`
2. **Test locally** with `uvicorn app.main:app --reload`
3. **Commit and push** to main branch
4. **GitHub Actions** automatically builds and pushes new image
5. **Restart deployment** to pull new image:
   ```bash
   kubectl rollout restart deployment/fastapi -n fastapi-prod
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

## 📚 Related Documentation

- **GitOps Repository**: [glasgow-gitops](https://github.com/Hatchi-Kin/glasgow-gitops)
- **ArgoCD**: https://argo-cd.readthedocs.io/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Docker Hub**: https://hub.docker.com/r/hatchikin/glasgow-fastapi

