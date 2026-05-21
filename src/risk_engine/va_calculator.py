"""Value-at-Risk (VaR) Calculator.

Implements parametric (variance-covariance) and historical simulation methods.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from scipy import stats

from .models import VaRResult


class VaRCalculator:
    """Compute Value-at-Risk using multiple methods."""

    def __init__(
        self,
        confidence: float = 0.99,
        time_horizon_days: int = 1,
        portfolio_value: float = 1_000_000.0,
    ):
        """Initialize the VaR calculator.

        Args:
            confidence: Confidence level (e.g., 0.99 for 99% VaR).
            time_horizon_days: Holding period in days.
            portfolio_value: Total portfolio value in USD.
        """
        self.confidence = confidence
        self.time_horizon = time_horizon_days
        self.portfolio_value = portfolio_value
        self.z_score = float(stats.norm.ppf(confidence))

    def parametric_var(
        self,
        returns: np.ndarray,
        weights: Optional[np.ndarray] = None,
        portfolio_id: str = "default",
        calculation_date: Optional[str] = None,
    ) -> VaRResult:
        """Compute parametric (variance-covariance) VaR.

        Args:
            returns: Matrix of returns (T x N assets) or 1D array (single asset).
            weights: Portfolio weights (N,). If None, equal-weighted.
            portfolio_id: Identifier for the portfolio.
            calculation_date: Date string (YYYY-MM-DD).

        Returns:
            VaRResult with parametric VaR.
        """
        returns = np.asarray(returns, dtype=np.float64)

        if returns.ndim == 1:
            returns = returns.reshape(-1, 1)

        n_assets = returns.shape[1]
        if weights is None:
            weights = np.ones(n_assets) / n_assets
        else:
            weights = np.asarray(weights, dtype=np.float64)

        # Portfolio returns
        portfolio_returns = returns @ weights

        # Mean and covariance
        mean_returns = np.mean(returns, axis=0)
        cov_matrix = np.cov(returns, rowvar=False)

        # Portfolio mean and std
        port_mean = float(weights @ mean_returns)
        port_std = float(np.sqrt(weights @ cov_matrix @ weights))

        # Scale to time horizon
        h = self.time_horizon
        var_pct = self.z_score * port_std * math.sqrt(h) - port_mean * h
        var_usd = var_pct * self.portfolio_value

        # Conditional VaR (Expected Shortfall)
        threshold = stats.norm.ppf(1 - self.confidence)
        cvar_pct = port_mean * h + port_std * math.sqrt(h) * (
            stats.norm.pdf(threshold) / (1 - self.confidence)
        )
        cvar_usd = cvar_pct * self.portfolio_value

        # Component VaRs
        marginal_vars = self.z_score * (cov_matrix @ weights) * math.sqrt(h)
        component_var = {}
        for i in range(n_assets):
            cv = float(marginal_vars[i] * weights[i] * self.portfolio_value)
            component_var[f"asset_{i}"] = round(cv, 2)

        return VaRResult(
            portfolio_id=portfolio_id,
            method="parametric",
            confidence_level=self.confidence,
            time_horizon_days=h,
            calculation_date=calculation_date or "",
            var_usd=round(abs(var_usd), 2),
            cvar_usd=round(abs(cvar_usd), 2),
            portfolio_value_usd=self.portfolio_value,
            var_pct=round(abs(var_pct) * 100, 4),
            component_var={k: round(v, 2) for k, v in component_var.items()},
            expected_breaches=round((1 - self.confidence) * 252 / h, 1),
        )

    def historical_simulation(
        self,
        returns: np.ndarray,
        weights: Optional[np.ndarray] = None,
        portfolio_id: str = "default",
        calculation_date: Optional[str] = None,
    ) -> VaRResult:
        """Compute VaR using historical simulation.

        Args:
            returns: Matrix of returns (T x N) or 1D array (single asset).
            weights: Portfolio weights (N,). If None, equal-weighted.
            portfolio_id: Identifier for the portfolio.
            calculation_date: Date string (YYYY-MM-DD).

        Returns:
            VaRResult with historical simulation VaR.
        """
        returns = np.asarray(returns, dtype=np.float64)

        if returns.ndim == 1:
            returns = returns.reshape(-1, 1)

        n_assets = returns.shape[1]
        if weights is None:
            weights = np.ones(n_assets) / n_assets

        # Portfolio returns
        portfolio_returns = returns @ weights

        # Scale to time horizon
        h = self.time_horizon
        if h > 1:
            # Use rolling sum for multi-day
            rolled = np.convolve(portfolio_returns, np.ones(h), mode="valid")
            portfolio_returns = rolled

        # Historical VaR
        sorted_returns = np.sort(portfolio_returns)
        idx = int((1 - self.confidence) * len(sorted_returns))
        idx = max(0, min(idx, len(sorted_returns) - 1))
        var_pct = -sorted_returns[idx]
        var_usd = var_pct * self.portfolio_value

        # Conditional VaR
        tail_returns = sorted_returns[:idx + 1]
        cvar_pct = -np.mean(tail_returns) if len(tail_returns) > 0 else var_pct
        cvar_usd = cvar_pct * self.portfolio_value

        # Breaches
        actual_breaches = int(np.sum(portfolio_returns < -var_pct))
        expected_breaches = round((1 - self.confidence) * len(portfolio_returns), 1)

        return VaRResult(
            portfolio_id=portfolio_id,
            method="historical_simulation",
            confidence_level=self.confidence,
            time_horizon_days=h,
            calculation_date=calculation_date or "",
            var_usd=round(abs(var_usd), 2),
            cvar_usd=round(abs(cvar_usd), 2),
            portfolio_value_usd=self.portfolio_value,
            var_pct=round(abs(var_pct) * 100, 4),
            breaches_last_year=actual_breaches,
            expected_breaches=expected_breaches,
        )

    def compute_volatility(
        self,
        returns: np.ndarray,
        annualize: bool = True,
        trading_days: int = 252,
    ) -> float:
        """Compute annualized volatility from returns.

        Args:
            returns: 1D array of daily returns.
            annualize: Whether to annualize.
            trading_days: Number of trading days per year.

        Returns:
            Volatility as a decimal (e.g., 0.25 for 25%).
        """
        returns = np.asarray(returns, dtype=np.float64)
        vol = float(np.std(returns, ddof=1))
        if annualize:
            vol *= math.sqrt(trading_days)
        return vol

    def compute_max_drawdown(self, prices: np.ndarray) -> float:
        """Compute maximum drawdown from a price series.

        Args:
            prices: 1D array of prices.

        Returns:
            Maximum drawdown as a positive decimal (e.g., 0.15 for 15%).
        """
        prices = np.asarray(prices, dtype=np.float64)
        peak = np.maximum.accumulate(prices)
        drawdown = (peak - prices) / peak
        return float(np.max(drawdown))
