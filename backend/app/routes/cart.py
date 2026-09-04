from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..models.schemas import CartResponse, CartItemInput
from ..services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["Cart Management"])

@router.post("", response_model=CartResponse)
async def create_or_get_cart(
    cart_id: Optional[str] = Query(None),
    session_id: str = Query("customer_session")
):
    """Creates a new cart or retrieves an active cart."""
    try:
        return CartService.get_or_create_cart(cart_id=cart_id, customer_session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{cart_id}", response_model=CartResponse)
async def get_cart(cart_id: str):
    """Gets current cart details and server-computed total."""
    try:
        return CartService.get_or_create_cart(cart_id=cart_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{cart_id}/items", response_model=CartResponse)
async def add_item_to_cart(cart_id: str, item: CartItemInput, session_id: str = Query("customer_session")):
    """Adds a validated item to the cart."""
    try:
        return CartService.add_item_to_cart(
            cart_id=cart_id,
            product_id=item.product_id,
            quantity=item.quantity,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{cart_id}/items/{product_id}", response_model=CartResponse)
async def update_item_quantity(cart_id: str, product_id: str, quantity: int = Query(...), session_id: str = Query("customer_session")):
    """Updates the quantity of an item in the cart."""
    try:
        return CartService.update_item_quantity(
            cart_id=cart_id,
            product_id=product_id,
            quantity=quantity,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{cart_id}/items/{product_id}", response_model=CartResponse)
async def remove_item_from_cart(cart_id: str, product_id: str, session_id: str = Query("customer_session")):
    """Removes an item completely from the cart."""
    try:
        return CartService.remove_item_from_cart(
            cart_id=cart_id,
            product_id=product_id,
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
