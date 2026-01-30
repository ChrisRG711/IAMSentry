# IAMSentry Overwatch Integration

## Implementation Log

**Date:** 2026-01-27
**Status:** Deployed

**Deployed Revision:** `overwatch-00005-55n`

---

## Deployment Info

- **Service URL:** https://overwatch-105005824641.us-central1.run.app
- **Intranet URL:** https://intranet.documo.dev/overwatch/
- **Access:** Restricted to `devops@documo.com` via IAP + app-level check
- **Service Account:** `105005824641-compute@developer.gserviceaccount.com`

---

## What Was Done

### 1. Added IAM Health Tab to Overwatch

**Files Modified:**

| File | Change |
|------|--------|
| `intranet/overwatch/static/index.html` | Added nav button and tab content section |
| `intranet/overwatch/static/app.js` | Added JavaScript functions for loading/rendering IAM data |
| `intranet/overwatch/static/styles.css` | Added CSS styles for IAM components |
| `intranet/overwatch/app.py` | Added `/api/iam/stats` and `/api/iam/recommendations` endpoints |

### 2. Features Implemented

- **Stats Cards**: Total recommendations, High/Medium/Low risk counts
- **Breakdown Charts**: By account type (service accounts, users, groups) and by action type (remove, replace)
- **Recommendations Table**: Filterable by type and action, sortable by priority
- **Detail View**: Click to see full recommendation details
- **Caching**: 30-minute TTL cache for IAM data with force refresh option

### 3. Caching Implementation

- **Default TTL**: 30 minutes (configurable via `IAM_CACHE_TTL` environment variable)
- **Force Refresh**: Click "Refresh" button or add `?refresh=true` to API calls
- **Cache Info Display**: Shows when data was last refreshed in the UI header

### 4. API Endpoints Added

```
GET /overwatch/api/iam/stats[?refresh=true]
- Returns: total, by_subtype, by_priority, by_member_type, cache_info
- Add ?refresh=true to bypass cache and fetch fresh data

GET /overwatch/api/iam/recommendations[?refresh=true]
- Returns: list of recommendations with member, role, action, priority
- Add ?refresh=true to bypass cache and fetch fresh data
```

---

## What's Left To Do

- [x] Deploy updated Overwatch to Cloud Run
- [x] Add caching (30-minute TTL with force refresh)
- [ ] Test with production IAM data
- [ ] Add remediation modal (dry-run first)
- [ ] Add trend tracking (store scan results over time)
- [ ] Add export to CSV functionality

---

## How to Roll Back

### Option 1: Git Revert (Recommended)

```bash
cd /home/chris/git/devops

# View the changes
git diff intranet/overwatch/

# Revert all changes to Overwatch
git checkout -- intranet/overwatch/static/index.html
git checkout -- intranet/overwatch/static/app.js
git checkout -- intranet/overwatch/static/styles.css
git checkout -- intranet/overwatch/app.py
```

### Option 2: Restore from Backup

If committed, revert the commit:
```bash
git log --oneline intranet/overwatch/ -5  # Find the commit
git revert <commit-hash>
```

### Option 3: Manual Removal

1. **index.html**: Remove the `<button>` with `data-tab="iam-health"` and the entire `<section id="tab-iam-health">` block
2. **app.js**: Remove `iamRecommendations` and `iamStats` variables, remove `case 'iam-health':` from switch, remove all IAM HEALTH functions
3. **styles.css**: Remove everything under `/* IAM HEALTH STYLES */` comment
4. **app.py**: Remove the `# IAM HEALTH API` section with both endpoints

---

## Testing Locally

```bash
# Terminal 1: Start Overwatch locally
cd /home/chris/git/devops/intranet/overwatch
DEV_MODE=1 DEV_USER=chris.geier@documo.com python app.py

# Terminal 2: Test the APIs
curl http://localhost:8080/overwatch/api/iam/stats | jq
curl http://localhost:8080/overwatch/api/iam/recommendations | jq

# Open browser
open http://localhost:8080/overwatch/
```

---

## Deployment

```bash
# Build and deploy Overwatch
cd /home/chris/git/devops/intranet/overwatch

# Build container image
gcloud builds submit --tag us-central1-docker.pkg.dev/foiply-app/intranet/overwatch:latest --project=foiply-app

# Deploy to Cloud Run
gcloud run deploy overwatch \
  --image=us-central1-docker.pkg.dev/foiply-app/intranet/overwatch:latest \
  --region=us-central1 \
  --project=foiply-app \
  --service-account=105005824641-compute@developer.gserviceaccount.com \
  --ingress=internal-and-cloud-load-balancing
```

---

## Architecture

```
User → Overwatch UI → /api/iam/stats → In-Memory Cache (30m TTL) → gcloud recommender → GCP IAM Recommender API
                    → /api/iam/recommendations
```

Data is cached in-memory for 30 minutes. Use the Refresh button to force a fresh fetch from GCP.

---

## Related Files

- Original IAMSentry dashboard: `IAMSentry/IAMSentry/dashboard/server.py`
- IAMSentry output data: `IAMSentry/output/`
- IAM security workflow: `docs/runbooks/iam-security-workflow.md`
