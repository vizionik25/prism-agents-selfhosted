from unittest.mock import patch
import pytest
import datetime
from jose import jwt

from media_agents.services.credits import check_credits
from media_agents.services.license import LicenseService
from media_agents.auth.pwd_utils import get_password_hash, verify_password

# Hardcoded Test Private Key to sign test licenses
PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAtvyeraLbCWxANHVz+X3kFrpZPIxgo/a3q3sVunVV32x7g43X
yBLrGT/+fX1ghTArV4C5q1GwMLQTYWXi0ziy19uLgd19DCxGxAYpeQ9Z52d/unZ+
LryJ5k6nSYMcgHeaaNsJohX5pCOJ/9sjSa9VyFsZ34IpCRmbQFXnN5VqrMYxhlq0
oySwslFrgRaTJgSQ/fLrQBg9IJzrNKWCBQpfi3hJ3dLrrBILmQf1D4oilqPu1gqp
8rGGzFOf0zYXN6n7+W239EWh/KY7k6bufgcao8OxgGQUdD2TT6bl7hZrlXzPDSwa
1vg/1MppqXdeev4YC/mrbVwYDUWTgFQY1J3ToQIDAQABAoIBAAMyyC09xvlTsI2a
LfRC7I0vJacmxvumsNAo/xi6u00D7ua+QHLJTd2rni2gVuMNE/zcDaK+c0duplYR
+1R4zbtzJW2YKvre/T+o4emxSH+Ach2Wu57igcCKSGdDCOj/7i1+Ap2YJ7xkOKHF
uUis7WFqojmjY0c68Nk/hyKUFIC/kHSI/DjVKquHFhGfszk2eLyBuBMAvTistGYd
s3XuwQaw050tJ5uMXjwGwlZlIOLjRiEzsCuzJmlVdku+HZJIhoPR+Hq76DeBnFai
9abtEVrzDqtMpqNlexKuggwLzOqnnFgr4VBVFL8YexuJvr7oa/V3RLkxMo57V0dv
/hJxjqcCgYEA954zhGWmc8aZe75VEnPiY+9+kDRx2be8tdhwVorwG3WdajyRoRlS
RnX23xzymmVzdJCORWhkDKCyASCw4uCLR4xCLZehV2sw92gxLFG0s+RD0ZouxIik
8Sj9vzyzNaQcL62GKTsluX0ogtZM7Dk9oj757b137r5KrvDcx9cuTycCgYEAvS5X
EXCyFeEoU7j5aFsLDo5L/7P5eVSOLHX/Z60CQC/P2tMIILyLvzz+AiKJY8LAu2wT
1MD7/iQPqAmy1iotnIxZZjk+uqoUa8hj7VS5JAjSUDtIqEwdRwuZ5zYrrvgTaMfa
WpkqADaBkBvxSG5pOEGbPjLevf8bkyZ649UuA/cCgYB0qY+CGFZFA9O6TmFMcVa/
WM3baSoetodtcYzz6T/Y4CALNoAyU3jFA70NP1k5zwSHbbfqEZXZsThMebd9HOfi
DL39Nwxn4HPQjMFmLRSjEK+3KBpStEJp8LMkj5erdSdmey3TbS+H5eTZR9g0D3/v
WhZsoTDJRdRv+cE7UjFaTwKBgQCjoOpENnKCRC5qQ+rNXTnyDBgmAhf83qreP+16
UgVJWVFyFufH0O0aqvmVBSRKek/TjEaW1ZjgF3bHRCQ/41lyN1638TmVoLhrBXeQ
9p/wUAUAylYs4zDLm3gxqQQdoYrALWRqymGur3ZfHBwVJxKxSuWo5b0NHxNNspHG
cEQNvwKBgCPN93WvcgbQpPOV6TMP+tJwzj2h8NJjU83uxIrpDalT8X9YdIEJeHPc
Y3huGKIaegUSQOSyLw77ZAUQiCdjf6f6/YmIZX1D5s3TfCJTrYAH1Mx24RpYLohA
rAUrwJJwhOzMhq73IZT6xJasWaXj6CSsE8dhfpDR/ieFDFpLOH7X
-----END RSA PRIVATE KEY-----"""


def test_password_hashing():
    pwd = "my-secret-password"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong-pwd", hashed) is False
    assert (
        verify_password(pwd, "invalid-hash-that-will-cause-bcrypt-exception") is False
    )


def test_credits_bypass_self_hosted(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SELF_HOSTED", "true")
    import media_agents.services.credits as credits_module

    monkeypatch.setattr(credits_module, "SELF_HOSTED", True)

    user = {"subscriptionCredits": 0, "packCredits": 0}
    # Should not raise exception despite 0 credits, since it is bypassed
    check_credits(user, "image")


def test_license_verification_missing_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PRISM_LICENSE_KEY", "")
    import media_agents.services.license as license_module

    monkeypatch.setattr(license_module, "PRISM_LICENSE_KEY", "")

    assert LicenseService.get_license_claims() is None
    assert LicenseService.has_enterprise_license() is False


def test_license_verification_valid_key(monkeypatch: pytest.MonkeyPatch):
    # Manually sign JWT to avoid importing scripts folder
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    payload = {
        "iss": "prism-agents.com",
        "sub": "prism-license-key",
        "tier": "ENTERPRISE",
        "expires_at": exp.isoformat().replace("+00:00", "Z"),
        "organization": "Test Org",
        "self_hosted_domain": "localhost",
    }
    token = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

    monkeypatch.setenv("PRISM_LICENSE_KEY", token)
    import media_agents.services.license as license_module

    monkeypatch.setattr(license_module, "PRISM_LICENSE_KEY", token)

    claims = LicenseService.get_license_claims()
    assert claims is not None
    assert claims["tier"] == "ENTERPRISE"
    assert claims["organization"] == "Test Org"
    assert LicenseService.has_enterprise_license() is True


def test_verify_password_exception():
    with patch(
        "media_agents.auth.pwd_utils.bcrypt.checkpw",
        side_effect=Exception("Mocked exception"),
    ):
        assert verify_password("pwd", "hash") is False


def test_verify_password_none_input():
    assert verify_password(None, "hash") is False
    assert verify_password("pwd", None) is False
    assert verify_password(None, None) is False


def test_verify_password_invalid_hash_formats():
    pwd = "my-secret-password"
    # Empty hash
    assert verify_password(pwd, "") is False
    # Hash missing $ sign structure
    assert verify_password(pwd, "invalidhashwithoutdollarsigns") is False
    # Short string
    assert verify_password(pwd, "short") is False
