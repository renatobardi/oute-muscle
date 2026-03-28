"""Test cases for resource-exhaustion-001: HTTP requests without timeout."""

import requests

# ruleid: resource-exhaustion-001
response = requests.get(url)

# ruleid: resource-exhaustion-001
data = requests.post(api_url, json=payload)

# ruleid: resource-exhaustion-001
result = requests.put(endpoint, data=body)

# ok
response = requests.get(url, timeout=30)

# ok
response = requests.get(url, timeout=(3.05, 27))

# ok
session = requests.Session()
response = session.get(url, timeout=10)
