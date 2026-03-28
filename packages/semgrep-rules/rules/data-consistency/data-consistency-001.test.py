"""Test cases for data-consistency-001: multiple DB writes without transaction."""

# ruleid: data-consistency-001
session.add(user)
session.add(profile)
session.commit()

# ruleid: data-consistency-001
session.add(order)
session.add(payment)
session.add(audit_log)
session.commit()

# ok: wrapped in begin() context manager
with session.begin():
    session.add(user)
    session.add(profile)

# ok: single write is fine
session.add(user)
session.commit()
