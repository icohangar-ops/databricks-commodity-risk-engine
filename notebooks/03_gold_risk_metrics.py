# Databricks notebook source
# Gold Layer - VaR, Margin Impact
from pyspark.sql.functions import *
from pyspark.sql.window import Window
CATALOG = "workspace"
df_p = spark.read.table(f"{CATALOG}.risk_silver.commodity_prices")
w = Window.partitionBy("commodity_upper").orderBy("price_date")
df_vol = df_p.withColumn("prev_price",lag("price").over(w)).withColumn("daily_return",(col("price")-col("prev_price"))/col("prev_price")).withColumn("volatility_3d",stddev("daily_return").over(w.rowsBetween(-3,0))).withColumn("volatility_pct",round(col("volatility_3d")*100,4))
df_vol.writeTo(f"{CATALOG}.risk_gold.price_volatility").using("delta").createOrReplace()
print("price_volatility: created")

df_var = df_vol.groupBy("commodity_upper").agg(avg("price").alias("avg_price"),avg("volatility_pct").alias("avg_vol_pct")).withColumn("var_95_pct",round(col("avg_price")*1.65*col("avg_vol_pct")/100,2)).withColumn("cvar_99_pct",round(col("avg_price")*2.33*col("avg_vol_pct")/100,2))
df_var.writeTo(f"{CATALOG}.risk_gold.value_at_risk").using("delta").createOrReplace()
print("value_at_risk:")
df_var.select("commodity_upper","avg_price","var_95_pct").show(truncate=False)

df_c = spark.read.table(f"{CATALOG}.risk_silver.contracts")
df_impact = df_c.join(df_var.select(col("commodity_upper").alias("commodity"),col("var_95_pct").alias("pv95")),"commodity").withColumn("worst_case_usd",round(col("quantity_mt")*col("pv95"),2)).withColumn("risk_level",when(col("worst_case_usd")>1000000,"High").when(col("worst_case_usd")>100000,"Medium").otherwise("Low"))
df_impact.writeTo(f"{CATALOG}.risk_gold.contract_risk").using("delta").createOrReplace()
print("contract_risk:")
df_impact.select("contract_id","commodity","notional_usd","worst_case_usd","risk_level").orderBy(desc("worst_case_usd")).show(truncate=False)
print("Gold layer complete")
