terraform {
  required_version = ">= 1.15"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.4.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.27.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7.0"
    }
  }

  # State lives in a versioned bucket created by `just infra-bootstrap`.
  # The bucket name is passed at init: terraform init -backend-config="bucket=<name>"
  backend "gcs" {
    prefix = "docpilot"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region

  # Budgets are a billing-account API; bill its quota to this project.
  user_project_override = true
  billing_project       = var.project_id
}
