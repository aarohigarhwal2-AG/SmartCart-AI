from fastapi import APIRouter, HTTPException, Header, Request, Query
from typing import Optional
from ..models.schemas import (
    CreateOrderRequest, CreateOrderResponse,
    VerifyPaymentRequest, VerifyPaymentResponse
)
from ..services.razorpay_service import RazorpayService

router = APIRouter(prefix="/checkout", tags=["Checkout & Razorpay Payments"])

@router.post("/create-order", response_model=CreateOrderResponse)
async def create_checkout_order(req: CreateOrderRequest, session_id: str = Query("checkout_user")):
    """
    Creates a server-side order with Razorpay in paise.
    Requires user_confirmed == True.
    """
    try:
        return RazorpayService.create_order(req, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(req: VerifyPaymentRequest, session_id: str = Query("checkout_user")):
    """
    Verifies Razorpay payment signature, updates order status to paid,
    and updates catalog inventory.
    """
    try:
        return RazorpayService.verify_payment(req, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None)
):
    """Receives Razorpay server webhook notifications."""
    raw_body = await request.body()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return RazorpayService.process_webhook(payload, x_razorpay_signature or "", raw_body)
