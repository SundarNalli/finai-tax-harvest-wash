from __future__ import annotations
import datetime as dt
import db

# Deterministic-ish seed based on 'today'

def seed_demo(conn):
    db.clear_all(conn)

    today = dt.date.today()

    # Lots (mixed P/L)
    lots = [
        ("SPY", 50.0, (today - dt.timedelta(days=120)).isoformat(), 520.00),
        ("QQQ", 30.0, (today - dt.timedelta(days=90)).isoformat(), 480.00),
        ("AAPL", 40.0, (today - dt.timedelta(days=400)).isoformat(), 195.00),
        ("TSLA", 20.0, (today - dt.timedelta(days=70)).isoformat(), 270.00),
        ("NVDA", 10.0, (today - dt.timedelta(days=50)).isoformat(), 130.00),
        ("VTI", 60.0, (today - dt.timedelta(days=200)).isoformat(), 260.00),
    ]
    db.insert_lots(conn, lots)

    # Recent buys (one blocks SPY cluster)
    buys = [
        ("VOO", 5.0, (today - dt.timedelta(days=15)).isoformat()),
        ("AAPL", 5.0, (today - dt.timedelta(days=15)).isoformat()),
    ]
    db.insert_recent_buys(conn, buys)

    # Market prices
    prices = {
        "SPY": 500.00, "IVV": 500.10, "VOO": 499.90,
        "VTI": 250.00, "ITOT": 248.50, "SCHB": 249.75,
        "SCHX": 52.00, "VTV": 160.00, "SCHF": 36.00,
        "QQQ": 455.00, "QQQM": 354.00,
        "SCHG": 77.00, "XLK": 225.00, "IYW": 120.00,
        "AAPL": 178.00, "VGT": 540.00,
        "TSLA": 245.00, "XLY": 180.00, "CARZ": 52.00, "DRIV": 28.00,
        "NVDA": 115.00, "SOXX": 210.00, "SMH": 195.00,
    }
    db.upsert_prices(conn, today.isoformat(), prices)

    # Policy clusters + alternatives
    clusters = []
    cluster_map = {
        1: ["SPY","IVV","VOO"],
        2: ["QQQ","QQQM"],
        3: ["VTI","ITOT","SCHB"],
    }
    for cid, symbols in cluster_map.items():
        for s in symbols:
            clusters.append((cid, s))

    alternatives = []
    alt_map = {
        "SPY": ["VTI","SCHX","ITOT"],
        "IVV": ["VTI","SCHX","ITOT"],
        "VOO": ["VTI","SCHX","ITOT"],
        "QQQ": ["SCHG","XLK","IYW"],
        "QQQM": ["SCHG","XLK","IYW"],
        "VTI": ["SCHX","VTV","SCHF"],
        "ITOT": ["SCHX","VTV","SCHF"],
        "SCHB": ["SCHX","VTV","SCHF"],
        "AAPL": ["XLK","VGT"],
        "TSLA": ["XLY","CARZ","DRIV"],
        "NVDA": ["SOXX","SMH"],
    }
    for base, lst in alt_map.items():
        for alt in lst:
            alternatives.append((base, alt))

    db.set_policy(conn, clusters, alternatives)

    return {
        "lots": len(lots),
        "recent_buys": len(buys),
        "market_symbols": len(prices),
        "clusters": len(clusters),
        "alternatives": len(alternatives),
    }
