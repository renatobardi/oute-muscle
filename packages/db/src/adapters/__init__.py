"""PostgreSQL adapters — real implementations of ports using SQLAlchemy + pgvector.

Placed here (packages/db) because this package has the right dependencies:
  - sqlalchemy[asyncio]
  - asyncpg
  - pgvector
  - oute-muscle-core (domain entities + port interfaces)
"""
