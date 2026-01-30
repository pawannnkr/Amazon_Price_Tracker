# GitHub Actions Setup Guide

## Overview
This project includes 6 automated workflows for linting, testing, building, deploying, security scanning, and releasing:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `lint-and-test.yml` | Push/PR to main/develop | Python lint, format checks, unit tests with PostgreSQL |
| `build-docker.yml` | Push/PR/tags to main/develop | Build & push Docker images to GHCR |
| `deploy-cloudrun.yml` | Push to main / manual trigger | Deploy to Google Cloud Run |
| `deploy-gke.yml` | Push to main / manual trigger | Deploy to Google Kubernetes Engine |
| `security-scan.yml` | Push/PR/weekly schedule | Bandit, Safety, pip-audit, Trivy scans |
| `release.yml` | Tag push (v*) | Create release, push images to GHCR & GCP |

---

## Prerequisites

### 1. GitHub Repository Secrets
Configure these in **Settings → Secrets and variables → Actions**:

#### Required for Docker/Registry
```
GITHUB_TOKEN              # Auto-provided by GitHub Actions
```

#### Required for GCP Deployments (Cloud Run / GKE)
```
GCP_PROJECT_ID            # e.g., my-project-123
GCP_REGION                # e.g., us-central1
GCP_ZONE                  # e.g., us-central1-a
GCP_WORKLOAD_IDENTITY_PROVIDER  # Format: projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID
GCP_SERVICE_ACCOUNT       # e.g., github-actions@my-project.iam.gserviceaccount.com
GCP_SA_KEY                # JSON contents of service account key file
```

#### Required for Cloud Run
```
SERVICE_NAME              # e.g., amazon-price-tracker
REGISTRY_REPO             # e.g., app-images (Artifact Registry repo)
CORS_ORIGIN               # e.g., https://yourdomain.com or *
DATABASE_URL              # postgresql://user:pass@host:5432/db
EMAIL_ID                  # SMTP sender email
EMAIL_PASS                # SMTP password
SMTP_SERVER               # e.g., smtp.gmail.com
SMTP_PORT                 # e.g., 587
```

#### Required for GKE
```
GKE_CLUSTER               # e.g., my-cluster
GKE_ZONE                  # e.g., us-central1-a
# ... plus all Cloud Run secrets above
```

#### Optional: Slack Notifications
```
SLACK_WEBHOOK             # Slack webhook URL for deployment notifications
```

---

## GCP Setup Instructions

### Step 1: Create Service Account
```bash
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions CI/CD"
```

### Step 2: Grant Permissions
For **Cloud Run** deployments:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/artifactregistry.writer

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/run.admin

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.serviceAccountUser
```

For **GKE** deployments, add:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/container.developer
```

### Step 3: Create Service Account Key (Legacy - for GCP_SA_KEY)
```bash
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Copy contents to GCP_SA_KEY secret (as raw JSON)
cat key.json
rm key.json
```

### Step 4: Set Up Workload Identity Federation (Recommended for keyless auth)
```bash
# Create Workload Identity Pool
gcloud iam workload-identity-pools create "github-actions" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions"

# Create OIDC Provider
gcloud iam workload-identity-pools providers create-oidc "github" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --display-name="GitHub" \
  --attribute-mapping="google.subject=assertion.sub,assertion.aud=assertion.aud" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Configure service account impersonation
gcloud iam service-accounts add-iam-policy-binding \
  github-actions@${PROJECT_ID}.iam.gserviceaccount.com \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_ID}/locations/global/workloadIdentityPools/github-actions/attribute.repository_owner/${GITHUB_ORG}"
```

### Step 5: Create Artifact Registry Repository
```bash
gcloud artifacts repositories create app-images \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker images for Cloud Run/GKE"
```

### Step 6: Enable Required APIs
```bash
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  container.googleapis.com \
  cloudbuild.googleapis.com
```

---

## Cloud Run Deployment

### Initial Setup
```bash
# Test deployment via CLI first
gcloud run deploy amazon-price-tracker \
  --image=gcr.io/YOUR_PROJECT_ID/amazon-price-tracker \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=5000 \
  --memory=512Mi \
  --set-env-vars="DATABASE_URL=..." \
  --set-secrets="DATABASE_URL=database-url:latest"
```

### Via GitHub Actions
1. Push to `main` branch → `deploy-cloudrun.yml` runs automatically
2. Monitor progress in **Actions** tab
3. Or manually trigger: **Actions → Deploy to Cloud Run → Run workflow**

---

## GKE Deployment

### Prerequisites
```bash
# Create GKE cluster (if not exists)
gcloud container clusters create my-cluster \
  --zone us-central1-a \
  --num-nodes=2 \
  --machine-type=n1-standard-1

# Create namespaces
kubectl create namespace staging
kubectl create namespace production
```

### Via GitHub Actions
1. Push to `main` or tag release → `deploy-gke.yml` runs
2. Select environment (staging/production) via workflow dispatch
3. Workflow creates secrets and updates deployment image

---

## Local Testing

### Run Workflows Locally with Act
```bash
# Install act: https://github.com/nektos/act
act push -j lint-and-test
act push -j build-docker
```

### Test Docker Build
```bash
docker build -t amazon-price-tracker:test .
docker run -p 5000:5000 --env-file .env amazon-price-tracker:test
```

---

## Monitoring & Debugging

### View Workflow Logs
- GitHub UI: **Actions** tab → select workflow → view detailed logs
- Annotation format: `::error::message` triggers failure
- Use `actions/upload-artifact` to save reports (bandit, coverage)

### Health Check Integration
All deploy workflows verify service health before completing:
```bash
curl -f https://YOUR_SERVICE_URL/api/health
```

### Slack Notifications
Deploy workflows send notifications to configured webhook on success/failure. Set `SLACK_WEBHOOK` in secrets.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid GCP_SA_KEY" | Verify JSON key is raw content (not base64) |
| Cloud Run deployment fails | Check Database URL and env vars are set; verify network access to DB |
| Image push fails | Ensure Artifact Registry repo exists and service account has `artifactregistry.writer` role |
| GKE deployment pending | Check node capacity; may need to scale cluster |
| Security scan errors in PRs | Review Bandit/Trivy reports; filter in config or suppress with comments |

---

## Next Steps

1. **Update `.env` example** in repository root with placeholder values
2. **Create CHANGELOG.md** for release notes
3. **Add branch protection rules**: Require passing workflows before merge to `main`
4. **Configure Slack webhook** for deployment notifications
5. **Set up cost alerts** in GCP for Cloud Run/GKE resources
