from media_agents.analytics.client import is_internal_email


def test_is_internal_email_none_or_empty():
    assert is_internal_email(None) is False
    assert is_internal_email("") is False


def test_is_internal_email_no_at_symbol():
    assert is_internal_email("notanemail") is False
    assert is_internal_email("user.example.com") is False


def test_is_internal_email_non_internal():
    assert is_internal_email("user@example.com") is False
    assert is_internal_email("test@gmail.com") is False


def test_is_internal_email_exact_email_match():
    assert is_internal_email("vizionik4@gmail.com") is True


def test_is_internal_email_exact_email_match_case_insensitive():
    assert is_internal_email("VIZIONIK4@gmail.com") is True
    assert is_internal_email("VIZIONIK4@GMAIL.COM") is True


def test_is_internal_email_domain_match():
    assert is_internal_email("nik@vizionikmedia.com") is True
    assert is_internal_email("someone.else@vizionikmedia.com") is True


def test_is_internal_email_domain_match_case_insensitive():
    assert is_internal_email("nik@VIZIONIKMEDIA.COM") is True
    assert is_internal_email("SOMEONE@vizionikmedia.com") is True
    assert is_internal_email("nik@VizionikMedia.com") is True
