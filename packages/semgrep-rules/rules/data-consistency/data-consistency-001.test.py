"""Test cases for data-consistency-001: consecutive session.add() outside transaction."""

# ruleid: data-consistency-001
session.add(user)
session.add(profile)
session.commit()

# ruleid: data-consistency-001
session.add(order)
# ruleid: data-consistency-001
session.add(payment)
session.add(audit_log)
session.commit()

# ok
with session.begin():
    session.add(user)
    session.add(profile)

# ok
session.add(user)
session.commit()
