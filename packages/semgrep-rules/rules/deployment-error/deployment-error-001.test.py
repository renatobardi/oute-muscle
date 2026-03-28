"""Test cases for deployment-error-001: hardcoded database credentials."""

# ruleid: deployment-error-001
DATABASE_URL = "postgresql://admin:secret123@prod-db.internal:5432/myapp"

# ruleid: deployment-error-001
REDIS_URL = "redis://:mypassword@cache.internal:6379/0"

# ruleid: deployment-error-001
db_password = "P@ssw0rd_prod_2024"

# ok: reads from environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")

# ok: reads from secret manager
db_password = get_secret("DB_PASSWORD")

# ok: empty string default
API_KEY = os.getenv("API_KEY", "")
