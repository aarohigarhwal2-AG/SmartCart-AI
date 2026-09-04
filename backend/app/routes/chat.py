from fastapi import APIRouter, HTTPException
from ..models.schemas import ChatRequest, ChatResponse
from ..services.recommendation_service import RecommendationService
from ..services.cart_service import CartService

router = APIRouter(prefix="/chat", tags=["Customer AI Chat"])

@router.post("", response_model=ChatResponse)
async def chat_interaction(req: ChatRequest):
    """
    Processes customer natural language chat query, performs intent extraction,
    budget verification, and generates safe explainable recommendations.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Chat message cannot be empty.")

    res = RecommendationService.process_chat(
        session_id=req.session_id,
        message=req.message
    )

    if req.cart_id:
        try:
            res.active_cart = CartService.get_or_create_cart(req.cart_id, req.session_id)
        except Exception:
            pass

    return res
