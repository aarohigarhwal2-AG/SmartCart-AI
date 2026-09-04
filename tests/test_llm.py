import pytest
from backend.app.database import init_db
from backend.app.services.catalog_service import CatalogService
from backend.app.services.llm_service import LLMService
from backend.app.models.schemas import ProductResponse, CrossSellSuggestion
from backend.app.config import settings

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_intent_sanitization_defense():
    # 1. Negative budget should be sanitized to None
    malformed_data = {
        "intent": "product_search",
        "budget": -2500,
        "category": "Keyboards",
        "requirements": ["wfh", 123, None]
    }
    sanitized = LLMService.validate_and_sanitize_intent(malformed_data, "test message")
    assert sanitized.budget is None
    assert sanitized.category == "Keyboards"
    assert sanitized.requirements == ["wfh", "123"]
    assert sanitized.quantity == 1

    # 2. Invalid intent string should default to product_search
    bad_intent_data = {
        "intent": "hacked_malicious_intent",
        "budget": 3000
    }
    sanitized2 = LLMService.validate_and_sanitize_intent(bad_intent_data, "test message")
    assert sanitized2.intent == "product_search"
    assert sanitized2.budget == 3000.0

    # 3. Empty query should trigger ambiguity flag
    empty_data = {
        "intent": "product_search",
        "budget": None,
        "category": None,
        "requirements": []
    }
    sanitized3 = LLMService.validate_and_sanitize_intent(empty_data, "hi")
    assert sanitized3.ambiguous is True
    assert sanitized3.clarification_question is not None

def test_multilingual_intent_extraction():
    # Hindi query
    hindi_query = "मुझे work from home के लिए ₹3,000 के अंदर setup चाहिए"
    intent1 = LLMService.extract_intent(hindi_query)
    assert intent1.budget == 3000.0
    assert "work-from-home" in intent1.requirements

    # Hinglish query
    hinglish_query = "1500 ke andar wireless mouse dikhao"
    intent2 = LLMService.extract_intent(hinglish_query)
    assert intent2.budget == 1500.0
    assert "mouse" in intent2.requirements

    # English query with 'k' abbreviation
    eng_query = "keyboard under 2k"
    intent3 = LLMService.extract_intent(eng_query)
    assert intent3.budget == 2000.0
    assert "keyboard" in intent3.requirements

def test_llm_explanation_generation_sandboxed():
    intent = LLMService.extract_intent("work from home setup under 3000")
    
    # Mock verified candidates
    candidates = [
        ProductResponse(
            id="P101",
            name="Wireless Ergonomic Keyboard",
            category="Keyboards",
            description="Compact wireless keyboard",
            price=1499.0,
            currency="INR",
            stock=10,
            tags="keyboard;office",
            created_at="2026-09-04T00:00:00"
        ),
        ProductResponse(
            id="P103",
            name="Adjustable Aluminium Laptop Stand",
            category="Stands",
            description="Aluminium stand",
            price=1299.0,
            currency="INR",
            stock=15,
            tags="stand;laptop",
            created_at="2026-09-04T00:00:00"
        )
    ]

    cross_sells = [
        CrossSellSuggestion(
            product=ProductResponse(
                id="P102",
                name="Wireless Optical Mouse",
                category="Mice",
                description="Silent mouse",
                price=799.0,
                currency="INR",
                stock=20,
                tags="mouse",
                created_at="2026-09-04T00:00:00"
            ),
            complementary_to="Wireless Ergonomic Keyboard",
            reason="Enhances navigation and desk comfort.",
            savings_tip="Adds complete utility for ₹799."
        )
    ]

    explanation = LLMService.generate_explanation(intent, candidates, cross_sells)
    assert "Wireless Ergonomic Keyboard" in explanation
    assert "Adjustable Aluminium Laptop Stand" in explanation
    assert "₹2,798" in explanation or "₹3,000" in explanation

def test_real_catalog_import_and_filtering():
    # Verify loading the real catalog CSV
    if settings.REAL_CATALOG_PATH.exists():
        content = settings.REAL_CATALOG_PATH.read_text(encoding="utf-8")
        result = CatalogService.parse_and_import_csv(content, session_id="test_real_catalog")
        assert result.valid_count == 11
        assert result.rejected_count == 0

        # Query budget <= 2000 for webcam
        webcams_under_2000 = [
            p for p in CatalogService.list_products(category="Cameras", in_stock_only=True)
            if p.price <= 2000
        ]
        # Zebronics Zeb-Ultimate Star (1399) should be included, Logitech Brio (2199) and 4K (2999 out of stock) excluded
        webcam_ids = [p.id for p in webcams_under_2000]
        assert "R104" in webcam_ids
        assert "R105" not in webcam_ids
        assert "R108" not in webcam_ids
