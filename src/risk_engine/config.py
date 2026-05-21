"""Configuration for the Commodity Risk Engine."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    """Central configuration for the Commodity Risk pipeline."""

    # Unity Catalog
    catalog: str = "workspace"
    bronze_schema: str = "risk_bronze"
    silver_schema: str = "risk_silver"
    gold_schema: str = "risk_gold"
    ml_schema: str = "ml_experiments"

    # Bronze tables
    bronze_prices_table: str = "commodity_prices"
    bronze_contracts_table: str = "contracts"
    bronze_fx_table: str = "fx_rates"

    # Silver tables
    silver_prices_table: str = "prices_cleaned"
    silver_contracts_table: str = "contracts_cleaned"
    silver_returns_table: str = "price_returns"

    # Gold tables
    gold_var_table: str = "var_results"
    gold_margin_table: str = "margin_impacts"
    gold_exposure_table: str = "exposure_summary"

    # Workspace
    workspace_url: str = "https://REDACTED_DATABRICKS_WORKSPACE"
    workspace_id: str = "REDACTED_DATABRICKS_WORKSPACE_ID"

    # VaR parameters
    var_confidence: float = 0.99
    var_window_days: int = 252
    var_historical_window: int = 500

    # Margin parameters
    margin_buffer_pct: float = 0.10
    margin_call_threshold_pct: float = 0.05

    # MLflow
    mlflow_experiment_name: str = "/risk/margin_prediction"
    mlflow_tracking_uri: str = "databricks"

    # Pipeline
    bronze_checkpoint: str = "/tmp/checkpoints/risk_bronze"
    silver_checkpoint: str = "/tmp/checkpoints/risk_silver"
    gold_checkpoint: str = "/tmp/checkpoints/risk_gold"

    @property
    def bronze_prices_fqn(self) -> str:
        return f"{self.catalog}.{self.bronze_schema}.{self.bronze_prices_table}"

    @property
    def bronze_contracts_fqn(self) -> str:
        return f"{self.catalog}.{self.bronze_schema}.{self.bronze_contracts_table}"

    @property
    def bronze_fx_fqn(self) -> str:
        return f"{self.catalog}.{self.bronze_schema}.{self.bronze_fx_table}"

    @property
    def silver_prices_fqn(self) -> str:
        return f"{self.catalog}.{self.silver_schema}.{self.silver_prices_table}"

    @property
    def silver_returns_fqn(self) -> str:
        return f"{self.catalog}.{self.silver_schema}.{self.silver_returns_table}"

    @property
    def gold_var_fqn(self) -> str:
        return f"{self.catalog}.{self.gold_schema}.{self.gold_var_table}"

    @property
    def gold_margin_fqn(self) -> str:
        return f"{self.catalog}.{self.gold_schema}.{self.gold_margin_table}"


# Default configuration instance
config = RiskConfig()
