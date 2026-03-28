"""Test cases for injection-001: SQL injection via string formatting."""

# ruleid: injection-001
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# ruleid: injection-001
cursor.execute("SELECT * FROM %s WHERE name = '%s'" % (table, name))

# ruleid: injection-001
cursor.execute("UPDATE users SET role = '{}' WHERE id = {}".format(role, uid))

# ok: parameterized query with tuple
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# ok: parameterized query with named params
cursor.execute("SELECT * FROM users WHERE name = :name", {"name": name})

# ok: ORM filter
User.objects.filter(id=user_id).first()
