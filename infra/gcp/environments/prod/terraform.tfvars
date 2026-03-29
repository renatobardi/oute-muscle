project_id  = "oute-488706"
region      = "us-central1"
environment = "prod"
github_org  = "oute-me"
github_repo = "oute-muscle"

api_image = "us-central1-docker.pkg.dev/oute-488706/muscle-prod-docker/muscle-api:latest"

db_tier = "db-custom-4-15360"   # 4 vCPU / 15 GB — production sizing
db_name = "oute"
db_user = "muscle_app"

cloud_run_min_instances = 2     # warm instances — avoid cold start on prod
cloud_run_max_instances = 20
cloud_run_cpu           = "2000m"
cloud_run_memory        = "1Gi"
