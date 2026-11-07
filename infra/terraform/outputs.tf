output "region" {
  value = var.region
}

output "cluster_name" {
  value = module.eks.cluster_name
}

output "ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "rds_address" {
  value = aws_db_instance.this.address
}

output "rds_secret_arn" {
  value = aws_db_instance.this.master_user_secret[0].secret_arn
}

output "external_secrets_role_arn" {
  value = aws_iam_role.external_secrets.arn
}

output "github_actions_user" {
  value = aws_iam_user.github_actions.name
}
