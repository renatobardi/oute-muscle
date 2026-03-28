"""Test cases for cascading-failure-001: retry without exponential backoff."""

import time

# ruleid: cascading-failure-001
for attempt in range(3):
    try:
        result = call_service()
        break
    except Exception:
        time.sleep(1)

# ruleid: cascading-failure-001
for i in range(5):
    try:
        response = requests.post(url, json=data)
        break
    except requests.RequestException:
        time.sleep(0.5)

# ok
for attempt in range(5):
    try:
        result = call_service()
        break
    except Exception:
        wait = 2**attempt
        time.sleep(wait)

# ok
from tenacity import retry, wait_exponential


@retry(wait=wait_exponential(multiplier=1, min=1, max=10))
def call_with_retry():
    return call_service()
