import pytest
from backend.app.database import init_db
from backend.app.services.catalog_service import CatalogService
from backend.app.services.recommendation_service import RecommendationService

@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    # Seed full representative catalog
    csv_data = """id,name,category,description,price,stock,tags
P101,Wireless Keyboard,Keyboards,Office keyboard,1499,20,office;keyboard;wireless;work-from-home
P102,Wireless Mouse,Mice,Office mouse,799,30,office;mouse;wireless;work-from-home
P103,Laptop Stand,Stands,Aluminium stand,1299,15,work-from-home;stand;laptop
P104,USB Hub,Accessories,4-port hub,699,20,laptop;accessory;usb;hub
P105,Luxury Webcam,Cameras,Expensive 4k webcam,7500,5,camera;webcam
P106,Out of Stock Keyboard,Keyboards,Sold out item,1200,0,keyboard
"""
    CatalogService.parse_and_import_csv(csv_data, session_id="test_suite")

def test_intent_extraction_budget_and_requirements():
    query = "I need a work from home setup under ₹3,000"
    intent = RecommendationService.extract_intent(query)
    assert intent.intent == "product_search"
    assert intent.budget == 3000.0
    assert "work-from-home" in intent.requirements

def test_ambiguous_query_trigger():
    query = "hi"
    intent = RecommendationService.extract_intent(query)
    assert intent.intent == "clarification"

def test_budget_compliance_wfh_bundle():
    # User asks for WFH setup under 3000
    res = RecommendationService.process_chat("test_session", "WFH setup under 3000")
    assert res.budget_respected is True
    assert res.suggested_total <= 3000.0
    assert len(res.recommendations) > 0
    
    # Verify no out-of-stock items are recommended
    rec_ids = [r.product.id for r in res.recommendations]
    assert "P106" not in rec_ids

    # Verify cross-sell complement is present
    assert len(res.cross_sells) > 0
    cross_sell_cats = [cs.product.category for cs in res.cross_sells]
    assert any(c in ["Mice", "Accessories"] for c in cross_sell_cats)

def test_over_budget_items_excluded():
    # User asks for camera under 2000, Luxury Webcam is 7500
    res = RecommendationService.process_chat("test_session", "webcam under 2000")
    rec_ids = [r.product.id for r in res.recommendations if not r.is_upsell]
    assert "P105" not in rec_ids
