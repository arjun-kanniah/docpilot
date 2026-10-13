# DocPilot on Cloud Run, built from the cloudrun-blueprint modules.

module "project" {
  source = "github.com/arjun-kanniah/cloudrun-blueprint//modules/project?ref=v0.1.0"

  project_id          = var.project_id
  github_repositories = [var.github_repository]
  billing_account     = var.billing_account
  budget_name         = "DocPilot monthly"
  monthly_budget      = var.monthly_budget
}

module "app" {
  source = "github.com/arjun-kanniah/cloudrun-blueprint//modules/service?ref=v0.1.0"

  project_id                  = var.project_id
  region                      = var.region
  name                        = "docpilot"
  display_name                = "DocPilot"
  github_repository           = var.github_repository
  workload_identity_pool_name = module.project.workload_identity_pool_name

  memory        = "1Gi"
  concurrency   = 20
  max_instances = 2 # hard ceiling on cost and on LLM spend
  health_path   = "/api/health"

  env = {
    DOCPILOT_DEMO_MODE               = "true"
    DOCPILOT_LLM_PROVIDER            = "anthropic"
    DOCPILOT_ALLOWED_MODELS          = jsonencode(var.demo_models)
    DOCPILOT_ANSWER_MAX_TOKENS       = "4000"
    DOCPILOT_DEMO_QUESTIONS_PER_HOUR = tostring(var.questions_per_hour)
    DOCPILOT_DEMO_QUESTIONS_PER_DAY  = tostring(var.questions_per_day)
  }

  # Created by `just secret <id>`, never by Terraform, so values stay out of state.
  secrets = {
    DOCPILOT_DATABASE_URL = "database-url"
    ANTHROPIC_API_KEY     = "anthropic-api-key"
    OPENAI_API_KEY        = "openai-api-key"
    GEMINI_API_KEY        = "gemini-api-key"
    DOCPILOT_PROXY_SECRET = module.domain.proxy_secret_id
  }

  # Migrations and the demo library, run by each deploy before the new revision goes live.
  jobs = {
    migrate = {
      command    = ["sh", "-c"]
      args       = ["alembic upgrade head && python -m docpilot.seed demo/library/*"]
      memory     = "1Gi"
      secret_env = ["DOCPILOT_DATABASE_URL"]
    }
  }

  depends_on = [module.project]
}

module "domain" {
  source = "github.com/arjun-kanniah/cloudrun-blueprint//modules/cloudflare-domain?ref=v0.1.0"

  project_id       = var.project_id
  zone             = var.zone
  hostname         = var.domain
  origin_url       = module.app.uri
  name             = "docpilot"
  secret_id        = "proxy-secret"
  client_ip_header = "x-docpilot-client-ip"
  secret_header    = "x-docpilot-proxy-secret"

  depends_on = [module.project]
}
