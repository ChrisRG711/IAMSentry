#!/bin/bash
# IAMSentry Cloud Run Deployment Script
#
# Usage:
#   ./deploy.sh                    # Interactive mode
#   ./deploy.sh --project my-proj  # With arguments
#
# Environment variables (optional):
#   PROJECT_ID    - GCP project ID
#   REGION        - GCP region (default: us-central1)
#   SERVICE_NAME  - Cloud Run service name (default: iamsentry)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           IAMSentry Cloud Run Deployment                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Default values
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-iamsentry}"
MIN_INSTANCES=0
MAX_INSTANCES=10
MEMORY="512Mi"
CPU="1"
ENABLE_IAP="false"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project)
            PROJECT_ID="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -n|--name)
            SERVICE_NAME="$2"
            shift 2
            ;;
        --enable-iap)
            ENABLE_IAP="true"
            shift
            ;;
        --min-instances)
            MIN_INSTANCES="$2"
            shift 2
            ;;
        --max-instances)
            MAX_INSTANCES="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -p, --project      GCP project ID (required)"
            echo "  -r, --region       GCP region (default: us-central1)"
            echo "  -n, --name         Service name (default: iamsentry)"
            echo "  --enable-iap       Enable Identity-Aware Proxy"
            echo "  --min-instances    Minimum instances (default: 0)"
            echo "  --max-instances    Maximum instances (default: 10)"
            echo "  -h, --help         Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

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

check_command gcloud || { echo -e "${RED}Please install Google Cloud SDK${NC}"; exit 1; }
check_command docker || { echo -e "${RED}Please install Docker${NC}"; exit 1; }

# Get project ID if not set
if [ -z "$PROJECT_ID" ]; then
    # Try to get from gcloud config
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

    if [ -z "$PROJECT_ID" ]; then
        read -p "Enter GCP project ID: " PROJECT_ID
    else
        read -p "Use project '$PROJECT_ID'? [Y/n]: " confirm
        if [[ "$confirm" =~ ^[Nn]$ ]]; then
            read -p "Enter GCP project ID: " PROJECT_ID
        fi
    fi
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID is required${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Deployment Configuration:${NC}"
echo "  Project:      $PROJECT_ID"
echo "  Region:       $REGION"
echo "  Service:      $SERVICE_NAME"
echo "  IAP Enabled:  $ENABLE_IAP"
echo ""

read -p "Continue with deployment? [Y/n]: " confirm
if [[ "$confirm" =~ ^[Nn]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Step 1: Enable APIs
echo ""
echo -e "${YELLOW}Step 1: Enabling required APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    containerregistry.googleapis.com \
    artifactregistry.googleapis.com \
    recommender.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com \
    --project=$PROJECT_ID

echo -e "${GREEN}✓${NC} APIs enabled"

# Step 2: Create service account
echo ""
echo -e "${YELLOW}Step 2: Setting up service account...${NC}"

SA_NAME="iamsentry-sa"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# Check if SA exists
if gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &>/dev/null; then
    echo "  Service account already exists: $SA_EMAIL"
else
    gcloud iam service-accounts create $SA_NAME \
        --display-name="IAMSentry Service Account" \
        --project=$PROJECT_ID
    echo "  Created service account: $SA_EMAIL"
fi

# Grant permissions
echo "  Granting IAM permissions..."

ROLES=(
    "roles/recommender.iamViewer"
    "roles/iam.securityReviewer"
    "roles/resourcemanager.projectIamAdmin"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$role" \
        --quiet 2>/dev/null || true
    echo "    - $role"
done

echo -e "${GREEN}✓${NC} Service account configured"

# Step 3: Build Docker image
echo ""
echo -e "${YELLOW}Step 3: Building Docker image...${NC}"

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME:$(date +%Y%m%d-%H%M%S)"
IMAGE_LATEST="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"

echo "  Building: $IMAGE_TAG"
docker build -t $IMAGE_TAG -t $IMAGE_LATEST .

echo -e "${GREEN}✓${NC} Image built"

# Step 4: Push to Container Registry
echo ""
echo -e "${YELLOW}Step 4: Pushing image to Container Registry...${NC}"

# Configure Docker for GCR
gcloud auth configure-docker gcr.io --quiet

docker push $IMAGE_TAG
docker push $IMAGE_LATEST

echo -e "${GREEN}✓${NC} Image pushed"

# Step 5: Generate API key
echo ""
echo -e "${YELLOW}Step 5: Generating API key...${NC}"

API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32 | tr -d '/+=' | head -c 43)

echo -e "${GREEN}✓${NC} API key generated"
echo ""
echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  SAVE THIS API KEY - IT WILL NOT BE SHOWN AGAIN!             ║${NC}"
echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  API Key: ${GREEN}$API_KEY${NC}"
echo ""

# Step 6: Deploy to Cloud Run
echo ""
echo -e "${YELLOW}Step 6: Deploying to Cloud Run...${NC}"

# Build environment variables
ENV_VARS="IAMSENTRY_AUTH_ENABLED=true"
ENV_VARS+=",IAMSENTRY_API_KEYS=$API_KEY"
ENV_VARS+=",IAMSENTRY_LOG_FORMAT=json"
ENV_VARS+=",IAMSENTRY_DATA_DIR=/app/output"

if [ "$ENABLE_IAP" = "true" ]; then
    ENV_VARS+=",IAMSENTRY_IAP_ENABLED=true"
fi

gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_LATEST \
    --platform=managed \
    --region=$REGION \
    --service-account=$SA_EMAIL \
    --set-env-vars="$ENV_VARS" \
    --min-instances=$MIN_INSTANCES \
    --max-instances=$MAX_INSTANCES \
    --memory=$MEMORY \
    --cpu=$CPU \
    --allow-unauthenticated \
    --project=$PROJECT_ID

echo -e "${GREEN}✓${NC} Deployed to Cloud Run"

# Step 7: Get service URL
echo ""
echo -e "${YELLOW}Step 7: Getting service URL...${NC}"

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(status.url)')

echo -e "${GREEN}✓${NC} Service URL: $SERVICE_URL"

# Summary
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Deployment Complete!                             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Service Details:${NC}"
echo "  URL:             $SERVICE_URL"
echo "  Service Account: $SA_EMAIL"
echo "  Region:          $REGION"
echo ""
echo -e "${BLUE}Access:${NC}"
echo "  Dashboard:   $SERVICE_URL"
echo "  API Health:  $SERVICE_URL/api/health"
echo "  Metrics:     $SERVICE_URL/metrics"
echo ""
echo -e "${BLUE}API Authentication:${NC}"
echo "  curl -H \"X-API-Key: $API_KEY\" $SERVICE_URL/api/stats"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Save your API key securely"
echo "  2. Configure CORS origins if needed"
echo "  3. Set up Cloud Scheduler for automated scans"
if [ "$ENABLE_IAP" = "true" ]; then
    echo "  4. Configure IAP OAuth consent and grant access"
fi
echo ""
