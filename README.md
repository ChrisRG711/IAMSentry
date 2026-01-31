# IAMSentry

[![CI](https://github.com/ChrisRG711/IAMSentry/actions/workflows/ci.yml/badge.svg)](https://github.com/ChrisRG711/IAMSentry/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://github.com/ChrisRG711/IAMSentry/blob/main/Dockerfile)


**GCP IAM Security Auditor and Remediation Tool**

IAMSentry automatically analyzes Google Cloud Platform's Identity and Access Management (IAM) configurations to identify over-privileged access, calculate risk scores, and optionally apply recommended security fixes.

## Features

- **IAM Recommendation Scanning** - Fetches recommendations from GCP's IAM Recommender API
- **Risk Scoring** - Calculates risk scores based on account type, privilege level, and usage patterns
- **Web Dashboard** - Visual interface for reviewing recommendations and applying remediations
- **Automated Remediation** - Safely apply recommendations with dry-run mode (enabled by default)
- **Audit Logging** - Comprehensive compliance logging with optional HMAC signing
- **Authentication** - API Key, HTTP Basic Auth, and Google IAP support
- **Docker Ready** - Containerized deployment with Docker and docker-compose

## Quick Start

### Option 1: Interactive Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/ChrisRG711/IAMSentry.git
cd IAMSentry

# Run the setup wizard
./setup.sh
```

The setup wizard will:
- Install dependencies (optionally in a virtual environment)
- Configure GCP authentication
- Generate a configuration file
- Create API keys for dashboard access

### Option 2: Manual Installation

```bash
# Install
pip install -e ".[dashboard]"

# Authenticate with GCP
gcloud auth application-default login

# Validate your setup
iamsentry validate

# Scan for recommendations
iamsentry scan --config config.yaml --output ./output

# Start the dashboard
iamsentry-dashboard --port 8080
```

### Option 3: Docker

```bash
# Build and run with docker-compose
docker compose up -d

# Or build manually
docker build -t iamsentry .
docker run -p 8080:8080 -v ~/.config/gcloud:/home/iamsentry/.config/gcloud:ro iamsentry
```

### Option 4: Cloud Run (Production)

Deploy to Google Cloud Run with one command:

```bash
cd deploy/cloudrun
./deploy.sh --project your-gcp-project-id
```

Or use Terraform for infrastructure-as-code:

```bash
cd deploy/cloudrun/terraform
terraform init
terraform apply -var="project_id=your-gcp-project-id"
```

See [deploy/cloudrun/README.md](deploy/cloudrun/README.md) for detailed instructions.

### Option 5: Kubernetes (Helm)

Deploy to Kubernetes using Helm:

```bash
# Install the chart
helm install iamsentry ./deploy/helm/iamsentry \
  --namespace iamsentry \
  --create-namespace \
  --set gcp.projectId=your-gcp-project-id

# With Workload Identity (GKE)
helm install iamsentry ./deploy/helm/iamsentry \
  --namespace iamsentry \
  --create-namespace \
  --set gcp.projectId=your-gcp-project-id \
  --set gcp.workloadIdentity.enabled=true \
  --set gcp.workloadIdentity.serviceAccountEmail=iamsentry@your-project.iam.gserviceaccount.com
```

See [deploy/helm/iamsentry/README.md](deploy/helm/iamsentry/README.md) for detailed instructions including:
- GKE Workload Identity setup
- Ingress configuration
- Prometheus ServiceMonitor
- Horizontal Pod Autoscaling

## Documentation

See [docs/README.md](docs/README.md) for full documentation including:
- Configuration guide
- Authentication setup
- Architecture overview
- Plugin development
- API reference

## Attribution

IAMSentry is a fork of [CureIAM](https://github.com/gojek/CureIAM), originally developed by the **Gojek Product Security Team** 

We are grateful to the original authors for their foundational work on GCP IAM recommendation scanning built upon the Cloudmarker framework.

### What's New in IAMSentry

This fork has been substantially extended with:

| Feature | Description |
|---------|-------------|
| Web Dashboard | Vue.js + FastAPI visualization interface |
| Authentication | API Key, HTTP Basic Auth, and Google IAP support |
| Audit Logging | Compliance logging with HMAC signing |
| Modern CLI | Typer-based CLI with rich formatting |
| Security Hardening | Input validation, injection prevention |
| Test Suite | Comprehensive automated testing |
| Docker Support | Dockerfile and docker-compose for easy deployment |
| Setup Wizard | Interactive setup script for quick onboarding |
| Pre-flight Checks | `iamsentry validate` command for configuration validation |
| Cloud Run Deploy | One-command deployment to GCP Cloud Run |
| Terraform IaC | Infrastructure-as-code for reproducible deployments |
| Kubernetes Helm | Production-ready Helm chart for K8s/GKE deployment |
| Prometheus Metrics | `/metrics` endpoint for monitoring |
| JSON Logging | Structured logs for log aggregators (ELK, Splunk, etc.) |
| Shell Completion | Tab completion for bash, zsh, fish, powershell |

See [NOTICE](NOTICE) for full attribution details.


## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Run tests
pytest

# Check code quality
black IAMSentry tests
mypy IAMSentry
flake8 IAMSentry tests
```

## Security

For security concerns, please see [SECURITY.md](SECURITY.md).

