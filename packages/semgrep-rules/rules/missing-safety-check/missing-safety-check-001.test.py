"""Test cases for missing-safety-check-001: dict.get() result used without None check."""

# ruleid: missing-safety-check-001
token = headers.get("Authorization")
parts = token.split(" ")

# ruleid: missing-safety-check-001
value = config.get("timeout")
time.sleep(value)

# ok: default value provided to get()
timeout = config.get("timeout", 30)
time.sleep(timeout)

# ok: None check before use
token = headers.get("Authorization")
if token is not None:
    parts = token.split(" ")

# ok: walrus operator check
if token := headers.get("Authorization"):
    parts = token.split(" ")
