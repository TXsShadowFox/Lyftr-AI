"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.mock_provider import MockProvider


@pytest.fixture(scope="session")
def mock_provider():
    provider = MockProvider()
    provider.start()
    yield provider
    provider.stop()


@pytest.fixture
def provider(mock_provider: MockProvider):
    mock_provider.reset()
    yield mock_provider
    mock_provider.reset()


@pytest.fixture
def make_settings(tmp_path: Path, provider: MockProvider):
    def _make(**overrides: Any) -> Settings:
        values: dict[str, Any] = {
            "database_url": f"sqlite:///{tmp_path / 'app.db'}",
            "llm_model": "openai/lyftr-mock",
            "llm_api_base": provider.url,
            "llm_api_keys": "test-key-1,test-key-2",
            "llm_temperature": 0.0,
            "llm_request_timeout": 10.0,
            "llm_num_retries": 0,
            "cache_enabled": True,
            "enable_failure_simulation": True,
            "allowed_origins": "http://localhost:3000,http://127.0.0.1:3000",
            "log_level": "WARNING",
            "environment": "test",
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    return _make


@pytest.fixture
def settings(make_settings):
    return make_settings()


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def second_client(make_settings):
    """Factory for a second app sharing a database URL."""

    def _open(settings: Settings) -> TestClient:
        return TestClient(create_app(settings))

    return _open
