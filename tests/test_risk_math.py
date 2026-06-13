"""Characterization and edge-case tests for the money/math critical path.

Covers the two engines that produce dollar figures fed to risk reporting:

  * ``risk_engine.va_calculator.VaRCalculator`` -- parametric & historical VaR,
    volatility, max drawdown.
  * ``risk_engine.margin_engine.MarginEngine`` -- contract margin, margin calls,
    batch exposure contributions, portfolio summary.

Expected values are derived by hand from the formulas (see comments), so a
regression in the math will fail these tests rather than silently shipping a
wrong number. Two regression guards lock in bugs that were found and fixed
while writing these tests:

  * single-asset 1-D parametric VaR used to crash (``np.cov`` collapsing to a
    0-d array before the ``w @ cov @ w`` quadratic form), and
  * omitting ``calculation_date`` used to crash pydantic validation (empty
    string is not a date).
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pytest
from scipy import stats

from risk_engine.config import RiskConfig
from risk_engine.margin_engine import MarginEngine
from risk_engine.models import Commodity, Contract, ContractType, Currency, MarginImpact
from risk_engine.va_calculator import VaRCalculator

CALC_DATE = "2026-06-13"


# --------------------------------------------------------------------------- #
# VaRCalculator -- parametric                                                 #
# --------------------------------------------------------------------------- #
class TestParametricVaR:
    def test_single_asset_matches_closed_form(self):
        """1-D returns: VaR% = z * sigma * sqrt(h) - mean * h, in USD * portfolio.

        This also guards the single-asset regression: np.cov on a (T, 1) array
        collapses to a 0-d scalar, which previously broke the quadratic form.
        """
        returns = np.array([0.01, -0.02, 0.015, -0.005, 0.0])
        calc = VaRCalculator(confidence=0.99, time_horizon_days=1,
                             portfolio_value=1_000_000.0)

        sigma = float(np.std(returns, ddof=1))          # sample std, ddof=1
        mean = float(np.mean(returns))
        z = float(stats.norm.ppf(0.99))
        expected_var_pct = z * sigma * math.sqrt(1) - mean * 1
        expected_var_usd = round(abs(expected_var_pct) * 1_000_000.0, 2)

        res = calc.parametric_var(returns, calculation_date=CALC_DATE)

        assert res.method == "parametric"
        assert res.var_usd == pytest.approx(expected_var_usd, abs=0.01)
        assert res.var_pct == pytest.approx(round(abs(expected_var_pct) * 100, 4), abs=1e-4)

    def test_missing_calculation_date_does_not_crash(self):
        """Regression: calculation_date is optional; omitting it must not raise.

        The empty-string fallback used to fail pydantic date validation.
        """
        res = VaRCalculator(confidence=0.99).parametric_var(
            np.array([0.01, -0.02, 0.015, -0.005, 0.0])
        )
        # Whatever the default, it must parse as a real date.
        assert date.fromisoformat(str(res.calculation_date))

    def test_higher_confidence_gives_higher_var(self):
        """Monotonicity: 99% VaR must exceed 95% VaR for the same returns."""
        returns = np.array([0.01, -0.02, 0.015, -0.005, 0.0, 0.03, -0.01])
        var95 = VaRCalculator(confidence=0.95).parametric_var(
            returns, calculation_date=CALC_DATE).var_usd
        var99 = VaRCalculator(confidence=0.99).parametric_var(
            returns, calculation_date=CALC_DATE).var_usd
        assert var99 > var95 > 0

    def test_zero_volatility_zero_mean_gives_zero_var(self):
        """Edge: constant zero returns => sigma=0, mean=0 => VaR=0."""
        res = VaRCalculator(confidence=0.99).parametric_var(
            np.zeros(6), calculation_date=CALC_DATE)
        assert res.var_usd == 0.0
        assert res.var_pct == 0.0

    def test_zero_volatility_nonzero_drift(self):
        """Edge: constant positive returns => sigma=0, VaR driven by -mean*h.

        returns all 0.01, h=1, portfolio 1e6 => |0 - 0.01*1| * 1e6 = 10_000.
        """
        res = VaRCalculator(confidence=0.99, portfolio_value=1_000_000.0).parametric_var(
            np.full(5, 0.01), calculation_date=CALC_DATE)
        assert res.var_usd == pytest.approx(10_000.0, abs=0.01)

    def test_time_horizon_scales_by_sqrt(self):
        """sqrt-of-time: with ~zero mean, 4-day VaR ~= 2x 1-day VaR."""
        returns = np.array([0.01, -0.01, 0.02, -0.02, 0.015, -0.015])
        v1 = VaRCalculator(confidence=0.99, time_horizon_days=1).parametric_var(
            returns, calculation_date=CALC_DATE).var_usd
        v4 = VaRCalculator(confidence=0.99, time_horizon_days=4).parametric_var(
            returns, calculation_date=CALC_DATE).var_usd
        assert v4 == pytest.approx(v1 * math.sqrt(4), rel=0.02)

    def test_two_asset_component_var_and_value(self):
        """Multi-asset parametric path computes and rounds component VaRs."""
        returns = np.array([
            [0.01, 0.02], [-0.02, -0.01], [0.015, 0.0],
            [-0.005, 0.01], [0.0, -0.02],
        ])
        res = VaRCalculator(confidence=0.99).parametric_var(
            returns, calculation_date=CALC_DATE)
        assert set(res.component_var.keys()) == {"asset_0", "asset_1"}
        assert res.var_usd > 0


# --------------------------------------------------------------------------- #
# VaRCalculator -- historical simulation                                      #
# --------------------------------------------------------------------------- #
class TestHistoricalVaR:
    def test_known_quantile(self):
        """idx = int((1-conf) * N); VaR = -sorted_returns[idx], * portfolio.

        200 obs, conf=0.99 => idx=2 => 3rd-smallest return. The constructed
        series sorts to [-0.10 x20, -0.08 x20, ...] so the 3rd element is -0.10.
        VaR% = 0.10 => 0.10 * 1e6 = 100_000.
        """
        block = np.array([-0.10, -0.08, -0.06, -0.04, -0.02,
                          0.0, 0.02, 0.04, 0.06, 0.08])
        returns = np.tile(block, 20)  # 200 obs
        res = VaRCalculator(confidence=0.99, portfolio_value=1_000_000.0).historical_simulation(
            returns, calculation_date=CALC_DATE)
        assert res.method == "historical_simulation"
        assert res.var_usd == pytest.approx(100_000.0, abs=0.01)

    def test_cvar_at_least_var(self):
        """Expected shortfall (CVaR) must be >= VaR (tail mean is worse)."""
        rng = np.random.default_rng(42)
        returns = rng.normal(0, 0.02, size=1000)
        res = VaRCalculator(confidence=0.99).historical_simulation(
            returns, calculation_date=CALC_DATE)
        assert res.cvar_usd >= res.var_usd > 0

    def test_missing_calculation_date_does_not_crash(self):
        res = VaRCalculator(confidence=0.99).historical_simulation(
            np.tile(np.array([-0.05, 0.0, 0.05]), 50))
        assert date.fromisoformat(str(res.calculation_date))


# --------------------------------------------------------------------------- #
# VaRCalculator -- volatility & drawdown                                      #
# --------------------------------------------------------------------------- #
class TestVolatilityAndDrawdown:
    def test_annualized_volatility(self):
        """vol = std(ddof=1) * sqrt(252)."""
        returns = np.array([0.01, -0.02, 0.015, -0.005, 0.0])
        calc = VaRCalculator()
        expected = float(np.std(returns, ddof=1)) * math.sqrt(252)
        assert calc.compute_volatility(returns) == pytest.approx(expected, rel=1e-9)

    def test_unannualized_volatility(self):
        returns = np.array([0.01, -0.02, 0.015, -0.005, 0.0])
        calc = VaRCalculator()
        assert calc.compute_volatility(returns, annualize=False) == pytest.approx(
            float(np.std(returns, ddof=1)), rel=1e-9)

    def test_max_drawdown_known_series(self):
        """Peak 120 -> trough 80 => drawdown 40/120 = 0.3333..."""
        prices = np.array([100.0, 120.0, 90.0, 110.0, 80.0])
        assert VaRCalculator().compute_max_drawdown(prices) == pytest.approx(
            (120.0 - 80.0) / 120.0, rel=1e-9)

    def test_monotone_increasing_series_has_zero_drawdown(self):
        prices = np.array([100.0, 101.0, 105.0, 110.0])
        assert VaRCalculator().compute_max_drawdown(prices) == pytest.approx(0.0, abs=1e-12)


# --------------------------------------------------------------------------- #
# MarginEngine                                                                #
# --------------------------------------------------------------------------- #
def _contract(commodity=Commodity.NICKEL, volume=100.0, strike=18000.0,
              margin_pct=None, currency=Currency.USD):
    return Contract(
        contract_id="C1",
        contract_type=ContractType.FORWARD,
        commodity=commodity,
        notional_volume_tonnes=volume,
        strike_price_usd=strike,
        contract_date=date(2026, 1, 1),
        maturity_date=date(2026, 12, 1),
        counterparty="ACME",
        currency=currency,
        margin_pct=margin_pct,
    )


class TestContractMargin:
    def test_known_nickel_contract(self):
        """100t Ni @ 20000, strike 18000.

        notional = 100 * 20000 = 2_000_000
        mtm      = (20000 - 18000) * 100 = 200_000
        margin   = notional * (0.12 base + 0.05 vol buffer) = 340_000
        buffer   = notional * 0.05 = 100_000
        pnl      = mtm * fx(1.0) = 200_000  -> positive, no margin call
        """
        m = MarginEngine().compute_contract_margin(
            _contract(), current_price_usd=20000.0, calculation_date=date(2026, 6, 13))
        assert m.notional_usd == pytest.approx(2_000_000.0)
        assert m.mark_to_market_usd == pytest.approx(200_000.0)
        assert m.margin_required_usd == pytest.approx(340_000.0)
        assert m.margin_buffer_usd == pytest.approx(100_000.0)
        assert m.unrealized_pnl_usd == pytest.approx(200_000.0)
        assert m.margin_call_triggered is False

    def test_fx_rate_applied_to_pnl(self):
        """Unrealized P&L is MtM * fx_rate."""
        m = MarginEngine().compute_contract_margin(
            _contract(), current_price_usd=20000.0, fx_rate=1.5,
            calculation_date=date(2026, 6, 13))
        # mtm = 200_000; pnl = 200_000 * 1.5
        assert m.unrealized_pnl_usd == pytest.approx(300_000.0)

    def test_loss_triggers_margin_call(self):
        """Strike 30000 above price 20000 => big negative P&L beyond threshold.

        notional @ 20000 = 2_000_000; total_margin = 340_000;
        threshold = 340_000 * 0.05 = 17_000;
        pnl = (20000 - 30000) * 100 = -1_000_000 < -17_000 => call.
        """
        m = MarginEngine().compute_contract_margin(
            _contract(strike=30000.0), current_price_usd=20000.0,
            calculation_date=date(2026, 6, 13))
        assert m.unrealized_pnl_usd == pytest.approx(-1_000_000.0)
        assert m.margin_call_triggered is True

    def test_small_loss_below_threshold_no_call(self):
        """A loss smaller than the threshold must NOT trigger a margin call.

        threshold = 340_000 * 0.05 = 17_000. Strike 20100 => pnl = -100*100 =
        -10_000, which is inside the threshold.
        """
        m = MarginEngine().compute_contract_margin(
            _contract(strike=20100.0), current_price_usd=20000.0,
            calculation_date=date(2026, 6, 13))
        assert m.unrealized_pnl_usd == pytest.approx(-10_000.0)
        assert m.margin_call_triggered is False

    def test_explicit_margin_pct_overrides_default(self):
        """contract.margin_pct overrides the per-commodity DEFAULT_MARGINS."""
        m = MarginEngine().compute_contract_margin(
            _contract(margin_pct=0.20), current_price_usd=20000.0,
            calculation_date=date(2026, 6, 13))
        # base 0.20 + vol buffer 0.05 = 0.25 -> 2_000_000 * 0.25 = 500_000
        assert m.margin_required_usd == pytest.approx(500_000.0)

    def test_strike_defaults_to_current_price_zero_mtm(self):
        """No strike => strike = current price => zero MtM, zero P&L."""
        c = _contract(strike=None)
        m = MarginEngine().compute_contract_margin(
            c, current_price_usd=20000.0, calculation_date=date(2026, 6, 13))
        assert m.mark_to_market_usd == pytest.approx(0.0)
        assert m.unrealized_pnl_usd == pytest.approx(0.0)


class TestBatchAndSummary:
    def test_exposure_contributions_sum_to_100(self):
        contracts = [
            Contract(contract_id="A", contract_type=ContractType.FORWARD,
                     commodity=Commodity.NICKEL, notional_volume_tonnes=100,
                     strike_price_usd=18000, contract_date=date(2026, 1, 1),
                     maturity_date=date(2026, 12, 1), counterparty="X"),
            Contract(contract_id="B", contract_type=ContractType.FORWARD,
                     commodity=Commodity.COBALT, notional_volume_tonnes=50,
                     strike_price_usd=30000, contract_date=date(2026, 1, 1),
                     maturity_date=date(2026, 12, 1), counterparty="Y"),
        ]
        prices = {"Ni": 20000.0, "Co": 40000.0}
        out = MarginEngine().compute_batch_margins(
            contracts, prices, calculation_date=date(2026, 6, 13))
        # Ni notional 2_000_000; Co notional 2_000_000; total 4_000_000 -> 50/50.
        assert sum(m.exposure_contribution_pct for m in out) == pytest.approx(100.0, abs=0.01)
        for m in out:
            assert m.exposure_contribution_pct == pytest.approx(50.0, abs=0.01)

    def test_batch_sorted_by_notional_desc(self):
        contracts = [
            Contract(contract_id="small", contract_type=ContractType.FORWARD,
                     commodity=Commodity.NICKEL, notional_volume_tonnes=1,
                     strike_price_usd=18000, contract_date=date(2026, 1, 1),
                     maturity_date=date(2026, 12, 1), counterparty="X"),
            Contract(contract_id="big", contract_type=ContractType.FORWARD,
                     commodity=Commodity.NICKEL, notional_volume_tonnes=1000,
                     strike_price_usd=18000, contract_date=date(2026, 1, 1),
                     maturity_date=date(2026, 12, 1), counterparty="X"),
        ]
        out = MarginEngine().compute_batch_margins(
            contracts, {"Ni": 20000.0}, calculation_date=date(2026, 6, 13))
        assert [m.contract_id for m in out] == ["big", "small"]

    def test_portfolio_summary_aggregates(self):
        engine = MarginEngine()
        contracts = [
            Contract(contract_id="A", contract_type=ContractType.FORWARD,
                     commodity=Commodity.NICKEL, notional_volume_tonnes=100,
                     strike_price_usd=18000, contract_date=date(2026, 1, 1),
                     maturity_date=date(2026, 12, 1), counterparty="X"),
            Contract(contract_id="B", contract_type=ContractType.FORWARD,
                     commodity=Commodity.NICKEL, notional_volume_tonnes=200,
                     strike_price_usd=30000, contract_date=date(2026, 1, 1),
                     maturity_date=date(2026, 12, 1), counterparty="Y"),
        ]
        margins = engine.compute_batch_margins(
            contracts, {"Ni": 20000.0}, calculation_date=date(2026, 6, 13))
        summary = engine.compute_portfolio_summary(margins)

        assert summary["contract_count"] == 2
        assert summary["total_notional_usd"] == pytest.approx(
            sum(m.notional_usd for m in margins))
        assert summary["total_unrealized_pnl_usd"] == pytest.approx(
            sum(m.unrealized_pnl_usd for m in margins))
        # Contract B is a 10_000 USD loss/t over 200t = -2_000_000 -> margin call.
        assert summary["margin_calls"] == 1

    def test_empty_portfolio_summary(self):
        summary = MarginEngine().compute_portfolio_summary([])
        assert summary["contract_count"] == 0
        assert summary["total_notional_usd"] == 0
        assert summary["margin_calls"] == 0
