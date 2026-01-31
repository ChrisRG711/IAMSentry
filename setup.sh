#!/bin/bash
# IAMSentry Quick Setup Script
# This script helps you get started with IAMSentry quickly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    IAMSentry Setup Wizard                     ║"
echo "║         GCP IAM Security Auditor and Remediation Tool         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 found"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 not found"
        return 1
    fi
}

MISSING_DEPS=0

check_command python3 || MISSING_DEPS=1
check_command pip3 || check_command pip || MISSING_DEPS=1
check_command gcloud || echo -e "  ${YELLOW}⚠${NC} gcloud not found (optional, but recommended)"

if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "\n${RED}Error: Missing required dependencies. Please install them and try again.${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo -e "${RED}Error: Python 3.9+ required (found $PYTHON_VERSION)${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION"

echo ""

# Installation options
echo -e "${YELLOW}Installation Options:${NC}"
echo "  1) Install in current environment (pip install -e .)"
echo "  2) Create virtual environment and install"
echo "  3) Skip installation (already installed)"
echo ""
read -p "Choose option [2]: " INSTALL_OPTION
INSTALL_OPTION=${INSTALL_OPTION:-2}

case $INSTALL_OPTION in
    1)
        echo -e "\n${BLUE}Installing IAMSentry...${NC}"
        pip3 install -e ".[dashboard]"
        ;;
    2)
        echo -e "\n${BLUE}Creating virtual environment...${NC}"
        python3 -m venv .venv
        source .venv/bin/activate
        echo -e "${BLUE}Installing IAMSentry...${NC}"
        pip install -e ".[dashboard]"
        echo -e "\n${GREEN}Virtual environment created. Activate with:${NC}"
        echo -e "  source .venv/bin/activate"
        ;;
    3)
        echo -e "${YELLOW}Skipping installation...${NC}"
        ;;
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""

# GCP Authentication
echo -e "${YELLOW}GCP Authentication Setup:${NC}"
echo "  1) Use Application Default Credentials (gcloud auth)"
echo "  2) Use service account key file"
echo "  3) Skip (configure manually later)"
echo ""
read -p "Choose option [1]: " AUTH_OPTION
AUTH_OPTION=${AUTH_OPTION:-1}

KEY_FILE_PATH=""
case $AUTH_OPTION in
    1)
        echo -e "\n${BLUE}Setting up Application Default Credentials...${NC}"
        if command -v gcloud &> /dev/null; then
            gcloud auth application-default login
        else
            echo -e "${YELLOW}gcloud not found. Please run manually:${NC}"
            echo "  gcloud auth application-default login"
        fi
        ;;
    2)
        read -p "Enter path to service account key file: " KEY_FILE_PATH
        if [ ! -f "$KEY_FILE_PATH" ]; then
            echo -e "${RED}File not found: $KEY_FILE_PATH${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓${NC} Service account key file found"
        ;;
    3)
        echo -e "${YELLOW}Skipping authentication setup...${NC}"
        ;;
esac

echo ""

# Project configuration
echo -e "${YELLOW}GCP Project Configuration:${NC}"
read -p "Enter GCP project ID(s) to scan (comma-separated, or leave empty for all): " PROJECTS

# Convert to YAML array format
if [ -n "$PROJECTS" ]; then
    PROJECTS_YAML=$(echo "$PROJECTS" | sed 's/,/", "/g' | sed 's/^/["/' | sed 's/$/"]/')
else
    PROJECTS_YAML="[]"
fi

echo ""

# Dashboard configuration
echo -e "${YELLOW}Dashboard Configuration:${NC}"
read -p "Enable dashboard authentication? [Y/n]: " ENABLE_AUTH
ENABLE_AUTH=${ENABLE_AUTH:-Y}

API_KEY=""
if [[ "$ENABLE_AUTH" =~ ^[Yy]$ ]]; then
    # Generate a random API key
    API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo -e "${GREEN}Generated API key:${NC} $API_KEY"
    echo -e "${YELLOW}Save this key! You'll need it to access the dashboard.${NC}"
fi

read -p "Dashboard port [8080]: " DASHBOARD_PORT
DASHBOARD_PORT=${DASHBOARD_PORT:-8080}

echo ""

# Create configuration file
echo -e "${BLUE}Creating configuration file...${NC}"

CONFIG_FILE="config.yaml"
if [ -f "$CONFIG_FILE" ]; then
    read -p "config.yaml already exists. Overwrite? [y/N]: " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
        CONFIG_FILE="config.generated.yaml"
        echo -e "${YELLOW}Writing to $CONFIG_FILE instead${NC}"
    fi
fi

# Generate key_file_path line if provided
KEY_FILE_LINE=""
if [ -n "$KEY_FILE_PATH" ]; then
    KEY_FILE_LINE="    key_file_path: \"$KEY_FILE_PATH\""
else
    KEY_FILE_LINE="    # key_file_path: \"/path/to/service-account-key.json\"  # Optional - uses ADC if not specified"
