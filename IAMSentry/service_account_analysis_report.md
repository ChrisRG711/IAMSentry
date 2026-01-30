Analyzing service accounts from: iam_recommendations_results.json
# Service Account IAM Optimization Report
============================================================
Analyzed 51 service accounts
Total current role assignments: 121
Total recommended removals: 121
Potential reduction: 100.0%

## Application Service (18 accounts)
--------------------------------------------------

### documo-app@foiply-app.iam.gserviceaccount.com
**Current Roles (5):**
  - roles/cloudsql.client (Specialized Function)
  - roles/compute.admin (Administrative Access)
  - roles/container.developer (Specialized Function)
  - roles/logging.viewer (Read-Only Access)
  - roles/networkmanagement.admin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/compute.admin (Administrative Access)
  - roles/container.developer (Specialized Function)
  - roles/logging.viewer (Read-Only Access)
  - roles/networkmanagement.admin (Administrative Access)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### documo-dev-ko@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/storage.objectAdmin (Administrative Access)
  - roles/storage.objectCreator (Storage Operations)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectAdmin (Administrative Access)
  - roles/storage.objectCreator (Storage Operations)
**Usage Analysis:**
  - This role has not been used during the observation window.

### documo-devops-gsm@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/secretmanager.admin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/secretmanager.admin (Administrative Access)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### documo-gcs-backup-sync@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.admin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/storage.admin (Administrative Access)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - Replace the current role with a smaller role to cover the permissions needed.

