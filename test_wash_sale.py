from __future__ import annotations
from fastapi.testclient import TestClient
from main import app

def test_build_and_latest_plan():
    client = TestClient(app)

    # Seed demo
    r = client.post("/seed/demo")
    assert r.status_code == 200

    # Build plan
    r = client.post("/plan/build")
    assert r.status_code == 200
    data = r.json()
    assert "plan_id" in data

    # Fetch latest
    r = client.get("/plan/latest")
    assert r.status_code == 200
    plan = r.json()
    items = plan["items"]
    assert isinstance(items, list) and len(items) > 0

    # Ensure SPY cluster is blocked due to recent VOO buy
    blocked_syms = {i["symbol"] for i in items if i["wash_sale_blocked"]}
    assert "SPY" in blocked_syms or "IVV" in blocked_syms or "VOO" in blocked_syms

    # Ensure any non-blocked item has safe replacement and 31+ days re-entry
    for it in items:
        if not it["wash_sale_blocked"]:
            assert it["replacement_symbol"] is not None
            assert it["replacement_symbol"] not in {"SPY","IVV","VOO"} if it["symbol"] in {"SPY","IVV","VOO"} else True
            # 31-day rule
            from datetime import date
            sale = date.fromisoformat(it["sale_date"])
            reenter = date.fromisoformat(it["reentry_date_ok_after"])
            assert (reenter - sale).days >= 31


def test_explain_latest_text():
    client = TestClient(app)
    client.post("/seed/demo")
    client.post("/plan/build")

    r = client.post("/explain/latest")
    assert r.status_code == 200
    assert isinstance(r.text, str)
    assert len(r.text) > 0