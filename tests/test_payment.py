import pytest
import hmac
import hashlib
from backend.app.database import init_db
from backend.app.services.catalog_service import CatalogService
from backend.app.services.cart_service import CartService
from backend.app.services.razorpay_service import RazorpayService
from backend.app.models.schemas import CreateOrderRequest, VerifyPaymentRequest
from backend.app.config import settings

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    csv_data = """id,name,category,description,price,stock,tags
P201,Wireless Keyboard,Keyboards,Test item,1499,10,keyboard
P202,Wireless Mouse,Mice,Test item,799,10,mouse
"""
    CatalogService.parse_and_import_csv(csv_data, session_id="test_suite")

def test_order_creation_with_confirmation_gate():
    # Create cart with items (1499 + 799 = 2298)
    cart = CartService.get_or_create_cart(customer_session_id="test_payer")
    CartService.add_item_to_cart(cart.cart_id, "P201", 1)
    CartService.add_item_to_cart(cart.cart_id, "P202", 1)

    # 1. Failure without confirmation gate
    with pytest.raises(ValueError) as exc:
        RazorpayService.create_order(
            CreateOrderRequest(cart_id=cart.cart_id, user_confirmed=False)
        )
    assert "user confirmation" in str(exc.value)

    # 2. Success with confirmation
    order_res = RazorpayService.create_order(
        CreateOrderRequest(cart_id=cart.cart_id, user_confirmed=True)
    )
    assert order_res.amount == 2298.0
    assert order_res.amount_in_paise == 229800
    assert order_res.currency == "INR"
    assert order_res.razorpay_order_id.startswith("order_test_")

def test_payment_signature_verification_and_stock_deduction():
    cart = CartService.get_or_create_cart(customer_session_id="test_payer")
    CartService.add_item_to_cart(cart.cart_id, "P201", 2) # 2 keyboards (initial stock 10)
    
    order_res = RazorpayService.create_order(
        CreateOrderRequest(cart_id=cart.cart_id, user_confirmed=True)
    )

    # Valid test payment verification
    verify_res = RazorpayService.verify_payment(VerifyPaymentRequest(
        order_id=order_res.order_id,
        razorpay_order_id=order_res.razorpay_order_id,
        razorpay_payment_id="pay_test_987654",
        razorpay_signature="mock_signature_success"
    ))
    assert verify_res.success is True
    assert verify_res.status == "paid"

    # Verify inventory was automatically deducted (10 - 2 = 8)
    p = CatalogService.get_product("P201")
    assert p.stock == 8

def test_idempotent_duplicate_payment_callback():
    cart = CartService.get_or_create_cart(customer_session_id="test_payer")
    CartService.add_item_to_cart(cart.cart_id, "P202", 1)
    
    order_res = RazorpayService.create_order(
        CreateOrderRequest(cart_id=cart.cart_id, user_confirmed=True)
    )

    req = VerifyPaymentRequest(
        order_id=order_res.order_id,
        razorpay_order_id=order_res.razorpay_order_id,
        razorpay_payment_id="pay_test_duplicate",
        razorpay_signature="mock_signature_success"
    )

    # First call verifies
    res1 = RazorpayService.verify_payment(req)
    assert res1.success is True

    # Second identical callback should be handled gracefully without re-deducting or erroring
    res2 = RazorpayService.verify_payment(req)
    assert res2.success is True
    assert res2.status == "paid"