### documo-qa-sftp@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.admin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/storage.admin (Administrative Access)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### foiply-app@appspot.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectAdmin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectAdmin (Administrative Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-converter-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/secretmanager.secretAccessor (Secret Management)
**RECOMMENDED REMOVALS:**
  - roles/secretmanager.secretAccessor (Secret Management)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-documo-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-faxbridge-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/artifactregistry.reader (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-faxengine-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-fusion-operarius-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/secretmanager.secretAccessor (Secret Management)
**RECOMMENDED REMOVALS:**
  - roles/secretmanager.secretAccessor (Secret Management)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-fusion-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/container.admin (Administrative Access)
  - roles/secretmanager.secretAccessor (Secret Management)
**RECOMMENDED REMOVALS:**
  - roles/container.admin (Administrative Access)
  - roles/secretmanager.secretAccessor (Secret Management)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-fusion-worker-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/secretmanager.secretAccessor (Secret Management)
**RECOMMENDED REMOVALS:**
  - roles/secretmanager.secretAccessor (Secret Management)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-fusion@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/container.admin (Administrative Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectAdmin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/container.admin (Administrative Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectAdmin (Administrative Access)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-gotenberg-chromium-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/artifactregistry.reader (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-gotenberg-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/artifactregistry.reader (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-portal@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/container.admin (Administrative Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectAdmin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/container.admin (Administrative Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectAdmin (Administrative Access)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gsa-xfs-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudsql.instanceUser (Standard User Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/secretmanager.secretAccessor (Secret Management)
**RECOMMENDED REMOVALS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudsql.instanceUser (Standard User Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/secretmanager.secretAccessor (Secret Management)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - Replace the current role with a smaller role to cover the permissions needed.

## CI/CD - GitLab (2 accounts)
--------------------------------------------------

### gitlab-5318ef1768e1a92506f3bd@foiply-app.iam.gserviceaccount.com
**Current Roles (9):**
  - roles/artifactregistry.writer (Container/Artifact Management)
  - roles/cloudbuild.builds.editor (Read/Write Access)
  - roles/compute.admin (Administrative Access)
  - roles/gkehub.admin (Administrative Access)
  - roles/gkehub.gatewayAdmin (Administrative Access)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/serviceusage.serviceUsageConsumer (Specialized Function)
  - roles/storage.objectAdmin (Administrative Access)
  - roles/storage.objectUser (Standard User Access)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.writer (Container/Artifact Management)
  - roles/cloudbuild.builds.editor (Read/Write Access)
  - roles/compute.admin (Administrative Access)
  - roles/gkehub.admin (Administrative Access)
  - roles/gkehub.gatewayAdmin (Administrative Access)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/serviceusage.serviceUsageConsumer (Specialized Function)
  - roles/storage.objectAdmin (Administrative Access)
  - roles/storage.objectUser (Standard User Access)
**SUGGESTED REPLACEMENTS:**
  - roles/artifactregistry.writer (Container/Artifact Management)
  - roles/cloudbuild.builds.editor (Read/Write Access)
  - roles/container.developer (Specialized Function)
  - roles/iam.workloadIdentityUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - Replace the current role with a smaller role to cover the permissions needed.

### gitlab@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/cloudbuild.builds.editor (Read/Write Access)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/cloudbuild.builds.editor (Read/Write Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

## Certificate Management (1 accounts)
--------------------------------------------------

### cert-manager@documo-development.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/dns.admin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/dns.admin (Administrative Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

## Data Collection (1 accounts)
--------------------------------------------------

### collector@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/cloudfunctions.invoker (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/monitoring.metricsScopesViewer (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/cloudfunctions.invoker (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/monitoring.metricsScopesViewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

## Database Management (2 accounts)
--------------------------------------------------

### cloud-sql@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectAdmin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectAdmin (Administrative Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### cloudsql-read-only@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudsql.instanceUser (Standard User Access)
**RECOMMENDED REMOVALS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudsql.instanceUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

## Development/DevOps (3 accounts)
--------------------------------------------------

### dan-kott-workstation@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/container.admin (Administrative Access)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/storage.objectAdmin (Administrative Access)
  - roles/workstations.admin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/container.admin (Administrative Access)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/storage.objectAdmin (Administrative Access)
  - roles/workstations.admin (Administrative Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### devops-workstations@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/editor (Read/Write Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/secretmanager.admin (Administrative Access)
  - roles/workstations.serviceAgent (Specialized Function)
**RECOMMENDED REMOVALS:**
  - roles/editor (Read/Write Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/secretmanager.admin (Administrative Access)
  - roles/workstations.serviceAgent (Specialized Function)
**Usage Analysis:**
  - This role has not been used during the observation window.

### ubuntu-workstation@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/compute.serviceAgent (Compute Resources)
  - roles/config.agent (Specialized Function)
  - roles/iam.serviceAccountUser (Standard User Access)
**RECOMMENDED REMOVALS:**
  - roles/compute.serviceAgent (Compute Resources)
  - roles/config.agent (Specialized Function)
  - roles/iam.serviceAccountUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

## Environment-Specific (2 accounts)
--------------------------------------------------

### xfs-production@foiply-app.iam.gserviceaccount.com
**Current Roles (6):**
  - roles/composer.environmentAndStorageObjectUser (Standard User Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.secretVersionManager (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/composer.environmentAndStorageObjectUser (Standard User Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.secretVersionManager (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### xfs-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (7):**
  - roles/composer.environmentAndStorageObjectUser (Standard User Access)
  - roles/container.defaultNodeServiceAccount (Specialized Function)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.secretVersionManager (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/composer.environmentAndStorageObjectUser (Standard User Access)
  - roles/container.defaultNodeServiceAccount (Specialized Function)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.secretVersionManager (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

## File Transfer/Communication (1 accounts)
--------------------------------------------------

### sftp-sa@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectCreator (Storage Operations)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectCreator (Storage Operations)
**Usage Analysis:**
  - This role has not been used during the observation window.

## Infrastructure/Compute (3 accounts)
--------------------------------------------------

### 105005824641-compute@developer.gserviceaccount.com
**Current Roles (4):**
  - roles/clouddeploy.releaser (Specialized Function)
  - roles/container.developer (Specialized Function)
  - roles/eventarc.eventReceiver (Specialized Function)
  - roles/remotebuildexecution.artifactViewer (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/clouddeploy.releaser (Specialized Function)
  - roles/container.developer (Specialized Function)
  - roles/eventarc.eventReceiver (Specialized Function)
  - roles/remotebuildexecution.artifactViewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gke-artifact-puller@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/artifactregistry.reader (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### gke-limited@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/cloudfunctions.invoker (Specialized Function)
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudtrace.agent (Specialized Function)
  - roles/run.invoker (Specialized Function)
**RECOMMENDED REMOVALS:**
  - roles/cloudfunctions.invoker (Specialized Function)
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudtrace.agent (Specialized Function)
  - roles/run.invoker (Specialized Function)
**Usage Analysis:**
  - This role has not been used during the observation window.

## Monitoring/Security (3 accounts)
--------------------------------------------------

### datadog-118@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/cloudasset.viewer (Read-Only Access)
  - roles/compute.viewer (Read-Only Access)
  - roles/monitoring.viewer (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/cloudasset.viewer (Read-Only Access)
  - roles/compute.viewer (Read-Only Access)
  - roles/monitoring.viewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### grafana-gcp-service-account@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/logging.viewer (Read-Only Access)
  - roles/monitoring.viewer (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/logging.viewer (Read-Only Access)
  - roles/monitoring.viewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### tenable-io@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/compute.viewer (Read-Only Access)
  - roles/logging.viewer (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/compute.viewer (Read-Only Access)
  - roles/logging.viewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

## Other/Unknown (8 accounts)
--------------------------------------------------

### data-discovery-service-account@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/documentai.editor (Read/Write Access)
  - roles/storage.objectUser (Standard User Access)
**RECOMMENDED REMOVALS:**
  - roles/documentai.editor (Read/Write Access)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### marko-report-bot@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectCreator (Storage Operations)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectCreator (Storage Operations)
**Usage Analysis:**
  - This role has not been used during the observation window.

### openemr-787@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/compute.admin (Administrative Access)
  - roles/config.agent (Specialized Function)
  - roles/iam.serviceAccountUser (Standard User Access)
**RECOMMENDED REMOVALS:**
  - roles/compute.admin (Administrative Access)
  - roles/config.agent (Specialized Function)
  - roles/iam.serviceAccountUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### openemr@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/compute.admin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/compute.admin (Administrative Access)
**Usage Analysis:**
  - Replace the current role with a smaller role to cover the permissions needed.

### rp-csm-cnah9bt9cnna1iqe201g@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - projects/foiply-app/roles/redpandaConnectorsCnah9bt9cnna1iqe201gJ1lp (Specialized Function)
**RECOMMENDED REMOVALS:**
  - projects/foiply-app/roles/redpandaConnectorsCnah9bt9cnna1iqe201gJ1lp (Specialized Function)
**Usage Analysis:**
  - This role has not been used during the observation window.

### sandratest@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/container.developer (Specialized Function)
**RECOMMENDED REMOVALS:**
  - roles/container.developer (Specialized Function)
**Usage Analysis:**
  - This role has not been used during the observation window.

### service-105005824641@containerregistry.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/editor (Read/Write Access)
**RECOMMENDED REMOVALS:**
  - roles/editor (Read/Write Access)
**Usage Analysis:**
  - Replace OEV role with service agent role and other curated roles.

### test-nick@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/storage.objectUser (Standard User Access)
**RECOMMENDED REMOVALS:**
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

## Secret Management (2 accounts)
--------------------------------------------------

### xfs-production-secrets-manager@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - Replace the current role with a smaller role to cover the permissions needed.

### xfs-secret-manager-sa@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - Replace the current role with a smaller role to cover the permissions needed.

## Serverless/Functions (2 accounts)
--------------------------------------------------

### cloud-functions@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/cloudfunctions.admin (Administrative Access)
  - roles/cloudfunctions.invoker (Specialized Function)
  - roles/logging.logWriter (Specialized Function)
  - roles/run.invoker (Specialized Function)
**RECOMMENDED REMOVALS:**
  - roles/cloudfunctions.admin (Administrative Access)
  - roles/cloudfunctions.invoker (Specialized Function)
  - roles/logging.logWriter (Specialized Function)
  - roles/run.invoker (Specialized Function)
**Usage Analysis:**
  - This role has not been used during the observation window.

### firebase-service-account@firebase-sa-management.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/firebase.managementServiceAgent (Specialized Function)
**RECOMMENDED REMOVALS:**
  - roles/firebase.managementServiceAgent (Specialized Function)
**Usage Analysis:**
  - This role has not been used during the observation window.

## Storage Management (3 accounts)
--------------------------------------------------

### gcs-object-admin@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectAdmin (Administrative Access)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectAdmin (Administrative Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### prod-faxstorage-buckets-sa@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectViewer (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectViewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.

### staging-buckets-sa@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectViewer (Read-Only Access)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectViewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
