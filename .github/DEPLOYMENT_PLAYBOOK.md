# GitHub Actions Deployment Playbook

## Decision Tree: Which Deployment Path?

```
                    ┌─ Code Change ─┐
                    │                │
         ┌──────────┴────────────┬───┴─────────┐
         │                       │              │
    Bugfix/Feature         Prepare Release   Create Tag
         │                       │              │
         ↓                       ↓              ↓
    Push to                  Tag as           git push
    develop/main             v1.0.0           --tags
         │                       │              │
         ↓                       ↓              ↓
    ╔═════════════════╗  ╔═════════════════╗  ║
    ║ lint-and-test ║  ║  build-docker   ║  ║
    ║ (5-10 min)    ║  ║  (3-5 min)      ║  ║
    ╚═════════════════╝  ╚════════════════╝  ║
         │                       │              │
         │ (Pass)                │ (Push)      ║
         ↓                       ↓              ║
    Ready to merge         GHCR + GCP         ║
    (if PR)               Artifact Registry    ║
         │                       │              ║
         └───────────┬───────────┴──────────────╨─┐
                     │                            │
             Merge to main                   release.yml
             (auto deploy)              (GitHub Release)
                     │                            │
         ┌───────────┴───────────┐               │
         │                       │               │
    ┌─────────────┐      ┌──────────────┐      │
    │  Automated  │ or   │   Manual     │      │
    │             │      │   Dispatch   │      │
    └─────────────┘      └──────────────┘      │
         │                       │              │
    deploy-cloudrun.yml OR deploy-gke.yml      │
    (Build + Deploy + Health Check)            │
         │                                      │
         └──────────────┬───────────────────────┘
                        ↓
              ┌─────────────────────┐
              │  🎉 Live! 🎉       │
              │  Slack notification │
              └─────────────────────┘
```

---

## Common Deployment Scenarios

### Scenario 1: Regular Bugfix → Development
```bash
git checkout develop
git pull origin develop
# Make changes
git add .
git commit -m "fix: handle missing price data"
git push origin develop
```

**What runs:**
- ✅ `lint-and-test.yml` (Python 3.10, 3.11, 3.12)
- ✅ `security-scan.yml`
- ✅ `build-docker.yml` (GHCR image tagged `develop`)

**Next step:** Create PR to `main` when ready.

---

### Scenario 2: Code Ready for Production
```bash
git checkout main
git pull origin main
git merge develop  # Or use GitHub UI
git push origin main
```

**What runs automatically:**
- ✅ `lint-and-test.yml`
- ✅ `build-docker.yml` (GHCR image tagged `latest`)
- ✅ `deploy-cloudrun.yml` OR `deploy-gke.yml` (you choose via env secret)

**Result:** Live in staging environment within 10-15 minutes.

---

### Scenario 3: Production Release
```bash
git tag v1.2.3
git push --tags
```

**What runs:**
- ✅ `build-docker.yml` (tags: `v1.2.3`, `latest`)
- ✅ `release.yml` (creates GitHub Release page)
- ✅ Image pushed to GHCR + GCP Artifact Registry

**Manual step (if needed):**
```bash
# Trigger production deployment
gh workflow run deploy-cloudrun.yml \
  --ref main \
  --field environment=production
```

---

### Scenario 4: Hotfix (Emergency Fix)
```bash
git checkout main
git pull origin main

# Quick fix
echo "HOTFIX" > hotfix.txt
git add hotfix.txt
git commit -m "hotfix: critical bug"

# Tag immediately
git tag v1.2.4-hotfix.1
git push --tags
git push origin main
```

**Result:** v1.2.4-hotfix.1 released and deployed within 5 minutes.

---

## Deployment Rollout Strategies

### Strategy 1: Direct Deploy (Current)
```
Code → Tests → Build → Deploy
       ↓
    Pass? → Yes → Live immediately
      ↓ No
    Blocked
```
**Use for:** Staging, non-critical services
**Risk:** Low (tests catch issues)

### Strategy 2: Staged Rollout (Recommended for Production)
```
Code → Tests → Build → Deploy to Staging
                         ↓ (health check)
                    Manual Approval
                         ↓
                  Deploy to Production
```

**To implement:** Add manual approval step to Cloud Run deploy.

---

