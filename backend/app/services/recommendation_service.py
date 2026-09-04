import re
import json
from typing import List, Optional, Tuple, Dict, Any
from ..database import db_session, log_audit
from ..models.schemas import (
    ProductResponse, ExtractedIntent, ProductRecommendation,
    CrossSellSuggestion, ChatResponse
)
from .catalog_service import CatalogService
from .llm_service import LLMService
from ..config import settings

# Rule-based cross-sell mappings (Category / Tag -> Complementary Categories/Keywords)
CROSS_SELL_RULES: Dict[str, Dict[str, Any]] = {
    "keyboards": {
        "target_categories": ["Mice", "Accessories"],
        "preferred_tags": ["mouse", "wrist-rest", "mat"],
        "reason": "Pairs seamlessly with your keyboard for ergonomic typing and navigation."
    },
    "mice": {
        "target_categories": ["Accessories", "Keyboards"],
        "preferred_tags": ["mat", "wrist-rest", "keyboard"],
        "reason": "Enhances precision and desk comfort alongside your mouse."
    },
    "stands": {
        "target_categories": ["Accessories", "Mice", "Keyboards"],
        "preferred_tags": ["hub", "cooling", "keyboard"],
        "reason": "Expands laptop connectivity and cooling while elevated on the stand."
    },
    "cameras": {
        "target_categories": ["Audio", "Lighting"],
        "preferred_tags": ["headset", "microphone", "lighting", "lamp"],
        "reason": "Provides studio-grade audio and lighting for crystal-clear video calls."
    },
    "audio": {
        "target_categories": ["Cameras", "Lighting"],
        "preferred_tags": ["webcam", "camera", "lighting"],
        "reason": "Completes your professional meeting and work-from-home audio-visual kit."
    }
}

