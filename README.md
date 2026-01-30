# IAMSentry

[![CI](https://github.com/documo/iamsentry/actions/workflows/ci.yml/badge.svg)](https://github.com/documo/iamsentry/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)


**GCP IAM Security Auditor and Remediation Tool**

IAMSentry automatically analyzes Google Cloud Platform's Identity and Access Management (IAM) configurations to identify over-privileged access, calculate risk scores, and optionally apply recommended security fixes.

## Features

- **IAM Recommendation Scanning** - Fetches recommendations from GCP's IAM Recommender API
- **Risk Scoring** - Calculates risk scores based on account type, privilege level, and usage patterns
- **Web Dashboard** - Visual interface for reviewing recommendations and applying remediations
- **Automated Remediation** - Safely apply recommendations with dry-run mode (enabled by default)
- **Audit Logging** - Comprehensive compliance logging with optional HMAC signing
- **Authentication** - API Key and HTTP Basic Auth for dashboard security

## Quick Start

```bash
# Install
pip install -e .

# Authenticate with GCP
gcloud auth application-default login

# Check status
iamsentry status

# Scan for recommendations
iamsentry scan --config config.yaml --output ./output

# Start the dashboard
iamsentry-dashboard --port 8080
```

## Documentation

See [docs/README.md](docs/README.md) for full documentation including:
- Configuration guide
- Authentication setup
- Architecture overview
- Plugin development
- API reference

## Attribution

IAMSentry is a fork of [CureIAM](https://github.com/gojek/CureIAM), originally developed by the **Gojek Product Security Team** and released under the Apache License 2.0.

We are grateful to the original authors for their foundational work on GCP IAM recommendation scanning built upon the Cloudmarker framework.

### What's New in IAMSentry

This fork has been substantially extended with:

| Feature | Description |
|---------|-------------|
| Web Dashboard | Vue.js + FastAPI visualization interface |
| Authentication | API Key and HTTP Basic Auth support |
| Audit Logging | Compliance logging with HMAC signing |
| Modern CLI | Typer-based CLI with rich formatting |
| Security Hardening | Input validation, injection prevention |
| Test Suite | Comprehensive automated testing |

See [NOTICE](NOTICE) for full attribution details.

## License

Licensed under the Apache License 2.0.

- Original CureIAM Copyright 2021 Gojek
- Modifications and additions Copyright 2024 Documo

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

