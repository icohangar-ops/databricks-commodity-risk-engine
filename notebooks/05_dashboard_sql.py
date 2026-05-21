# Databricks notebook source
# SQL Dashboard - Risk Analytics
from pyspark.sql.functions import *
CATALOG = "workspace"
print("--- Top Contracts by Risk ---")
spark.sql(f"SELECT contract_id,commodity,notional_usd,worst_case_usd,risk_level FROM {CATALOG}.risk_gold.contract_risk ORDER BY worst_case_usd DESC").show(truncate=False)
print("--- VaR by Commodity ---")
spark.sql(f"SELECT commodity_upper,avg_price,var_95_pct,cvar_99_pct FROM {CATALOG}.risk_gold.value_at_risk ORDER BY var_95_pct DESC").show(truncate=False)
print("--- Portfolio Summary ---")
spark.sql(f"SELECT commodity,COUNT(*) as contracts,SUM(notional_usd) as total,AVG(margin_pct) as avg_margin FROM {CATALOG}.risk_silver.contracts GROUP BY commodity ORDER BY total DESC").show(truncate=False)
print("Dashboard queries ready")
