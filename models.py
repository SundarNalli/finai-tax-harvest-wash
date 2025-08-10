from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import datetime as dt

# ---- Domain Models ----

class TaxLot(BaseModel):
    symbol: str
    shares: float
    buy_date: dt.date
    cost_basis_per_share: float

class Portfolio(BaseModel):
    lots: List[TaxLot] = Field(default_factory=list)
    cash: float = 0.0

class RecentBuy(BaseModel):
    date: dt.date
    symbol: str
    shares: float

class MarketData(BaseModel):
    asof: dt.date
    prices: Dict[str, float] = Field(default_factory=dict)

    def price(self, symbol: str) -> Optional[float]:
        return self.prices.get(symbol)

# ---- Policy ----

class ReplacementPolicy(BaseModel):
    prohibited_equivalents: List[List[str]] = Field(default_factory=list)
    recommended_alternatives: Dict[str, List[str]] = Field(default_factory=dict)

    def cluster_for(self, symbol: str) -> set[str]:
        for cluster in self.prohibited_equivalents:
            if symbol in cluster:
                return set(cluster)
        return {symbol}

    def safe_alternatives(self, symbol: str) -> List[str]:
        cluster = self.cluster_for(symbol)
        alts = self.recommended_alternatives.get(symbol, [])
        if not alts:
            # try match by any symbol sharing a cluster mapping
            for s, lst in self.recommended_alternatives.items():
                if symbol in self.cluster_for(s):
                    alts = lst
                    break
        return [a for a in alts if a not in cluster]

# ---- Planning Schemas ----

class HarvestItem(BaseModel):
    symbol: str
    lot_index: int
    shares_to_sell: float
    sale_price: float
    loss_dollars: float
    replacement_symbol: Optional[str]
    replacement_shares: Optional[float]
    replacement_price: Optional[float]
    sale_date: dt.date
    reentry_date_ok_after: dt.date
    wash_sale_blocked: bool = False
    block_reason: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("loss_dollars")
    @classmethod
    def loss_positive(cls, v: float):
        if v < 0:
            raise ValueError("loss_dollars must be >= 0")
        return v

class HarvestPlan(BaseModel):
    asof: dt.date
    items: List[HarvestItem]
    total_harvestable_loss: float
    simulated_cash_delta: float
    policy_version: str = "demo-1"

# ---- DB DTOs ----

class PlanRow(BaseModel):
    id: int
    asof: dt.date
    total_loss: float
    cash_delta: float
    created_at: dt.datetime

class PlanItemRow(BaseModel):
    plan_id: int
    item_index: int
    data: HarvestItem
