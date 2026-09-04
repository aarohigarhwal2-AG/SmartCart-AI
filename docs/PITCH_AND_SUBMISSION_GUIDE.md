# 🏆 SmartCart AI — Project Pitch, Submission Guide & Technical Documentation

> **Track 01**: AI Commerce & Agentic Merchant Workflows  
> **Repository**: [https://github.com/aarohigarhwal2-AG/SmartCart-AI](https://github.com/aarohigarhwal2-AG/SmartCart-AI)  
> **One-Click Deploy**: [Deploy to Render](https://render.com/deploy?repo=https://github.com/aarohigarhwal2-AG/SmartCart-AI)

---

## 📌 1. Project Overview & One-Liner
**SmartCart AI** is a conversational merchant growth agent that converts raw product catalogs into AI-readable inventories, extracts structured customer intents within budget constraints (supporting English, Hindi, and Hinglish), performs explainable upselling and cross-selling, and creates confirmation-gated checkout carts using Razorpay Test Mode.

---

## 🎯 2. Project Objectives
1. **Transform Static Catalogs into AI-Readable Inventories**: Upload, validate, and index merchant CSV product catalogs with row-by-row diagnostics.
2. **Accurately Parse Multilingual Intent & Budget Constraints**: Convert unstructured shopper queries into structured JSON schemas (`budget`, `category`, `requirements`).
3. **Provide Explainable, In-Stock Recommendations**: Recommend product bundles strictly under budget with contextual, explainable cross-sell add-ons.
4. **Enforce Financial Correctness & Safety Gating**: Ensure the LLM never touches pricing or stock calculations. All totals are deterministically computed by the backend.
5. **Confirmation-Gated Razorpay Checkout & Analytics**: Gate payment orders behind explicit user confirmation, process server-side orders in paise with HMAC SHA-256 signatures, and track live merchant conversion metrics.

---

## 💡 3. What Does It Solve?
* **Solves Rigid Keyword Search**: Evaluates complex conversational requests (e.g., *"WFH setup under ₹3,000"*) and automatically bundles matching products under the budget limit.
* **Eliminates LLM Financial Hallucinations**: Implements a strict separation of concerns—AI handles language comprehension and explanations; the backend deterministically controls inventory, prices, and totals.
* **Increases Merchant Cross-Sell Conversions**: Generates contextual, explainable recommendations that show why companion items complete the user's workspace.
* **Prevents Premature & Insecure Payments**: Mandatory confirmation gate and server-side cryptographic signature verification with idempotency protection.
* **Eliminates Black-Box AI Decisions**: Real-time Merchant Analytics Dashboard and a live, structured JSON Safety Audit Trail.

---

## 🛠️ 4. Build Challenges & Technical Obstacles
1. **Preventing LLM Financial Hallucinations**: Sandboxed the LLM to only explain backend-verified items; all arithmetic (`subtotal = sum(price * qty)`) is handled by Python and SQLite.
2. **Multilingual & Hinglish Token Collisions**: Solved regex token collisions between English `k` multiplier and Hindi word *"ke"* using strict word boundaries `(k\b)` and defensive schema sanitization.
3. **SQLite Concurrency & Lock Contention**: Configured SQLite with Write-Ahead Logging (`WAL`) and connection timeouts to eliminate transaction locks.
4. **Razorpay Server-Side Gating & Idempotency**: Required `user_confirmed: true` flag and bound order amounts in paise with HMAC-SHA256 signature verification.
5. **Cross-Platform Portability**: Configured standard ASCII console output for Windows and added root deployment files (`render.yaml`, `Procfile`, `requirements.txt`).

---

## 🎬 5. 5-Minute Video Pitch & Demo Script

### Timeline Overview
* **0:00 – 0:45**: The Hook & Problem Statement (rigid search vs dangerous hallucinations).
* **0:45 – 1:30**: Core Architectural Principle (AI Language vs Backend Financial Determinism).
* **1:30 – 3:30**: Live Product Walkthrough (Merchant CSV upload → Hinglish chat query → In-budget bundle → Confirmation gate → Razorpay Test payment).
* **3:30 – 4:15**: Merchant Growth Analytics & Live Safety Audit Trail.
* **4:15 – 5:00**: Testing Rigor (19/19 pytest pass), Open Source, and Wrap-Up.

---

## 🧪 6. Verification & Automated Test Matrix (19/19 Passed)
* ✅ Budget ₹3,000 constraint enforcement (bundle total <= budget).
* ✅ Out-of-stock items exclusion from recommendations and cart additions.
* ✅ CSV parser validation (rejecting negative prices, non-numeric stock, missing columns).
* ✅ Multilingual intent extraction (Hindi, English, Hinglish).
* ✅ Mandatory confirmation gate before order creation.
* ✅ Server-side Razorpay order in paise (`amount * 100`).
* ✅ HMAC SHA-256 payment signature verification and stock deduction.
* ✅ Duplicate callback idempotency.
