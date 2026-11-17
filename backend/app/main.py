import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .database import init_db
from .services.catalog_service import CatalogService
from .routes import catalog, chat, cart, payment, analytics

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Conversational Merchant Growth Agent & Razorpay Test Checkout System"
)

# CORS middleware for open web/local dev access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(catalog.router, prefix=settings.API_PREFIX)
app.include_router(chat.router, prefix=settings.API_PREFIX)
app.include_router(cart.router, prefix=settings.API_PREFIX)
app.include_router(payment.router, prefix=settings.API_PREFIX)
app.include_router(analytics.router, prefix=settings.API_PREFIX)

@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": "test_mode"
    }

# Mount Frontend static files
FRONTEND_DIR = settings.BASE_DIR / "frontend" / "static"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        response = FileResponse(str(FRONTEND_DIR / "index.html"))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

@app.on_event("startup")
def on_startup():
    init_db()
    # Always sync/upsert verified catalog on startup so image URLs and stock are accurate
    try:
        if settings.SAMPLE_CATALOG_PATH.exists():
            content = settings.SAMPLE_CATALOG_PATH.read_text(encoding="utf-8")
            CatalogService.parse_and_import_csv(content, session_id="system_init")
    except Exception as e:
        print(f"Startup catalog load warning: {e}")
