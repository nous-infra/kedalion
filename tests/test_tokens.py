"""Tests for channel token digests."""

from backend.api.tokens import token_digest


def test_digest_is_deterministic_and_key_dependent() -> None:
    key_a, key_b = b"a" * 32, b"b" * 32
    assert token_digest(key_a, "sample") == token_digest(key_a, "sample")
    assert token_digest(key_a, "sample") != token_digest(key_b, "sample")
    assert token_digest(key_a, "sample") != token_digest(key_a, "other")
    assert len(token_digest(key_a, "sample")) == 32
