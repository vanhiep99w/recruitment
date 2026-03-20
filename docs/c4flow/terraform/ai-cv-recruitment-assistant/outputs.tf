output "ec2_host" {
  description = "EC2 Elastic IP address"
  value       = aws_eip.app.public_ip
}

output "ssh_private_key" {
  description = "SSH private key for EC2 access"
  value       = tls_private_key.app.private_key_pem
  sensitive   = true
}

output "fqdn" {
  description = "Fully qualified domain name"
  value       = "${var.subdomain}.${var.domain}"
}
