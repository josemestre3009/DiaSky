import sys
from pathlib import Path

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db import Base
import app.models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings().database_url)


def run_migrations_online() -> None:
    from sqlalchemy import engine_from_config, pool

    engine = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
