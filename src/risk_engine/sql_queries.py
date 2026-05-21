"""SQL query templates for Commodity Risk dashboards."""

from .config import RiskConfig


def get_top_contracts_by_risk_query(
    config: RiskConfig | None = None,
    limit: int = 10,
) -> str:
    """Top contracts by risk exposure."""
    cfg = config or RiskConfig()
    return f"""
SELECT
    contract_id,
    commodity,
    notional_usd,
    mark_to_market_usd,
    unrealized_pnl_usd,
    margin_required_usd,
    margin_call_triggered,
    exposure_contribution_pct
FROM {cfg.gold_margin_fqn}
WHERE calculation_date = (SELECT MAX(calculation_date) FROM {cfg.gold_margin_fqn})
ORDER BY notional_usd DESC
LIMIT {limit};
"""


def get_var_summary_query(
    config: RiskConfig | None = None,
) -> str:
    """VaR summary by method."""
    cfg = config or RiskConfig()
    return f"""
SELECT
    method,
    confidence_level,
    time_horizon_days,
    var_usd,
    cvar_usd,
    portfolio_value_usd,
    var_pct,
    calculation_date
FROM {cfg.gold_var_fqn}
WHERE calculation_date = (SELECT MAX(calculation_date) FROM {cfg.gold_var_fqn})
ORDER BY method;
"""


def get_price_volatility_query(
    config: RiskConfig | None = None,
) -> str:
    """Commodity price volatility summary."""
    cfg = config or RiskConfig()
    return f"""
SELECT
    commodity,
    COUNT(*) AS data_points,
    ROUND(AVG(daily_return), 6) AS avg_daily_return,
    ROUND(STDDEV(daily_return), 6) AS daily_vol,
    ROUND(STDDEV(daily_return) * SQRT(252), 4) AS annualized_vol,
    ROUND(MIN(daily_return), 6) AS min_return,
    ROUND(MAX(daily_return), 6) AS max_return,
    ROUND(LAST(price_usd, price_date) - FIRST(price_usd, price_date), 2) AS price_change
FROM {cfg.silver_returns_fqn}
GROUP BY commodity
ORDER BY annualized_vol DESC;
"""


def get_fx_exposure_query(
    config: RiskConfig | None = None,
) -> str:
    """FX exposure breakdown."""
    cfg = config or RiskConfig()
    return f"""
SELECT
    currency,
    ROUND(AVG(fx_rate), 4) AS avg_fx_rate,
    ROUND(MIN(fx_rate), 4) AS min_fx_rate,
    ROUND(MAX(fx_rate), 4) AS max_fx_rate,
    COUNT(DISTINCT price_date) AS data_points
FROM {cfg.bronze_fx_fqn}
WHERE price_date >= DATE_SUB(CURRENT_DATE(), 30)
GROUP BY currency
ORDER BY avg_fx_rate;
"""


def get_margin_call_alerts_query(
    config: RiskConfig | None = None,
) -> str:
    """Contracts triggering margin calls."""
    cfg = config or RiskConfig()
    return f"""
SELECT
    m.contract_id,
    m.commodity,
    m.notional_usd,
    m.unrealized_pnl_usd,
    m.margin_required_usd,
    m.margin_buffer_usd,
    m.exposure_contribution_pct,
    m.calculation_date,
    c.counterparty,
    c.maturity_date
FROM {cfg.gold_margin_fqn} m
LEFT JOIN {cfg.silver_prices_fqn} c
    ON m.contract_id = c.contract_id
WHERE m.margin_call_triggered = true
  AND m.calculation_date = (SELECT MAX(calculation_date) FROM {cfg.gold_margin_fqn})
ORDER BY m.unrealized_pnl_usd ASC;
"""


def get_portfolio_pnl_query(
    config: RiskConfig | None = None,
) -> str:
    """Portfolio P&L by commodity."""
    cfg = config or RiskConfig()
    return f"""
SELECT
    commodity,
    SUM(notional_usd) AS total_notional,
    SUM(mark_to_market_usd) AS total_mtm,
    SUM(unrealized_pnl_usd) AS total_pnl,
    ROUND(SUM(unrealized_pnl_usd) / NULLIF(SUM(notional_usd), 0) * 100, 4) AS pnl_pct,
    COUNT(*) AS contract_count
FROM {cfg.gold_margin_fqn}
WHERE calculation_date = (SELECT MAX(calculation_date) FROM {cfg.gold_margin_fqn})
GROUP BY commodity
ORDER BY total_pnl ASC;
"""


def get_var_breach_history_query(
    config: RiskConfig | None = None,
) -> str:
    """VaR breach history over time."""
    cfg = config or RiskConfig()
    return f"""
SELECT
    calculation_date,
    method,
    confidence_level,
    var_usd,
    cvar_usd,
    breaches_last_year,
    expected_breaches,
    ROUND(breaches_last_year / NULLIF(expected_breaches, 0), 2) AS breach_ratio
FROM {cfg.gold_var_fqn}
ORDER BY calculation_date DESC, method;
"""
