"""Pytest configuration and fixtures."""
import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables before any imports."""
    # Set a dummy OpenAI API key for tests that import but don't use it
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "sk-test-dummy-key-not-real"

    # Set DATABASE_URL for tests if not set
    if not os.environ.get("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    yield
