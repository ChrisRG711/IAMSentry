# IAMSentry Cloud Run Deployment

This guide covers deploying IAMSentry to Google Cloud Run with optional Identity-Aware Proxy (IAP) for authentication.

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/install) installed and configured
- [Terraform](https://www.terraform.io/downloads) >= 1.0 (optional, for IaC deployment)
- [Docker](https://www.docker.com/get-started) installed
- A GCP project with billing enabled

## Quick Deploy (Manual)

### 1. Set Environment Variables

```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export SERVICE_NAME="iamsentry"
```

### 2. Enable Required APIs

```bash
gcloud services enable \
    run.googleapis.com \
    containerregistry.googleapis.com \
    artifactregistry.googleapis.com \
    recommender.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iap.googleapis.com \
    --project=$PROJECT_ID
```

### 3. Build and Push Docker Image

```bash
# Build the image
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest
```

### 4. Create Service Account

```bash
# Create service account for IAMSentry
gcloud iam service-accounts create iamsentry-sa \
    --display-name="IAMSentry Service Account" \
    --project=$PROJECT_ID

# Grant required permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:iamsentry-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/recommender.iamViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:iamsentry-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.securityReviewer"
```

### 5. Deploy to Cloud Run

```bash
# Generate an API key
API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "Your API Key: $API_KEY"

# Deploy
gcloud run deploy $SERVICE_NAME \
    --image=gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
    --platform=managed \
    --region=$REGION \
    --service-account=iamsentry-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars="IAMSENTRY_AUTH_ENABLED=true,IAMSENTRY_API_KEYS=$API_KEY" \
    --allow-unauthenticated \
    --project=$PROJECT_ID
```

### 6. Get the Service URL

```bash
gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(status.url)'
```

---

## Terraform Deployment (Recommended)

For production deployments, use Terraform for reproducible infrastructure.

### 1. Initialize Terraform

```bash
cd deploy/cloudrun/terraform
terraform init
```

### 2. Create terraform.tfvars

```hcl
project_id       = "your-gcp-project-id"
region           = "us-central1"
service_name     = "iamsentry"
enable_iap       = true  # Enable Identity-Aware Proxy
iap_oauth_client = ""    # Will be created if empty
```

### 3. Apply Terraform

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

### 4. Get Outputs

```bash
terraform output service_url
terraform output api_key
```

---

## Identity-Aware Proxy (IAP) Setup

IAP provides Google-managed authentication for your Cloud Run service.

### Benefits
- Google handles authentication (OAuth 2.0)
- Users sign in with Google accounts
- No API keys or passwords needed
- Audit logging of all access

### Enable IAP

1. **Create OAuth Consent Screen** (if not exists):
   ```bash
   # Go to: https://console.cloud.google.com/apis/credentials/consent
   ```

2. **Create OAuth Client**:
   ```bash
   # Go to: https://console.cloud.google.com/apis/credentials
   # Create OAuth 2.0 Client ID (Web application)
   ```

3. **Configure IAMSentry for IAP**:
   ```bash
   # Set environment variables in Cloud Run:
   IAMSENTRY_IAP_ENABLED=true
   IAMSENTRY_IAP_AUDIENCE=/projects/PROJECT_NUMBER/global/backendServices/SERVICE_ID
   ```

4. **Grant IAP Access**:
   ```bash
   gcloud iap web add-iam-policy-binding \
       --member="user:admin@example.com" \
       --role="roles/iap.httpsResourceAccessor" \
       --project=$PROJECT_ID
   ```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `IAMSENTRY_AUTH_ENABLED` | Enable authentication | `true` |
| `IAMSENTRY_API_KEYS` | Comma-separated API keys | |
| `IAMSENTRY_IAP_ENABLED` | Enable Google IAP validation | `false` |
| `IAMSENTRY_IAP_AUDIENCE` | IAP audience for JWT validation | |
| `IAMSENTRY_LOG_FORMAT` | `json` or `text` | `text` |
| `IAMSENTRY_LOG_LEVEL` | Logging level | `INFO` |
| `IAMSENTRY_DATA_DIR` | Output directory | `/app/output` |
| `IAMSENTRY_CORS_ORIGINS` | Allowed CORS origins | |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Google Cloud                              │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │   Cloud     │───▶│  Cloud Run   │───▶│  Recommender  │  │
│  │   Load      │    │  (IAMSentry) │    │     API       │  │
│  │  Balancer   │    └──────────────┘    └───────────────┘  │
│  └─────────────┘           │                               │
│         │                  │                               │
│         ▼                  ▼                               │
│  ┌─────────────┐    ┌──────────────┐                       │
│  │     IAP     │    │   Cloud      │                       │
│  │  (Optional) │    │   Storage    │                       │
│  └─────────────┘    │  (Results)   │                       │
│                     └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Monitoring

### Cloud Monitoring

Cloud Run automatically exports metrics. View them in:
- Cloud Console > Cloud Run > [Service] > Metrics

### Prometheus Metrics

If you have Prometheus set up, configure a scrape job:

```yaml
scrape_configs:
  - job_name: 'iamsentry'
    static_configs:
      - targets: ['your-service-url.run.app']
    metrics_path: /metrics
    scheme: https
```

---

## Troubleshooting

### "Permission denied" errors

Ensure the service account has required roles:
```bash
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:iamsentry-sa@"
```

### IAP not working

1. Check OAuth consent screen is configured
2. Verify IAP is enabled for the backend service
3. Check IAP audience matches your configuration
4. Ensure user has `roles/iap.httpsResourceAccessor`

### Container fails to start

Check logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
    --project=$PROJECT_ID \
    --limit=50
```

---

## Cost Considerations

Cloud Run pricing is based on:
- **CPU**: Billed per 100ms while processing requests
- **Memory**: Billed per GB-second
- **Requests**: First 2 million requests/month are free

For typical IAMSentry usage (scanning a few times per day), costs should be minimal.

**Cost optimization tips:**
- Set `--min-instances=0` for scale-to-zero
- Use `--cpu-throttling` to reduce costs during idle
- Schedule scans during off-peak hours

---

## Security Best Practices

1. **Enable IAP** for production deployments
2. **Use Secret Manager** for API keys instead of environment variables
3. **Restrict service account permissions** to minimum required
4. **Enable VPC connector** if scanning private projects
5. **Set up Cloud Audit Logs** for compliance
6. **Use custom domain** with managed SSL certificate

---

## Next Steps

- [Set up scheduled scans with Cloud Scheduler](../cloudscheduler/README.md)
- [Configure alerts with Cloud Monitoring](../monitoring/README.md)
- [Deploy to GKE instead](../gke/README.md)
