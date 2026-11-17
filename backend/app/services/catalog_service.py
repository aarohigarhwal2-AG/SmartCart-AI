import csv
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from ..database import db_session, log_audit
from ..models.schemas import ProductResponse, CatalogUploadResponse

class CatalogService:
    @staticmethod
    def parse_and_import_csv(csv_content: str, session_id: str = "merchant_admin") -> CatalogUploadResponse:
        """
        Parses CSV data, strictly validates row-by-row, reports errors,
        and saves valid items to the database.
        """
        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        
        required_headers = {"id", "name", "category", "description", "price", "stock", "tags"}
        if not reader.fieldnames or not required_headers.issubset(set(f.strip().lower() for f in reader.fieldnames)):
            missing = required_headers - set(f.strip().lower() for f in (reader.fieldnames or []))
            raise ValueError(f"Invalid CSV format. Missing required columns: {', '.join(missing)}")

        valid_products: List[Dict[str, Any]] = []
        errors: List[str] = []
        seen_ids = set()
        row_idx = 1 # 1-based (header is row 1, data starts row 2)

        for raw_row in reader:
            row_idx += 1
            row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items() if k}
            
            p_id = row.get("id", "")
            p_name = row.get("name", "")
            p_category = row.get("category", "")
            p_desc = row.get("description", "")
            p_price_str = row.get("price", "")
            p_stock_str = row.get("stock", "")
            p_tags = row.get("tags", "")
            p_image = row.get("image_url", "").strip()

            # Fallback high quality product photo based on category / keywords
            if not p_image:
                cat_lower = (p_category or "").lower()
                tag_lower = (p_tags or "").lower()
                if "keyboard" in cat_lower or "keyboard" in tag_lower:
                    p_image = "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500&auto=format&fit=crop&q=80"
                elif "mic" in cat_lower or "mouse" in tag_lower or "mice" in cat_lower:
                    p_image = "https://images.unsplash.com/photo-1527814050087-3793815479db?w=500&auto=format&fit=crop&q=80"
                elif "stand" in cat_lower or "stand" in tag_lower:
                    p_image = "https://images.unsplash.com/photo-1527689368864-3a821dbccc34?w=500&auto=format&fit=crop&q=80"
                elif "cooling" in cat_lower or "cooling" in tag_lower:
                    p_image = "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=500&auto=format&fit=crop&q=80"
                elif "camera" in cat_lower or "webcam" in tag_lower:
                    p_image = "https://images.unsplash.com/photo-1587826080692-f439cd0b70da?w=500&auto=format&fit=crop&q=80"
                elif "audio" in cat_lower or "headset" in tag_lower or "sound" in tag_lower:
                    p_image = "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop&q=80"
                elif "light" in cat_lower or "lamp" in tag_lower:
                    p_image = "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=500&auto=format&fit=crop&q=80"
                elif "wrist" in tag_lower:
                    p_image = "https://images.unsplash.com/photo-1595225476474-87563907a212?w=500&auto=format&fit=crop&q=80"
                elif "mat" in tag_lower or "pad" in tag_lower:
                    p_image = "https://images.unsplash.com/photo-1616440347437-b1c73416efc2?w=500&auto=format&fit=crop&q=80"
                elif "hub" in tag_lower or "usb" in tag_lower:
                    p_image = "https://images.unsplash.com/photo-1625842268584-8f3296236761?w=500&auto=format&fit=crop&q=80"
                elif "cable" in tag_lower or "organizer" in tag_lower:
                    p_image = "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=500&auto=format&fit=crop&q=80"
                else:
                    p_image = "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=500&auto=format&fit=crop&q=80"

            # Validation checks
            if not p_id:
                errors.append(f"Row {row_idx}: Product ID is missing.")
                continue
            if p_id in seen_ids:
                errors.append(f"Row {row_idx}: Duplicate Product ID '{p_id}' in uploaded file.")
                continue
            if not p_name:
                errors.append(f"Row {row_idx} (ID: {p_id}): Product Name is missing.")
                continue
            
            try:
                p_price = float(p_price_str)
                if p_price < 0:
                    errors.append(f"Row {row_idx} (ID: {p_id}): Price cannot be negative ({p_price_str}).")
                    continue
            except (ValueError, TypeError):
                errors.append(f"Row {row_idx} (ID: {p_id}): Invalid numeric price '{p_price_str}'.")
                continue

            try:
                p_stock = int(float(p_stock_str))
                if p_stock < 0:
                    errors.append(f"Row {row_idx} (ID: {p_id}): Stock cannot be negative ({p_stock_str}).")
                    continue
            except (ValueError, TypeError):
                errors.append(f"Row {row_idx} (ID: {p_id}): Invalid numeric stock '{p_stock_str}'.")
                continue

            seen_ids.add(p_id)
            valid_products.append({
                "id": p_id,
                "name": p_name,
                "category": p_category or "General",
                "description": p_desc,
                "price": p_price,
                "currency": "INR",
                "stock": p_stock,
                "tags": p_tags,
                "image_url": p_image,
                "created_at": datetime.now(timezone.utc).isoformat()
            })

        # Upsert into database
        if valid_products:
            with db_session() as conn:
                for p in valid_products:
                    conn.execute("""
                        INSERT INTO products (id, name, category, description, price, currency, stock, tags, image_url, created_at)
                        VALUES (:id, :name, :category, :description, :price, :currency, :stock, :tags, :image_url, :created_at)
                        ON CONFLICT(id) DO UPDATE SET
                            name=excluded.name,
                            category=excluded.category,
                            description=excluded.description,
                            price=excluded.price,
                            stock=excluded.stock,
                            tags=excluded.tags,
                            image_url=excluded.image_url;
                    """, p)

                log_audit(
                    session_id=session_id,
                    action="CATALOG_UPLOAD",
                    input_data={"total_rows": row_idx - 1},
                    output_data={"valid_count": len(valid_products), "rejected_count": len(errors), "errors": errors},
                    conn=conn
                )

        all_products = CatalogService.list_products()
        return CatalogUploadResponse(
            total_rows=row_idx - 1,
            valid_count=len(valid_products),
            rejected_count=len(errors),
            errors=errors,
            products=all_products
        )

    @staticmethod
    def list_products(category: Optional[str] = None, in_stock_only: bool = False, query: Optional[str] = None) -> List[ProductResponse]:
        with db_session() as conn:
            sql = "SELECT id, name, category, description, price, currency, stock, tags, image_url, created_at FROM products WHERE 1=1"
            params: List[Any] = []

            if in_stock_only:
                sql += " AND stock > 0"
            if category:
                sql += " AND LOWER(category) = LOWER(?)"
                params.append(category)
            if query:
                sql += " AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags) LIKE ?)"
                q_wildcard = f"%{query.lower()}%"
                params.extend([q_wildcard, q_wildcard, q_wildcard])

            sql += " ORDER BY price ASC"
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [ProductResponse(**dict(r)) for r in rows]

    @staticmethod
    def get_product(product_id: str) -> Optional[ProductResponse]:
        with db_session() as conn:
            cursor = conn.execute(
                "SELECT id, name, category, description, price, currency, stock, tags, image_url, created_at FROM products WHERE id = ?",
                (product_id,)
            )
            row = cursor.fetchone()
            return ProductResponse(**dict(row)) if row else None

