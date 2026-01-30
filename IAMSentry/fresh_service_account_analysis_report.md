Analyzing service accounts from: fresh_iam_recommendations_results.json
# Service Account IAM Optimization Report
============================================================
Analyzed 52 service accounts
Total current role assignments: 152
Total recommended removals: 104
Potential reduction: 68.4%

## Application Service (17 accounts)
--------------------------------------------------

### documo-app@foiply-app.iam.gserviceaccount.com
**Current Roles (8):**
  - roles/certificatemanager.editor (Read/Write Access)
  - roles/cloudsql.client (Specialized Function)
  - roles/compute.admin (Administrative Access)
  - roles/container.developer (Specialized Function)
  - roles/documentai.admin (Administrative Access)
  - roles/logging.viewer (Read-Only Access)
  - roles/networkmanagement.admin (Administrative Access)
  - roles/storage.admin (Administrative Access)
**Permission Usage:** 21/1584 (1.3%)
**Actually Used Permissions (21):**
  - certificatemanager.certmapentries.create
  - certificatemanager.certmapentries.get
  - certificatemanager.certmaps.create
  - certificatemanager.certmaps.get
  - certificatemanager.certs.create
  - certificatemanager.certs.get
  - certificatemanager.certs.use
  - certificatemanager.dnsauthorizations.create
  - certificatemanager.dnsauthorizations.get
  - certificatemanager.dnsauthorizations.list
  - certificatemanager.dnsauthorizations.use
  - certificatemanager.operations.get
  - documentai.processors.processBatch
  - documentai.processors.processOnline
  - storage.objects.create
  - storage.objects.delete
  - storage.objects.get
  - storage.objects.getIamPolicy
  - storage.objects.list
  - storage.objects.setIamPolicy
  - storage.objects.update
**RECOMMENDED REMOVALS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/compute.admin (Administrative Access)
  - roles/container.developer (Specialized Function)
  - roles/logging.viewer (Read-Only Access)
  - roles/networkmanagement.admin (Administrative Access)
**KEEP THESE ROLES:**
  - roles/certificatemanager.editor (Read/Write Access)
  - roles/documentai.admin (Administrative Access)
  - roles/storage.admin (Administrative Access)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 12 of the permissions in this role binding were used in the past 64 days.
  - 7 of the permissions in this role binding were used in the past 90 days.
  - 2 of the permissions in this role binding were used in the past 90 days.

### documo-dev-ko@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/storage.admin (Administrative Access)
  - roles/storage.objectAdmin (Administrative Access)
  - roles/storage.objectCreator (Storage Operations)
**Permission Usage:** 1/115 (0.9%)
**Actually Used Permissions (1):**
  - storage.buckets.get
**RECOMMENDED REMOVALS:**
  - roles/storage.objectAdmin (Administrative Access)
  - roles/storage.objectCreator (Storage Operations)
**KEEP THESE ROLES:**
  - roles/storage.admin (Administrative Access)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 1 specific permissions
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.

### documo-devops-gsm@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/secretmanager.admin (Administrative Access)
**Permission Usage:** 0/31 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/secretmanager.admin (Administrative Access)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### documo-gcs-backup-sync@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.admin (Administrative Access)
**Permission Usage:** 1/78 (1.3%)
**Actually Used Permissions (1):**
  - storage.objects.list
**RECOMMENDED REMOVALS:**
  - roles/storage.admin (Administrative Access)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 1 specific permissions
**Usage Analysis:**
  - Replace the current role with a smaller role to cover the permissions needed.
  - 1 of the permissions in this role binding were used in the past 90 days.

