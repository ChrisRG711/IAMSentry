# IAMSentry Helm Chart

Deploy IAMSentry to Kubernetes using Helm.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- GCP service account with IAM permissions (see [GCP Setup](#gcp-setup))

## Installation

### Quick Start

```bash
# Add the Helm repository (if published)
# helm repo add iamsentry https://charts.example.com
# helm repo update

# Install from local chart
helm install iamsentry ./deploy/helm/iamsentry \
  --namespace iamsentry \
  --create-namespace \
  --set gcp.projectId=your-project-id
```

### With Custom Values

```bash
# Create a values file
cat > my-values.yaml <<EOF
gcp:
  projectId: "your-gcp-project"
  workloadIdentity:
    enabled: true
    serviceAccountEmail: "iamsentry@your-project.iam.gserviceaccount.com"

auth:
  enabled: true
  apiKeys: "your-secure-api-key"

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: iamsentry.your-domain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: iamsentry-tls
      hosts:
        - iamsentry.your-domain.com

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
EOF

# Install with custom values
helm install iamsentry ./deploy/helm/iamsentry \
  --namespace iamsentry \
  --create-namespace \
  -f my-values.yaml
```

## Configuration

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Container image repository | `gcr.io/your-project/iamsentry` |
| `image.tag` | Container image tag | Chart appVersion |
| `gcp.projectId` | GCP project to scan | `""` |
| `gcp.regions` | GCP regions to scan | `["global", "us-central1", "us-east1"]` |
| `auth.enabled` | Enable authentication | `true` |
| `auth.apiKeys` | API keys (comma-separated) | `""` |
| `auth.iap.enabled` | Enable Google IAP | `false` |
| `ingress.enabled` | Enable ingress | `false` |
| `autoscaling.enabled` | Enable HPA | `false` |
| `metrics.enabled` | Enable Prometheus metrics | `true` |
| `persistence.enabled` | Enable persistent storage | `false` |

### All Parameters

See [values.yaml](values.yaml) for the complete list of configurable parameters.

## GCP Setup

### Option 1: Workload Identity (Recommended for GKE)

1. Enable Workload Identity on your GKE cluster:
   ```bash
   gcloud container clusters update CLUSTER_NAME \
     --workload-pool=PROJECT_ID.svc.id.goog
   ```

2. Create a GCP service account:
   ```bash
   gcloud iam service-accounts create iamsentry-sa \
     --display-name="IAMSentry Service Account"
   ```

3. Grant required permissions:
   ```bash
   PROJECT_ID=$(gcloud config get-value project)

   # Viewer for reading IAM recommendations
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:iamsentry-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/recommender.iamViewer"

   # Optional: For remediation
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:iamsentry-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.securityAdmin"
   ```

4. Bind the Kubernetes service account to the GCP service account:
   ```bash
   gcloud iam service-accounts add-iam-policy-binding \
     iamsentry-sa@$PROJECT_ID.iam.gserviceaccount.com \
     --role="roles/iam.workloadIdentityUser" \
     --member="serviceAccount:$PROJECT_ID.svc.id.goog[iamsentry/iamsentry]"
   ```

5. Deploy with Workload Identity:
   ```bash
   helm install iamsentry ./deploy/helm/iamsentry \
     --namespace iamsentry \
     --set gcp.projectId=$PROJECT_ID \
     --set gcp.workloadIdentity.enabled=true \
     --set gcp.workloadIdentity.serviceAccountEmail=iamsentry-sa@$PROJECT_ID.iam.gserviceaccount.com \
     --set serviceAccount.annotations."iam\.gke\.io/gcp-service-account"=iamsentry-sa@$PROJECT_ID.iam.gserviceaccount.com
   ```

### Option 2: Service Account Key (Not recommended for production)

1. Create a service account key:
   ```bash
   gcloud iam service-accounts keys create key.json \
     --iam-account=iamsentry-sa@$PROJECT_ID.iam.gserviceaccount.com
   ```

2. Create a Kubernetes secret:
   ```bash
   kubectl create secret generic gcp-sa-key \
     --from-file=key.json=key.json \
     --namespace iamsentry
   ```

3. Mount the secret in your values:
   ```yaml
   extraVolumes:
     - name: gcp-key
       secret:
         secretName: gcp-sa-key

   extraVolumeMounts:
     - name: gcp-key
       mountPath: /var/secrets/google
       readOnly: true

   extraEnv:
     - name: GOOGLE_APPLICATION_CREDENTIALS
       value: /var/secrets/google/key.json
   ```

## Authentication

### API Key Authentication

```yaml
auth:
  enabled: true
  apiKeys: "key1,key2,key3"
```

Access with header: `X-API-Key: key1`

### Basic Authentication

```yaml
auth:
  enabled: true
  basicAuthUsers: "admin:securepassword,readonly:anotherpassword"
```

### Google IAP (Identity-Aware Proxy)

For GKE with IAP-enabled ingress:

```yaml
auth:
  enabled: true
  iap:
    enabled: true
    audience: "/projects/PROJECT_NUMBER/global/backendServices/SERVICE_ID"

ingress:
  enabled: true
  annotations:
    kubernetes.io/ingress.global-static-ip-name: iamsentry-ip
    networking.gke.io/managed-certificates: iamsentry-cert
```

## Monitoring

### Prometheus Metrics

Metrics are exposed at `/metrics` by default. Enable ServiceMonitor for Prometheus Operator:

```yaml
metrics:
  enabled: true
  serviceMonitor:
    enabled: true
    labels:
      release: prometheus
    interval: 30s
```

### Health Checks

- Liveness: `/api/health`
- Readiness: `/api/health`
- Startup: `/api/health`

## Upgrading

```bash
helm upgrade iamsentry ./deploy/helm/iamsentry \
  --namespace iamsentry \
  -f my-values.yaml
```

## Uninstalling

```bash
helm uninstall iamsentry --namespace iamsentry
kubectl delete namespace iamsentry
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n iamsentry
kubectl describe pod -n iamsentry -l app.kubernetes.io/name=iamsentry
```

### View Logs

```bash
kubectl logs -f deployment/iamsentry -n iamsentry
```

### Check Service Account Permissions

```bash
# Verify Workload Identity binding
kubectl get serviceaccount -n iamsentry iamsentry -o yaml

# Test GCP authentication from the pod
kubectl exec -it deployment/iamsentry -n iamsentry -- \
  gcloud auth list
```

### Common Issues

1. **Pod CrashLoopBackOff**: Check logs and ensure GCP credentials are configured
2. **403 Forbidden from GCP**: Verify IAM permissions on the service account
3. **Ingress not working**: Check ingress controller logs and annotations

## Development

### Lint the Chart

```bash
helm lint ./deploy/helm/iamsentry
```

### Render Templates Locally

```bash
helm template iamsentry ./deploy/helm/iamsentry \
  --namespace iamsentry \
  --set gcp.projectId=test-project
```

### Test Installation

```bash
helm install iamsentry ./deploy/helm/iamsentry \
  --namespace iamsentry \
  --create-namespace \
  --dry-run \
  --debug
```

## License

MIT License - See [LICENSE](../../../LICENSE) for details.
