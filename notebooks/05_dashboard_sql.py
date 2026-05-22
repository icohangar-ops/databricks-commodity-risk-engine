# Databricks notebook source
# Dashboard Queries for Risk Analytics (Serverless Compatible)
from pyspark.sql.functions import *
CATALOG = "workspace"
print("Dashboard SQL - Risk Analytics")

try:
    print("--- Top Contracts by Risk ---")
    df = spark.read.table(f"{CATALOG}.risk_gold.contract_risk")
    df.select("contract_id", "commodity", "notional_usd", "worst_case_usd", "risk_level").orderBy(desc("worst_case_usd")).show(truncate=False)
except Exception as e:
    print(f"Error reading contract_risk: {e}")

try:
    print("--- VaR by Commodity ---")
    df2 = spark.read.table(f"{CATALOG}.risk_gold.value_at_risk")
    df2.select("commodity_upper", "avg_price", "var_95_pct", "cvar_99_pct").orderBy(desc("var_95_pct")).show(truncate=False)
except Exception as e:
    print(f"Error reading value_at_risk: {e}")

try:
    print("--- Portfolio Summary ---")
    df3 = spark.read.table(f"{CATALOG}.risk_silver.contracts")
    df3.groupBy("commodity").agg(
        count("*").alias("contracts"),
        sum("notional_usd").alias("total"),
        avg("margin_pct").alias("avg_margin")
    ).orderBy(desc("total")).show(truncate=False)
except Exception as e:
    print(f"Error reading contracts: {e}")

print("Dashboard queries complete")
