"""Test cases for unsafe-regex-001: catastrophic backtracking detection."""
import re

# ruleid: unsafe-regex-001
pattern = re.compile(r"(a+)+b")

# ruleid: unsafe-regex-001
bad = re.compile(r"(\w+\s?)+$")

# ruleid: unsafe-regex-001
evil = re.compile(r"(a|aa)+b")

# ruleid: unsafe-regex-001
nested = re.compile(r"([a-zA-Z]+\d*)*end")

# ok
safe1 = re.compile(r"^[a-z0-9]+$")

# ok
safe2 = re.compile(r"^\d{1,10}$")

# ok
safe3 = re.compile(r"https?://[a-zA-Z0-9./]+")