class RecommendationService:
    @staticmethod
    def extract_intent(user_message: str) -> ExtractedIntent:
        """
        Extracts structured intent from user message via LLM (OpenRouter / Gemini)
        with defensive schema validation and fallback parser.
        """
        return LLMService.extract_intent(user_message)

    @staticmethod
    def search_and_recommend(
        intent: ExtractedIntent,
        session_id: str = "customer_chat"
    ) -> Tuple[List[ProductRecommendation], List[CrossSellSuggestion], str, bool]:
        """
        Deterministic backend search & ranking with LLM explainability.
        Guarantees:
        1. Only catalog in-stock products are recommended.
        2. Strict budget compliance (sum <= budget or single item <= budget).
        3. Explainable reasons for every recommendation and cross-sell.
        """
        all_in_stock = CatalogService.list_products(in_stock_only=True)
        if not all_in_stock:
            return ([], [], "The product catalog is currently empty or all items are out of stock. Please check back later.", True)

        budget = intent.budget
        reqs = [r.lower() for r in intent.requirements]
        is_bundle_search = "setup" in reqs or "bundle" in reqs or (not intent.category and len(reqs) > 1)

        recommendations: List[ProductRecommendation] = []
        cross_sells: List[CrossSellSuggestion] = []
        budget_respected = True

        # Bundle / Multi-Product Setup Recommendation Flow (e.g., "WFH setup under 3000")
        if is_bundle_search and budget:
            scored_products = []
            for p in all_in_stock:
                p_tags = [t.lower() for t in p.tags.split(";")]
                match_count = sum(1 for r in reqs if r in p_tags or r in p.name.lower() or r in p.description.lower())
                scored_products.append((p, match_count))

            # Sort by relevance match then price
            scored_products.sort(key=lambda x: (-x[1], x[0].price))
            
            selected_items: List[ProductResponse] = []
            current_total = 0.0
            
            # Select 1-2 essential core items that fit budget
            for p, score in scored_products:
                if current_total + p.price <= budget:
                    if not any(item.category == p.category for item in selected_items):
                        selected_items.append(p)
                        current_total += p.price
                        if len(selected_items) >= 2:
                            break

            if not selected_items and scored_products:
                for p, score in scored_products:
                    if p.price <= budget:
                        selected_items.append(p)
                        current_total += p.price
                        break

            for p in selected_items:
                recommendations.append(ProductRecommendation(
                    product=p,
                    reason=f"Recommended for your setup. Fits perfectly within your ₹{budget:,.0f} budget.",
                    match_score=0.95,
                    is_upsell=False
                ))

            # Check for cross-sell complementary item with remaining budget
            remaining_budget = budget - current_total
            rec_cat_names = [r.product.category.lower() for r in recommendations]
            
            for p in all_in_stock:
                if p.id not in [r.product.id for r in recommendations]:
                    for cat in rec_cat_names:
                        rule = CROSS_SELL_RULES.get(cat, {})
                        if p.category in rule.get("target_categories", []):
                            cross_sells.append(CrossSellSuggestion(
                                product=p,
                                complementary_to=", ".join([r.product.name for r in recommendations]),
                                reason=rule.get("reason", "Complementary accessory for your workspace setup."),
                                savings_tip=f"Adds complete utility for ₹{p.price:,.0f}." if p.price <= remaining_budget else f"High-value upgrade for only ₹{p.price:,.0f}."
                            ))
                            break
                if len(cross_sells) >= 2:
                    break

        # Single Category / Targeted Search Flow (e.g., "keyboard under 1500" or "wireless mouse")
        else:
            candidates: List[ProductResponse] = []
            for p in all_in_stock:
                p_tags = [t.lower() for t in p.tags.split(";")]
                name_desc = (p.name + " " + p.description).lower()
                
                matches_cat = (intent.category and p.category.lower() == intent.category.lower())
                matches_req = any(r in p_tags or r in name_desc for r in reqs) if reqs else True

                if matches_cat or matches_req:
                    if budget is None or p.price <= budget:
                        candidates.append(p)

            candidates.sort(key=lambda x: x.price)

            for p in candidates[:2]:
                recommendations.append(ProductRecommendation(
                    product=p,
                    reason=f"In-stock {p.category.lower()} matching your requirements." + (f" Well within your ₹{budget:,.0f} budget." if budget else ""),
                    match_score=0.90,
                    is_upsell=False
                ))

            # Up-sell suggestion if a premium variant exists
            if intent.category:
                upsell_candidates = [
                    p for p in all_in_stock 
                    if p.category.lower() == intent.category.lower() 
                    and p.id not in [r.product.id for r in recommendations]
                    and (not budget or p.price <= budget * 1.35)
                ]
                if upsell_candidates:
                    premium = max(upsell_candidates, key=lambda x: x.price)
                    recommendations.append(ProductRecommendation(
                        product=premium,
                        reason=f"Premium {premium.name} with advanced features for ₹{premium.price:,.0f}.",
                        match_score=0.85,
                        is_upsell=True
                    ))

            # Cross-sell suggestions
            if recommendations:
                primary_cat = recommendations[0].product.category.lower()
                rule = CROSS_SELL_RULES.get(primary_cat, {})
                target_cats = rule.get("target_categories", ["Accessories"])
                
                for p in all_in_stock:
                    if p.category in target_cats and p.id not in [r.product.id for r in recommendations]:
                        cross_sells.append(CrossSellSuggestion(
                            product=p,
                            complementary_to=recommendations[0].product.name,
                            reason=rule.get("reason", "Great companion item for your selection."),
                            savings_tip=f"Complete your setup for ₹{p.price:,.0f}"
                        ))
                        if len(cross_sells) >= 2:
                            break

        # Generate conversational reply summary using LLM service (with sandboxed candidate constraint)
        primary_recs = [r.product for r in recommendations if not r.is_upsell]
        reply = LLMService.generate_explanation(intent, primary_recs, cross_sells)
        if not recommendations and budget:
            budget_respected = False

        # Log audit trail
        log_audit(
            session_id=session_id,
            action="AI_RECOMMENDATION",
            input_data={"intent": intent.model_dump(), "budget": budget},
            output_data={
                "recommended_ids": [r.product.id for r in recommendations],
                "cross_sell_ids": [c.product.id for c in cross_sells],
                "budget_respected": budget_respected
            }
        )

        return (recommendations, cross_sells, reply, budget_respected)

    @staticmethod
    def process_chat(session_id: str, message: str) -> ChatResponse:
        """Processes customer chat message end-to-end with intent parsing and recommendations."""
        intent = RecommendationService.extract_intent(message)

        if intent.ambiguous and intent.clarification_question:
            log_audit(session_id=session_id, action="AMBIGUOUS_QUERY_CLARIFICATION", input_data={"message": message})
            return ChatResponse(
                session_id=session_id,
                reply=intent.clarification_question,
                intent=intent,
                recommendations=[],
                cross_sells=[],
                suggested_total=0.0,
                budget_respected=True
            )

        recs, cross_sells, reply, budget_ok = RecommendationService.search_and_recommend(intent, session_id)
        suggested_total = sum(r.product.price for r in recs if not r.is_upsell)

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            intent=intent,
            recommendations=recs,
            cross_sells=cross_sells,
            suggested_total=suggested_total,
            budget_respected=budget_ok
        )
