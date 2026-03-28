variable "project_id"   { type = string }
variable "region"       { type = string }
variable "name_prefix"  { type = string }
variable "environment"  { type = string }
variable "labels"       { type = map(string) }
variable "db_tier"      { type = string; default = "db-custom-2-7680" }
variable "db_name"      { type = string; default = "oute" }
variable "db_user"      { type = string; default = "muscle_app" }
