import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "SmartCart AI"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Base and storage paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / "data" / "smartcart.db"
    SAMPLE_CATALOG_PATH: Path = BASE_DIR / "data" / "sample_catalog.csv"
    REAL_CATALOG_PATH: Path = BASE_DIR / "data" / "real_catalog.csv"
    
    # Razorpay Settings
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_demo_smartcart")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "demo_secret_key_123456")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "webhook_secret_demo")
    
    # AI / LLM Settings (OpenRouter & Gemini)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    
    # Synthetic baseline counts for merchant demo analytics
    DEMO_BASELINE_CONVERSATIONS: int = 15
    DEMO_BASELINE_CARTS: int = 10
    DEMO_BASELINE_CHECKOUTS: int = 7
    DEMO_BASELINE_PAYMENTS: int = 6

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
