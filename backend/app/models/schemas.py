from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# Product schemas
class ProductBase(BaseModel):
    id: str
    name: str
    category: str
    description: str
    price: float
    currency: str = "INR"
    stock: int
    tags: str

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    created_at: str

class CatalogUploadResponse(BaseModel):
    total_rows: int
    valid_count: int
    rejected_count: int
    errors: List[str]
    products: List[ProductResponse]

# Chat & Recommendation schemas
class ChatMessage(BaseModel):
    role: str # "user", "assistant", "system"
    content: str

class ChatRequest(BaseModel):
    session_id: str
    message: str
    cart_id: Optional[str] = None
    history: Optional[List[ChatMessage]] = None

class ExtractedIntent(BaseModel):
    intent: str # "product_search", "budget_inquiry", "clarification", "add_to_cart", "checkout_inquiry", "general_help"
    budget: Optional[float] = None
    category: Optional[str] = None
    requirements: List[str] = []
    quantity: int = 1
    ambiguous: bool = False
    clarification_question: Optional[str] = None

class ProductRecommendation(BaseModel):
    product: ProductResponse
    reason: str
    match_score: float
    is_upsell: bool = False

class CrossSellSuggestion(BaseModel):
    product: ProductResponse
    complementary_to: str
    reason: str
    savings_tip: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: ExtractedIntent
    recommendations: List[ProductRecommendation] = []
    cross_sells: List[CrossSellSuggestion] = []
    suggested_total: float = 0.0
    budget_respected: bool = True
    active_cart: Optional[Any] = None

# Cart schemas
class CartItemInput(BaseModel):
    product_id: str
    quantity: int = 1

class CartItemDetail(BaseModel):
    id: int
    product_id: str
    name: str
    category: str
    quantity: int
    unit_price: float
    line_total: float

class CartResponse(BaseModel):
    cart_id: str
    customer_session_id: str
    items: List[CartItemDetail]
    subtotal: float
    discount: float
    total: float
    currency: str
    status: str
    item_count: int

# Payment schemas
class CreateOrderRequest(BaseModel):
    cart_id: str
    customer_name: Optional[str] = "Valued Customer"
    customer_email: Optional[str] = "customer@example.com"
    customer_contact: Optional[str] = "9999999999"
    user_confirmed: bool = Field(..., description="Confirmation flag gating order creation")

class CreateOrderResponse(BaseModel):
    order_id: str
    razorpay_order_id: str
    cart_id: str
    amount_in_paise: int
    amount: float
    currency: str
    key_id: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_contact: Optional[str] = None
    test_mode: bool = True

class VerifyPaymentRequest(BaseModel):
    order_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class VerifyPaymentResponse(BaseModel):
    success: bool
    message: str
    order_id: str
    razorpay_payment_id: str
    status: str

# Analytics schemas
class MerchantAnalytics(BaseModel):
    total_conversations: int
    product_search_requests: int
    carts_created: int
    checkout_attempts: int
    successful_test_payments: int
    failed_payments: int
    average_cart_value: float
    cross_sell_impressions: int
    cross_sell_accepted: int
    cross_sell_acceptance_rate_pct: float
    total_revenue: float
    data_mode: str = "Synthetic Baseline + Live Session Activity"

class AuditLogItem(BaseModel):
    id: int
    session_id: str
    action: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    timestamp: str
