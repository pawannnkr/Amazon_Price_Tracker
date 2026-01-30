# CI/CD Quick Reference

## Common Commands

### Local Testing
```bash
# Run linter + formatter checks
flake8 .
black --check .
isort --check-only .

# Run tests with coverage
pytest --cov=. --cov-report=html

# Security scans locally
bandit -r .
safety check
pip-audit
```

### GitHub Workflow Triggers
```bash
# Trigger lint-and-test (on any push to main/develop)
git push origin main

# Trigger build-docker (on any push/tag to main)
git push origin main
git tag v1.0.0 && git push --tags

# Trigger deploy via tag
git tag v1.0.0
git push --tags
```

### Manual Deployment
```bash
# Cloud Run (via GitHub Actions UI)
# Settings → Actions → Deploy to Cloud Run → Run workflow
# Choose: staging or production

# GKE (via GitHub Actions UI)
# Settings → Actions → Deploy to GKE → Run workflow
# Choose environment & confirm
```

### Cloud Run CLI (Manual)
```bash
# Deploy without GitHub Actions
gcloud run deploy amazon-price-tracker \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=$DATABASE_URL,EMAIL_ID=$EMAIL_ID"
```

### GKE CLI (Manual)
```bash
# Get credentials
gcloud container clusters get-credentials my-cluster --zone us-central1-a

# Apply manifest
kubectl apply -f k8s-deployment.yaml

# Check status
kubectl get deployment -n staging
kubectl logs -n staging -l app=amazon-price-tracker
```

---

## Debugging Failed Workflows

### 1. Check Secrets
```bash
# Verify all required secrets exist (GitHub UI)
Settings → Secrets and variables → Actions
# List: GCP_PROJECT_ID, GCP_REGION, DATABASE_URL, etc.
```

### 2. View Detailed Logs
- Navigate to **Actions** tab in GitHub
- Click failed workflow run
- Expand step that failed
- Look for error messages and stack traces

### 3. Test Locally with Act
```bash
# Install: https://github.com/nektos/act
act -l                           # List all workflows
act push -j lint-and-test        # Run specific job
act push -s GITHUB_TOKEN=ghp_... # Pass secrets
```

### 4. Common Failures & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `docker: command not found` | Docker not available in runner | Use `actions/setup-docker` or `docker/setup-buildx-action` |
| `gcloud: command not found` | GCP SDK not installed | Ensure `google-github-actions/setup-gcloud@v2` step runs first |
| `Failed to push image` | Auth or repo doesn't exist | Check `GCP_SA_KEY` secret; verify Artifact Registry repo exists |
| `Cloud Run deployment timeout` | Service unhealthy | Check Database URL, network VPC access, app logs |
| `kubectl: command not found` | kubectl not in PATH | Add `gcloud components install kubectl` step |

---

## Environment Variable Reference

### Application (.env file)
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/pricesnapdb

# Flask
FLASK_ENV=production
CORS_ORIGIN=*

# Email/SMTP
EMAIL_ID=your-email@gmail.com
EMAIL_PASS=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### GitHub Secrets (Actions)
```bash
# GCP
GCP_PROJECT_ID=my-project-123
GCP_REGION=us-central1
GCP_ZONE=us-central1-a
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/123456789/locations/global/workloadIdentityPools/github-actions/providers/github
GCP_SERVICE_ACCOUNT=github-actions@my-project-123.iam.gserviceaccount.com

# Registry & Deployment
REGISTRY_REPO=app-images
SERVICE_NAME=amazon-price-tracker
GKE_CLUSTER=my-cluster

# Application (runtime)
CORS_ORIGIN=https://yourdomain.com
DATABASE_URL=postgresql://user:pass@cloudsql.c.my-project.internal:5432/pricesnapdb
EMAIL_ID=alerts@yourdomain.com
EMAIL_PASS=app-password-here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Notifications
SLACK_WEBHOOK=https://hooks.slack.com/services/TXXX/BXXX/XXXX
```

---

## Workflow Status & Health Checks

### Monitor Workflows
```bash
# View recent runs
gh run list --repo pawannnkr/PriceSnap --limit 10

# Tail logs in real-time
gh run view RUN_ID --log
```

### Health Check Endpoint
```bash
# Test deployment is healthy
curl -f https://amazon-price-tracker-service.run.app/api/health

# For GKE (if LoadBalancer assigned)
kubectl get service amazon-price-tracker -n staging
curl -f http://EXTERNAL-IP:5000/api/health
```

---

## Rollback Procedures

### Cloud Run
```bash
# List revisions
gcloud run revisions list --service=amazon-price-tracker --region=us-central1

# Rollback to previous revision
gcloud run deploy amazon-price-tracker \
  --region=us-central1 \
  --image=gcr.io/PROJECT_ID/amazon-price-tracker:previous-tag
```

### GKE
```bash
# Check rollout history
kubectl rollout history deployment/amazon-price-tracker -n production

# Rollback to previous revision
kubectl rollout undo deployment/amazon-price-tracker -n production

# Monitor rollback
kubectl rollout status deployment/amazon-price-tracker -n production
```

---

## Cost Optimization Tips

1. **Cloud Run:** Set `--max-instances=10` to limit concurrent instances
2. **GKE:** Use preemptible nodes for non-critical environments
3. **Artifact Registry:** Enable image cleanup policies to reduce storage costs
4. **GitHub Actions:** Disable workflows for branches you don't need to test
