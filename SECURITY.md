# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.4.x   | :white_check_mark: |
| < 0.4   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in IAMSentry, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead:

1. **Email**: Send details to the repository maintainers (check the repository for contact information)
2. **Private Disclosure**: Use GitHub's private vulnerability reporting feature if available

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Assessment**: We will assess the vulnerability and determine severity
- **Fix Timeline**: Critical vulnerabilities will be prioritized
- **Credit**: We will credit reporters in the release notes (unless you prefer anonymity)

## Security Best Practices for Users

### Credential Management

1. **Never commit credentials** to the repository
2. **Use Application Default Credentials** (ADC) when possible:
   ```bash
   gcloud auth application-default login
   ```
3. **Use Google Secret Manager** for service account keys:
   ```yaml
   key_file_path: gsm://project-id/secret-name
   ```
4. **Rotate credentials** regularly

### IAM Permissions

Grant only the minimum required permissions:

| Role | Purpose |
|------|---------|
| `roles/recommender.iamViewer` | Read IAM recommendations |
| `roles/iam.securityReviewer` | View IAM policies |
| `roles/resourcemanager.projectIamAdmin` | Apply remediations (optional) |

### Dashboard Security

When running the dashboard:

1. **Enable authentication**:
   ```bash
   export IAMSENTRY_AUTH_ENABLED=true
   export IAMSENTRY_API_KEYS="your-secure-api-key"
   ```

2. **Use HTTPS** in production (use a reverse proxy like nginx)

3. **Restrict network access** - don't expose to the public internet

4. **Review audit logs** regularly

### Configuration Security

1. Use `config.template.yaml` as a starting point
2. Keep actual config files (`config.yaml`) out of version control
3. Validate configuration before deployment

## Known Security Considerations

### Dry-Run Mode

IAMSentry defaults to dry-run mode for all remediation actions. This is a safety feature. Only enable actual remediation (`dry_run=false`) after thorough testing.

### Audit Logging

All IAM changes are logged with:
- Timestamp
- Actor (who made the change)
- Target (what was changed)
- Before/after state
- HMAC signature (for tamper detection)

### Input Validation

All user inputs are validated to prevent:
- Command injection
- Path traversal
- SQL injection (if using database backends)

## Security Updates

Security updates will be released as patch versions. Subscribe to GitHub releases to be notified of updates.
