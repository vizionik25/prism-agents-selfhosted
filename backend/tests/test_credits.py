import pytest

from media_agents.services.credits import (
    CREDIT_COSTS,
    TIER_CREDITS,
    get_command_type,
    check_credits,
)


def test_credit_costs_defined():
    assert CREDIT_COSTS["image"] == 1
    assert CREDIT_COSTS["video"] == 5
    assert CREDIT_COSTS["music"] == 3
    assert CREDIT_COSTS["3d"] == 10
    assert CREDIT_COSTS["remesh"] == 8
    assert CREDIT_COSTS["retexture"] == 8
    assert CREDIT_COSTS["research"] == 2
    assert CREDIT_COSTS["agent"] == 2
    assert CREDIT_COSTS["chat"] == 1
    assert CREDIT_COSTS["help"] == 0


def test_tier_credits_defined():
    assert TIER_CREDITS["FREE_TRIAL"] == 0
    assert TIER_CREDITS["STARTER"] == 30
    assert TIER_CREDITS["PLUS"] == 100
    assert TIER_CREDITS["PRO"] == 250


def test_get_command_type_image():
    assert get_command_type("/image a cat") == "image"


def test_get_command_type_video():
    assert get_command_type("/video a sunset") == "video"
    assert get_command_type("/motion a dancer") == "video"


def test_get_command_type_music():
    assert get_command_type("/music lofi beat") == "music"


def test_get_command_type_3d():
    assert get_command_type("/3d a tree") == "3d"
    assert get_command_type("/image-to-3d") == "3d"


def test_get_command_type_remesh():
    assert get_command_type("/remesh") == "remesh"


def test_get_command_type_retexture():
    assert get_command_type("/retexture") == "retexture"


def test_get_command_type_research():
    assert get_command_type("/research topic") == "research"


def test_get_command_type_create_agent():
    assert get_command_type("/create_agent") == "agent"


def test_get_command_type_help():
    assert get_command_type("/help") == "help"


def test_get_command_type_free_text():
    assert get_command_type("tell me a joke") == "chat"


def test_check_credits_sufficient_subscription():
    user = {"subscriptionCredits": 10, "packCredits": 0}
    check_credits(user, "image")  # costs 1, should not raise


def test_check_credits_sufficient_pack():
    user = {"subscriptionCredits": 0, "packCredits": 5}
    check_credits(user, "image")  # costs 1, should not raise


def test_check_credits_combined_pools():
    user = {"subscriptionCredits": 0, "packCredits": 5}
    check_credits(user, "video")  # costs 5, should not raise


def test_check_credits_insufficient():
    from fastapi import HTTPException

    user = {"subscriptionCredits": 0, "packCredits": 0}
    with pytest.raises(HTTPException) as exc_info:
        check_credits(user, "image")
    assert exc_info.value.status_code == 402


def test_check_credits_free_help():
    user = {"subscriptionCredits": 0, "packCredits": 0}
    check_credits(user, "help")  # costs 0, should not raise