## Monitoring After Deployment

### Immediate (0-5 minutes)
```bash
# Cloud Run
gcloud run services describe amazon-price-tracker --region us-central1 | grep url
curl -f https://SERVICE_URL/api/health

# GKE
kubectl rollout status deployment/amazon-price-tracker -n staging
kubectl get pods -n staging
```

### Short-term (5-30 minutes)
```bash
# Check for errors in logs
gcloud run logs read amazon-price-tracker --limit 100

# Or for GKE
kubectl logs -n staging -l app=amazon-price-tracker --tail=100
```

### Continuous
```bash
# Set up Cloud Monitoring dashboard
# Metrics to track:
# - Request rate
# - Error rate
# - Latency (p50, p95, p99)
# - Database connection count
```

---

## Rollback Decision Tree

```
              Service Unhealthy?
                      ↓
            ┌─────────┴─────────┐
            ↓                   ↓
       Recent deploy?     Not recent deploy?
            │                   │
       Yes: Rollback         Investigate
            │                   │
     ┌──────┴──────┐            │
     ↓             ↓            │
  Cloud Run     GKE             │
     │             │            │
     ↓             ↓            │
 Option A      kubectl          └─ Fix code
 (1 cmd)       rollout undo        Redeploy
               (1 cmd)
```

### Cloud Run Rollback
```bash
# List recent revisions
gcloud run revisions list \
  --service=amazon-price-tracker \
  --region=us-central1 \
  --limit=5

# Deploy previous stable revision
PREVIOUS_IMAGE="gcr.io/PROJECT_ID/amazon-price-tracker:stable-tag"
gcloud run deploy amazon-price-tracker \
  --image=$PREVIOUS_IMAGE \
  --region=us-central1 \
  --quiet
```

### GKE Rollback
```bash
# View rollout history
kubectl rollout history deployment/amazon-price-tracker -n production

# Rollback to previous
kubectl rollout undo deployment/amazon-price-tracker -n production

# Monitor rollback
kubectl rollout status deployment/amazon-price-tracker -n production --timeout=10m

# Or revert to specific revision
kubectl rollout undo deployment/amazon-price-tracker -n production --to-revision=3
```

---

## Pre-Deployment Checklist

Before pushing to `main`:

- [ ] All tests pass locally: `pytest --cov`
- [ ] No linting errors: `flake8 .` + `black --check .`
- [ ] Database migrations reviewed (if any)
- [ ] Environment variables documented in README
- [ ] Updated `.github/copilot-instructions.md` if architecture changed
- [ ] CHANGELOG entry added (for releases)
- [ ] Slack webhook configured (if using notifications)

---

## Incident Response

### Service Down
```bash
# 1. Check status immediately
gcloud run services describe amazon-price-tracker --region us-central1 | grep serving

# 2. View logs
gcloud run logs read amazon-price-tracker --limit=100 | grep -i error

# 3. Check database connectivity
echo "SELECT 1;" | psql $DATABASE_URL

# 4. Rollback if recent deploy caused it
kubectl rollout undo deployment/amazon-price-tracker

# 5. Post-incident review
# - What failed?
# - Why didn't tests catch it?
# - How to prevent next time?
```

### High Error Rate
```bash
# 1. Identify error pattern
gcloud run logs read amazon-price-tracker --limit=500 | grep ERROR | head -20

# 2. Scale down if under attack
gcloud run deploy amazon-price-tracker --max-instances=5

# 3. Revert recent changes
git log --oneline -5
git revert COMMIT_HASH

# 4. Push hotfix
git push origin main
```

---

## Cost Optimization During Deployment

| Action | Cost Impact | Recommendation |
|--------|-------------|-----------------|
| Keep max-instances=100 | High | Reduce to 10 or auto-scale |
| Large GKE cluster idle | High | Use preemptible nodes for staging |
| Multiple image layers | Medium | Use `.dockerignore` to slim image |
| Daily full scans | Low | Run weekly; on-demand via dispatch |

---

## Contact & Escalation

| Issue | Channel | SLA |
|-------|---------|-----|
| Workflow not triggering | Check repo settings | N/A |
| Deployment fails | Check action logs | 30 min |
| Service unhealthy | Slack alert | 15 min |
| Security vulnerability | GitHub Security tab | 24 hours |
