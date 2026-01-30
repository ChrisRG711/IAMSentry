# Contributing to IAMSentry

Thank you for your interest in contributing to IAMSentry! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Google Cloud SDK (for testing with real GCP resources)
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/documo/iamsentry.git
cd iamsentry

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
# Or:
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=IAMSentry --cov-report=html

# Run specific test file
pytest tests/test_auth_and_audit.py -v
```

### Code Quality

Before submitting a pull request, ensure your code passes all quality checks:

```bash
# Format code
black IAMSentry tests

# Sort imports
isort IAMSentry tests

# Type checking
mypy IAMSentry

# Linting
flake8 IAMSentry tests

# Security scan
bandit -r IAMSentry
```

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Use the bug report template (if available)
3. Include:
   - Python version
   - IAMSentry version
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages/logs (sanitize any sensitive data)

### Suggesting Features

1. Check existing issues/discussions
2. Describe the use case and problem it solves
3. Propose a solution if you have one

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Add/update tests as needed
5. Ensure all tests pass and code quality checks succeed
6. Commit with clear, descriptive messages
7. Push to your fork and create a Pull Request

#### Pull Request Guidelines

- Keep PRs focused on a single change
- Update documentation if needed
- Add tests for new functionality
- Follow existing code style
- Reference related issues in the PR description

## Project Structure

```
IAMSentry/
├── IAMSentry/           # Main package
│   ├── dashboard/       # Web dashboard (FastAPI + Vue.js)
│   ├── helpers/         # Utility modules
│   ├── models/          # Data models and risk scoring
│   └── plugins/         # Plugin system
│       ├── gcp/         # GCP-specific plugins
│       └── files/       # File storage plugins
├── tests/               # Test suite
├── docs/                # Documentation
└── .github/             # GitHub workflows
```

## Development Guidelines

### Adding a New Plugin

1. Inherit from the appropriate base class in `IAMSentry/plugins/gcp/base.py`
2. Implement required methods (`read()`, `eval()`, or `write()`)
3. Add configuration schema if needed
4. Write tests
5. Update documentation

### Security Considerations

- Never commit credentials or secrets
- Use environment variables or Secret Manager for sensitive config
- Validate all user inputs
- Follow the principle of least privilege for GCP permissions

## Questions?

Open an issue or discussion if you have questions about contributing.

## License

By contributing to IAMSentry, you agree that your contributions will be licensed under the Apache License 2.0.
