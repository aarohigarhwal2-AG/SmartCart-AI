import sqlite3
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from .config import settings

def get_db_connection():
    conn = sqlite3.connect(settings.DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

@contextmanager
def db_session():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db_session() as conn:
        cursor = conn.cursor()
        
        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'INR',
                stock INTEGER NOT NULL,
                tags TEXT NOT NULL,
                image_url TEXT,
                created_at TEXT NOT NULL
            );
        """)
        
        # Safe migration if image_url does not exist on existing databases
        cursor.execute("PRAGMA table_info(products)")
        product_columns = [col[1] for col in cursor.fetchall()]
        if "image_url" not in product_columns:
            cursor.execute("ALTER TABLE products ADD COLUMN image_url TEXT;")

        
        # Carts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carts (
                cart_id TEXT PRIMARY KEY,
                customer_session_id TEXT NOT NULL,
                subtotal REAL NOT NULL DEFAULT 0.0,
                discount REAL NOT NULL DEFAULT 0.0,
                total REAL NOT NULL DEFAULT 0.0,
                currency TEXT NOT NULL DEFAULT 'INR',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        
        # Cart items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cart_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                FOREIGN KEY(cart_id) REFERENCES carts(cart_id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE RESTRICT
            );
        """)
        
        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                cart_id TEXT NOT NULL,
                razorpay_order_id TEXT UNIQUE,
                razorpay_payment_id TEXT,
                razorpay_signature TEXT,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'INR',
                status TEXT NOT NULL DEFAULT 'created',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(cart_id) REFERENCES carts(cart_id)
            );
        """)
        
        # Audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                action TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                timestamp TEXT NOT NULL
            );
        """)

def log_audit(session_id: str, action: str, input_data: Any = None, output_data: Any = None, conn: Optional[sqlite3.Connection] = None):
    """Helper to append structured audit trails. Can use an existing connection or open a new one."""
    now_iso = datetime.now(timezone.utc).isoformat()
    sql = "INSERT INTO audit_logs (session_id, action, input_data, output_data, timestamp) VALUES (?, ?, ?, ?, ?)"
    params = (
        session_id or "system",
        action,
        json.dumps(input_data, default=str) if input_data is not None else None,
        json.dumps(output_data, default=str) if output_data is not None else None,
        now_iso
    )

    if conn is not None:
        conn.execute(sql, params)
    else:
        with db_session() as c:
            c.execute(sql, params)
