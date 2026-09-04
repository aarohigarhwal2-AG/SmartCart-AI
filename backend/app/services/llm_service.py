import re
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
import requests
from ..config import settings
from ..models.schemas import ExtractedIntent, ProductResponse, CrossSellSuggestion

logger = logging.getLogger("smartcart.llm")

INTENT_EXTRACTION_SYSTEM_PROMPT = """You are the Intent Extraction Engine for SmartCart AI, an e-commerce shopping agent.
Your job is to convert natural language shopper messages into structured JSON.
You must understand queries in English, Hindi (Devanagari), and Hinglish (e.g., "मुझे work from home के लिए ₹3,000 के अंदर setup चाहिए", "1500 ke andar keyboard dikhao", "laptop stand for wfh").

Return ONLY a JSON object matching this schema:
{
  "intent": "product_search" | "budget_inquiry" | "clarification" | "add_to_cart" | "checkout_inquiry" | "general_help",
  "budget": number | null,
  "category": string | null,
  "requirements": string[],
  "quantity": number,
  "ambiguous": boolean,
  "clarification_question": string | null
}

Guidelines:
1. Extract numerical budget (e.g., "₹3,000", "3000", "3k", "under 1500" -> 3000, 1500). If no budget is mentioned, set budget to null.
2. Standardize categories: "Keyboards", "Mice", "Stands", "Cameras", "Audio", "Lighting", "Accessories".
3. Extract relevant search keywords into "requirements" (e.g., ["work-from-home", "office", "ergonomic", "wireless"]).
4. If the message is too vague (e.g., "hi", "help", "suggest something" without any context or budget), set "ambiguous": true and provide a friendly "clarification_question".
5. Never invent or hallucinate product names or prices.
"""

RECOMMENDATION_EXPLANATION_SYSTEM_PROMPT = """You are the AI Merchant Assistant for SmartCart AI.
Your role is to write a concise, conversational, and transparent explanation of why the recommended products fit the customer's constraints.

CRITICAL SAFETY RULES:
1. You may ONLY reference the exact product names, categories, and prices provided in the candidate list.
2. NEVER invent, hallucinate, or mention products not in the provided candidates list.
3. NEVER alter or calculate different prices. Use the exact provided prices.
4. Highlight how the combination stays within the customer's budget and satisfies their requirements.
5. If complementary cross-sell accessories are provided, explain how they enhance the setup.
6. Keep the tone professional, helpful, and concise (2-4 sentences max).
"""

