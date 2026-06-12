import os
import json
import stripe
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# In-memory store for prototype — replace with Supabase in production
# Maps user_id → { "is_paid": bool, "plan": str }
user_subscriptions: dict = {}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    POST /api/webhook
    Listens for Stripe events to activate/deactivate paid access.
    Key events handled:
      - checkout.session.completed  → activate paid tier
      - customer.subscription.deleted → revert to free tier
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Verify the webhook came from Stripe (not a fake request)
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle subscription activation
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id")
        if user_id:
            user_subscriptions[user_id] = {"is_paid": True, "plan": "pro"}

    # Handle subscription cancellation
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        user_id = subscription.get("metadata", {}).get("user_id")
        if user_id:
            user_subscriptions[user_id] = {"is_paid": False, "plan": "free"}

    return {"status": "ok"}


def is_paid_user(user_id: str) -> bool:
    """Helper used by other routers to check if a user has a paid plan."""
    return user_subscriptions.get(user_id, {}).get("is_paid", False)