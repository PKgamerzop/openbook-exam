from alembic import context

from app.db import get_engine

engine = get_engine()

if context.is_offline_mode():
    context.configure(dialect_name=engine.dialect.name)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
