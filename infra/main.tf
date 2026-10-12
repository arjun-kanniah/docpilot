locals {
  services = [
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sts.googleapis.com",
  ]

  # Secret Manager secret ID => environment variable in the container.
  # The secrets and their values are created by `just secret <id>`, never by Terraform,
  # so values stay out of Terraform state.
  secrets = {
    "database-url"      = "DOCPILOT_DATABASE_URL"
    "anthropic-api-key" = "ANTHROPIC_API_KEY"
    "openai-api-key"    = "OPENAI_API_KEY"
    "gemini-api-key"    = "GEMINI_API_KEY"
  }

  image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docpilot.repository_id}/docpilot"

  # The first apply runs a placeholder; deploys replace the image (see lifecycle blocks).
  placeholder_image = "us-docker.pkg.dev/cloudrun/container/hello"
}

resource "google_project_service" "apis" {
  for_each           = toset(local.services)
  service            = each.value
  disable_on_destroy = false
}

# --- Container images ---------------------------------------------------------------------

resource "google_artifact_registry_repository" "docpilot" {
  repository_id = "docpilot"
  location      = var.region
  format        = "DOCKER"
  description   = "DocPilot images"

  # Keep the free 0.5 GB tier: only the latest few images are worth keeping.
  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 3
    }
  }
  cleanup_policies {
    id     = "delete-older"
    action = "DELETE"
    condition {
      older_than = "86400s"
    }
  }

  depends_on = [google_project_service.apis]
}

# --- Runtime identity and secrets ---------------------------------------------------------

resource "google_service_account" "runtime" {
  account_id   = "docpilot-run"
  display_name = "DocPilot runtime"
  description  = "Runs the Cloud Run service and migration job. Reads only DocPilot's secrets."

  depends_on = [google_project_service.apis]
}

data "google_secret_manager_secret" "app" {
  for_each  = local.secrets
  secret_id = each.key

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "runtime" {
  for_each  = local.secrets
  secret_id = data.google_secret_manager_secret.app[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.runtime.member
}

# --- The web app and API ------------------------------------------------------------------

resource "google_cloud_run_v2_service" "docpilot" {
  name                = "docpilot"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account                  = google_service_account.runtime.email
    max_instance_request_concurrency = 20
    timeout                          = "300s"

    scaling {
      min_instance_count = 0 # scale to zero: no cost when idle
      max_instance_count = 2 # hard ceiling on cost and on LLM spend
    }

    containers {
      image = local.placeholder_image

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      dynamic "env" {
        for_each = {
          DOCPILOT_DEMO_MODE               = "true"
          DOCPILOT_LLM_PROVIDER            = "anthropic"
          DOCPILOT_ALLOWED_MODELS          = jsonencode(var.demo_models)
          DOCPILOT_ANSWER_MAX_TOKENS       = "4000"
          DOCPILOT_DEMO_QUESTIONS_PER_HOUR = tostring(var.questions_per_hour)
          DOCPILOT_DEMO_QUESTIONS_PER_DAY  = tostring(var.questions_per_day)
        }
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.secrets
        content {
          name = env.value
          value_source {
            secret_key_ref {
              secret  = data.google_secret_manager_secret.app[env.key].secret_id
              version = "latest"
            }
          }
        }
      }

      startup_probe {
        http_get {
          path = "/api/health"
        }
        period_seconds    = 2
        failure_threshold = 30
      }
    }
  }

  lifecycle {
    # Deploys (GitHub Actions) set the image; Terraform owns everything else.
    ignore_changes = [template[0].containers[0].image, client, client_version]
  }

  depends_on = [google_secret_manager_secret_iam_member.runtime]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.docpilot.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Migrations and demo documents, run by each deploy before the new revision goes live.
resource "google_cloud_run_v2_job" "migrate" {
  name                = "docpilot-migrate"
  location            = var.region
  deletion_protection = false

  template {
    template {
      service_account = google_service_account.runtime.email
      max_retries     = 1
      timeout         = "600s"

      containers {
        image   = local.placeholder_image
        command = ["sh", "-c"]
        args    = ["alembic upgrade head && python -m docpilot.seed demo/aurora_knowledge_base.pdf"]

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        env {
          name = "DOCPILOT_DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = data.google_secret_manager_secret.app["database-url"].secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image, client, client_version]
  }

  depends_on = [google_secret_manager_secret_iam_member.runtime]
}

# --- Deploys from GitHub Actions, without key files --------------------------------------

resource "google_service_account" "deploy" {
  account_id   = "docpilot-deploy"
  display_name = "DocPilot deploy (GitHub Actions)"
  description  = "Pushes images and deploys DocPilot. Usable only from the main branch of the repo."

  depends_on = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"

  depends_on = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  # Only this repository's main branch can get tokens at all.
  attribute_condition = "assertion.repository == '${var.github_repository}' && assertion.ref == 'refs/heads/main'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "deploy_from_github" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

resource "google_artifact_registry_repository_iam_member" "deploy_push" {
  repository = google_artifact_registry_repository.docpilot.name
  location   = var.region
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.deploy.member
}

resource "google_cloud_run_v2_service_iam_member" "deploy_service" {
  name     = google_cloud_run_v2_service.docpilot.name
  location = var.region
  role     = "roles/run.developer"
  member   = google_service_account.deploy.member
}

resource "google_cloud_run_v2_job_iam_member" "deploy_job" {
  name     = google_cloud_run_v2_job.migrate.name
  location = var.region
  role     = "roles/run.developer"
  member   = google_service_account.deploy.member
}

# Deploying a revision that runs as the runtime account requires acting as it.
resource "google_service_account_iam_member" "deploy_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = google_service_account.deploy.member
}

# --- Spending alert -----------------------------------------------------------------------

data "google_project" "this" {}

resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account
  display_name    = "DocPilot monthly"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
    # Count spending before credits, so alerts fire while the free-trial credit is in use
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      units = tostring(var.monthly_budget)
    }
  }

  dynamic "threshold_rules" {
    for_each = [0.5, 0.9, 1.0]
    content {
      threshold_percent = threshold_rules.value
    }
  }

  depends_on = [google_project_service.apis]
}
