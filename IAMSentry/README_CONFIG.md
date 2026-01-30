# IAMSentry Configuration Guide

## Quick Start

1. **Copy the example config**: `cp example_config.yaml my_config.yaml`
2. **Edit the config file** with your specific settings
3. **Run IAMSentry**: `python -m IAMSentry my_config.yaml`

## Configuration Structure

### Required Sections

#### `logger`
Configures logging output. The example shows console and file logging.

#### `plugins`
Defines all available plugins. Each plugin has:
- `plugin`: Python class path
- Additional plugin-specific configuration

#### `audits`
Defines audit workflows by combining plugins:
- `clouds`: Data source plugins
- `processors`: Analysis plugins  
- `stores`: Storage plugins
- `alerts`: Notification plugins

#### `run`
Lists which audits to execute.

## GCP Setup

### 1. Service Account Setup
```bash
# Create service account
gcloud iam service-accounts create iamsentry-scanner

# Grant necessary permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:iamsentry-scanner@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/recommender.viewer"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:iamsentry-scanner@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/resourcemanager.projectViewer"

# Create and download key
gcloud iam service-accounts keys create iamsentry-key.json \
  --iam-account=iamsentry-scanner@PROJECT_ID.iam.gserviceaccount.com
```

### 2. Configuration Updates
Update these fields in your config:
```yaml
plugins:
  gcp_iam_reader:
    key_file_path: "/absolute/path/to/iamsentry-key.json"
  
  gcp_iam_processor:
    enforcer:
      key_file_path: "/absolute/path/to/iamsentry-key.json"
```

## Safety Settings

### Scan-Only Mode (Recommended)
```yaml
gcp_iam_processor:
  mode_scan: true
  mode_enforce: false  # NEVER apply changes
```

### Enforcement Mode (DANGEROUS)
⚠️ **Only use in non-production environments!**
```yaml
gcp_iam_processor:
  mode_scan: true
  mode_enforce: true   # Will actually modify IAM policies!
  enforcer:
    # Configure strict allowlists and blocklists
```

## Plugin Types

### Cloud Plugins
Read data from cloud providers:
- `GCPCloudIAMRecommendations`: Reads GCP IAM recommendations

### Processor Plugins
Analyze and score data:
- `GCPIAMRecommendationProcessor`: Risk scoring and recommendation processing

### Store Plugins
Save results:
- `FileStore`: Save to JSON/CSV files
- `ElasticsearchStore`: Save to Elasticsearch

### Alert Plugins
Send notifications (implement your own)

## Common Issues

### Missing Dependencies
```bash
pip install google-cloud-recommender google-cloud-resource-manager
pip install elasticsearch  # If using Elasticsearch plugin
```

### Permission Errors
Ensure your service account has these roles:
- `roles/recommender.viewer`
- `roles/resourcemanager.projectViewer`
- `roles/iam.securityReviewer`

### File Path Issues
Always use absolute paths for:
- Service account key files
- Output directories
- Log files

## Example Commands

```bash
# Dry run with detailed logging
python -m IAMSentry config.yaml --now

# Print base configuration
python -m IAMSentry --print-base-config

# Run on schedule (runs every day at configured time)
python -m IAMSentry config.yaml
```

## Security Best Practices

1. **Never run in enforcement mode on production**
2. **Use dedicated service accounts with minimal permissions**
3. **Store service account keys securely**
4. **Review all recommendations before applying**
5. **Test on development projects first**
6. **Monitor all changes made by the tool**