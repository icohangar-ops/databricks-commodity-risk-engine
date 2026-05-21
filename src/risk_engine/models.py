"""Pydantic models for the Commodity Risk Engine."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Commodity(str, Enum):
    """Tracked commodities."""

    NICKEL = "Ni"
    COBALT = "Co"
    LITHIUM = "Li"
    MHP = "MHP"
    COPPER = "Cu"
    IRON_ORE = "Fe"


class ContractType(str, Enum):
    """Contract types."""

    PHYSICAL = "physical"
    FORWARD = "forward"
    FUTURE = "future"
    SWAP = "swap"
    OPTION = "option"


class Currency(str, Enum):
    """ISO 4217 currencies."""

    USD = "USD"
    AUD = "AUD"
    CAD = "CAD"
    CNY = "CNY"
    EUR = "EUR"
    JPY = "JPY"
    GBP = "GBP"
    ZAR = "ZAR"
    CHF = "CHF"
    BRL = "BRL"


class CommodityPrice(BaseModel):
    """A single commodity price observation."""

    price_id: str
    commodity: Commodity
    price_date: date
    price_usd: float = Field(..., gt=0, description="Price in USD per tonne")
    unit: str = "USD/t"
    volume: Optional[float] = Field(None, description="Trading volume")
    open_usd: Optional[float] = None
    high_usd: Optional[float] = None
    low_usd: Optional[float] = None
    close_usd: Optional[float] = None
    source: str = "LME"
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


class Contract(BaseModel):
    """A commodity trading contract."""

    contract_id: str
    contract_type: ContractType
    commodity: Commodity
    notional_volume_tonnes: float = Field(..., gt=0)
    strike_price_usd: Optional[float] = Field(None, description="Strike or agreed price")
    current_price_usd: Optional[float] = Field(None, description="Current market price")
    contract_date: date
    maturity_date: date
    counterparty: str
    currency: Currency = Currency.USD
    fx_rate: float = Field(default=1.0, description="FX rate vs USD")
    margin_pct: Optional[float] = Field(None, description="Initial margin %")
    status: str = "active"


class RiskMetrics(BaseModel):
    """Risk metrics for a commodity or portfolio."""

    commodity: Commodity
    calculation_date: date
    window_days: int = 252

    daily_volatility: float = Field(..., ge=0, description="Annualized daily vol %")
    mean_return: float = Field(..., description="Mean daily return")
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class MarginImpact(BaseModel):
    """Margin impact assessment for a contract."""

    contract_id: str
    commodity: Commodity
    calculation_date: date

    notional_usd: float = Field(..., description="Notional value in USD")
    mark_to_market_usd: float = Field(..., description="Current MtM in USD")
    unrealized_pnl_usd: float = Field(..., description="Unrealized P&L")
    margin_required_usd: float = Field(..., description="Margin required")
    margin_buffer_usd: float = Field(default=0.0, description="Buffer above margin")
    margin_call_triggered: bool = False
    exposure_contribution_pct: float = Field(..., ge=0, le=100)

    computed_at: datetime = Field(default_factory=datetime.utcnow)


class VaRResult(BaseModel):
    """Value-at-Risk computation result."""

    portfolio_id: str = "default"
    method: str = Field(..., description="parametric, historical, or monte_carlo")
    confidence_level: float = Field(..., gt=0.5, le=1.0)
    time_horizon_days: int = 1
    calculation_date: date

    var_usd: float = Field(..., description="VaR in USD")
    cvar_usd: Optional[float] = Field(None, description="Conditional VaR (Expected Shortfall)")
    portfolio_value_usd: float = Field(default=1_000_000.0)
    var_pct: Optional[float] = Field(None, description="VaR as % of portfolio")

    # Component VaRs
    component_var: Optional[dict[str, float]] = Field(None, description="VaR by commodity")

    # Validation
    breaches_last_year: Optional[int] = None
    expected_breaches: Optional[float] = None

    computed_at: datetime = Field(default_factory=datetime.utcnow)
