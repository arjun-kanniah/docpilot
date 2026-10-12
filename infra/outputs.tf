output "url" {
  description = "Public URL of the demo."
  value       = module.domain.url
}

output "run_url" {
  description = "The Cloud Run service's own URL, behind the custom domain."
  value       = module.app.uri
}

output "image" {
  description = "Image path that deploys push to (tagged with the commit SHA)."
  value       = module.app.image
}

output "workload_identity_provider" {
  description = "For GitHub Actions: google-github-actions/auth workload_identity_provider."
  value       = module.project.workload_identity_provider
}

output "deploy_service_account" {
  description = "For GitHub Actions: google-github-actions/auth service_account."
  value       = module.app.deploy_service_account
}
