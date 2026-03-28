"""Test cases for unsafe-api-usage-001: unsafe deserialization."""
import pickle
import yaml

# ruleid: unsafe-api-usage-001
obj = pickle.loads(user_data)

# ruleid: unsafe-api-usage-001
config = yaml.load(request.body)

# ruleid: unsafe-api-usage-001
data = pickle.loads(redis_client.get(key))

# ok: yaml.safe_load is safe
config = yaml.safe_load(request.body)

# ok: json is safe
import json
data = json.loads(request.body)
