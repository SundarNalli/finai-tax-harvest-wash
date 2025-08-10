## app/db.py

from __future__ import annotations
import sqlite3
import datetime as dt
from typing import Iterable, List, Dict, Tuple, Optional

DB_PATH = "./tlh.sqlite"

SCHEMA = r"""
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS lots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  shares REAL NOT NULL,
  buy_date TEXT NOT NULL,
  cost_basis_per_share REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS recent_buys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  shares REAL NOT NULL,
  date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_prices (
  symbol TEXT PRIMARY KEY,
  price REAL NOT NULL,
  asof TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS policy_clusters (
  cluster_id INTEGER NOT NULL,
  symbol TEXT NOT NULL,
  PRIMARY KEY (cluster_id, symbol)
);

CREATE TABLE IF NOT EXISTS policy_alternatives (
  symbol TEXT NOT NULL,
  alt_symbol TEXT NOT NULL,
  PRIMARY KEY (symbol, alt_symbol)
);

CREATE TABLE IF NOT EXISTS plans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asof TEXT NOT NULL,
  total_loss REAL NOT NULL,
  cash_delta REAL NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_items (
  plan_id INTEGER NOT NULL,
  item_index INTEGER NOT NULL,
  data_json TEXT NOT NULL,
  PRIMARY KEY (plan_id, item_index),
  FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()

# ---- CRUD helpers ----

def clear_all(conn: sqlite3.Connection) -> None:
    for tbl in ["plan_items", "plans", "policy_alternatives", "policy_clusters", "market_prices", "recent_buys", "lots"]:
        conn.execute(f"DELETE FROM {tbl}")
    conn.commit()

def insert_lots(conn: sqlite3.Connection, rows: Iterable[Tuple[str,float,str,float]]):
    conn.executemany(
        "INSERT INTO lots(symbol, shares, buy_date, cost_basis_per_share) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()

def insert_recent_buys(conn: sqlite3.Connection, rows: Iterable[Tuple[str,float,str]]):
    conn.executemany(
        "INSERT INTO recent_buys(symbol, shares, date) VALUES (?,?,?)",
        rows,
    )
    conn.commit()

def upsert_prices(conn: sqlite3.Connection, asof: str, prices: Dict[str, float]):
    for sym, px in prices.items():
        conn.execute(
            "INSERT INTO market_prices(symbol, price, asof) VALUES (?,?,?) "
            "ON CONFLICT(symbol) DO UPDATE SET price=excluded.price, asof=excluded.asof",
            (sym, px, asof),
        )
    conn.commit()

def set_policy(conn: sqlite3.Connection, clusters: Iterable[Tuple[int, str]], alternatives: Iterable[Tuple[str, str]]):
    conn.execute("DELETE FROM policy_clusters")
    conn.execute("DELETE FROM policy_alternatives")
    conn.executemany("INSERT INTO policy_clusters(cluster_id, symbol) VALUES (?,?)", clusters)
    conn.executemany("INSERT INTO policy_alternatives(symbol, alt_symbol) VALUES (?,?)", alternatives)
    conn.commit()

# ---- Reads ----

def fetch_lots(conn: sqlite3.Connection) -> List[Dict]:
    cur = conn.execute("SELECT symbol, shares, buy_date, cost_basis_per_share FROM lots ORDER BY rowid")
    rows = cur.fetchall()
    # Convert sqlite3.Row objects to dictionaries to preserve column names
    return [dict(row) for row in rows]

def fetch_recent_buys(conn: sqlite3.Connection) -> List[Dict]:
    cur = conn.execute("SELECT symbol, shares, date FROM recent_buys ORDER BY date DESC")
    rows = cur.fetchall()
    # Convert sqlite3.Row objects to dictionaries to preserve column names
    return [dict(row) for row in rows]

def fetch_market(conn: sqlite3.Connection) -> Tuple[str, Dict[str, float]]:
    cur = conn.execute("SELECT symbol, price, asof FROM market_prices")
    rows = cur.fetchall()
    asofs = {r["asof"] for r in rows}
    asof = next(iter(asofs)) if asofs else dt.date.today().isoformat()
    prices = {r["symbol"]: r["price"] for r in rows}
    return asof, prices

# ---- Plans ----

def insert_plan(conn: sqlite3.Connection, asof: str, total_loss: float, cash_delta: float) -> int:
    created_at = dt.datetime.utcnow().isoformat()
    cur = conn.execute(
        "INSERT INTO plans(asof, total_loss, cash_delta, created_at) VALUES (?,?,?,?)",
        (asof, total_loss, cash_delta, created_at),
    )
    conn.commit()
    return int(cur.lastrowid)

def insert_plan_items(conn: sqlite3.Connection, plan_id: int, items_json: List[str]):
    conn.executemany(
        "INSERT INTO plan_items(plan_id, item_index, data_json) VALUES (?,?,?)",
        [(plan_id, i, j) for i, j in enumerate(items_json)],
    )
    conn.commit()

def fetch_latest_plan(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
    cur = conn.execute("SELECT id, asof, total_loss, cash_delta, created_at FROM plans ORDER BY id DESC LIMIT 1")
    return cur.fetchone()

def fetch_plan_items(conn: sqlite3.Connection, plan_id: int) -> List[str]:
    cur = conn.execute("SELECT data_json FROM plan_items WHERE plan_id=? ORDER BY item_index", (plan_id,))
    return [r[0] for r in cur.fetchall()]
