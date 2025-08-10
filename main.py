from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from typing import List, Dict
import datetime as dt
import json

import db
from models import TaxLot, RecentBuy, MarketData, ReplacementPolicy, HarvestItem, HarvestPlan
from logic import WashSaleNavigator, demo_policy, explain_plan
from seed import seed_demo

app = FastAPI(title="Tax-Loss Harvesting API", version="0.1.0")
_conn = db.connect()
db.init_db(_conn)

# ---------- Utilities ----------

def _policy_from_db() -> ReplacementPolicy:
    # clusters
    cur = _conn.execute("SELECT cluster_id, symbol FROM policy_clusters ORDER BY cluster_id, symbol")
    clusters_map: Dict[int, List[str]] = {}
    for row in cur.fetchall():
        clusters_map.setdefault(row["cluster_id"], []).append(row["symbol"])
    clusters = list(clusters_map.values())

    # alternatives
    cur = _conn.execute("SELECT symbol, alt_symbol FROM policy_alternatives ORDER BY symbol, alt_symbol")
    alts: Dict[str, List[str]] = {}
    for r in cur.fetchall():
        alts.setdefault(r["symbol"], []).append(r["alt_symbol"])

    if not clusters and not alts:
        return demo_policy()
    return ReplacementPolicy(prohibited_equivalents=clusters, recommended_alternatives=alts)


def _load_state():
    lots_rows = db.fetch_lots(_conn)
    lots = [TaxLot(symbol=r["symbol"], shares=r["shares"], buy_date=dt.date.fromisoformat(r["buy_date"]), cost_basis_per_share=r["cost_basis_per_share"]) for r in lots_rows]
    buy_rows = db.fetch_recent_buys(_conn)
    recent = [RecentBuy(symbol=r["symbol"], shares=r["shares"], date=dt.date.fromisoformat(r["date"])) for r in buy_rows]
    asof_str, prices = db.fetch_market(_conn)
    market = MarketData(asof=dt.date.fromisoformat(asof_str), prices=prices)
    return lots, recent, market

# ---------- Routes ----------

@app.post("/seed/demo")
def seed():
    summary = seed_demo(_conn)
    return {"status": "ok", **summary}

@app.get("/portfolio")
def get_portfolio():
    lots, _, market = _load_state()
    return {
        "asof": market.asof,
        "lots": [l.model_dump() for l in lots],
    }

@app.get("/market")
def get_market():
    asof_str, prices = db.fetch_market(_conn)
    return {"asof": asof_str, "prices": prices}

@app.post("/market")
def set_market(body: Dict[str, float]):
    asof = dt.date.today().isoformat()
    db.upsert_prices(_conn, asof, body)
    return {"status": "ok", "count": len(body), "asof": asof}

@app.get("/recent-buys")
def get_recent_buys():
    rows = db.fetch_recent_buys(_conn)
    return [{"symbol": r["symbol"], "shares": r["shares"], "date": r["date"]} for r in rows]

@app.post("/plan/build")
def build_plan(min_loss_dollars: float = 200.0, min_loss_pct: float = 0.05):
    lots, recent, market = _load_state()
    policy = _policy_from_db()
    nav = WashSaleNavigator(policy=policy, min_loss_dollars=min_loss_dollars, min_loss_pct=min_loss_pct)
    plan = nav.build_plan(lots, market, recent)

    # Persist
    plan_id = db.insert_plan(_conn, market.asof.isoformat(), plan.total_harvestable_loss, plan.simulated_cash_delta)
    items_json = [json.dumps(i.model_dump(), default=str) for i in plan.items]
    db.insert_plan_items(_conn, plan_id, items_json)

    return {"plan_id": plan_id, **plan.model_dump()}

@app.get("/plan/latest")
def get_latest_plan():
    prow = db.fetch_latest_plan(_conn)
    if not prow:
        raise HTTPException(status_code=404, detail="No plans yet")
    items_json = db.fetch_plan_items(_conn, int(prow["id"]))
    items = [HarvestItem(**json.loads(j)) for j in items_json]
    plan = HarvestPlan(asof=dt.date.fromisoformat(prow["asof"]), items=items, total_harvestable_loss=prow["total_loss"], simulated_cash_delta=prow["cash_delta"])
    return {"plan_id": int(prow["id"]), **plan.model_dump()}

@app.post("/explain/{plan_id}", response_class=PlainTextResponse)
@app.post("/explain/latest", response_class=PlainTextResponse)
def explain(plan_id: int | None = None):
    if plan_id is None:
        prow = db.fetch_latest_plan(_conn)
        if not prow:
            raise HTTPException(status_code=404, detail="No plans yet")
        plan_id = int(prow["id"])  # type: ignore
    items_json = db.fetch_plan_items(_conn, plan_id)
    if not items_json:
        raise HTTPException(status_code=404, detail="Plan items not found")
    prow = _conn.execute("SELECT asof, total_loss, cash_delta FROM plans WHERE id=?", (plan_id,)).fetchone()
    items = [HarvestItem(**json.loads(j)) for j in items_json]
    plan = HarvestPlan(asof=dt.date.fromisoformat(prow["asof"]), items=items, total_harvestable_loss=prow["total_loss"], simulated_cash_delta=prow["cash_delta"])
    text = explain_plan(plan)
    return text

@app.get("/")
def root():
    return {"service": "TLH Navigator", "endpoints": ["/seed/demo", "/portfolio", "/market", "/plan/build", "/plan/latest", "/explain/latest"]}
