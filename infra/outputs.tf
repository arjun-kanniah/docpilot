output "url" {
  description = "Public URL of the demo."
  value       = "https://${var.domain}"
}

output "run_url" {
  description = "The Cloud Run service's own URL, behind the custom domain."
  value       = google_cloud_run_v2_service.docpilot.uri
}

output "image" {
  description = "Image path that deploys push to (tagged with the commit SHA)."
  value       = local.image
}

output "workload_identity_provider" {
  description = "For GitHub Actions: google-github-actions/auth workload_identity_provider."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deploy_service_account" {
  description = "For GitHub Actions: google-github-actions/auth service_account."
  value       = google_service_account.deploy.email
}
