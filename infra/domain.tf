# --- Custom domain ------------------------------------------------------------------------
#
# Cloud Run's own domain mapping isn't offered in us-east5, a global load balancer costs about
# USD 18 a month, and Firebase Hosting buffers responses, which breaks streamed answers. So a
# Cloudflare Worker on the free plan fronts the service instead, with the domain's DNS on
# Cloudflare. The zones themselves are added in the Cloudflare dashboard, since moving a
# domain's nameservers is a manual step at the registrar.

data "cloudflare_zone" "site" {
  filter = { name = var.zone }
}

data "cloudflare_zone" "brand" {
  filter = { name = var.brand_zone }
}

locals {
  cloudflare_account_id = data.cloudflare_zone.site.account.id
}

# Lets the API trust the visitor IP that the Worker passes on.
resource "random_password" "proxy_secret" {
  length  = 40
  special = false
}

resource "google_secret_manager_secret" "proxy" {
  secret_id = "proxy-secret"
  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "proxy" {
  secret      = google_secret_manager_secret.proxy.id
  secret_data = random_password.proxy_secret.result
}

resource "google_secret_manager_secret_iam_member" "runtime_proxy" {
  secret_id = google_secret_manager_secret.proxy.id
  role      = "roles/secretmanager.secretAccessor"
  member    = google_service_account.runtime.member
}

resource "cloudflare_workers_script" "proxy" {
  account_id         = local.cloudflare_account_id
  script_name        = "docpilot-proxy"
  content            = file("${path.module}/worker/proxy.js")
  main_module        = "proxy.js"
  compatibility_date = "2026-09-01"

  bindings = [
    {
      name = "ORIGIN_HOST"
      type = "plain_text"
      text = trimprefix(google_cloud_run_v2_service.docpilot.uri, "https://")
    },
    {
      name = "PROXY_SECRET"
      type = "secret_text"
      text = random_password.proxy_secret.result
    },
  ]
}

# Creates the DNS record and certificate for the hostname and routes it to the Worker.
resource "cloudflare_workers_custom_domain" "docpilot" {
  account_id = local.cloudflare_account_id
  zone_id    = data.cloudflare_zone.site.zone_id
  hostname   = var.domain
  service    = cloudflare_workers_script.proxy.script_name
}

# --- Redirects ------------------------------------------------------------------------------
#
# arjunkanniah.com is the personal site and arjunkanniah.dev holds the demo apps. Until the
# .com has a site, it points at home_url; the bare .dev points at the .com. Both use 302s so
# browsers don't cache them once real pages exist.
#
# The apex and www names need a proxied record for Cloudflare to answer them; 192.0.2.1 is a
# reserved documentation address, never contacted, because the redirect rule answers first.

locals {
  redirect_hosts = {
    apps_apex  = { zone = data.cloudflare_zone.site.zone_id, name = var.zone }
    apps_www   = { zone = data.cloudflare_zone.site.zone_id, name = "www.${var.zone}" }
    brand_apex = { zone = data.cloudflare_zone.brand.zone_id, name = var.brand_zone }
    brand_www  = { zone = data.cloudflare_zone.brand.zone_id, name = "www.${var.brand_zone}" }
  }
}

resource "cloudflare_dns_record" "redirect" {
  for_each = local.redirect_hosts
  zone_id  = each.value.zone
  name     = each.value.name
  type     = "A"
  content  = "192.0.2.1"
  proxied  = true
  ttl      = 1
  comment  = "Placeholder so the redirect rule can answer"
}

resource "cloudflare_ruleset" "apps_redirect" {
  zone_id = data.cloudflare_zone.site.zone_id
  name    = "Personal site redirect"
  kind    = "zone"
  phase   = "http_request_dynamic_redirect"

  rules = [{
    description = "Send the bare domain and www to the personal site"
    expression  = "http.host in {\"${var.zone}\" \"www.${var.zone}\"}"
    action      = "redirect"
    action_parameters = {
      from_value = {
        status_code = 302
        target_url  = { value = "https://${var.brand_zone}" }
      }
    }
  }]
}

resource "cloudflare_ruleset" "brand_redirect" {
  zone_id = data.cloudflare_zone.brand.zone_id
  name    = "Home redirect"
  kind    = "zone"
  phase   = "http_request_dynamic_redirect"

  rules = [{
    description = "Send the personal site to home_url until it has pages of its own"
    expression  = "http.host in {\"${var.brand_zone}\" \"www.${var.brand_zone}\"}"
    action      = "redirect"
    action_parameters = {
      from_value = {
        status_code = 302
        target_url  = { value = var.home_url }
      }
    }
  }]
}
