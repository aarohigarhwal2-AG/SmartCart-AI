import json
from typing import List, Dict, Any
from ..database import db_session
from ..models.schemas import MerchantAnalytics, AuditLogItem
from ..config import settings

class AnalyticsService:
    @staticmethod
    def get_metrics() -> MerchantAnalytics:
        with db_session() as conn:
            # Live counts from database
            chats_count = conn.execute("SELECT COUNT(DISTINCT session_id) FROM audit_logs WHERE action IN ('AI_RECOMMENDATION', 'AMBIGUOUS_QUERY_CLARIFICATION')").fetchone()[0]
            search_count = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action = 'AI_RECOMMENDATION'").fetchone()[0]
            
            carts_count = conn.execute("SELECT COUNT(*) FROM carts").fetchone()[0]
            orders_created = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            orders_paid = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'paid'").fetchone()[0]
            orders_failed = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'failed'").fetchone()[0]
            
            rev_row = conn.execute("SELECT SUM(amount) FROM orders WHERE status = 'paid'").fetchone()[0]
            live_revenue = float(rev_row or 0.0)

            # Cross-sell metrics
            cross_impressions = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action = 'AI_RECOMMENDATION' AND output_data LIKE '%cross_sell_ids%'").fetchone()[0]
            cross_adds = conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action = 'CART_ITEM_ADDED'").fetchone()[0]

            # Aggregate baseline + live
            total_convs = settings.DEMO_BASELINE_CONVERSATIONS + chats_count
            total_searches = settings.DEMO_BASELINE_CONVERSATIONS - 3 + search_count
            total_carts = settings.DEMO_BASELINE_CARTS + carts_count
            total_checkouts = settings.DEMO_BASELINE_CHECKOUTS + orders_created
            total_paid = settings.DEMO_BASELINE_PAYMENTS + orders_paid
            
            baseline_rev = settings.DEMO_BASELINE_PAYMENTS * 2490.0 # ~₹14,940
            total_revenue = baseline_rev + live_revenue
            
            avg_cart = total_revenue / max(1, total_paid)

            total_cross_impressions = 28 + cross_impressions
            total_cross_accepted = 11 + min(cross_adds, cross_impressions)
            acceptance_rate = round((total_cross_accepted / max(1, total_cross_impressions)) * 100, 1)

            return MerchantAnalytics(
                total_conversations=total_convs,
                product_search_requests=total_searches,
                carts_created=total_carts,
                checkout_attempts=total_checkouts,
                successful_test_payments=total_paid,
                failed_payments=orders_failed,
                average_cart_value=round(avg_cart, 2),
                cross_sell_impressions=total_cross_impressions,
                cross_sell_accepted=total_cross_accepted,
                cross_sell_acceptance_rate_pct=acceptance_rate,
                total_revenue=round(total_revenue, 2),
                data_mode="Synthetic Demo Baseline + Live Session Activity"
            )

    @staticmethod
    def get_audit_logs(limit: int = 50) -> List[AuditLogItem]:
        with db_session() as conn:
            cursor = conn.execute(
                "SELECT id, session_id, action, input_data, output_data, timestamp FROM audit_logs ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            logs: List[AuditLogItem] = []
            for r in rows:
                in_data = json.loads(r["input_data"]) if r["input_data"] else None
                out_data = json.loads(r["output_data"]) if r["output_data"] else None
                logs.append(AuditLogItem(
                    id=r["id"],
                    session_id=r["session_id"],
                    action=r["action"],
                    input_data=in_data,
                    output_data=out_data,
                    timestamp=r["timestamp"]
                ))
            return logs
