import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from ..database import db_session, log_audit
from ..models.schemas import CartResponse, CartItemDetail
from .catalog_service import CatalogService

class CartService:
    @staticmethod
    def get_or_create_cart(cart_id: Optional[str] = None, customer_session_id: str = "anon") -> CartResponse:
        """Retrieves an existing cart or creates a new one in SQLite."""
        with db_session() as conn:
            if cart_id:
                cursor = conn.execute("SELECT * FROM carts WHERE cart_id = ?", (cart_id,))
                row = cursor.fetchone()
                if row:
                    return CartService._load_cart_details(conn, row["cart_id"])

            # Create new cart
            new_id = f"CART_{uuid.uuid4().hex[:8].upper()}"
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """INSERT INTO carts (cart_id, customer_session_id, subtotal, discount, total, currency, status, created_at, updated_at)
                   VALUES (?, ?, 0.0, 0.0, 0.0, 'INR', 'active', ?, ?)""",
                (new_id, customer_session_id, now, now)
            )
            log_audit(customer_session_id, "CART_CREATED", output_data={"cart_id": new_id}, conn=conn)
            return CartService._load_cart_details(conn, new_id)

    @staticmethod
    def add_item_to_cart(cart_id: str, product_id: str, quantity: int = 1, session_id: str = "anon") -> CartResponse:
        """
        Adds a product to the cart after strict backend validation:
        1. Product must exist.
        2. Quantity must be > 0.
        3. Sufficient stock must be available.
        4. Authoritative price is fetched directly from database.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be a positive integer greater than 0.")

        product = CatalogService.get_product(product_id)
        if not product:
            raise ValueError(f"Product ID '{product_id}' does not exist in catalog.")

        if product.stock <= 0:
            raise ValueError(f"Product '{product.name}' is out of stock.")

        with db_session() as conn:
            # Check cart exists
            c_row = conn.execute("SELECT * FROM carts WHERE cart_id = ?", (cart_id,)).fetchone()
            if not c_row:
                # Create if not exists
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    """INSERT INTO carts (cart_id, customer_session_id, subtotal, discount, total, currency, status, created_at, updated_at)
                       VALUES (?, ?, 0.0, 0.0, 0.0, 'INR', 'active', ?, ?)""",
                    (cart_id, session_id, now, now)
                )

            # Check existing item
            item_row = conn.execute(
                "SELECT * FROM cart_items WHERE cart_id = ? AND product_id = ?",
                (cart_id, product_id)
            ).fetchone()

            if item_row:
                new_qty = item_row["quantity"] + quantity
                if new_qty > product.stock:
                    raise ValueError(f"Requested quantity ({new_qty}) exceeds available stock ({product.stock}).")
                conn.execute(
                    "UPDATE cart_items SET quantity = ?, unit_price = ? WHERE id = ?",
                    (new_qty, product.price, item_row["id"])
                )
            else:
                if quantity > product.stock:
                    raise ValueError(f"Requested quantity ({quantity}) exceeds available stock ({product.stock}).")
                conn.execute(
                    "INSERT INTO cart_items (cart_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                    (cart_id, product_id, quantity, product.price)
                )

            # Recalculate totals
            CartService._recalculate_cart_total(conn, cart_id)
            log_audit(session_id, "CART_ITEM_ADDED", input_data={"cart_id": cart_id, "product_id": product_id, "qty": quantity}, conn=conn)
            return CartService._load_cart_details(conn, cart_id)

    @staticmethod
    def update_item_quantity(cart_id: str, product_id: str, quantity: int, session_id: str = "anon") -> CartResponse:
        """Updates item quantity in cart or removes if quantity is 0."""
        if quantity < 0:
            raise ValueError("Quantity cannot be negative.")

        if quantity == 0:
            return CartService.remove_item_from_cart(cart_id, product_id, session_id)

        product = CatalogService.get_product(product_id)
        if not product:
            raise ValueError(f"Product '{product_id}' not found.")

        if quantity > product.stock:
            raise ValueError(f"Requested quantity ({quantity}) exceeds available stock ({product.stock}).")

        with db_session() as conn:
            conn.execute(
                "UPDATE cart_items SET quantity = ?, unit_price = ? WHERE cart_id = ? AND product_id = ?",
                (quantity, product.price, cart_id, product_id)
            )
            CartService._recalculate_cart_total(conn, cart_id)
            log_audit(session_id, "CART_ITEM_UPDATED", input_data={"cart_id": cart_id, "product_id": product_id, "new_qty": quantity}, conn=conn)
            return CartService._load_cart_details(conn, cart_id)

    @staticmethod
    def remove_item_from_cart(cart_id: str, product_id: str, session_id: str = "anon") -> CartResponse:
        """Removes a product from the cart."""
        with db_session() as conn:
            conn.execute("DELETE FROM cart_items WHERE cart_id = ? AND product_id = ?", (cart_id, product_id))
            CartService._recalculate_cart_total(conn, cart_id)
            log_audit(session_id, "CART_ITEM_REMOVED", input_data={"cart_id": cart_id, "product_id": product_id}, conn=conn)
            return CartService._load_cart_details(conn, cart_id)

    @staticmethod
    def _recalculate_cart_total(conn, cart_id: str):
        """Authoritative backend cart total calculation."""
        cursor = conn.execute("""
            SELECT SUM(ci.quantity * p.price) as subtotal
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            WHERE ci.cart_id = ?
        """, (cart_id,))
        row = cursor.fetchone()
        subtotal = float(row["subtotal"] or 0.0)
        discount = 0.0
        total = subtotal - discount
        now = datetime.now(timezone.utc).isoformat()

        conn.execute(
            "UPDATE carts SET subtotal = ?, discount = ?, total = ?, updated_at = ? WHERE cart_id = ?",
            (subtotal, discount, total, now, cart_id)
        )

    @staticmethod
    def _load_cart_details(conn, cart_id: str) -> CartResponse:
        """Loads cart metadata and all item rows."""
        c_row = conn.execute("SELECT * FROM carts WHERE cart_id = ?", (cart_id,)).fetchone()
        if not c_row:
            raise ValueError(f"Cart '{cart_id}' not found.")

        items_cursor = conn.execute("""
            SELECT ci.id, ci.product_id, ci.quantity, ci.unit_price, p.name, p.category
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            WHERE ci.cart_id = ?
        """, (cart_id,))
        
        items: List[CartItemDetail] = []
        for r in items_cursor.fetchall():
            items.append(CartItemDetail(
                id=r["id"],
                product_id=r["product_id"],
                name=r["name"],
                category=r["category"],
                quantity=r["quantity"],
                unit_price=r["unit_price"],
                line_total=round(r["quantity"] * r["unit_price"], 2)
            ))

        return CartResponse(
            cart_id=c_row["cart_id"],
            customer_session_id=c_row["customer_session_id"],
            items=items,
            subtotal=round(c_row["subtotal"], 2),
            discount=round(c_row["discount"], 2),
            total=round(c_row["total"], 2),
            currency=c_row["currency"],
            status=c_row["status"],
            item_count=sum(item.quantity for item in items)
        )
