variable "region" {
  type    = string
  default = "sa-east-1"
}
variable "name" {
  type    = string
  default = "locaweb"
}
variable "vps_cidrs" {
  description = "IPv4 públicos fixos da API e Airflow, exclusivamente /32."
  type        = set(string)
  validation {
    condition     = length(var.vps_cidrs) > 0 && alltrue([for c in var.vps_cidrs : can(cidrnetmask(c)) && endswith(c, "/32")])
    error_message = "Informe pelo menos um IPv4 /32; redes abertas são proibidas."
  }
}
variable "lake_bucket" { type = string }
variable "budget_email" { type = string }
variable "monthly_budget_usd" {
  type    = number
  default = 15
}
variable "instance_class" {
  type    = string
  default = "db.t3.micro"
}
variable "glue_reader_secret_arn" {
  description = "Segredo com usuário SQL somente leitura, host, dbname, username, password e port."
  type        = string
}
