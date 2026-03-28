"""Test cases for missing-safety-check-001: dict.get() result used without None check."""

# ruleid: missing-safety-check-001
token = headers.get("Authorization")
parts = token.split(" ")

# ruleid: missing-safety-check-001
value = config.get("timeout")
time.sleep(value)

# ok
timeout = config.get("timeout", 30)
time.sleep(timeout)

# ok
token = headers.get("Authorization")
if token is not None:
    parts = token.split(" ")

# ok
if token := headers.get("Authorization"):
    parts = token.split(" ")
