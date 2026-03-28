"""Test cases for injection-001: SQL injection via string formatting."""

# ruleid: injection-001
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# ruleid: injection-001
cursor.execute("SELECT * FROM %s WHERE name = '%s'" % (table, name))

# ruleid: injection-001
cursor.execute(f"UPDATE users SET role = '{role}' WHERE id = {uid}")

# ok
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# ok
cursor.execute("SELECT * FROM users WHERE name = :name", {"name": name})

# ok
User.objects.filter(id=user_id).first()
