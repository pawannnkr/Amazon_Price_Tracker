# Docker Registry Setup & Deployment Guide

## Quick Start

### 1. Configure Your Registry

Edit [.dockerregistry](.dockerregistry) and set your preferred registry details:

```bash
# For Docker Hub
DOCKER_REGISTRY=docker.io
DOCKER_USERNAME=your_username
DOCKER_IMAGE_NAME=amazon-price-tracker
DOCKER_IMAGE_TAG=latest

# For Google Container Registry
GCR_PROJECT_ID=your-gcp-project-id
GCR_REGION=us-central1
GCR_IMAGE_NAME=amazon-price-tracker
GCR_IMAGE_TAG=latest
```

### 2. Build and Push Image

```bash
# Make script executable
chmod +x build-and-push.sh

# Build and push to Docker Hub
./build-and-push.sh docker-hub

# Build and push to Google Container Registry
./build-and-push.sh gcr

# Build only (without pushing)
./build-and-push.sh docker-hub true
```

---

## Docker Hub Setup

### Prerequisites
- Docker Hub account: https://hub.docker.com

### Step 1: Create Repository
1. Login to Docker Hub
2. Click "Create Repository"
3. Repository name: `amazon-price-tracker`
4. Make it Public or Private
5. Click Create

### Step 2: Configure .dockerregistry
```bash
DOCKER_REGISTRY=docker.io
DOCKER_USERNAME=your_docker_username
DOCKER_IMAGE_NAME=amazon-price-tracker
DOCKER_IMAGE_TAG=latest
```

### Step 3: Build and Push
```bash
chmod +x build-and-push.sh
./build-and-push.sh docker-hub
# Enter Docker Hub credentials when prompted
```

### Step 4: Pull and Run
```bash
docker run -p 5000:5000 \
  --env-file .env \
  your_username/amazon-price-tracker:latest
```

---

## Google Container Registry (GCR)

### Prerequisites
- GCP account with billing enabled
- `gcloud` CLI installed: https://cloud.google.com/sdk/docs/install

### Step 1: Setup GCP Project
```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable Container Registry API
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Authenticate Docker with GCR
gcloud auth configure-docker
```

### Step 2: Configure .dockerregistry
```bash
GCR_PROJECT_ID=your-gcp-project-id
GCR_REGION=us-central1
GCR_IMAGE_NAME=amazon-price-tracker
GCR_IMAGE_TAG=latest
```

### Step 3: Build and Push
```bash
chmod +x build-and-push.sh
./build-and-push.sh gcr
```

### Step 4: Deploy to Cloud Run
```bash
gcloud run deploy amazon-price-tracker \
  --image gcr.io/YOUR_PROJECT_ID/amazon-price-tracker:latest \
  --platform managed \
  --region us-central1 \
  --port 5000 \
  --memory 512Mi \
  --allow-unauthenticated
```

### Step 5: View Deployment
```bash
# Get service URL
gcloud run services describe amazon-price-tracker --region us-central1

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

---

## GitHub Container Registry (GHCR)

### Prerequisites
- GitHub account
- GitHub Personal Access Token (PAT) with `read:packages` scope

### Step 1: Create Personal Access Token
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token"
3. Select scopes: `read:packages`, `write:packages`, `delete:packages`
4. Generate and copy the token

### Step 2: Configure .dockerregistry
```bash
GHCR_USERNAME=your_github_username
GHCR_IMAGE_NAME=amazon-price-tracker
GHCR_IMAGE_TAG=latest
```

### Step 3: Build and Push
```bash
chmod +x build-and-push.sh
./build-and-push.sh ghcr
# Enter username: your_github_username
# Enter password: your_github_pat_token
```

### Step 4: Pull and Run
```bash
docker run -p 5000:5000 \
  --env-file .env \
  ghcr.io/your_github_username/amazon-price-tracker:latest
