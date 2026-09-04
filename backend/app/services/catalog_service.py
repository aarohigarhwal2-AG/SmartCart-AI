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
                "created_at": datetime.now(timezone.utc).isoformat()
            })

        # Upsert into database
        if valid_products:
            with db_session() as conn:
                for p in valid_products:
                    conn.execute("""
                        INSERT INTO products (id, name, category, description, price, currency, stock, tags, created_at)
                        VALUES (:id, :name, :category, :description, :price, :currency, :stock, :tags, :created_at)
                        ON CONFLICT(id) DO UPDATE SET
                            name=excluded.name,
                            category=excluded.category,
                            description=excluded.description,
                            price=excluded.price,
                            stock=excluded.stock,
                            tags=excluded.tags;
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
            sql = "SELECT id, name, category, description, price, currency, stock, tags, created_at FROM products WHERE 1=1"
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
                "SELECT id, name, category, description, price, currency, stock, tags, created_at FROM products WHERE id = ?",
                (product_id,)
            )
            row = cursor.fetchone()
            return ProductResponse(**dict(row)) if row else None
