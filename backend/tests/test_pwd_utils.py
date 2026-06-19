from media_agents.auth.pwd_utils import verify_password


def test_verify_password_invalid_hash_format():
    # Pass an invalid hash string that bcrypt can't handle
    # A valid bcrypt hash typically starts with $2a$, $2b$, etc. and has 60 characters
    result = verify_password("some_password", "invalid_hash_string")
    assert result is False


def test_verify_password_invalid_hash_format_with_valid_prefix():
    # Hash must be of specific length and format even if prefix matches
    result = verify_password("some_password", "$2b$invalid_format_hash")
    assert result is False
