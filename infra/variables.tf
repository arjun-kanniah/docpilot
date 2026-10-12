variable "project_id" {
  description = "Google Cloud project to deploy into."
  type        = string
}

variable "region" {
  description = "Region for Cloud Run and Artifact Registry. us-east5 (Columbus) sits next to the Neon database in AWS us-east-2 (Ohio)."
  type        = string
  default     = "us-east5"
}

variable "zone" {
  description = "Cloudflare zone (domain) for the demo apps."
  type        = string
  default     = "arjunkanniah.dev"
}

variable "domain" {
  description = "Custom domain for the demo, served by a Cloudflare Worker."
  type        = string
  default     = "docpilot.arjunkanniah.dev"
}

variable "brand_zone" {
  description = "Cloudflare zone for the personal site."
  type        = string
  default     = "arjunkanniah.com"
}

variable "home_url" {
  description = "Where the personal site redirects until it has pages of its own."
  type        = string
  default     = "https://github.com/arjun-kanniah"
}

variable "billing_account" {
  description = "Billing account ID (XXXXXX-XXXXXX-XXXXXX) for the budget alert."
  type        = string
}

variable "monthly_budget" {
  description = "Monthly budget in the billing account's currency; alerts at 50, 90 and 100%."
  type        = number
  default     = 20
}

variable "github_repository" {
  description = "owner/name of the repository allowed to deploy."
  type        = string
  default     = "arjun-kanniah/docpilot"
}

variable "demo_models" {
  description = "Models the public demo offers. Keep these cheap: the URL is public."
  type        = list(string)
  default     = ["claude-haiku-5-5", "gpt-6-luna", "gemini-3.5-flash-lite"]
}

variable "questions_per_hour" {
  description = "Questions each visitor may ask per hour."
  type        = number
  default     = 20
}

variable "questions_per_day" {
  description = "Questions per day per running instance, across all visitors."
  type        = number
  default     = 500
}

variable "email_aliases" {
  description = "Addresses at brand_zone that forward to email_forward_to."
  type        = list(string)
  default     = ["arjun", "support"]
}

variable "email_forward_to" {
  description = "Inbox that receives the aliases. Kept in terraform.tfvars, out of the public repo."
  type        = string
}
