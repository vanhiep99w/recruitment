variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "domain" {
  description = "Root domain (e.g. example.com)"
  type        = string
}

variable "subdomain" {
  description = "Subdomain prefix (e.g. my-app)"
  type        = string
}

variable "app_port" {
  description = "Application port on EC2"
  type        = number
  default     = 3000
}

variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for the domain"
  type        = string
}

variable "ssh_cidr" {
  description = "CIDR block allowed to SSH to the EC2 instance"
  type        = string
}

variable "certbot_email" {
  description = "Email for Let's Encrypt certificate notifications"
  type        = string
}
