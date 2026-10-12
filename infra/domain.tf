# The DocPilot custom domain itself is the blueprint's cloudflare-domain module (main.tf).
# The zones are added in the Cloudflare dashboard, since moving a domain's nameservers is a
# manual step at the registrar.

data "cloudflare_zone" "site" {
  filter = { name = var.zone }
}

data "cloudflare_zone" "brand" {
  filter = { name = var.brand_zone }
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
