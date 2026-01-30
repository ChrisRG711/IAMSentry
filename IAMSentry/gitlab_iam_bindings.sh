#!/bin/bash

# GitLab Service Account IAM Role Bindings
# Apply minimal required roles for GitLab CI/CD deployments

PROJECT_ID="foiply-app"
GITLAB_SA1="serviceAccount:gitlab@foiply-app.iam.gserviceaccount.com"
GITLAB_SA2="serviceAccount:gitlab-5318ef1768e1a92506f3bd@foiply-app.iam.gserviceaccount.com"

echo "Applying IAM roles for GitLab service accounts..."

# Roles to apply to both GitLab service accounts
ROLES=(
    "roles/artifactregistry.writer"
    "roles/cloudbuild.builds.editor"
    "roles/gkehub.gatewayAdmin"
    "roles/iam.workloadIdentityUser"
    "roles/storage.objectAdmin"
    "roles/serviceusage.serviceUsageConsumer"
)

# Apply roles to first GitLab service account
echo "Configuring roles for: $GITLAB_SA1"
for role in "${ROLES[@]}"; do
    echo "  Adding role: $role"
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="$GITLAB_SA1" \
        --role="$role"
done

echo ""

# Apply roles to second GitLab service account
echo "Configuring roles for: $GITLAB_SA2"
for role in "${ROLES[@]}"; do
    echo "  Adding role: $role"
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="$GITLAB_SA2" \
        --role="$role"
done

echo ""
echo "IAM role bindings completed!"
echo ""
echo "To verify the bindings, run:"
echo "gcloud projects get-iam-policy $PROJECT_ID --flatten=\"bindings[].members\" --format=\"table(bindings.role)\" --filter=\"bindings.members:gitlab\""

# Optional: Remove overly permissive roles if they exist
echo ""
echo "# OPTIONAL: Remove overly permissive roles (run these manually after verification):"
echo "# gcloud projects remove-iam-policy-binding $PROJECT_ID --member=\"$GITLAB_SA1\" --role=\"roles/compute.admin\""
echo "# gcloud projects remove-iam-policy-binding $PROJECT_ID --member=\"$GITLAB_SA2\" --role=\"roles/compute.admin\""
echo "# gcloud projects remove-iam-policy-binding $PROJECT_ID --member=\"$GITLAB_SA1\" --role=\"roles/gkehub.admin\""
echo "# gcloud projects remove-iam-policy-binding $PROJECT_ID --member=\"$GITLAB_SA2\" --role=\"roles/gkehub.admin\""