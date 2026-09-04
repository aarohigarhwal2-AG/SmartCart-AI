import pytest
from backend.app.database import init_db
from backend.app.services.catalog_service import CatalogService
from backend.app.services.cart_service import CartService

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    # Seed items for cart testing
    csv_data = """id,name,category,description,price,stock,tags
C101,Desk Lamp,Lighting,Adjustable lamp,1000,10,lamp
C102,Mouse Pad,Accessories,Smooth mat,500,20,mat
C103,Sold Out Stand,Stands,No stock stand,1500,0,stand
"""
    CatalogService.parse_and_import_csv(csv_data, session_id="test_suite")

def test_cart_creation_and_deterministic_total():
    cart = CartService.get_or_create_cart(customer_session_id="test_user")
    assert cart.cart_id.startswith("CART_")
    assert cart.total == 0.0
    assert len(cart.items) == 0

    # Add 2 Desk Lamps (2 * 1000 = 2000)
    cart = CartService.add_item_to_cart(cart.cart_id, "C101", quantity=2)
    assert cart.subtotal == 2000.0
    assert cart.total == 2000.0
    assert cart.item_count == 2

    # Add 1 Mouse Pad (1 * 500 = 500) -> Total 2500
    cart = CartService.add_item_to_cart(cart.cart_id, "C102", quantity=1)
    assert cart.subtotal == 2500.0
    assert cart.total == 2500.0
    assert cart.item_count == 3
    assert len(cart.items) == 2

def test_out_of_stock_item_rejection():
    cart = CartService.get_or_create_cart(customer_session_id="test_user")
    with pytest.raises(ValueError) as exc:
        CartService.add_item_to_cart(cart.cart_id, "C103", quantity=1)
    assert "out of stock" in str(exc.value)

def test_nonexistent_product_rejection():
    cart = CartService.get_or_create_cart(customer_session_id="test_user")
    with pytest.raises(ValueError) as exc:
        CartService.add_item_to_cart(cart.cart_id, "INVALID_XYZ", quantity=1)
    assert "does not exist" in str(exc.value)

def test_quantity_update_and_removal():
    cart = CartService.get_or_create_cart(customer_session_id="test_user")
    CartService.add_item_to_cart(cart.cart_id, "C101", quantity=1)
    
    # Update quantity to 4 (4 * 1000 = 4000)
    updated = CartService.update_item_quantity(cart.cart_id, "C101", quantity=4)
    assert updated.total == 4000.0
    assert updated.item_count == 4

    # Setting quantity to 0 removes item
    removed = CartService.update_item_quantity(cart.cart_id, "C101", quantity=0)
    assert removed.total == 0.0
    assert len(removed.items) == 0
