from datetime import datetime, timezone
from enum import Enum

from media_agents.analytics.traits import (
    _tier_value,
    _isoformat,
    full_identify_payload,
    signin_traits,
    credit_traits,
    tier_traits,
)


class MockTier(Enum):
    PRO = "PRO"
    STARTER = "STARTER"


def test_tier_value():
    assert _tier_value(MockTier.PRO) == "PRO"
    assert _tier_value("CUSTOM_TIER") == "CUSTOM_TIER"
    assert _tier_value(None) == "FREE_TRIAL"
    assert _tier_value("") == "FREE_TRIAL"


def test_isoformat():
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert _isoformat(dt) == "2023-01-01T12:00:00+00:00"
    assert _isoformat("not_a_date") == "not_a_date"
    assert _isoformat(None) is None


def test_full_identify_payload_complete():
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    user = {
        "email": "test@example.com",
        "username": "tester",
        "githubId": "12345",
        "createdAt": dt,
        "subscriptionTier": MockTier.PRO,
        "subscriptionCredits": 100,
        "packCredits": 50,
        "creditsResetAt": dt,
        "stripeCustomerId": "cus_123",
    }

    result = full_identify_payload(user)

    assert result == {
        "email": "test@example.com",
        "username": "tester",
        "github_id": "12345",
        "created_at": "2023-01-01T12:00:00+00:00",
        "subscription_tier": "PRO",
        "subscription_credits": 100,
        "pack_credits": 50,
        "credits_total": 150,
        "credits_reset_at": "2023-01-01T12:00:00+00:00",
        "is_internal": False,
    }


def test_full_identify_payload_internal_email():
    user = {
        "email": "vizionik4@gmail.com",
    }
    result = full_identify_payload(user)
    assert result["is_internal"] is True

    user_domain = {
        "email": "someone@vizionikmedia.com",
    }
    result_domain = full_identify_payload(user_domain)
    assert result_domain["is_internal"] is True


def test_full_identify_payload_minimal():
    user = {}
    result = full_identify_payload(user)

    assert result == {
        "email": None,
        "username": None,
        "github_id": None,
        "created_at": None,
        "subscription_tier": "FREE_TRIAL",
        "subscription_credits": 0,
        "pack_credits": 0,
        "credits_total": 0,
        "credits_reset_at": None,
        "is_internal": False,
    }


def test_signin_traits():
    user = {
        "subscriptionTier": MockTier.STARTER,
        "subscriptionCredits": 10,
        "packCredits": 20,
        "stripeCustomerId": "cus_456",
    }
    result = signin_traits(user)

    assert result == {
        "subscription_tier": "STARTER",
        "subscription_credits": 10,
        "pack_credits": 20,
        "credits_total": 30,
    }


def test_signin_traits_minimal():
    user = {}
    result = signin_traits(user)

    assert result == {
        "subscription_tier": "FREE_TRIAL",
        "subscription_credits": 0,
        "pack_credits": 0,
        "credits_total": 0,
    }


def test_credit_traits():
    user = {
        "subscriptionCredits": 15,
        "packCredits": 5,
    }
    result = credit_traits(user)

    assert result == {
        "subscription_credits": 15,
        "pack_credits": 5,
        "credits_total": 20,
    }


def test_credit_traits_minimal():
    user = {}
    result = credit_traits(user)

    assert result == {
        "subscription_credits": 0,
        "pack_credits": 0,
        "credits_total": 0,
    }


def test_tier_traits():
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    user = {
        "subscriptionTier": "CUSTOM",
        "stripeCustomerId": "cus_789",
        "creditsResetAt": dt,
    }
    result = tier_traits(user)

    assert result == {
        "subscription_tier": "CUSTOM",
        "credits_reset_at": "2023-01-01T12:00:00+00:00",
    }


def test_tier_traits_minimal():
    user = {}
    result = tier_traits(user)

    assert result == {
        "subscription_tier": "FREE_TRIAL",
        "credits_reset_at": None,
    }