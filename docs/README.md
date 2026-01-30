# IAMSentry Documentation

IAMSentry is a GCP IAM security auditing and remediation tool that analyzes IAM recommendations
from Google Cloud's Recommender API and provides risk scoring, reporting, and optional
automated remediation capabilities.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [Configuration](#configuration)
4. [Architecture](#architecture)
5. [Plugins](#plugins)
6. [API Reference](#api-reference)
7. [Development](#development)

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd IAMSentry

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Basic Usage

```bash
# Using Application Default Credentials (recommended)
gcloud auth application-default login

# Initialize a new config file
iamsentry init --output config.yaml

# Check authentication status
iamsentry status

# Scan projects for IAM recommendations
iamsentry scan --config config.yaml --output ./output

# Analyze scan results
iamsentry analyze ./output/results.json

# Remediate (dry-run by default)
iamsentry remediate ./output/results.json --dry-run
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `iamsentry init` | Generate a new configuration file |
| `iamsentry status` | Check GCP authentication and config status |
| `iamsentry scan` | Scan projects for IAM recommendations |
| `iamsentry analyze` | Analyze scan results and show risk scores |
| `iamsentry remediate` | Apply remediations (dry-run by default) |

### Web Dashboard

```bash
# Install dashboard dependencies
pip install -e ".[dashboard]"

# Start the dashboard server
iamsentry-dashboard --port 8080

# Visit http://localhost:8080
```

Dashboard features:
- Real-time statistics cards
- Recommendations table with filtering
- Risk distribution charts
- Remediation modal with dry-run option
- Project overview

### Legacy Usage

```bash
# Using the original manager interface
python -m IAMSentry -c config.yaml

# Using explicit service account key
python -m IAMSentry -c config.yaml --key-file /path/to/key.json
```

---

## Authentication

IAMSentry supports multiple authentication methods with the following priority:

### 1. Application Default Credentials (Recommended)

```bash
# For local development
gcloud auth application-default login

# For GKE workloads - uses Workload Identity automatically
# No configuration needed
```

### 2. Explicit Service Account Key File

```yaml
# config.yaml
plugins:
  gcpcloud:
    key_file_path: /path/to/service-account-key.json
```

### 3. Google Secret Manager Integration

Store service account keys securely in Secret Manager:

```yaml
# config.yaml
plugins:
  gcpcloud:
    key_file_path: gsm://project-id/secret-name/versions/latest
```

### Required IAM Permissions

The service account or user needs these roles:

| Role | Purpose |
|------|---------|
| `roles/recommender.iamViewer` | Read IAM recommendations |
| `roles/resourcemanager.projectIamAdmin` | Apply remediation (optional) |
| `roles/iam.securityReviewer` | View IAM policies |

---

## Configuration

IAMSentry uses YAML configuration files. Create `config.yaml`:

```yaml
# Basic configuration
logger:
  version: 1

audits:
  gcpiamaudit:
    readers:
      - gcpcloud
    processors:
      - gcpcloudiam
    stores:
      - filestore
    alerts:
      - email

# Reader plugin configuration
plugins:
  gcpcloud:
    # Optional: path to service account key
    # key_file_path: /path/to/key.json

    # Projects to scan ('*' for all accessible projects)
    projects:
      - my-project-1
      - my-project-2

    # Concurrency settings
    processes: 4
    threads: 10

    # Regions to scan
    regions:
      - global

  # Processor plugin configuration
  gcpcloudiam:
    mode_scan: true
    mode_enforce: false
    enforcer:
      blocklist_projects:
        - prod-critical-project
      blocklist_accounts:
        - terraform@project.iam.gserviceaccount.com
      allowlist_account_types:
        - user
        - group
      min_safe_to_apply_score_user: 60
      min_safe_to_apply_score_group: 60
      min_safe_to_apply_score_SA: 80

  # Output store configuration
  filestore:
    path: ./output
    bucket: gs://my-bucket/iamsentry

# Email alerts (optional)
email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  from_address: iamsentry@example.com
  to_addresses:
    - security@example.com
```

### Configuration Validation

IAMSentry validates configuration using Pydantic models:

```python
from IAMSentry.config_models import IAMSentryConfig

# Load and validate configuration
config = IAMSentryConfig.from_yaml('config.yaml')
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         IAMSentry                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐    ┌────────────┐    ┌─────────┐    ┌─────────┐   │
│  │ Readers │───▶│ Processors │───▶│ Stores  │───▶│ Alerts  │   │
│  └─────────┘    └────────────┘    └─────────┘    └─────────┘   │
│       │               │                                         │
│       ▼               ▼                                         │
│  ┌─────────────────────────────────┐                           │
│  │         IO Workers              │                           │
│  │  (Multiprocess + Multithread)   │                           │
│  └─────────────────────────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   GCP APIs      │
                    │  - Recommender  │
                    │  - IAM          │
                    │  - CRM          │
                    └─────────────────┘
```

### Components

| Component | Description |
|-----------|-------------|
| **Readers** | Fetch data from GCP APIs (recommendations, insights) |
| **Processors** | Analyze data, calculate risk scores, generate remediation plans |
| **Stores** | Persist results to files, GCS, or databases |
| **Alerts** | Send notifications via email, Slack, or webhooks |
| **IO Workers** | Concurrent processing using multiprocessing + threading |

---

## Plugins

### Reader Plugins

#### GCPCloudIAMRecommendations

Reads IAM recommendations from the GCP Recommender API.

```python
from IAMSentry.plugins.gcp.gcpcloud import GCPCloudIAMRecommendations

reader = GCPCloudIAMRecommendations(
    projects=['my-project'],
    processes=4,
    threads=10
)

for record in reader.read():
    print(record)
```

### Processor Plugins

#### GCPIAMRecommendationProcessor

Processes recommendations and calculates risk scores.

```python
from IAMSentry.plugins.gcp.gcpcloudiam import GCPIAMRecommendationProcessor

processor = GCPIAMRecommendationProcessor(
    mode_scan=True,
    mode_enforce=False
)

for result in processor.eval(record):
    print(f"Risk Score: {result['score']['risk_score']}")
```

#### GCPIAMRemediationProcessor

Optional remediation with dry-run mode (safe by default).

```python
from IAMSentry.plugins.gcp.gcpiam_remediation import GCPIAMRemediationProcessor

# Dry-run mode (simulation only)
processor = GCPIAMRemediationProcessor(
    mode_remediate=True,
    dry_run=True  # Always True by default for safety
)
```

### Store Plugins

#### FileStore

Saves results to local files or GCS.

```python
from IAMSentry.plugins.files.filestore import FileStore

store = FileStore(
    path='./output',
    bucket='gs://my-bucket/iamsentry'
)
```

---

## API Reference

### Core Modules

#### `IAMSentry.ioworkers`

Concurrent I/O workers with queue management and timeouts.

```python
from IAMSentry.ioworkers import run, request_shutdown

# Run concurrent workers
for result in run(
    input_func=get_projects,
    output_func=process_project,
    processes=4,
    threads=10,
    queue_size=1000,
    worker_timeout=300,
    queue_timeout=60
):
    print(result)

# Request graceful shutdown
request_shutdown()
```

#### `IAMSentry.plugins.gcp.util_gcp`

GCP authentication and API utilities.

```python
from IAMSentry.plugins.gcp import util_gcp

# Get credentials (ADC or key file)
credentials, project_id = util_gcp.get_credentials()

# Build API resource
crm = util_gcp.build_resource('cloudresourcemanager')

# Iterate paginated results
for project in util_gcp.get_resource_iterator(
    crm.projects(),
    'projects'
):
    print(project['projectId'])
```

#### `IAMSentry.plugins.gcp.base`

Base classes and mixins for GCP plugins.

```python
from IAMSentry.plugins.gcp.base import (
    GCPPluginBase,
    ValidationMixin,
    IAMPolicyModifier
)

# Use ValidationMixin for blocklist/allowlist checks
class MyProcessor(ValidationMixin):
    def __init__(self):
        self.init_validation_config({
            'blocklist_projects': ['prod-critical'],
            'allowlist_account_types': ['user']
        })

    def process(self, project, account):
        if self.validate_blocklist(project, account, 'user'):
            # Process allowed accounts
            pass

# Use IAMPolicyModifier for safe policy modifications
policy = IAMPolicyModifier.remove_member(
    policy, 'roles/editor', 'user:alice@example.com'
)
```

### Models

#### Risk Score Model

```python
from IAMSentry.models.iamriskscore import IAMRiskScoreModel

model = IAMRiskScoreModel(recommendation_dict)
score = model.score()

print(f"Risk Score: {score['risk_score']}")
print(f"Over-privilege Score: {score['over_privilege_score']}")
print(f"Safe to Apply Score: {score['safe_to_apply_recommendation_score']}")
```

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=IAMSentry --cov-report=html

# Run specific test file
pytest tests/test_gcp_utils.py -v
```

### Code Quality

```bash
# Format code
black IAMSentry tests

# Type checking
mypy IAMSentry

# Linting
flake8 IAMSentry tests
```

### Adding a New Plugin

1. Create plugin class inheriting from `GCPPluginBase`:

```python
from IAMSentry.plugins.gcp.base import GCPPluginBase, ValidationMixin

class MyCustomPlugin(GCPPluginBase, ValidationMixin):
    def __init__(self, key_file_path=None, **kwargs):
        super().__init__(key_file_path=key_file_path)
        self.init_validation_config(kwargs.get('validation', {}))

    def read(self):
        # Implement data reading
        yield {'data': 'example'}

    def done(self):
        _log.info('Plugin completed: %s', self.get_stats())
```

2. Register in `IAMSentry/plugins/__init__.py`

3. Add configuration to `config.yaml`

### Project Structure

```
IAMSentry/
├── IAMSentry/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config_models.py      # Pydantic configuration models
│   ├── ioworkers.py          # Concurrent I/O workers
│   ├── manager.py            # Audit orchestration
│   ├── workers.py            # Worker implementations
│   ├── helpers/
│   │   ├── hlogging.py       # Logging utilities
│   │   ├── hconfigs.py       # Configuration loading
│   │   ├── hsecrets.py       # Secret Manager integration
│   │   └── util.py           # General utilities
│   ├── models/
│   │   ├── iamriskscore.py   # Risk scoring model
│   │   └── applyrecommendationmodel.py
│   └── plugins/
│       ├── gcp/
│       │   ├── base.py       # Base classes and mixins
│       │   ├── util_gcp.py   # GCP utilities
│       │   ├── gcpcloud.py   # Recommendation reader
│       │   ├── gcpcloudiam.py # Recommendation processor
│       │   └── gcpiam_remediation.py # Remediation processor
│       └── files/
│           └── filestore.py  # File storage plugin
├── tests/
│   ├── conftest.py
│   ├── test_config_models.py
│   ├── test_helpers.py
│   └── test_gcp_utils.py
├── docs/
│   └── README.md             # This documentation
├── config.template.yaml
├── pyproject.toml
├── setup.cfg
└── requirements.txt
```

---

## Troubleshooting

### Common Issues

#### "No credentials found" Error

```bash
# Run ADC login
gcloud auth application-default login

# Or set credentials explicitly
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

#### "Permission denied" when reading recommendations

Ensure the service account has `roles/recommender.iamViewer`:

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:SA@PROJECT.iam.gserviceaccount.com" \
  --role="roles/recommender.iamViewer"
```

#### Worker timeouts

Increase timeout settings in configuration:

```yaml
plugins:
  gcpcloud:
    worker_timeout: 600  # 10 minutes
    queue_timeout: 120   # 2 minutes
```

---

## Attribution

IAMSentry is a fork of [CureIAM](https://github.com/gojek/CureIAM), originally created by the **Gojek Product Security Team** and released under the Apache License 2.0.

We extend our gratitude to the original authors for their foundational work on GCP IAM recommendation scanning and the Cloudmarker-based architecture.

### Significant Additions in IAMSentry

This fork has been substantially extended with the following features:

- **Web Dashboard** - Vue.js frontend with FastAPI backend for visualization
- **Authentication System** - API Key and HTTP Basic Auth support
- **Audit Logging** - Comprehensive compliance logging with HMAC signing
- **Modern CLI** - Typer-based CLI with rich output formatting
- **Security Hardening** - Input validation, command injection prevention
- **Configuration Validation** - Pydantic-based schema validation
- **Rate Limiting & CORS** - Production-ready API controls
- **Test Suite** - Comprehensive automated testing

See the [NOTICE](../NOTICE) file for full attribution details.

---

## License

This project is licensed under the Apache License 2.0. See [LICENSE](../LICENSE) for details.

Original CureIAM Copyright 2021 Gojek.
Modifications and additions Copyright 2024 Documo.

## Contributing

[Contribution guidelines]
