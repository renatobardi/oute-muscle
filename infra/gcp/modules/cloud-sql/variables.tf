variable "project_id"   { type = string }
variable "region"       { type = string }
variable "name_prefix"  { type = string }
variable "environment"  { type = string }
variable "labels"       { type = map(string) }
variable "db_tier" {
  type    = string
  default = "db-custom-2-7680"
}

variable "db_name" {
  type    = string
  default = "oute"
}

variable "db_user" {
  type    = string
  default = "muscle_app"
}

variable "existing_instance_name" {
  description = "Name of an existing Cloud SQL instance to reuse (shared-instance mode). Leave empty to create a dedicated instance."
  type        = string
  default     = ""
}