class LLMService:
    @staticmethod
    def is_llm_available() -> bool:
        """Checks if an LLM provider key (OpenRouter or Gemini) is configured."""
        return bool(settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("sk-or-v1-demo")) or bool(settings.GEMINI_API_KEY)

    @staticmethod
    def call_openrouter(messages: List[Dict[str, str]], json_mode: bool = False, temperature: float = 0.2) -> Optional[str]:
        """Calls OpenRouter chat completions API."""
        if not settings.OPENROUTER_API_KEY:
            return None

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com/smartcart-ai",
            "X-Title": "SmartCart AI Merchant Commerce",
            "Content-Type": "application/json"
        }

        payload: Dict[str, Any] = {
            "model": settings.OPENROUTER_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 500
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.warning(f"OpenRouter API returned status {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.warning(f"OpenRouter API request failed: {e}")
            return None

    @staticmethod
    def extract_intent(user_message: str) -> ExtractedIntent:
        """
        Extracts structured intent from user message via OpenRouter / Gemini with defensive validation and fallback.
        """
        # Try OpenRouter if key is present
        if settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("sk-or-v1-demo"):
            messages = [
                {"role": "system", "content": INTENT_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
            raw_response = LLMService.call_openrouter(messages, json_mode=True)
            if raw_response:
                try:
                    # Clean markdown fence if present
                    clean_json = raw_response.strip()
                    if clean_json.startswith("```json"):
                        clean_json = clean_json[7:]
                    if clean_json.startswith("```"):
                        clean_json = clean_json[3:]
                    if clean_json.endswith("```"):
                        clean_json = clean_json[:-3]
                    parsed = json.loads(clean_json.strip())
                    return LLMService.validate_and_sanitize_intent(parsed, user_message)
                except Exception as e:
                    logger.warning(f"Failed to parse LLM intent response: {e}")

        # Deterministic heuristic fallback
        return LLMService._fallback_intent_extractor(user_message)

    @staticmethod
    def validate_and_sanitize_intent(data: Dict[str, Any], raw_message: str) -> ExtractedIntent:
        """Defensive validation and sanitization for intent schemas."""
        allowed_intents = {"product_search", "budget_inquiry", "clarification", "add_to_cart", "checkout_inquiry", "general_help"}
        intent_type = data.get("intent", "product_search")
        if intent_type not in allowed_intents:
            intent_type = "product_search"

        # Validate budget
        budget_val = data.get("budget")
        budget: Optional[float] = None
        if budget_val is not None:
            try:
                budget = float(budget_val)
                if budget <= 0:
                    budget = None
            except (ValueError, TypeError):
                budget = None

        # Validate category
        category = data.get("category")
        if category and not isinstance(category, str):
            category = None

        # Validate requirements
        reqs = data.get("requirements", [])
        if not isinstance(reqs, list):
            reqs = []
        requirements = [str(r).strip().lower() for r in reqs if r]

        # Validate quantity
        quantity = 1
        try:
            quantity = max(1, int(data.get("quantity", 1)))
        except (ValueError, TypeError):
            quantity = 1

        ambiguous = bool(data.get("ambiguous", False))
        clarification_question = data.get("clarification_question")

        # Ambiguity safety check
        if not category and budget is None and not requirements and intent_type == "product_search":
            ambiguous = True
            clarification_question = clarification_question or "Could you share what products you are looking for (e.g., keyboard, mouse, stand) and your budget?"

        return ExtractedIntent(
            intent=intent_type,
            budget=budget,
            category=category,
            requirements=requirements,
            quantity=quantity,
            ambiguous=ambiguous,
            clarification_question=clarification_question
        )

    @staticmethod
    def generate_explanation(
        user_intent: ExtractedIntent,
        recommended_products: List[ProductResponse],
        cross_sells: List[CrossSellSuggestion]
    ) -> str:
        """
        Generates conversational explanation for verified product recommendations using OpenRouter or deterministic template.
        """
        if not recommended_products:
            if user_intent.budget:
                return f"I could not find any in-stock items under ₹{user_intent.budget:,.0f} matching your query. Would you like to adjust your budget or explore other categories?"
            return "I couldn't find matching products in the catalog right now. Try searching for keyboards, mice, laptop stands, or desk accessories!"

        # If LLM available, format prompt with STRICT sandbox candidate list
        if settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("sk-or-v1-demo"):
            prompt_context = {
                "customer_budget": user_intent.budget,
                "customer_requirements": user_intent.requirements,
                "verified_candidates": [
                    {"name": p.name, "category": p.category, "price": f"₹{p.price:,.0f}"} 
                    for p in recommended_products
                ],
                "verified_cross_sells": [
                    {"name": c.product.name, "price": f"₹{c.product.price:,.0f}", "reason": c.reason}
                    for c in cross_sells
                ]
            }

            messages = [
                {"role": "system", "content": RECOMMENDATION_EXPLANATION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Customer Request Context: {json.dumps(prompt_context)}\nWrite the recommendation explanation following the safety rules:"}
            ]

            llm_text = LLMService.call_openrouter(messages, json_mode=False, temperature=0.3)
            if llm_text and len(llm_text.strip()) > 10:
                return llm_text.strip()

        # Deterministic explainable fallback template
        rec_names = [f"**{p.name}** (₹{p.price:,.0f})" for p in recommended_products]
        combo_total = sum(p.price for p in recommended_products)
        
        if len(rec_names) > 1:
            reply = f"Here is a curated setup within your requirements: {', '.join(rec_names)}. Combined total is **₹{combo_total:,.0f}**."
        else:
            reply = f"I recommend {rec_names[0]} based on your criteria."

        if user_intent.budget:
            remaining = user_intent.budget - combo_total
            if remaining > 0:
                reply += f" It fits within your ₹{user_intent.budget:,.0f} budget with **₹{remaining:,.0f}** to spare."

        if cross_sells:
            reply += f" You can also pair it with **{cross_sells[0].product.name}** (₹{cross_sells[0].product.price:,.0f}) as a complementary addition."

        return reply

    @staticmethod
    def _fallback_intent_extractor(user_message: str) -> ExtractedIntent:
        """Regex/Heuristic fallback for offline / zero-config intent extraction."""
        text = user_message.strip()
        lower = text.lower()

        # 1. Budget extraction (Handles ₹, Rs, 3k, 3000, 3,000, under 3000, 3000 ke andar)
        budget: Optional[float] = None
        budget_match = re.search(r'(?:under|below|budget of|budget|within|max|upto|up to|₹|rs\.?|के अंदर|के अन्दर)?\s*(?:₹|rs\.?)?\s*(\d+(?:,\d+)?)\s*(k\b)?', lower)
        if budget_match:
            num_str = budget_match.group(1).replace(',', '')
            val = float(num_str)
            if budget_match.group(2) and budget_match.group(2).lower() == 'k':
                val *= 1000
            budget = val

        # 2. Requirements & category mapping
        requirements: List[str] = []
        category: Optional[str] = None
        
        keywords_map = {
            "work from home": ["work-from-home", "office"],
            "wfh": ["work-from-home", "office"],
            "office": ["office"],
            "setup": ["setup", "bundle"],
            "keyboard": ["keyboard"],
            "mouse": ["mouse"],
            "stand": ["stand", "laptop"],
            "laptop": ["laptop"],
            "hub": ["hub", "usb"],
            "webcam": ["webcam", "camera"],
            "camera": ["camera", "webcam"],
            "headset": ["headset", "audio"],
            "headphones": ["audio", "headset"],
            "lamp": ["lighting", "lamp"],
            "light": ["lighting"],
            "mat": ["mat", "desk"],
            "wrist rest": ["wrist-rest"],
            "cooling": ["cooling", "stand"],
            "ergonomic": ["ergonomic"]
        }

        for k, tags in keywords_map.items():
            if k in lower:
                requirements.extend(tags)
                if k in ["keyboard", "keyboards"]:
                    category = "Keyboards"
                elif k in ["mouse", "mice"]:
                    category = "Mice"
                elif k in ["stand", "stands"]:
                    category = "Stands"
                elif k in ["webcam", "camera"]:
                    category = "Cameras"
                elif k in ["headset", "headphones"]:
                    category = "Audio"

        requirements = list(dict.fromkeys(requirements))

        # Intent
        if any(w in lower for w in ["add", "cart", "buy", "purchase", "checkout"]):
            intent_type = "add_to_cart" if "add" in lower else "checkout_inquiry"
        elif any(w in lower for w in ["help", "what can you do", "who are you"]):
            intent_type = "general_help"
        elif len(text.split()) < 3 and not category and not budget and not requirements:
            intent_type = "clarification"
        else:
            intent_type = "product_search"

        ambiguous = False
        clarification_question = None
        if intent_type == "product_search" and not category and not budget and not requirements:
            ambiguous = True
            clarification_question = "Could you tell me what kind of setup or accessories you are looking for (e.g., keyboard, mouse, stand) and your budget?"

        return ExtractedIntent(
            intent=intent_type,
            budget=budget,
            category=category,
            requirements=requirements,
            quantity=1,
            ambiguous=ambiguous,
            clarification_question=clarification_question
        )