```

---

## Local Docker Compose (Development)

### Step 1: Build Image
```bash
docker build -t amazon-price-tracker:dev .
```

### Step 2: Run with Docker Compose
```bash
docker-compose up -d
```

### Step 3: Check Logs
```bash
docker-compose logs amazon-price-tracker
docker-compose logs price-tracker-worker
```

### Step 4: Stop Services
```bash
docker-compose down
```

---

## Production Deployment Examples

### Deploy to Cloud Run
```bash
# Build and push
./build-and-push.sh gcr

# Deploy
gcloud run deploy amazon-price-tracker \
  --image gcr.io/YOUR_PROJECT_ID/amazon-price-tracker:latest \
  --region us-central1 \
  --port 5000 \
  --memory 512Mi \
  --set-env-vars "FLASK_ENV=production"
```

### Deploy to Docker Swarm
```bash
# Build image
docker build -t amazon-price-tracker:1.0 .

# Create service
docker service create \
  --name amazon-price-tracker \
  --publish 5000:5000 \
  --env-file /etc/amazon-tracker/.env \
  amazon-price-tracker:1.0
```

### Deploy to Kubernetes (using k8s-deployment.yaml)
```bash
# Update image in k8s-deployment.yaml
sed -i 's|gcr.io/YOUR_PROJECT_ID|gcr.io/my-project|g' k8s-deployment.yaml

# Apply deployment
kubectl apply -f k8s-deployment.yaml

# Check status
kubectl get deployments
kubectl get services
kubectl logs deployment/amazon-price-tracker-api
```

---

## Image Tagging Best Practices

### Tag with Version
```bash
docker build -t your_username/amazon-price-tracker:1.0 .
docker push your_username/amazon-price-tracker:1.0

docker build -t your_username/amazon-price-tracker:latest .
docker push your_username/amazon-price-tracker:latest
```

### Tag with Date
```bash
docker build -t your_username/amazon-price-tracker:$(date +%Y%m%d) .
docker push your_username/amazon-price-tracker:$(date +%Y%m%d)
```

### Tag with Git Commit
```bash
docker build -t your_username/amazon-price-tracker:$(git rev-parse --short HEAD) .
docker push your_username/amazon-price-tracker:$(git rev-parse --short HEAD)
```

---

## Monitoring Images in Registry

### Docker Hub
```bash
# View image details
docker pull your_username/amazon-price-tracker:latest

# Get image digest
docker inspect your_username/amazon-price-tracker:latest
```

### Google Container Registry
```bash
# List images
gcloud container images list --project=YOUR_PROJECT_ID

# Get image details
gcloud container images describe gcr.io/YOUR_PROJECT_ID/amazon-price-tracker:latest

# View image tags
gcloud container images list-tags gcr.io/YOUR_PROJECT_ID/amazon-price-tracker
```

### GitHub Container Registry
```bash
# Login to GitHub
echo $PAT_TOKEN | docker login ghcr.io -u username --password-stdin

# Pull image
docker pull ghcr.io/username/amazon-price-tracker:latest
```

---

## Troubleshooting

### Authentication Errors
```bash
# Docker Hub
docker login

# GCR
gcloud auth configure-docker
gcloud auth login

# GHCR
docker logout ghcr.io
docker login ghcr.io
```

### Image Not Found
```bash
# Check if image exists
docker images

# Pull from registry
docker pull your_username/amazon-price-tracker:latest
```

### Registry Quota Exceeded
- Docker Hub: 6 pulls per 6 hours (free tier)
- GCR: 5GB free storage, 1GB download per month
- GHCR: 0.5GB free storage per user

---

## Cost Optimization

| Registry | Cost | Best For |
|----------|------|----------|
| Docker Hub | Free (with limits) | Small projects, learning |
| GCR | Pay-per-use | GCP projects, Cloud Run |
| GHCR | Free (with limits) | GitHub-hosted projects |
| Artifactory | Paid (self-hosted free) | Enterprise, private repos |

---

## Next Steps

1. Choose your preferred registry
2. Update [.dockerregistry](.dockerregistry)
3. Run `./build-and-push.sh <registry>`
4. Deploy using the appropriate platform guide
5. Monitor logs and performance
