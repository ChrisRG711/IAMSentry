"""Centralized constants for IAMSentry.

This module contains all shared constants used across the IAMSentry package.
Import version and other constants from here to ensure consistency.
"""

from typing import Dict, List

# Version - Single source of truth
VERSION = "0.4.0"

# Default concurrency settings
DEFAULT_PROCESSES = 4
DEFAULT_THREADS = 10

# Risk score thresholds
RISK_THRESHOLDS: Dict[str, int] = {
    "critical": 90,
    "high": 70,
    "medium": 40,
    "low": 0,
}

# Safe-to-apply score defaults by account type
DEFAULT_SAFE_SCORES: Dict[str, int] = {
    "user": 60,
    "group": 40,
    "serviceAccount": 80,
}

# Account type weights for risk calculation
ACCOUNT_TYPE_WEIGHTS: Dict[str, int] = {
    "user": 2,
    "group": 3,
    "serviceAccount": 5,
}

# GCP OAuth scopes
GCP_SCOPES: List[str] = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/cloud-platform.read-only",
]

# API retry settings
API_MAX_RETRIES = 3
API_RETRY_DELAY = 1.0  # seconds
API_RETRY_MULTIPLIER = 2.0
API_TIMEOUT = 60  # seconds

# Recommendation subtypes
RECOMMENDATION_SUBTYPES = {
    "REMOVE_ROLE": "Remove role completely",
    "REPLACE_ROLE": "Replace with a smaller role",
    "REPLACE_ROLE_CUSTOMIZABLE": "Replace with custom role",
}

# Critical service account patterns (for safety checks)
CRITICAL_ACCOUNT_PATTERNS: List[str] = [
    "prod",
    "admin",
    "terraform",
    "deployment",
    "ci-cd",
    "github-actions",
]

# Output formats supported
OUTPUT_FORMATS = ["json", "csv", "yaml", "table"]

# Dashboard defaults
DASHBOARD_DEFAULT_HOST = "0.0.0.0"
DASHBOARD_DEFAULT_PORT = 8080
