variable "project_id"         { type = string }
variable "region"             { type = string }
variable "name_prefix"        { type = string }
variable "environment"        { type = string }
variable "labels"             { type = map(string) }
variable "image"              { type = string }
variable "service_account"    { type = string }
variable "db_instance"        { type = string }
variable "db_name"            { type = string }
variable "db_user"            { type = string }
variable "db_password_secret" { type = string }
variable "min_instances"      { type = number; default = 0 }
variable "max_instances"      { type = number; default = 10 }
variable "cpu"                { type = string; default = "1000m" }
variable "memory"             { type = string; default = "512Mi" }
