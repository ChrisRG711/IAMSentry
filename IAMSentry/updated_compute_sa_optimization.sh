#!/bin/bash

# Updated script for 105005824641-compute@developer.gserviceaccount.com
# Based on FRESH data showing actual permission usage (6/458 permissions used)

PROJECT_ID="foiply-app"
SERVICE_ACCOUNT="serviceAccount:105005824641-compute@developer.gserviceaccount.com"

echo "Optimizing Compute Engine service account based on FRESH usage data..."
echo "Service Account: $SERVICE_ACCOUNT"
echo "Current: 8 roles, 458 permissions, 6 permissions actually used (1.3%)"
echo ""

# Backup current IAM policy
echo "📋 Creating backup of current IAM policy..."
BACKUP_FILE="iam-policy-backup-compute-sa-$(date +%Y%m%d-%H%M%S).json"
gcloud projects get-iam-policy $PROJECT_ID > "$BACKUP_FILE"
echo "✅ Backup saved to: $BACKUP_FILE"
echo ""

echo "🔍 Current roles for this service account:"
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:105005824641-compute@developer.gserviceaccount.com"
echo ""

# Roles to KEEP (showing actual usage)
KEEP_ROLES=(
    "roles/artifactregistry.reader"
    "roles/logging.logWriter" 
    "roles/monitoring.metricWriter"
)

# Roles to REMOVE (0% usage in fresh data)
REMOVE_ROLES=(
    "roles/clouddeploy.releaser"
    "roles/container.developer"
    "roles/eventarc.eventReceiver"
    "roles/clouddeploy.jobRunner"
    "roles/remotebuildexecution.artifactViewer"
)

echo "🟢 KEEPING these roles (showing actual usage):"
for role in "${KEEP_ROLES[@]}"; do
    echo "  ✅ $role"
done
echo ""

echo "🔴 REMOVING these roles (0% usage):"
for role in "${REMOVE_ROLES[@]}"; do
    echo "  🗑️  $role"
    
    if gcloud projects remove-iam-policy-binding $PROJECT_ID \
        --member="$SERVICE_ACCOUNT" \
        --role="$role" \
        --quiet; then
        echo "     ✅ Successfully removed: $role"
    else
        echo "     ⚠️  Failed to remove or already removed: $role"
    fi
done
echo ""

echo "🔍 Verifying final state:"
FINAL_ROLES=$(gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --format="value(bindings.role)" \
    --filter="bindings.members:105005824641-compute@developer.gserviceaccount.com")

echo "Remaining roles:"
echo "$FINAL_ROLES"
echo ""

echo "📈 Optimization Summary:"
echo "   - Started with: 8 roles, 458 permissions"
echo "   - Removed: ${#REMOVE_ROLES[@]} unused roles"
echo "   - Kept: ${#KEEP_ROLES[@]} actively used roles"
echo "   - Permission reduction: ~85% (from 458 to ~67 permissions)"
echo "   - Usage efficiency: From 1.3% to ~9% usage rate"
echo ""
echo "🔄 Rollback command if needed:"
echo "   gcloud projects set-iam-policy $PROJECT_ID $BACKUP_FILE"