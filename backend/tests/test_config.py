"""Configuration, URL and failure-header parsing units."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.database import sqlite_path_from_url
from app.services.failover_service import (
    is_retryable_failure,
    parse_failure_header,
    simulated_status_for,
)


def make_settings(**overrides) -> Settings:
    values = {"database_url": "sqlite:///./test.db", **overrides}
    return Settings(_env_file=None, **values)


def test_key_parsing_preserves_order_and_duplicates():
    settings = make_settings(llm_api_keys=" first , ,second,first ")

    assert settings.api_keys == ["first", "second", "first"]
    assert settings.key_count == 3


def test_empty_key_list_is_supported():
    settings = make_settings(llm_api_keys=" , ")

    assert settings.api_keys == []
    assert settings.key_count == 0


def test_cors_origins_are_split_and_wildcard_collapses():
    assert make_settings(allowed_origins="http://a.test, http://b.test").cors_origins == [
        "http://a.test",
        "http://b.test",
    ]
    assert make_settings(allowed_origins="http://a.test,*").cors_origins == ["*"]


def test_database_url_must_be_sqlite():
    with pytest.raises(ValidationError):
        make_settings(database_url="postgresql://user:pass@localhost/db")


@pytest.mark.parametrize(
    ("url", "path"),
    [
        ("sqlite:///./data/app.db", "./data/app.db"),
        ("sqlite:////data/app.db", "/data/app.db"),
        ("sqlite+pysqlite:///./app.db", "./app.db"),
    ],
)
def test_sqlite_url_translation(url, path):
    assert sqlite_path_from_url(url) == path


def test_blank_api_base_becomes_none():
    assert make_settings(llm_api_base="   ").llm_api_base is None


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, {}),
        ("", {}),
        ("key_1=429", {"key_1": 429}),
        ("key_1=429,key_2=500", {"key_1": 429, "key_2": 500}),
        ("*=503", {"*": 503}),
        ("key_1=429, *=502", {"key_1": 429, "*": 502}),
        ("key_1=418", {}),
        ("key_1=429,key_1=500", {"key_1": 500}),
        ("key_0=429", {}),
        ("key_1", {}),
        ("key_1=abc", {}),
        ("key_1=429,garbage,=429,key_2=500", {"key_1": 429, "key_2": 500}),
    ],
)
def test_failure_header_parser(header, expected):
    assert parse_failure_header(header) == expected


def test_specific_key_rule_takes_precedence_over_wildcard():
    simulation = {"*": 429, "key_2": 500}

    assert simulated_status_for("key_1", simulation) == 429
    assert simulated_status_for("key_2", simulation) == 500
    assert simulated_status_for("key_3", simulation) == 429


def test_only_fatal_exceptions_are_not_retryable():
    assert is_retryable_failure(RuntimeError("provider down")) is True
    assert is_retryable_failure(TimeoutError()) is True
    assert is_retryable_failure(KeyboardInterrupt()) is False
    assert is_retryable_failure(SystemExit()) is False