fi

cat > "$CONFIG_FILE" << EOF
# IAMSentry Configuration
# Generated by setup.sh on $(date)

# Logging configuration
logger:
  version: 1
  disable_existing_loggers: false
  formatters:
    simple:
      format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
      datefmt: "%Y-%m-%d %H:%M:%S"
  handlers:
    console:
      class: logging.StreamHandler
      formatter: simple
      stream: ext://sys.stdout
    file:
      class: logging.handlers.TimedRotatingFileHandler
      formatter: simple
      filename: ./logs/iamsentry.log
      when: midnight
      backupCount: 7
  root:
    level: INFO
    handlers:
      - console
      - file

# Schedule for automated scans (24-hour format, or "disabled")
schedule: "disabled"

# Plugin configurations
plugins:
  # GCP Cloud Plugin - reads IAM recommendations
  gcp_iam_reader:
    plugin: IAMSentry.plugins.gcp.gcpcloud.GCPCloudIAMRecommendations
$KEY_FILE_LINE
    projects: $PROJECTS_YAML
    regions:
      - "global"
      - "us-central1"
      - "us-east1"
      - "us-west1"
      - "europe-west1"

  # IAM Processor Plugin - calculates risk scores
  gcp_iam_processor:
    plugin: IAMSentry.plugins.gcp.gcpcloudiam.GCPIAMRecommendationProcessor
    mode_scan: true
    mode_enforce: false  # Set to true to apply recommendations (DANGEROUS!)

    enforcer:
      blocklist_projects: []
      blocklist_accounts: []
      blocklist_account_types:
        - "serviceAccount"
      allowlist_account_types:
        - "user"
        - "group"
      min_safe_to_apply_score_user: 60
      min_safe_to_apply_score_group: 40
      min_safe_to_apply_score_SA: 80

  # File Storage Plugin
  file_store:
    plugin: IAMSentry.plugins.files.filestore.FileStore
    output_dir: "./output"
    file_format: "json"

# Audit definitions
audits:
  gcp_iam_audit:
    clouds:
      - gcp_iam_reader
    processors:
      - gcp_iam_processor
    stores:
      - file_store
    alerts: []
    applyRecommendations: false

# Which audits to run
run:
  - gcp_iam_audit
EOF

echo -e "${GREEN}✓${NC} Configuration written to $CONFIG_FILE"

# Create necessary directories
mkdir -p logs output

echo ""

# Create .env file for dashboard
if [ -n "$API_KEY" ]; then
    echo -e "${BLUE}Creating .env file for dashboard...${NC}"
    cat > .env << EOF
# IAMSentry Dashboard Environment Variables
# Generated by setup.sh on $(date)

# Authentication
IAMSENTRY_AUTH_ENABLED=true
IAMSENTRY_API_KEYS=$API_KEY

# Dashboard settings
IAMSENTRY_DATA_DIR=./output

# CORS (add your frontend URL if different)
IAMSENTRY_CORS_ORIGINS=http://localhost:$DASHBOARD_PORT,http://127.0.0.1:$DASHBOARD_PORT

# Rate limiting
IAMSENTRY_RATE_LIMIT=100
IAMSENTRY_RATE_WINDOW=60
EOF
    echo -e "${GREEN}✓${NC} Environment file written to .env"
fi

echo ""

# Validate setup
echo -e "${YELLOW}Validating setup...${NC}"

# Check if iamsentry command exists
if command -v iamsentry &> /dev/null || [ -f ".venv/bin/iamsentry" ]; then
    echo -e "  ${GREEN}✓${NC} iamsentry command available"
else
    echo -e "  ${YELLOW}⚠${NC} iamsentry command not in PATH (try: source .venv/bin/activate)"
fi

# Check GCP credentials
echo -e "  Checking GCP credentials..."
if python3 -c "from google.auth import default; default()" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} GCP credentials valid"
else
    echo -e "  ${YELLOW}⚠${NC} GCP credentials not configured (run: gcloud auth application-default login)"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Setup Complete!                            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""

if [ "$INSTALL_OPTION" -eq 2 ]; then
    echo "  1. Activate the virtual environment:"
    echo "     source .venv/bin/activate"
    echo ""
fi

echo "  2. Run a scan:"
echo "     iamsentry scan --config $CONFIG_FILE"
echo ""
echo "  3. Start the dashboard:"
if [ -n "$API_KEY" ]; then
    echo "     source .env && iamsentry-dashboard --port $DASHBOARD_PORT"
    echo ""
    echo "     Access at: http://localhost:$DASHBOARD_PORT"
    echo "     API Key: $API_KEY"
else
    echo "     iamsentry-dashboard --port $DASHBOARD_PORT"
    echo ""
    echo "     Access at: http://localhost:$DASHBOARD_PORT"
fi
echo ""
echo "  4. View help:"
echo "     iamsentry --help"
echo ""
echo -e "${YELLOW}Documentation:${NC} https://github.com/ChrisRG711/IAMSentry#readme"
echo ""
