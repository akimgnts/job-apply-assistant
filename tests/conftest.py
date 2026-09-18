"""Test configuration and fixtures.

Sets up PYTHONPATH, environment, and async test support.
"""
import os
import sys
from pathlib import Path

# Add project root to PYTHONPATH so 'app' module can be imported
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test OpenAI API key (mock)
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "sk-test-mock-key")
os.environ["TELEGRAM_BOT_TOKEN"] = os.environ.get("TELEGRAM_BOT_TOKEN", "dummy-test-token")

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_db_session():
    """Mock async DB session (optional for Phase 3 tests)."""
    from unittest.mock import MagicMock
    return MagicMock()


@pytest.fixture
def test_db():
    """PostgreSQL test database fixture.

    Requires TEST_DATABASE_URL env var pointing to test database.
    Refuses to run if URL is missing or not a test database.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.database.models import Base

    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if not test_db_url:
        pytest.skip("TEST_DATABASE_URL not set. Run tests with: TEST_DATABASE_URL='postgresql+psycopg2://testuser:testpass@localhost:5432/test_job' pytest")

    # Refuse non-test databases
    if "test" not in test_db_url.lower():
        raise RuntimeError(f"TEST_DATABASE_URL must contain 'test' in database name. Got: {test_db_url}")

    if "sqlite" in test_db_url:
        raise RuntimeError("TEST_DATABASE_URL points to SQLite. Use PostgreSQL for integration tests.")

    engine = create_engine(test_db_url, echo=False)

    # Verify connection
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            if "PostgreSQL" not in version:
                raise RuntimeError(f"Expected PostgreSQL, got: {version}")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to test database: {e}")

    # Create all tables
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    # Create default test company
    from app.database.models import Company
    company = Company(id=1, name="Test Company")
    session.add(company)
    session.commit()

    yield session

    session.close()

    # Cleanup: drop all tables after test
    Base.metadata.drop_all(engine)
