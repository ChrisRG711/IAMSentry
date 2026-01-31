# IAMSentry Cloud Run Terraform Configuration
#
# This configuration deploys IAMSentry to Google Cloud Run with:
# - Service account with required IAM permissions
# - Cloud Run service with configurable settings
# - Optional Identity-Aware Proxy (IAP) for authentication
#
# Usage:
#   terraform init
#   terraform plan -var="project_id=your-project"
#   terraform apply

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.50.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0.0"
    }
  }
}

# Configure the Google Cloud provider
provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "containerregistry.googleapis.com",
    "artifactregistry.googleapis.com",
    "recommender.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iap.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# Generate API key
resource "random_password" "api_key" {
  length  = 43
  special = false
}

# Service Account for IAMSentry
resource "google_service_account" "iamsentry" {
  account_id   = "${var.service_name}-sa"
  display_name = "IAMSentry Service Account"
  description  = "Service account for IAMSentry Cloud Run service"
  project      = var.project_id

  depends_on = [google_project_service.apis]
}

# IAM permissions for the service account
resource "google_project_iam_member" "iamsentry_roles" {
  for_each = toset([
    "roles/recommender.iamViewer",
    "roles/iam.securityReviewer",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.iamsentry.email}"
}

# Additional role for remediation (optional)
resource "google_project_iam_member" "iamsentry_admin" {
  count = var.enable_remediation ? 1 : 0

  project = var.project_id
  role    = "roles/resourcemanager.projectIamAdmin"
  member  = "serviceAccount:${google_service_account.iamsentry.email}"
}

# Cloud Run service
resource "google_cloud_run_v2_service" "iamsentry" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    service_account = google_service_account.iamsentry.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.container_image != "" ? var.container_image : "gcr.io/${var.project_id}/${var.service_name}:latest"

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
      }

      ports {
        container_port = 8080
      }

      # Environment variables
      env {
        name  = "IAMSENTRY_AUTH_ENABLED"
        value = "true"
      }

      env {
        name  = "IAMSENTRY_API_KEYS"
        value = random_password.api_key.result
      }

      env {
        name  = "IAMSENTRY_LOG_FORMAT"
        value = "json"
      }

      env {
        name  = "IAMSENTRY_LOG_LEVEL"
        value = var.log_level
      }

      env {
        name  = "IAMSENTRY_DATA_DIR"
        value = "/app/output"
      }

      env {
        name  = "IAMSENTRY_METRICS_ENABLED"
        value = "true"
      }

      # IAP configuration (if enabled)
      dynamic "env" {
        for_each = var.enable_iap ? [1] : []
        content {
          name  = "IAMSENTRY_IAP_ENABLED"
          value = "true"
        }
      }

      # Startup probe
      startup_probe {
        http_get {
          path = "/api/health"
          port = 8080
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      # Liveness probe
      liveness_probe {
        http_get {
          path = "/api/health"
          port = 8080
        }
        period_seconds = 30
      }
    }

    # VPC connector (optional)
    dynamic "vpc_access" {
      for_each = var.vpc_connector != "" ? [1] : []
      content {
        connector = var.vpc_connector
        egress    = "ALL_TRAFFIC"
      }
    }
  }

  # Allow traffic
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.apis,
    google_project_iam_member.iamsentry_roles,
  ]
}

# IAM policy for public access (when IAP is disabled)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count = var.enable_iap ? 0 : 1

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.iamsentry.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# IAP Brand (OAuth consent screen) - only if IAP is enabled
resource "google_iap_brand" "iamsentry" {
  count = var.enable_iap && var.iap_support_email != "" ? 1 : 0

  support_email     = var.iap_support_email
  application_title = "IAMSentry"
  project           = var.project_id
}

# IAP OAuth Client - only if IAP is enabled
resource "google_iap_client" "iamsentry" {
  count = var.enable_iap && var.iap_support_email != "" ? 1 : 0

  display_name = "IAMSentry IAP Client"
  brand        = google_iap_brand.iamsentry[0].name
}

# Output the service URL
output "service_url" {
  description = "The URL of the deployed IAMSentry service"
  value       = google_cloud_run_v2_service.iamsentry.uri
}

output "service_account_email" {
  description = "The email of the IAMSentry service account"
  value       = google_service_account.iamsentry.email
}

output "api_key" {
  description = "The generated API key for authentication"
  value       = random_password.api_key.result
  sensitive   = true
}

output "iap_client_id" {
  description = "The IAP OAuth client ID (if IAP is enabled)"
  value       = var.enable_iap && var.iap_support_email != "" ? google_iap_client.iamsentry[0].client_id : ""
  sensitive   = true
}
