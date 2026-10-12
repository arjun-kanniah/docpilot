variable "project_id" {
  description = "Google Cloud project to deploy into."
  type        = string
}

variable "region" {
  description = "Region for Cloud Run and Artifact Registry. us-east5 (Columbus) sits next to the Neon database in AWS us-east-2 (Ohio)."
  type        = string
  default     = "us-east5"
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
