"""Margin Impact Engine.

Computes contract-level margin impacts for Ni, Co, Li, MHP contracts.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from .config import RiskConfig
from .models import Commodity, Contract, MarginImpact


class MarginEngine:
    """Engine for computing margin impacts on commodity contracts."""

    # Standard margin requirements by commodity (% of notional)
    DEFAULT_MARGINS: dict[Commodity, float] = {
        Commodity.NICKEL: 0.12,
        Commodity.COBALT: 0.15,
        Commodity.LITHIUM: 0.18,
        Commodity.MHP: 0.14,
        Commodity.COPPER: 0.08,
        Commodity.IRON_ORE: 0.10,
    }

    # Volatility buffers by commodity (additional margin buffer %)
    VOLATILITY_BUFFERS: dict[Commodity, float] = {
        Commodity.NICKEL: 0.05,
        Commodity.COBALT: 0.08,
        Commodity.LITHIUM: 0.12,
        Commodity.MHP: 0.07,
        Commodity.COPPER: 0.04,
        Commodity.IRON_ORE: 0.03,
    }

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()

    def compute_contract_margin(
        self,
        contract: Contract,
        current_price_usd: float,
        fx_rate: float = 1.0,
        calculation_date: Optional[date] = None,
    ) -> MarginImpact:
        """Compute margin impact for a single contract.

        Args:
            contract: The commodity contract.
            current_price_usd: Current market price in USD/t.
            fx_rate: FX rate (foreign currency per USD).
            calculation_date: Date of calculation.

        Returns:
            MarginImpact with full margin breakdown.
        """
        calc_date = calculation_date or date.today()
        commodity = contract.commodity

        # Notional value in USD
        notional_usd = contract.notional_volume_tonnes * current_price_usd

        # Mark-to-market
        strike = contract.strike_price_usd or current_price_usd
        mtm_per_tonne = current_price_usd - strike
        mtm_usd = mtm_per_tonne * contract.notional_volume_tonnes

        # Unrealized P&L (accounting for FX)
        unrealized_pnl = mtm_usd * fx_rate

        # Margin requirement
        base_margin_pct = contract.margin_pct or self.DEFAULT_MARGINS.get(commodity, 0.10)
        margin_required = notional_usd * base_margin_pct

        # Volatility buffer
        vol_buffer_pct = self.VOLATILITY_BUFFERS.get(commodity, 0.05)
        margin_buffer = notional_usd * vol_buffer_pct

        # Total margin required with buffer
        total_margin = margin_required + margin_buffer

        # Margin call check
        margin_call_triggered = unrealized_pnl < -(total_margin * self.config.margin_call_threshold_pct)

        return MarginImpact(
            contract_id=contract.contract_id,
            commodity=commodity,
            calculation_date=calc_date,
            notional_usd=round(notional_usd, 2),
            mark_to_market_usd=round(mtm_usd, 2),
            unrealized_pnl_usd=round(unrealized_pnl, 2),
            margin_required_usd=round(total_margin, 2),
            margin_buffer_usd=round(margin_buffer, 2),
            margin_call_triggered=margin_call_triggered,
            exposure_contribution_pct=0.0,  # Set in batch computation
        )

    def compute_batch_margins(
        self,
        contracts: list[Contract],
        prices: dict[str, float],
        fx_rates: dict[str, float] | None = None,
        calculation_date: Optional[date] = None,
    ) -> list[MarginImpact]:
        """Compute margins for a batch of contracts.

        Args:
            contracts: List of commodity contracts.
            prices: Dict of commodity -> current price USD/t.
            fx_rates: Dict of currency code -> FX rate.
            calculation_date: Date of calculation.

        Returns:
            List of MarginImpact objects with exposure contributions.
        """
        fx_rates = fx_rates or {}
        results: list[MarginImpact] = []

        total_notional = sum(
            c.notional_volume_tonnes * prices.get(c.commodity.value, 0)
            for c in contracts
        ) or 1.0

        for contract in contracts:
            current_price = prices.get(contract.commodity.value, 0)
            fx = fx_rates.get(contract.currency.value, 1.0)

            impact = self.compute_contract_margin(
                contract=contract,
                current_price_usd=current_price,
                fx_rate=fx,
                calculation_date=calculation_date,
            )

            # Exposure contribution
            impact.exposure_contribution_pct = round(
                impact.notional_usd / total_notional * 100, 2
            )

            results.append(impact)

        return sorted(results, key=lambda m: m.notional_usd, reverse=True)

    def compute_portfolio_summary(
        self,
        margins: list[MarginImpact],
    ) -> dict:
        """Compute aggregate portfolio margin summary.

        Args:
            margins: List of computed margin impacts.

        Returns:
            Dictionary with portfolio-level summary.
        """
        if not margins:
            return {
                "total_notional_usd": 0,
                "total_mtm_usd": 0,
                "total_unrealized_pnl_usd": 0,
                "total_margin_required_usd": 0,
                "margin_calls": 0,
                "contract_count": 0,
            }

        return {
            "total_notional_usd": round(sum(m.notional_usd for m in margins), 2),
            "total_mtm_usd": round(sum(m.mark_to_market_usd for m in margins), 2),
            "total_unrealized_pnl_usd": round(sum(m.unrealized_pnl_usd for m in margins), 2),
            "total_margin_required_usd": round(sum(m.margin_required_usd for m in margins), 2),
            "total_margin_buffer_usd": round(sum(m.margin_buffer_usd for m in margins), 2),
            "margin_calls": sum(1 for m in margins if m.margin_call_triggered),
            "contract_count": len(margins),
            "avg_margin_pct": round(
                sum(m.margin_required_usd for m in margins)
                / max(sum(m.notional_usd for m in margins), 1)
                * 100,
                4,
            ),
        }
