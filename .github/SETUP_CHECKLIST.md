# GitHub Actions Setup Checklist

Complete these steps to activate GitHub Actions for PriceSnap.

## Phase 1: Repository Setup (5 minutes)
- [ ] Commit and push all `.github/` changes
  ```bash
  git add .github/ conftest.py .gitignore
  git commit -m "ci: add GitHub Actions workflows"
  git push origin main
  ```
- [ ] Verify workflows appear in GitHub UI: **Actions** tab
- [ ] Check for any syntax errors in workflow logs

## Phase 2: GitHub Secrets Setup (10 minutes)
Go to **Settings → Secrets and variables → Actions**

### Docker Build (Required for `build-docker.yml`)
```
GITHUB_TOKEN → Already provided by GitHub (no action needed)
```

### Optional: Slack Notifications
```
SLACK_WEBHOOK → Slack webhook URL for deployment alerts
```
- [ ] Add Slack webhook (optional but recommended)

## Phase 3: GCP Setup (if deploying to Cloud Run/GKE) (20-30 minutes)

### A. Create Service Account
```bash
export PROJECT_ID="your-gcp-project-id"

gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions CI/CD"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/artifactregistry.writer

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/run.admin

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/iam.serviceAccountUser

# For GKE only:
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/container.developer
```
- [ ] Service account created
- [ ] Roles assigned

### B. Set Up Workload Identity Federation (Recommended - Keyless)
```bash
# Create Workload Identity Pool
gcloud iam workload-identity-pools create "github-actions" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions"

# Get pool resource name
POOL_NAME=$(gcloud iam workload-identity-pools describe "github-actions" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --format='value(name)')

# Create OIDC Provider
gcloud iam workload-identity-pools providers create-oidc "github" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --display-name="GitHub" \
  --attribute-mapping="google.subject=assertion.sub,assertion.aud=assertion.aud" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Allow repo to use service account
REPO="pawannnkr/PriceSnap"  # Change to your repo
gcloud iam service-accounts add-iam-policy-binding \
  github-actions@${PROJECT_ID}.iam.gserviceaccount.com \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_ID}/locations/global/workloadIdentityPools/github-actions/attribute.repository_owner/pawannnkr"

# Get provider resource name for GitHub secrets
PROVIDER_NAME=$(gcloud iam workload-identity-pools providers describe "github" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --format='value(name)')

echo "Add to GitHub secrets:"
echo "GCP_WORKLOAD_IDENTITY_PROVIDER=${PROVIDER_NAME}"
```
- [ ] Workload Identity Pool created
- [ ] OIDC Provider created
- [ ] Service account configured for keyless auth

### C. Create Artifact Registry (for container images)
```bash
gcloud artifacts repositories create app-images \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker images for Cloud Run/GKE"
```
- [ ] Artifact Registry repo created

### D. Enable Required GCP APIs
```bash
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  container.googleapis.com \
  cloudbuild.googleapis.com \
  cloudresourcemanager.googleapis.com
```
- [ ] APIs enabled

### E. Add GitHub Secrets for GCP
Go to **Settings → Secrets and variables → Actions** and add:
```
GCP_PROJECT_ID              # Your GCP project ID
GCP_REGION                  # e.g., us-central1
GCP_ZONE                    # e.g., us-central1-a
GCP_WORKLOAD_IDENTITY_PROVIDER  # From step B (WIF pool + provider)
GCP_SERVICE_ACCOUNT         # github-actions@PROJECT_ID.iam.gserviceaccount.com
```
- [ ] GCP_PROJECT_ID
- [ ] GCP_REGION
- [ ] GCP_ZONE
- [ ] GCP_WORKLOAD_IDENTITY_PROVIDER
- [ ] GCP_SERVICE_ACCOUNT

## Phase 4: Cloud Run Setup (if using Cloud Run) (15 minutes)

### A. Add Cloud Run Secrets
Go to **Settings → Secrets and variables → Actions** and add:
```
SERVICE_NAME       # e.g., amazon-price-tracker
REGISTRY_REPO      # e.g., app-images
CORS_ORIGIN        # e.g., https://yourdomain.com or *
DATABASE_URL       # postgresql://user:pass@host:5432/db
EMAIL_ID           # SMTP sender email
EMAIL_PASS         # SMTP password
SMTP_SERVER        # e.g., smtp.gmail.com
SMTP_PORT          # e.g., 587
```
- [ ] SERVICE_NAME
- [ ] REGISTRY_REPO
- [ ] CORS_ORIGIN
- [ ] DATABASE_URL
- [ ] EMAIL_ID
- [ ] EMAIL_PASS
- [ ] SMTP_SERVER
- [ ] SMTP_PORT

