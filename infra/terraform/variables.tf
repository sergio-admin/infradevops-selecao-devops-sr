variable "region" {
  type    = string
  default = "us-east-2"
}

variable "project" {
  type    = string
  default = "comments"
}

variable "github_repo" {
  type    = string
  default = "sergio-admin/infradevops-selecao-devops-sr"
}

variable "node_instance_type" {
  type    = string
  default = "m7i-flex.large"
}
