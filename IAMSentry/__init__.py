"""IAMSentry - GCP IAM Security Auditor and Remediation Tool.

IAMSentry automatically analyzes Google Cloud Platform's Identity and Access
Management (IAM) configurations to identify over-privileged access, calculate
risk scores, and optionally apply recommended security fixes.

Example:
    >>> from IAMSentry import __version__
    >>> print(__version__)
    '0.4.0'
"""

from IAMSentry.constants import VERSION

__version__ = VERSION
__all__ = ["__version__"]
