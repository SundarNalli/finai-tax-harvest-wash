from __future__ import annotations
from typing import List, Tuple, Optional
import datetime as dt
import json
from models import (
    TaxLot, RecentBuy, MarketData, ReplacementPolicy, HarvestItem, HarvestPlan
)

# ---- Navigator ----

class WashSaleNavigator:
    def __init__(self, policy: ReplacementPolicy, min_loss_dollars: float = 200.0, min_loss_pct: float = 0.05):
        self.policy = policy
        self.min_loss_dollars = min_loss_dollars
        self.min_loss_pct = min_loss_pct

    def _cluster(self, symbol: str) -> set[str]:
        return set(self.policy.prohibited_equivalents[0]) if False else self.policy.cluster_for(symbol)

    def _is_blocked(self, symbol: str, sale_date: dt.date, buys: List[RecentBuy]) -> Tuple[bool, str]:
        cluster = self.policy.cluster_for(symbol)
        for rb in buys:
            if rb.symbol in cluster and 0 <= (sale_date - rb.date).days <= 30:
                return True, f"Recent buy on {rb.date.isoformat()} for {rb.symbol} triggers 30-day window"
        return False, ""

    def _pick_replacement(self, symbol: str, proceeds: float, market: MarketData) -> Tuple[Optional[str], Optional[float], Optional[float]]:
        for alt in self.policy.safe_alternatives(symbol):
            px = market.price(alt)
            if px and px > 0.01:
                qty = proceeds / px
                return alt, qty, px
        return None, None, None

    def build_plan(self, lots: List[TaxLot], market: MarketData, buys: List[RecentBuy]) -> HarvestPlan:
        items: List[HarvestItem] = []
        total_loss = 0.0
        cash_delta = 0.0
        today = market.asof

        for idx, lot in enumerate(lots):
            px = market.price(lot.symbol)
            if px is None:
                continue
            pnl = px - lot.cost_basis_per_share
            loss_total = (-pnl if pnl < 0 else 0.0) * lot.shares
            loss_pct = (lot.cost_basis_per_share - px) / max(lot.cost_basis_per_share, 1e-9) if lot.cost_basis_per_share > 0 else 0.0

            if loss_total < self.min_loss_dollars or loss_pct < self.min_loss_pct:
                continue

            blocked, reason = self._is_blocked(lot.symbol, today, buys)
            proceeds = lot.shares * px

            repl_symbol = None
            repl_shares = None
            repl_price = None

            if not blocked:
                repl_symbol, repl_shares, repl_price = self._pick_replacement(lot.symbol, proceeds, market)
                if repl_symbol is None:
                    blocked = True
                    reason = "No safe replacement with known price"

            item = HarvestItem(
                symbol=lot.symbol,
                lot_index=idx,
                shares_to_sell=round(lot.shares, 6),
                sale_price=px,
                loss_dollars=round(loss_total, 2),
                replacement_symbol=repl_symbol,
                replacement_shares=(None if repl_shares is None else round(repl_shares, 6)),
                replacement_price=repl_price,
                sale_date=today,
                reentry_date_ok_after=today + dt.timedelta(days=31),
                wash_sale_blocked=blocked,
                block_reason=(reason if blocked else None),
                notes=None,
            )

            if not blocked:
                total_loss += item.loss_dollars
                repl_cost = (repl_shares or 0.0) * (repl_price or 0.0)
                cash_delta += proceeds - repl_cost

            items.append(item)

        plan = HarvestPlan(
            asof=today,
            items=items,
            total_harvestable_loss=round(total_loss, 2),
            simulated_cash_delta=round(cash_delta, 2),
        )
        # sanity validation
        for it in plan.items:
            if not it.wash_sale_blocked:
                if it.replacement_symbol in self.policy.cluster_for(it.symbol):
                    raise ValueError("Replacement is substantially identical")
                if (it.reentry_date_ok_after - it.sale_date).days < 31:
                    raise ValueError("Re-entry date violates 31-day rule")
        return plan

# ---- Policy Seeder ----

def demo_policy() -> ReplacementPolicy:
    clusters = [
        ["SPY", "IVV", "VOO"],
        ["QQQ", "QQQM"],
        ["VTI", "ITOT", "SCHB"],
    ]
    alternatives = {
        "SPY": ["VTI", "SCHX", "ITOT"],
        "IVV": ["VTI", "SCHX", "ITOT"],
        "VOO": ["VTI", "SCHX", "ITOT"],
        "QQQ": ["SCHG", "XLK", "IYW"],
        "QQQM": ["SCHG", "XLK", "IYW"],
        "VTI": ["SCHX", "VTV", "SCHF"],
        "ITOT": ["SCHX", "VTV", "SCHF"],
        "SCHB": ["SCHX", "VTV", "SCHF"],
        "AAPL": ["XLK", "VGT"],
        "TSLA": ["XLY", "CARZ", "DRIV"],
        "NVDA": ["SOXX", "SMH"],
    }
    return ReplacementPolicy(prohibited_equivalents=clusters, recommended_alternatives=alternatives)

# ---- LLM Explanation (Optional) ----

def explain_plan(plan: HarvestPlan) -> str:
    try:
        import ollama
        payload = {
            "asof": plan.asof.isoformat(),
            "total_loss": plan.total_harvestable_loss,
            "cash_delta": plan.simulated_cash_delta,
            "items": [
                {
                    "symbol": it.symbol,
                    "lot_index": it.lot_index,
                    "loss": it.loss_dollars,
                    "repl": it.replacement_symbol,
                    "qty": it.replacement_shares,
                    "blocked": it.wash_sale_blocked,
                    "reason": it.block_reason,
                    "reenter": it.reentry_date_ok_after.isoformat(),
                } for it in plan.items
            ]
        }
        prompt = (
            "Explain this tax-loss harvesting plan in concise bullets for an investor. "
            "Cover what's sold and why, wash-sale avoidance, replacements, and re-entry date.\n\n"
            + json.dumps(payload, indent=2)
        )
        resp = ollama.chat(model="llama3.2", messages=[{"role": "user", "content": prompt}], options={"num_ctx": 4096})
        return resp.get("message", {}).get("content", "").strip() or "(empty LLM response)"
    except Exception:
        # deterministic fallback
        lines = [
            f"As of {plan.asof.isoformat()}, estimated harvestable loss ≈ ${plan.total_harvestable_loss:,.2f}.",
        ]
        if abs(plan.simulated_cash_delta) > 0.01:
            lines.append(f"Approx. cash drift from replacements: ${plan.simulated_cash_delta:,.2f}.")
        for it in plan.items:
            if it.wash_sale_blocked:
                lines.append(f"BLOCKED {it.symbol}[lot {it.lot_index}] — {it.block_reason}")
            else:
                lines.append(
                    f"SELL {it.symbol}[lot {it.lot_index}] to harvest ${it.loss_dollars:,.2f}; "
                    f"BUY {it.replacement_symbol} (~{it.replacement_shares:.4f} sh). "
                    f"Re-enter after {it.reentry_date_ok_after.isoformat()}."
                )
        lines.append("(Demo only, not tax advice.)")
        return "\n".join(lines)
