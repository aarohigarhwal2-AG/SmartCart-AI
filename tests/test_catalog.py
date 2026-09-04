import pytest
from backend.app.database import init_db
from backend.app.services.catalog_service import CatalogService

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_valid_csv_import():
    sample_csv = """id,name,category,description,price,stock,tags
T101,Test Keyboard,Keyboards,A test keyboard,1500,10,office;keyboard
T102,Test Mouse,Mice,A test mouse,800,20,office;mouse
"""
    result = CatalogService.parse_and_import_csv(sample_csv, session_id="test_suite")
    assert result.valid_count == 2
    assert result.rejected_count == 0
    assert len(result.errors) == 0

    p1 = CatalogService.get_product("T101")
    assert p1 is not None
    assert p1.name == "Test Keyboard"
    assert p1.price == 1500.0
    assert p1.stock == 10

def test_missing_header_rejection():
    bad_csv = """id,name,description,price
T103,Bad CSV,Missing columns,500
"""
    with pytest.raises(ValueError) as exc:
        CatalogService.parse_and_import_csv(bad_csv)
    assert "Missing required columns" in str(exc.value)

def test_invalid_price_and_stock_rejection():
    dirty_csv = """id,name,category,description,price,stock,tags
T104,Negative Price,Keyboards,Invalid price,-500,5,test
T105,String Stock,Mice,Invalid stock,1200,five,test
T106,Valid Product,Stands,Good item,999,15,test
"""
    result = CatalogService.parse_and_import_csv(dirty_csv, session_id="test_suite")
    assert result.valid_count == 1
    assert result.rejected_count == 2
    assert len(result.errors) == 2
    assert any("Price cannot be negative" in e for e in result.errors)
    assert any("Invalid numeric stock" in e for e in result.errors)

def test_out_of_stock_query_filter():
    csv_data = """id,name,category,description,price,stock,tags
T107,In Stock Item,General,Available,500,5,test
T108,Out of Stock Item,General,Unavailable,500,0,test
"""
    CatalogService.parse_and_import_csv(csv_data, session_id="test_suite")
    in_stock_list = CatalogService.list_products(in_stock_only=True)
    in_stock_ids = [p.id for p in in_stock_list]
    assert "T107" in in_stock_ids
    assert "T108" not in in_stock_ids
