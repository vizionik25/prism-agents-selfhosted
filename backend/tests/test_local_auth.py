import pytest

from media_agents.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


# Local auth tests are skipped as local auth is disabled
@pytest.mark.skip(reason="Local authentication is disabled.")
def test_register_weak_password():
    pass


@pytest.mark.skip(reason="Local authentication is disabled.")
def test_register_weak_password_no_special():
    pass


@pytest.mark.skip(reason="Local authentication is disabled.")
def test_register_strong_password():
    pass
