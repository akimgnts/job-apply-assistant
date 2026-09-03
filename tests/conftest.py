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
