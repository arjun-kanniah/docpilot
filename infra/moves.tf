# Moves the resources into the blueprint modules without recreating them. Safe to delete
# once every state has been applied with these in place.

moved {
  from = google_project_service.apis
  to   = module.project.google_project_service.apis
}

moved {
  from = google_iam_workload_identity_pool.github
  to   = module.project.google_iam_workload_identity_pool.github
}

moved {
  from = google_iam_workload_identity_pool_provider.github
  to   = module.project.google_iam_workload_identity_pool_provider.github
}

moved {
  from = google_billing_budget.monthly
  to   = module.project.google_billing_budget.monthly[0]
}

moved {
  from = google_artifact_registry_repository.docpilot
  to   = module.app.google_artifact_registry_repository.this
}

moved {
  from = google_service_account.runtime
  to   = module.app.google_service_account.runtime
}

moved {
  from = google_secret_manager_secret_iam_member.runtime["database-url"]
  to   = module.app.google_secret_manager_secret_iam_member.runtime["DOCPILOT_DATABASE_URL"]
}

moved {
  from = google_secret_manager_secret_iam_member.runtime["anthropic-api-key"]
  to   = module.app.google_secret_manager_secret_iam_member.runtime["ANTHROPIC_API_KEY"]
}

moved {
  from = google_secret_manager_secret_iam_member.runtime["openai-api-key"]
  to   = module.app.google_secret_manager_secret_iam_member.runtime["OPENAI_API_KEY"]
}

moved {
  from = google_secret_manager_secret_iam_member.runtime["gemini-api-key"]
  to   = module.app.google_secret_manager_secret_iam_member.runtime["GEMINI_API_KEY"]
}

moved {
  from = google_secret_manager_secret_iam_member.runtime_proxy
  to   = module.app.google_secret_manager_secret_iam_member.runtime["DOCPILOT_PROXY_SECRET"]
}

moved {
  from = google_cloud_run_v2_service.docpilot
  to   = module.app.google_cloud_run_v2_service.this
}

moved {
  from = google_cloud_run_v2_service_iam_member.public
  to   = module.app.google_cloud_run_v2_service_iam_member.public[0]
}

moved {
  from = google_cloud_run_v2_job.migrate
  to   = module.app.google_cloud_run_v2_job.this["migrate"]
}

moved {
  from = google_service_account.deploy
  to   = module.app.google_service_account.deploy
}

moved {
  from = google_service_account_iam_member.deploy_from_github
  to   = module.app.google_service_account_iam_member.deploy_from_github
}

moved {
  from = google_artifact_registry_repository_iam_member.deploy_push
  to   = module.app.google_artifact_registry_repository_iam_member.deploy_push
}

moved {
  from = google_cloud_run_v2_service_iam_member.deploy_service
  to   = module.app.google_cloud_run_v2_service_iam_member.deploy_service
}

moved {
  from = google_cloud_run_v2_job_iam_member.deploy_job
  to   = module.app.google_cloud_run_v2_job_iam_member.deploy_job["migrate"]
}

moved {
  from = google_service_account_iam_member.deploy_as_runtime
  to   = module.app.google_service_account_iam_member.deploy_as_runtime
}

moved {
  from = random_password.proxy_secret
  to   = module.domain.random_password.proxy_secret
}

moved {
  from = google_secret_manager_secret.proxy
  to   = module.domain.google_secret_manager_secret.proxy
}

moved {
  from = google_secret_manager_secret_version.proxy
  to   = module.domain.google_secret_manager_secret_version.proxy
}

moved {
  from = cloudflare_workers_script.proxy
  to   = module.domain.cloudflare_workers_script.proxy
}

moved {
  from = cloudflare_workers_custom_domain.docpilot
  to   = module.domain.cloudflare_workers_custom_domain.this
}
