# --- Email --------------------------------------------------------------------------------
#
# Cloudflare Email Routing forwards each address to an inbox; it receives only. Replies go out
# from the inbox, e.g. with Gmail's "Send mail as".

resource "cloudflare_email_routing_address" "inbox" {
  account_id = local.cloudflare_account_id
  email      = var.email_forward_to # Cloudflare emails it a link to confirm before forwarding
}

# Turns Email Routing on and adds its MX, SPF and DKIM records to the zone.
resource "cloudflare_email_routing_dns" "brand" {
  zone_id = data.cloudflare_zone.brand.zone_id
}

resource "cloudflare_email_routing_rule" "brand" {
  for_each = toset(var.email_aliases)
  zone_id  = data.cloudflare_zone.brand.zone_id
  name     = "${each.key}@${var.brand_zone}"
  enabled  = true

  matchers = [{ type = "literal", field = "to", value = "${each.key}@${var.brand_zone}" }]
  actions  = [{ type = "forward", value = [cloudflare_email_routing_address.inbox.email] }]

  depends_on = [cloudflare_email_routing_dns.brand]
}

# Tells receiving servers how to treat mail that fails SPF/DKIM checks; p=none only monitors,
# so replies sent from Gmail as these addresses are still delivered.
resource "cloudflare_dns_record" "dmarc" {
  zone_id = data.cloudflare_zone.brand.zone_id
  name    = "_dmarc.${var.brand_zone}"
  type    = "TXT"
  content = "\"v=DMARC1; p=none\""
  ttl     = 1
}
