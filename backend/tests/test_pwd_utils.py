from media_agents.auth.pwd_utils import verify_password, get_password_hash


def test_get_password_hash():
    # Test that it creates a valid hash
    password = "super_secret_password"
    hashed = get_password_hash(password)
    assert hashed != password
    assert isinstance(hashed, str)
    assert hashed.startswith("$2")  # A valid bcrypt hash starts with $2a$, $2b$, etc.


def test_verify_password_success():
    # Test that a valid password and hash work
    password = "super_secret_password"
    hashed = get_password_hash(password)
    result = verify_password(password, hashed)
    assert result is True


def test_verify_password_incorrect_password():
    # Test that a wrong password returns False
    password = "super_secret_password"
    hashed = get_password_hash(password)
    result = verify_password("wrong_password", hashed)
    assert result is False


def test_verify_password_invalid_hash_format():
    # Pass an invalid hash string that bcrypt can't handle
    # A valid bcrypt hash typically starts with $2a$, $2b$, etc. and has 60 characters
    result = verify_password("some_password", "invalid_hash_string")
    assert result is False


def test_verify_password_invalid_hash_format_with_valid_prefix():
    # Hash must be of specific length and format even if prefix matches
    result = verify_password("some_password", "$2b$invalid_format_hash")
    assert result is False


def test_verify_password_type_error():
    # Passing None to trigger a type error when encoding, which goes to exception block
    result = verify_password(None, "some_hash")
    assert result is False
