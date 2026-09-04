from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import List, Optional
from ..models.schemas import ProductResponse, CatalogUploadResponse
from ..services.catalog_service import CatalogService
from ..config import settings

router = APIRouter(prefix="/catalog", tags=["Merchant Catalog"])

@router.post("/upload", response_model=CatalogUploadResponse)
async def upload_catalog(file: UploadFile = File(...)):
    """Uploads and parses a merchant CSV product catalog."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files (.csv) are supported.")
    
    try:
        content = (await file.read()).decode("utf-8")
        result = CatalogService.parse_and_import_csv(content, session_id="merchant_upload")
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/load-sample", response_model=CatalogUploadResponse)
async def load_sample_catalog():
    """Loads the pre-packaged 15-item sample work-from-home catalog."""
    if not settings.SAMPLE_CATALOG_PATH.exists():
        raise HTTPException(status_code=404, detail="Sample catalog file not found.")
    
    content = settings.SAMPLE_CATALOG_PATH.read_text(encoding="utf-8")
    return CatalogService.parse_and_import_csv(content, session_id="merchant_sample_load")

@router.post("/load-real", response_model=CatalogUploadResponse)
async def load_real_catalog():
    """Loads the real-world 11-item catalog sourced from Amazon.in and Flipkart."""
    if not settings.REAL_CATALOG_PATH.exists():
        raise HTTPException(status_code=404, detail="Real catalog file not found.")
    
    content = settings.REAL_CATALOG_PATH.read_text(encoding="utf-8")
    return CatalogService.parse_and_import_csv(content, session_id="merchant_real_load")

@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    in_stock_only: bool = Query(False, description="Show only in-stock items"),
    query: Optional[str] = Query(None, description="Search term across name/desc/tags")
):
    """Retrieves all products with optional filters."""
    return CatalogService.list_products(category=category, in_stock_only=in_stock_only, query=query)

@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    """Retrieves a single product by ID."""
    p = CatalogService.get_product(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found.")
    return p
