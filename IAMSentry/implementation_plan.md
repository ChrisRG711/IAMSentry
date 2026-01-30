# Service Account IAM Optimization Implementation Plan

## Executive Summary
- **51 service accounts** analyzed
- **121 role assignments** currently active  
- **121 roles recommended for removal** (100% optimization potential)
- Most accounts have **zero permission usage** in 90-day observation window

## Key Findings
1. **Over-privileged accounts**: Many service accounts have admin roles but show 0% usage
2. **Broad permissions**: Admin roles assigned when specific functionality needed
3. **Unused accounts**: Several accounts appear inactive during observation period
4. **Optimization opportunity**: Significant security improvement possible

## Implementation Strategy

### Phase 1: High-Risk Admin Role Removals (Immediate)
Remove admin roles from accounts with 0% usage:

```bash
# GitLab CI/CD Optimization
gcloud projects remove-iam-policy-binding foiply-app \
  --member="serviceAccount:gitlab-5318ef1768e1a92506f3bd@foiply-app.iam.gserviceaccount.com" \
  --role="roles/compute.admin"

gcloud projects remove-iam-policy-binding foiply-app \
  --member="serviceAccount:gitlab-5318ef1768e1a92506f3bd@foiply-app.iam.gserviceaccount.com" \
  --role="roles/gkehub.admin"

# Replace with minimal CI/CD roles
gcloud projects add-iam-policy-binding foiply-app \
  --member="serviceAccount:gitlab-5318ef1768e1a92506f3bd@foiply-app.iam.gserviceaccount.com" \
  --role="roles/container.developer"

gcloud projects add-iam-policy-binding foiply-app \
  --member="serviceAccount:gitlab-5318ef1768e1a92506f3bd@foiply-app.iam.gserviceaccount.com" \
  --role="roles/gkehub.gatewayUser"
```

### Phase 2: Application Service Account Optimization

#### Storage-Related Accounts
Replace storage.admin with specific permissions:

```bash
# documo-gcs-backup-sync: Backup operations
gcloud projects remove-iam-policy-binding foiply-app \
  --member="serviceAccount:documo-gcs-backup-sync@foiply-app.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding foiply-app \
  --member="serviceAccount:documo-gcs-backup-sync@foiply-app.iam.gserviceaccount.com" \
  --role="roles/storage.objectCreator"

# documo-qa-sftp: SFTP file operations  
gcloud projects remove-iam-policy-binding foiply-app \
  --member="serviceAccount:documo-qa-sftp@foiply-app.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding foiply-app \
  --member="serviceAccount:documo-qa-sftp@foiply-app.iam.gserviceaccount.com" \
  --role="roles/storage.objectUser"
```

#### Secret Management Accounts
Replace secretmanager.admin with accessor:

```bash
# documo-devops-gsm: Secret access only
gcloud projects remove-iam-policy-binding foiply-app \
  --member="serviceAccount:documo-devops-gsm@foiply-app.iam.gserviceaccount.com" \
  --role="roles/secretmanager.admin"

gcloud projects add-iam-policy-binding foiply-app \
  --member="serviceAccount:documo-devops-gsm@foiply-app.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Phase 3: Custom Role Creation for High-Usage Accounts

#### Custom Role for Application Services
Create minimal application role:

```bash
gcloud iam roles create applicationMinimal \
  --project=foiply-app \
  --title="Application Minimal Role" \
  --description="Minimal permissions for application service accounts" \
  --permissions=cloudsql.instances.connect,secretmanager.versions.access,storage.objects.get,storage.objects.create
```

#### Custom Role for CI/CD
Create GitLab-specific role:

```bash
gcloud iam roles create gitlabCICD \
  --project=foiply-app \
  --title="GitLab CI/CD Role" \
  --description="Specific permissions for GitLab deployments" \
  --permissions=artifactregistry.repositories.uploadArtifacts,cloudbuild.builds.create,container.clusters.get,gkehub.memberships.get,iam.serviceAccounts.actAs
```

### Phase 4: Account Lifecycle Management

#### Unused Account Deactivation
Accounts with 0% usage and no recent activity:

```bash
# Disable unused accounts (review first)
gcloud iam service-accounts disable gsa-converter-staging@foiply-app.iam.gserviceaccount.com
gcloud iam service-accounts disable test-nick@foiply-app.iam.gserviceaccount.com
gcloud iam service-accounts disable sandratest@foiply-app.iam.gserviceaccount.com
```

## Category-Specific Recommendations

### CI/CD - GitLab (2 accounts)
- **Current**: Broad admin roles (compute.admin, gkehub.admin)
- **Recommended**: Specific deployment roles
- **Risk**: High - Admin access for automated systems

### Application Service (18 accounts)  
- **Current**: Mix of admin and specific roles
- **Recommended**: Application-minimal custom roles
- **Risk**: Medium - Over-privileged application access

### Storage Management (5 accounts)
- **Current**: storage.admin for most operations
- **Recommended**: storage.objectUser/objectCreator based on function
- **Risk**: Medium - Unnecessary write/delete permissions

### Monitoring/Security (4 accounts)
- **Current**: Some have unnecessary admin access
- **Recommended**: Read-only monitoring roles
- **Risk**: Low - Read-only sufficient for monitoring

## Validation Steps

### Pre-Implementation
1. **Backup current IAM policy**:
   ```bash
   gcloud projects get-iam-policy foiply-app > current-iam-policy-backup.json
   ```

2. **Test in staging environment first**

3. **Notify application teams** of pending changes

### Post-Implementation  
1. **Monitor application functionality** for 48 hours
2. **Check for permission denied errors** in logs
3. **Validate CI/CD pipelines** still function
4. **Review monitoring/alerting** continues to work

### Rollback Plan
```bash
# Quick rollback script
gcloud projects set-iam-policy foiply-app current-iam-policy-backup.json
```

## Expected Security Benefits
- **Reduced attack surface**: Eliminate unused admin privileges
- **Principle of least privilege**: Match permissions to actual usage
- **Improved compliance**: Better alignment with security frameworks
- **Audit readiness**: Clear purpose for each permission grant

## Timeline
- **Week 1**: Phase 1 (High-risk admin removals)
- **Week 2**: Phase 2 (Application optimizations)  
- **Week 3**: Phase 3 (Custom role implementation)
- **Week 4**: Phase 4 (Lifecycle management)

## Success Metrics
- Reduction in admin role assignments: Target 80%+
- Zero production incidents from permission changes
- Improved security scan scores
- Faster access reviews due to clearer role purposes