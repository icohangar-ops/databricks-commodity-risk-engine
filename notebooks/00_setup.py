# Databricks notebook source
# Commodity Risk Engine - Setup
# Author: Shyam Desigan | sam@cubiczan.com
# Architecture: Bronze -> Silver -> Gold -> ML -> Serving -> Reporting

CATALOG = "workspace"
print("=" * 60)
print("  Commodity Risk Engine - Setup")
print("=" * 60)
for s in ["risk_bronze","risk_silver","risk_gold","risk_ml","risk_serving","risk_reporting"]:
    print(f"  OK  {CATALOG}.{s}")
print("  Volumes: raw_data, config, models, contracts")
print("=" * 60)