### B. Create Cloud SQL Database (if needed)
```bash
gcloud sql instances create pricesnapdb \
  --database-version=POSTGRES_15 \
  --region=us-central1 \
  --tier=db-f1-micro

gcloud sql databases create pricesnapdb \
  --instance=pricesnapdb

gcloud sql users create priceapp \
  --instance=pricesnapdb \
  --password=STRONG_PASSWORD
```
- [ ] PostgreSQL instance created
- [ ] Database created
- [ ] User created

### C. Configure Cloud SQL Proxy (if not using Cloud SQL)
- [ ] Ensure DATABASE_URL points to publicly accessible PostgreSQL

## Phase 5: GKE Setup (if using GKE) (20 minutes)

### A. Create GKE Cluster (if not exists)
```bash
gcloud container clusters create pricesnapcluster \
  --region=us-central1 \
  --num-nodes=2 \
  --machine-type=n1-standard-1 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=3
```
- [ ] GKE cluster created

### B. Create Namespaces
```bash
kubectl create namespace staging
kubectl create namespace production
```
- [ ] Namespaces created

### C. Add GKE Secrets
Go to **Settings → Secrets and variables → Actions** and add:
```
GKE_CLUSTER     # e.g., pricesnapcluster
GKE_ZONE        # e.g., us-central1-a
```
- [ ] GKE_CLUSTER
- [ ] GKE_ZONE

## Phase 6: Test the Workflows (5-10 minutes)

### Test 1: Lint & Test
```bash
git push origin develop
# or create a test PR
```
**Expected:** GitHub Actions runs, tests pass
- [ ] `lint-and-test.yml` passes

### Test 2: Docker Build
```bash
git push origin main
```
**Expected:** Image built and pushed to GHCR
- [ ] `build-docker.yml` completes
- [ ] Image visible in GitHub Packages

### Test 3: Manual Deployment
- Go to **Actions → Deploy to Cloud Run → Run workflow**
- Select environment: **staging**
- Confirm deployment

**Expected:** Service deployed and health check passes
- [ ] Deployment succeeds
- [ ] Health check passes
- [ ] Service is live

### Test 4: Verify Service
```bash
# Get Cloud Run URL from workflow logs
curl -f https://SERVICE_URL/api/health

# Expected output: {"status": "healthy"}
```
- [ ] `/api/health` responds with 200 OK

## Phase 7: Configure Branch Protection (5 minutes)

Go to **Settings → Branches → Branch protection rules** for `main`:
- [ ] Require status checks to pass before merging
  - [ ] check: `lint-and-test`
  - [ ] check: `build-docker`
  - [ ] check: `security-scan`
- [ ] Require branches to be up to date before merging
- [ ] Require code reviews before merging (recommended)
- [ ] Dismiss stale pull request approvals when new commits are pushed

## Phase 8: Documentation & Handoff (5 minutes)

- [ ] README.md updated with CI/CD section
- [ ] Team informed of new workflows
- [ ] Slack webhook configured (if applicable)
- [ ] Cost alerts set up in GCP
- [ ] On-call runbook created (`.github/DEPLOYMENT_PLAYBOOK.md` serves as reference)

---

## Verification Checklist

After completing all phases, verify:

- [ ] Actions tab shows all 6 workflows
- [ ] GitHub Packages contains at least one image
- [ ] GCP Artifact Registry contains image
- [ ] Cloud Run / GKE service is running
- [ ] `/api/health` endpoint responds
- [ ] Slack notifications work (if configured)
- [ ] Security scans run weekly

---

## Rollback Instructions (if needed)

If something goes wrong:

```bash
# Remove workflows (temporary)
git rm .github/workflows/*.yml
git commit -m "ci: temporarily disable workflows"
git push origin main

# Fix issues, then restore
git restore .github/workflows/
git commit -m "ci: restore workflows"
git push origin main
```

---

## Support Resources

- **Workflow Details:** `.github/workflows/` (inline comments)
- **Setup Guide:** `.github/GITHUB_ACTIONS_SETUP.md`
- **Quick Reference:** `.github/CI-CD-CHEATSHEET.md`
- **Deployment Guide:** `.github/DEPLOYMENT_PLAYBOOK.md`
- **Implementation Notes:** `.github/IMPLEMENTATION_SUMMARY.md`

---

**Estimated Total Time:** ~1.5 hours (first-time setup)  
**Ongoing Maintenance:** ~5 minutes/month (Dependabot updates)
