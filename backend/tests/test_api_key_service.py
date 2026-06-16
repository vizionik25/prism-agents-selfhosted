"""Tests for the API key service — generation, hashing, validation."""

from __future__ import annotations

import hashlib
import re

from media_agents.services.api_key import (
    generate_raw_key,
    hash_key,
    key_prefix,
    MAX_KEYS_PER_USER,
    API_KEY_PREFIX,
    DISCLAIMER_TEXT,
)


def test_generate_raw_key_format():
    raw = generate_raw_key()
    assert raw.startswith(API_KEY_PREFIX)
    assert len(raw) > 40
    assert len(raw) < 60


def test_generate_raw_key_unique():
    keys = {generate_raw_key() for _ in range(50)}
    assert len(keys) == 50


def test_hash_key_deterministic():
    raw = generate_raw_key()
    assert hash_key(raw) == hash_key(raw)


def test_hash_key_is_sha256_hex():
    raw = generate_raw_key()
    h = hash_key(raw)
    assert len(h) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", h)


def test_hash_key_matches_manual_sha256():
    raw = "sk-prism-testvalue123"
    expected = hashlib.sha256(raw.encode()).hexdigest()
    assert hash_key(raw) == expected


def test_key_prefix_returns_first_12_chars():
    raw = "sk-prism-abcdefghijklmnopqrstuvwxyz"
    assert key_prefix(raw) == "sk-prism-abc..."


def test_max_keys_is_10():
    assert MAX_KEYS_PER_USER == 10


def test_disclaimer_text_not_empty():
    assert len(DISCLAIMER_TEXT) > 100
