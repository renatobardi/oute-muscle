"""Test cases for race-condition-001: TOCTOU file race condition."""
import os

# ruleid: race-condition-001
if os.path.exists("/tmp/lock"):
    os.remove("/tmp/lock")

# ruleid: race-condition-001
if os.path.exists(config_file):
    with open(config_file) as f:
        data = f.read()

# ruleid: race-condition-001
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# ok: atomic makedirs avoids TOCTOU
os.makedirs(output_dir, exist_ok=True)

# ok: direct open without prior existence check
with open("file.txt", "w") as f:
    f.write("data")
