"""Test cases for missing-error-handling-001: silent exception swallowing."""

# ruleid: missing-error-handling-001
try:
    risky_operation()
except Exception:
    pass

# ruleid: missing-error-handling-001
try:
    connect_to_db()
except:
    pass

# ruleid: missing-error-handling-001
try:
    parse_config()
except Exception as e:
    pass

# ok: exception is logged and re-raised
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed: %s", e)
    raise

# ok: exception re-raised as domain error
try:
    connect_to_db()
except ConnectionError as e:
    raise RuntimeError("DB unavailable") from e

# ok: intentional KeyError default
try:
    value = cache[key]
except KeyError:
    value = default