### documo-qa-sftp@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.admin (Administrative Access)
**Permission Usage:** 0/78 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/storage.admin (Administrative Access)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### foiply-app@appspot.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectAdmin (Administrative Access)
**Permission Usage:** 0/28 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectAdmin (Administrative Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### gsa-converter-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/secretmanager.secretAccessor (Secret Management)
**Permission Usage:** 4/42 (9.5%)
**Actually Used Permissions (4):**
  - artifactregistry.repositories.downloadArtifacts
  - logging.logEntries.create
  - monitoring.metricDescriptors.create
  - monitoring.timeSeries.create
**RECOMMENDED REMOVALS:**
  - roles/secretmanager.secretAccessor (Secret Management)
**KEEP THESE ROLES:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 4 specific permissions
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 2 of the permissions in this role binding were used in the past 90 days.

### gsa-documo-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**Permission Usage:** 0/39 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### gsa-faxbridge-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**Permission Usage:** 3/39 (7.7%)
**Actually Used Permissions (3):**
  - logging.logEntries.create
  - monitoring.metricDescriptors.create
  - monitoring.timeSeries.create
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
**KEEP THESE ROLES:**
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 3 specific permissions
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 2 of the permissions in this role binding were used in the past 90 days.

### gsa-faxengine-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**Permission Usage:** 0/39 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### gsa-fusion-operarius-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/secretmanager.secretAccessor (Secret Management)
**Permission Usage:** 4/42 (9.5%)
**Actually Used Permissions (4):**
  - artifactregistry.repositories.downloadArtifacts
  - logging.logEntries.create
  - monitoring.metricDescriptors.create
  - monitoring.timeSeries.create
**RECOMMENDED REMOVALS:**
  - roles/secretmanager.secretAccessor (Secret Management)
**KEEP THESE ROLES:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 4 specific permissions
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 2 of the permissions in this role binding were used in the past 90 days.

### gsa-fusion-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (5):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/container.admin (Administrative Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/secretmanager.secretAccessor (Secret Management)
**Permission Usage:** 4/471 (0.8%)
**Actually Used Permissions (4):**
  - artifactregistry.repositories.downloadArtifacts
  - logging.logEntries.create
  - monitoring.metricDescriptors.create
  - monitoring.timeSeries.create
**RECOMMENDED REMOVALS:**
  - roles/container.admin (Administrative Access)
  - roles/secretmanager.secretAccessor (Secret Management)
**KEEP THESE ROLES:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 4 specific permissions
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 2 of the permissions in this role binding were used in the past 90 days.

### gsa-fusion-worker-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/secretmanager.secretAccessor (Secret Management)
**Permission Usage:** 4/42 (9.5%)
**Actually Used Permissions (4):**
  - artifactregistry.repositories.downloadArtifacts
  - logging.logEntries.create
  - monitoring.metricDescriptors.create
  - monitoring.timeSeries.create
**RECOMMENDED REMOVALS:**
  - roles/secretmanager.secretAccessor (Secret Management)
**KEEP THESE ROLES:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 4 specific permissions
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 2 of the permissions in this role binding were used in the past 90 days.

### gsa-fusion@foiply-app.iam.gserviceaccount.com
**Current Roles (5):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/compute.networkAdmin (Administrative Access)
  - roles/container.admin (Administrative Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectAdmin (Administrative Access)
**Permission Usage:** 0/1354 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/container.admin (Administrative Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectAdmin (Administrative Access)
**KEEP THESE ROLES:**
  - roles/compute.networkAdmin (Administrative Access)
**SUGGESTED REPLACEMENTS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 56 days.

### gsa-gotenberg-chromium-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**Permission Usage:** 3/39 (7.7%)
**Actually Used Permissions (3):**
  - logging.logEntries.create
  - monitoring.metricDescriptors.create
  - monitoring.timeSeries.create
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
**KEEP THESE ROLES:**
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 3 specific permissions
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 2 of the permissions in this role binding were used in the past 90 days.

### gsa-gotenberg-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**Permission Usage:** 3/39 (7.7%)
**Actually Used Permissions (3):**
  - logging.logEntries.create
  - monitoring.metricDescriptors.create
  - monitoring.timeSeries.create
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
**KEEP THESE ROLES:**
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 3 specific permissions
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 2 of the permissions in this role binding were used in the past 90 days.

### gsa-xfs-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (8):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudsql.instanceUser (Standard User Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/storage.objectUser (Standard User Access)
**Permission Usage:** 10/79 (12.7%)
**Actually Used Permissions (9):**
  - artifactregistry.repositories.downloadArtifacts
  - logging.logEntries.create
  - monitoring.metricDescriptors.create
  - monitoring.metricDescriptors.list
  - monitoring.timeSeries.create
  - secretmanager.versions.access
  - storage.objects.create
  - storage.objects.delete
  - storage.objects.get
**RECOMMENDED REMOVALS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudsql.instanceUser (Standard User Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/secretmanager.secretAccessor (Secret Management)
**KEEP THESE ROLES:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/storage.objectUser (Standard User Access)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 9 specific permissions
**Usage Analysis:**
  - 4 of the permissions in this role binding were used in the past 90 days.
  - This role has not been used during the observation window.
  - Replace the current role with a smaller role to cover the permissions needed.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 3 of the permissions in this role binding were used in the past 90 days.

## CI/CD - GitLab (2 accounts)
--------------------------------------------------

### gitlab-5318ef1768e1a92506f3bd@foiply-app.iam.gserviceaccount.com
**Current Roles (13):**
  - roles/artifactregistry.writer (Container/Artifact Management)
  - roles/cloudbuild.builds.editor (Read/Write Access)
  - roles/compute.admin (Administrative Access)
  - roles/container.admin (Administrative Access)
  - roles/container.developer (Specialized Function)
  - roles/gkehub.admin (Administrative Access)
  - roles/gkehub.gatewayAdmin (Administrative Access)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/serviceusage.serviceUsageConsumer (Specialized Function)
  - roles/storage.objectAdmin (Administrative Access)
  - roles/storage.objectUser (Standard User Access)
  - roles/viewer (Read-Only Access)
**Permission Usage:** 145/7139 (2.0%)
**Actually Used Permissions (62):**
  - container.backendConfigs.delete
  - container.backendConfigs.get
  - container.backendConfigs.update
  - container.clusters.connect
  - container.clusters.get
  - container.clusters.getCredentials
  - container.configMaps.create
  - container.configMaps.get
  - container.deployments.create
  - container.deployments.delete
  - container.deployments.get
  - container.deployments.update
  - container.events.list
  - container.horizontalPodAutoscalers.create
  - container.horizontalPodAutoscalers.delete
  - container.horizontalPodAutoscalers.get
  - container.horizontalPodAutoscalers.update
  - container.ingresses.create
  - container.ingresses.get
  - container.ingresses.update
  - container.jobs.create
  - container.jobs.delete
  - container.jobs.get
  - container.jobs.list
  - container.jobs.update
  - container.namespaces.get
  - container.networkPolicies.create
  - container.networkPolicies.get
  - container.podDisruptionBudgets.create
  - container.podDisruptionBudgets.delete
  - container.podDisruptionBudgets.get
  - container.podDisruptionBudgets.update
  - container.pods.getLogs
  - container.pods.list
  - container.replicaSets.list
  - container.secrets.create
  - container.secrets.delete
  - container.secrets.get
  - container.secrets.list
  - container.secrets.update
  - container.serviceAccounts.create
  - container.serviceAccounts.get
  - container.services.create
  - container.services.delete
  - container.services.get
  - container.services.update
  - container.statefulSets.create
  - container.statefulSets.get
  - container.thirdPartyObjects.create
  - container.thirdPartyObjects.delete
  - container.thirdPartyObjects.get
  - container.thirdPartyObjects.update
  - gkehub.gateway.delete
  - gkehub.gateway.generateCredentials
  - gkehub.gateway.get
  - gkehub.gateway.patch
  - gkehub.gateway.post
  - gkehub.gateway.put
  - gkehub.memberships.list
  - resourcemanager.projects.get
  - secretmanager.secrets.list
  - secretmanager.versions.access
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
**KEEP THESE ROLES:**
  - roles/container.admin (Administrative Access)
  - roles/container.developer (Specialized Function)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/viewer (Read-Only Access)
**SUGGESTED REPLACEMENTS:**
  - roles/artifactregistry.writer (Container/Artifact Management)
  - roles/cloudbuild.builds.editor (Read/Write Access)
  - roles/container.developer (Specialized Function)
  - roles/iam.workloadIdentityUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 52 of the permissions in this role binding were used in the past 90 days.
  - Replace the current role with a smaller role to cover the permissions needed.
  - 2 of the permissions in this role binding were used in the past 7 days.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 6 of the permissions in this role binding were used in the past 90 days.
  - 53 of the permissions in this role binding were used in the past 90 days.
  - 2 of the permissions in this role binding were used in the past 90 days.
  - 25 of the permissions in this role binding were used in the past 90 days.

### gitlab@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/cloudbuild.builds.editor (Read/Write Access)
**Permission Usage:** 0/42 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/cloudbuild.builds.editor (Read/Write Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

## Certificate Management (1 accounts)
--------------------------------------------------

### cert-manager@documo-development.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/dns.admin (Administrative Access)
**Permission Usage:** 0/45 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/dns.admin (Administrative Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

## Database Management (1 accounts)
--------------------------------------------------

### cloudsql-read-only@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudsql.instanceUser (Standard User Access)
  - roles/cloudsql.viewer (Read-Only Access)
**Permission Usage:** 0/57 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudsql.instanceUser (Standard User Access)
**KEEP THESE ROLES:**
  - roles/cloudsql.viewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 39 days.

## Development/DevOps (3 accounts)
--------------------------------------------------

### dan-kott-workstation@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/container.admin (Administrative Access)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/storage.objectAdmin (Administrative Access)
  - roles/workstations.admin (Administrative Access)
**Permission Usage:** 0/501 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/container.admin (Administrative Access)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/storage.objectAdmin (Administrative Access)
  - roles/workstations.admin (Administrative Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### devops-workstations@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/editor (Read/Write Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/secretmanager.admin (Administrative Access)
  - roles/workstations.serviceAgent (Specialized Function)
**Permission Usage:** 0/20727 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/editor (Read/Write Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/secretmanager.admin (Administrative Access)
  - roles/workstations.serviceAgent (Specialized Function)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### devops@documo.com
**Permission Usage:** 1726/14497 (11.9%)

## Environment-Specific (2 accounts)
--------------------------------------------------

### xfs-production@foiply-app.iam.gserviceaccount.com
**Current Roles (9):**
  - roles/composer.environmentAndStorageObjectUser (Standard User Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.secretVersionManager (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
  - roles/storage.objectUser (Standard User Access)
**Permission Usage:** 3/91 (3.3%)
**Actually Used Permissions (2):**
  - logging.logEntries.create
  - monitoring.timeSeries.create
**RECOMMENDED REMOVALS:**
  - roles/composer.environmentAndStorageObjectUser (Standard User Access)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.secretVersionManager (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
**KEEP THESE ROLES:**
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/storage.objectUser (Standard User Access)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 2 specific permissions
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.

### xfs-staging@foiply-app.iam.gserviceaccount.com
**Current Roles (7):**
  - roles/composer.environmentAndStorageObjectUser (Standard User Access)
  - roles/container.defaultNodeServiceAccount (Specialized Function)
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/iam.workloadIdentityUser (Standard User Access)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.secretVersionManager (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
**Permission Usage:** 0/65 (0.0%)
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
  - 0 of the permissions in this role binding were used in the past 90 days.

## File Transfer/Communication (1 accounts)
--------------------------------------------------

### sftp-sa@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectCreator (Storage Operations)
**Permission Usage:** 0/9 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectCreator (Storage Operations)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

## Infrastructure/Compute (3 accounts)
--------------------------------------------------

### 105005824641-compute@developer.gserviceaccount.com
**Current Roles (8):**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/clouddeploy.jobRunner (Specialized Function)
  - roles/clouddeploy.releaser (Specialized Function)
  - roles/container.developer (Specialized Function)
  - roles/eventarc.eventReceiver (Specialized Function)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/remotebuildexecution.artifactViewer (Read-Only Access)
**Permission Usage:** 6/458 (1.3%)
**Actually Used Permissions (5):**
  - artifactregistry.repositories.downloadArtifacts
  - logging.logEntries.create
  - monitoring.metricDescriptors.create
  - monitoring.metricDescriptors.list
  - monitoring.timeSeries.create
**RECOMMENDED REMOVALS:**
  - roles/clouddeploy.releaser (Specialized Function)
  - roles/container.developer (Specialized Function)
  - roles/eventarc.eventReceiver (Specialized Function)
  - roles/remotebuildexecution.artifactViewer (Read-Only Access)
**KEEP THESE ROLES:**
  - roles/artifactregistry.reader (Read-Only Access)
  - roles/clouddeploy.jobRunner (Specialized Function)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 5 specific permissions
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - 3 of the permissions in this role binding were used in the past 90 days.

### gke-artifact-puller@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/artifactregistry.reader (Read-Only Access)
**Permission Usage:** 0/31 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/artifactregistry.reader (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### gke-limited@foiply-app.iam.gserviceaccount.com
**Current Roles (7):**
  - roles/cloudfunctions.invoker (Specialized Function)
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudtrace.agent (Specialized Function)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/monitoring.viewer (Read-Only Access)
  - roles/run.invoker (Specialized Function)
**Permission Usage:** 7/48 (14.6%)
**Actually Used Permissions (6):**
  - logging.logEntries.create
  - monitoring.dashboards.get
  - monitoring.metricDescriptors.create
  - monitoring.metricDescriptors.list
  - monitoring.timeSeries.create
  - monitoring.timeSeries.list
**RECOMMENDED REMOVALS:**
  - roles/cloudfunctions.invoker (Specialized Function)
  - roles/cloudsql.client (Specialized Function)
  - roles/cloudtrace.agent (Specialized Function)
  - roles/run.invoker (Specialized Function)
**KEEP THESE ROLES:**
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/monitoring.viewer (Read-Only Access)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 6 specific permissions
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 3 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.

## Monitoring/Security (1 accounts)
--------------------------------------------------

### grafana-gcp-service-account@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/logging.viewer (Read-Only Access)
  - roles/monitoring.viewer (Read-Only Access)
**Permission Usage:** 0/61 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/logging.viewer (Read-Only Access)
  - roles/monitoring.viewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

## Other/Unknown (15 accounts)
--------------------------------------------------

### ben.turner@documo.com
**Permission Usage:** 0/21 (0.0%)

### dan.kott@documo.com
**Permission Usage:** 267/617 (43.3%)

### finance@documo.com
**Permission Usage:** 0/2 (0.0%)

### gazal.shukla@documo.com
**Permission Usage:** 0/2 (0.0%)

### it-sys@documo.com
**Permission Usage:** 264/12246 (2.2%)

### marko-report-bot@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectCreator (Storage Operations)
**Permission Usage:** 0/9 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectCreator (Storage Operations)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### openemr-787@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/compute.admin (Administrative Access)
  - roles/config.agent (Specialized Function)
  - roles/iam.serviceAccountUser (Standard User Access)
**Permission Usage:** 0/989 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/compute.admin (Administrative Access)
  - roles/config.agent (Specialized Function)
  - roles/iam.serviceAccountUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### openemr@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/compute.admin (Administrative Access)
  - roles/config.agent (Specialized Function)
  - roles/iam.serviceAccountUser (Standard User Access)
**Permission Usage:** 21/989 (2.1%)
**Actually Used Permissions (21):**
  - compute.disks.create
  - compute.disks.get
  - compute.instances.create
  - compute.instances.get
  - compute.instances.setLabels
  - compute.instances.setMetadata
  - compute.instances.setServiceAccount
  - compute.instances.setTags
  - compute.subnetworks.use
  - compute.subnetworks.useExternalIp
  - compute.zoneOperations.get
  - compute.zones.get
  - config.deployments.getLock
  - config.deployments.getState
  - config.deployments.updateState
  - iam.serviceAccounts.actAs
  - logging.logEntries.create
  - storage.buckets.get
  - storage.objects.create
  - storage.objects.delete
  - storage.objects.get
**RECOMMENDED REMOVALS:**
  - roles/compute.admin (Administrative Access)
**KEEP THESE ROLES:**
  - roles/config.agent (Specialized Function)
  - roles/iam.serviceAccountUser (Standard User Access)
**Usage Analysis:**
  - Replace the current role with a smaller role to cover the permissions needed.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 12 of the permissions in this role binding were used in the past 90 days.
  - 8 of the permissions in this role binding were used in the past 90 days.

### rp-csm-cnah9bt9cnna1iqe201g@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - projects/foiply-app/roles/redpandaConnectorsCnah9bt9cnna1iqe201gJ1lp (Specialized Function)
**Permission Usage:** 0/2 (0.0%)
**RECOMMENDED REMOVALS:**
  - projects/foiply-app/roles/redpandaConnectorsCnah9bt9cnna1iqe201gJ1lp (Specialized Function)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### sandra.gendy@documo.com
**Permission Usage:** 506/3837 (13.2%)

### service-105005824641@containerregistry.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/containerregistry.ServiceAgent (Specialized Function)
  - roles/editor (Read/Write Access)
**Permission Usage:** 0/10265 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/editor (Read/Write Access)
**KEEP THESE ROLES:**
  - roles/containerregistry.ServiceAgent (Specialized Function)
**Usage Analysis:**
  - Replace OEV role with service agent role and other curated roles.
  - 0 of the permissions in this role binding were used in the past 90 days.

### steve.chong@documo.com
**Permission Usage:** 31/766 (4.0%)

### test-nick@foiply-app.iam.gserviceaccount.com
**Current Roles (2):**
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/storage.objectUser (Standard User Access)
**Permission Usage:** 0/33 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/storage.objectUser (Standard User Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### v-dan.kott@documo.com
**Permission Usage:** 0/11627 (0.0%)

### v-sandra.gendy@documo.com
**Permission Usage:** 0/11627 (0.0%)

## Secret Management (2 accounts)
--------------------------------------------------

### xfs-production-secrets-manager@foiply-app.iam.gserviceaccount.com
**Current Roles (3):**
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
  - roles/storage.objectUser (Standard User Access)
**Permission Usage:** 5/38 (13.2%)
**Actually Used Permissions (5):**
  - secretmanager.versions.access
  - storage.objects.create
  - storage.objects.delete
  - storage.objects.get
  - storage.objects.list
**RECOMMENDED REMOVALS:**
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
  - roles/storage.objectUser (Standard User Access)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 5 specific permissions
**Usage Analysis:**
  - 4 of the permissions in this role binding were used in the past 90 days.
  - This role has not been used during the observation window.
  - Replace the current role with a smaller role to cover the permissions needed.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.

### xfs-secret-manager-sa@foiply-app.iam.gserviceaccount.com
**Current Roles (4):**
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
  - roles/storage.objectUser (Standard User Access)
**Permission Usage:** 4/47 (8.5%)
**Actually Used Permissions (4):**
  - storage.objects.create
  - storage.objects.delete
  - storage.objects.get
  - storage.objects.list
**RECOMMENDED REMOVALS:**
  - roles/iam.serviceAccountTokenCreator (Identity Management)
  - roles/secretmanager.secretAccessor (Secret Management)
  - roles/secretmanager.viewer (Read-Only Access)
  - roles/storage.objectUser (Standard User Access)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 4 specific permissions
**Usage Analysis:**
  - 4 of the permissions in this role binding were used in the past 90 days.
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.
  - Replace the current role with a smaller role to cover the permissions needed.

## Serverless/Functions (2 accounts)
--------------------------------------------------

### cloud-functions@foiply-app.iam.gserviceaccount.com
**Current Roles (7):**
  - roles/cloudfunctions.admin (Administrative Access)
  - roles/cloudfunctions.invoker (Specialized Function)
  - roles/logging.logWriter (Specialized Function)
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/run.invoker (Specialized Function)
  - roles/secretmanager.admin (Administrative Access)
  - roles/storage.objectAdmin (Administrative Access)
**Permission Usage:** 6/279 (2.2%)
**Actually Used Permissions (5):**
  - monitoring.timeSeries.create
  - secretmanager.versions.access
  - storage.objects.create
  - storage.objects.delete
  - storage.objects.get
**RECOMMENDED REMOVALS:**
  - roles/cloudfunctions.admin (Administrative Access)
  - roles/cloudfunctions.invoker (Specialized Function)
  - roles/logging.logWriter (Specialized Function)
  - roles/run.invoker (Specialized Function)
**KEEP THESE ROLES:**
  - roles/monitoring.metricWriter (Monitoring/Observability)
  - roles/secretmanager.admin (Administrative Access)
  - roles/storage.objectAdmin (Administrative Access)
**CUSTOM ROLE OPPORTUNITY:** Yes
   Create role with 5 specific permissions
**Usage Analysis:**
  - 4 of the permissions in this role binding were used in the past 90 days.
  - This role has not been used during the observation window.
  - 1 of the permissions in this role binding were used in the past 90 days.
  - 0 of the permissions in this role binding were used in the past 90 days.

### firebase-service-account@firebase-sa-management.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/firebase.managementServiceAgent (Specialized Function)
**Permission Usage:** 0/82 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/firebase.managementServiceAgent (Specialized Function)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

## Storage Management (2 accounts)
--------------------------------------------------

### prod-faxstorage-buckets-sa@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectViewer (Read-Only Access)
**Permission Usage:** 0/8 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectViewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.

### staging-buckets-sa@foiply-app.iam.gserviceaccount.com
**Current Roles (1):**
  - roles/storage.objectViewer (Read-Only Access)
**Permission Usage:** 0/8 (0.0%)
**RECOMMENDED REMOVALS:**
  - roles/storage.objectViewer (Read-Only Access)
**Usage Analysis:**
  - This role has not been used during the observation window.
  - 0 of the permissions in this role binding were used in the past 90 days.
