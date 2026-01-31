# IAMSentry Cloud Run Terraform Variables
#
# Copy terraform.tfvars.example to terraform.tfvars and customize values.

variable "project_id" {
  description = "The GCP project ID to deploy to"
  type        = string
}

variable "region" {
  description = "The GCP region for Cloud Run deployment"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
  default     = "iamsentry"
}

variable "container_image" {
  description = "Container image to deploy (leave empty to use gcr.io/PROJECT/SERVICE:latest)"
  type        = string
  default     = ""
}

# Scaling configuration
variable "min_instances" {
  description = "Minimum number of instances (0 for scale-to-zero)"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

# Resource limits
variable "cpu" {
  description = "CPU limit for each instance"
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory limit for each instance"
  type        = string
  default     = "512Mi"
}

# Logging
variable "log_level" {
  description = "Logging level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"
}

# IAP configuration
variable "enable_iap" {
  description = "Enable Identity-Aware Proxy for authentication"
  type        = bool
  default     = false
}

variable "iap_support_email" {
  description = "Support email for IAP OAuth consent screen (required if enable_iap=true)"
  type        = string
  default     = ""
}

variable "iap_allowed_members" {
  description = "List of members allowed to access via IAP (e.g., 'user:admin@example.com')"
  type        = list(string)
  default     = []
}

# Remediation
variable "enable_remediation" {
  description = "Grant service account permissions to apply IAM changes (dangerous!)"
  type        = bool
  default     = false
}

# Networking
variable "vpc_connector" {
  description = "VPC connector for private networking (optional)"
  type        = string
  default     = ""
}

# Tags
variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default = {
    app         = "iamsentry"
    managed-by  = "terraform"
    environment = "production"
  }
}
