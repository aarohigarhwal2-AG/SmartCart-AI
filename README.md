# 🛒 SmartCart AI

> **A Conversational Merchant Growth Agent & Razorpay Test Checkout System**

SmartCart AI is an agentic merchant commerce platform that converts raw product catalogs into AI-readable inventories, extracts structured customer intents within budget constraints, provides explainable recommendations and cross-sells, enforces server-side pricing and inventory integrity, and handles confirmation-gated Razorpay Test Mode checkouts.

---

## 🌟 Core Philosophy & Architecture

```
Merchant Catalog (CSV) 
         ↓
  Catalog Processing (Validation & SQLite Ingestion)
         ↓
  Customer Natural Language Chat
         ↓
  Intent & Budget Extraction (Safe JSON Schema)
         ↓
  Deterministic Product Search (In-Stock & Budget Filtering)
         ↓
  Explainable AI Recommendation + Upsell / Cross-Sell Rules
         ↓
  Server-Authoritative Cart Total Calculation
         ↓
  Mandatory User Confirmation Gate
         ↓
  Razorpay Test Mode Order Creation (in Paise) & HMAC Verification
         ↓
  Real-time Merchant Growth Analytics & Safety Audit Log
```

### 🛡️ Critical Separation of Concerns
1. **AI / LLM Responsibilities (Language & Reasoning)**:
   - Natural language comprehension & intent parsing.
   - Requirement and budget extraction.
   - Explainable product rationale (e.g. *"Why this item fits your budget and ergonomic setup"*).
2. **Backend Engine Responsibilities (Correctness & Money)**:
   - Product pricing, discount, and inventory stock control.
   - Strict budget ceiling enforcement (`sum(prices) <= budget`).
   - Server-side authoritative cart totals (`subtotal = sum(unit_price * qty)`).
   - Razorpay order creation via server-side Orders API in smallest currency unit (paise).
   - HMAC-SHA256 signature verification and idempotency / duplicate payment prevention.
   - User confirmation gating prior to any payment transaction.

---

## 📁 Project Structure

```
smartcart-ai/
├── backend/
│   ├── app/
│   │   ├── config.py                 # Configuration & environment settings
│   │   ├── database.py               # SQLite WAL connection & schema setup
│   │   ├── main.py                   # FastAPI app entrypoint & static routes
│   │   ├── models/
│   │   │   ├── db_models.py          # Database model structures
│   │   │   └── schemas.py            # Pydantic schemas (intent, cart, payment)
│   │   ├── routes/
│   │   │   ├── catalog.py            # CSV upload & product search endpoints
│   │   │   ├── chat.py               # Conversational AI & recommendation API
│   │   │   ├── cart.py               # Validated cart CRUD endpoints
│   │   │   ├── payment.py            # Razorpay order create & HMAC verify
│   │   │   └── analytics.py          # Merchant KPIs & audit log endpoints
│   │   └── services/
│   │       ├── catalog_service.py    # CSV validator & inventory manager
│   │       ├── recommendation_service.py # Intent parser & cross-sell engine
│   │       ├── cart_service.py       # Deterministic cart calculations
│   │       ├── razorpay_service.py   # Razorpay API client & test simulator
│   │       └── analytics_service.py  # Funnel & metric aggregations
│   └── requirements.txt              # Python dependencies
├── frontend/
│   └── static/
│       ├── index.html                # 4-in-1 Merchant/Shopper Single Page UI
│       ├── style.css                 # Modern commerce styling & responsiveness
│       └── app.js                    # Reactive client controller & state
├── data/
│   ├── sample_catalog.csv            # 15-product sample WFH inventory
│   └── smartcart.db                  # Local SQLite database
├── tests/
│   ├── test_catalog.py               # CSV parsing, row error & stock tests
│   ├── test_cart.py                  # Server-side pricing & stock tests
│   ├── test_recommendations.py       # Intent extraction & budget tests
│   └── test_payment.py               # Razorpay order, signature & stock tests
├── .env.example
├── README.md
└── run.py                            # One-click startup script
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)

### 2. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Run the Application
```bash
python run.py
```

Open your browser at:
- **Interactive UI**: [http://localhost:8000](http://localhost:8000)
- **API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Running Automated Tests

Run the full pytest suite:
```bash
python -m pytest tests/ -v
```

### Tested Test Matrix:
| Test Case | Expected Result |
| :--- | :--- |
| **Budget ₹3,000 constraint** | Recommended product bundle total never exceeds ₹3,000 |
| **Out-of-stock items** | Automatically excluded from all recommendations & cart additions |
| **Invalid CSV prices / stock** | Rejected row-by-row with descriptive error reasons |
| **Missing CSV headers** | Informative validation error returned |
| **Nonexistent Product ID** | Cart mutation safely rejected |
| **Server-Side Pricing** | Cart total strictly computed by backend (`sum(price * qty)`) |
| **Confirmation Gate** | Payment order creation blocked if `user_confirmed=False` |
| **Razorpay In-Paise Order** | ₹2,298 order sent as `229800` paise to Razorpay API |
| **Signature Verification** | Payment validated via HMAC SHA-256; stock decremented |
| **Duplicate Payment Callbacks** | Idempotently handled without duplicate orders or deductions |

---

## 🎬 5-Minute Demo Scenario

1. **Merchant Catalog Upload (Tab 1)**:
   - Click **"Load 15-Item Sample"** or upload a custom CSV.
   - Inspect the live inventory table showing 15 items across Keyboards, Mice, Laptop Stands, USB Hubs, Webcams, Audio, Lighting, and Accessories (with in-stock and out-of-stock indicators).
2. **Customer AI Assistant Chat (Tab 2)**:
   - Click the prompt chip: *"I need a work from home setup under ₹3,000"*.
   - The AI extracts the budget (`3000`), searches catalog, recommends the **Wireless Ergonomic Keyboard** (₹1,499) + **Adjustable Aluminium Laptop Stand** (₹1,299) totaling **₹2,798** (well under ₹3,000).
   - The AI identifies remaining budget and recommends a complementary **Wireless Optical Mouse** (₹799) or **USB-C Hub** as a cross-sell.
   - Click **"+ Add"** on the keyboard and stand, and click **"+ Add Companion"** on the mouse.
3. **Confirmation-Gated Cart & Razorpay Checkout (Tab 3)**:
   - View the server-calculated subtotal and breakdown.
   - Observe that the **"Pay with Razorpay Test Mode"** button is disabled until the user checks the **Confirmation Gate** checkbox.
   - Check the confirmation box and click Pay.
   - The test simulator or Razorpay Checkout creates the order in paise, confirms the HMAC verification, updates the order status to `PAID`, and decrements inventory in SQLite.
4. **Merchant Growth Analytics & Safety Audit Log (Tab 4)**:
   - View updated conversion metrics: Total Conversations, Carts Created, Paid Test Orders, Average Cart Value, and Cross-sell Acceptance Rate.
   - Inspect the live **Safety Audit Trail** table showing JSON timestamps for intent extraction, candidate filtering, cart total verification, and payment signature verification.

---

## 📜 License
MIT License. Built for Track 01 Merchant Commerce AI & Agentic Workflows.
