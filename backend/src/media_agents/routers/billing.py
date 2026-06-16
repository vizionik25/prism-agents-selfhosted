from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from media_agents.auth.dependencies import get_current_user
from media_agents.env import DEMO_MODE

router = APIRouter(prefix="/billing", tags=["billing"])


class BillingStatusResponse(BaseModel):
    tier: str
    subscription_credits: int
    pack_credits: int
    credits_reset_at: str | None


class PortalResponse(BaseModel):
    url: str


class CheckoutResponse(BaseModel):
    client_secret: str


class CheckoutRequest(BaseModel):
    type: str
    tier: str | None = None
    billing_period: str | None = None
    pack_size: str | None = None


@router.get("/status", response_model=BillingStatusResponse)
async def get_billing_status(current_user: dict = Depends(get_current_user)):
    """Return ENTERPRISE tier with unlimited credits for self-hosted deployments."""
    if DEMO_MODE:
        return BillingStatusResponse(
            tier="PRO",
            subscription_credits=999999,
            pack_credits=999999,
            credits_reset_at=None,
        )

    # Self-hosted always returns ENTERPRISE with unlimited credits
    return BillingStatusResponse(
        tier="ENTERPRISE",
        subscription_credits=999999,
        pack_credits=999999,
        credits_reset_at=None,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    current_user: dict = Depends(get_current_user),
):
    """Stripe checkout not available in self-hosted mode."""
    if DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Billing disabled in demo mode",
        )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Stripe billing not available in self-hosted mode. Use your own API keys.",
    )


@router.post("/webhook")
async def stripe_webhook():
    """Stripe webhook not available in self-hosted mode."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Stripe webhooks not available in self-hosted mode.",
    )


@router.get("/portal", response_model=PortalResponse)
async def billing_portal(current_user: dict = Depends(get_current_user)):
    """Stripe billing portal not available in self-hosted mode."""
    if DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Billing disabled in demo mode",
        )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Stripe billing portal not available in self-hosted mode.",
    )