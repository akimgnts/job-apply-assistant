from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import config
from app.database.db import Base

config_section = context.config.get_section(context.config.config_ini_section)
config_section["sqlalchemy.url"] = config.DATABASE_URL

fileConfig(context.config.config_file_name)
logger = logging.getLogger('alembic.env')

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config_section
    configuration["sqlalchemy.url"] = config.DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

import logging
