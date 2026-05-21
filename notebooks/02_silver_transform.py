# Databricks notebook source
# Silver Layer - Clean, Normalize
from pyspark.sql.functions import *
from pyspark.sql.window import Window
CATALOG = "workspace"
df_p = spark.read.table(f"{CATALOG}.risk_bronze.commodity_prices")
w = Window.partitionBy("date","commodity")
df_ps = df_p.withColumn("rn",row_number().over(w.orderBy("ingestion_ts"))).filter(col("rn")==1).drop("rn").withColumn("price_date",to_date(col("date"))).withColumn("commodity_upper",upper(col("commodity"))).withColumn("quality_score",lit(0.95)).withColumn("silver_ts",current_timestamp()).drop("ingestion_ts","date","source").withColumnRenamed("price_usd","price")
df_ps.writeTo(f"{CATALOG}.risk_silver.commodity_prices").using("delta").createOrReplace()
print(f"commodity_prices: {df_ps.count()} rows")

df_fx = spark.read.table(f"{CATALOG}.risk_bronze.fx_rates").dropDuplicates(["date","currency"]).withColumn("quality_score",lit(0.98)).withColumn("silver_ts",current_timestamp()).drop("ingestion_ts")
df_fx.writeTo(f"{CATALOG}.risk_silver.fx_rates").using("delta").createOrReplace()
print(f"fx_rates: {df_fx.count()} rows")

df_c = spark.read.table(f"{CATALOG}.risk_bronze.contracts").dropDuplicates(["contract_id"]).withColumn("notional_usd",round(col("quantity_mt")*col("contract_price"),2)).withColumn("margin_usd",round(col("notional_usd")*col("margin_pct")/100,2)).withColumn("quality_score",lit(0.95)).withColumn("silver_ts",current_timestamp()).drop("ingestion_ts")
df_c.writeTo(f"{CATALOG}.risk_silver.contracts").using("delta").createOrReplace()
print(f"contracts: {df_c.count()} rows")
print("Silver layer complete")
