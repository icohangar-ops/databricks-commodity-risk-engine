# Databricks notebook source
# Bronze Layer - Commodity Price Ingestion
from pyspark.sql.types import *
from pyspark.sql.functions import *
CATALOG = "workspace"
ps = StructType([StructField("date",StringType(),False),StructField("commodity",StringType(),False),StructField("price_usd",DoubleType(),False),StructField("unit",StringType(),False),StructField("source",StringType(),False)])
data = [("2025-01-15","Nickel",15850.0,"USD/tonne","LME"),("2025-01-16","Nickel",16200.0,"USD/tonne","LME"),("2025-01-17","Nickel",15900.0,"USD/tonne","LME"),("2025-01-15","Cobalt",28500.0,"USD/tonne","LME"),("2025-01-16","Cobalt",28200.0,"USD/tonne","LME"),("2025-01-17","Cobalt",27800.0,"USD/tonne","LME"),("2025-01-15","Lithium Carbonate",7500.0,"USD/tonne","Asian Metal"),("2025-01-16","Lithium Carbonate",7420.0,"USD/tonne","Asian Metal"),("2025-01-17","Lithium Carbonate",7350.0,"USD/tonne","Asian Metal"),("2025-01-15","MHP",420.0,"USD/tonne","Custom"),("2025-01-16","MHP",415.0,"USD/tonne","Custom"),("2025-01-17","MHP",425.0,"USD/tonne","Custom"),("2025-01-15","Copper",9250.0,"USD/tonne","LME"),("2025-01-16","Copper",9380.0,"USD/tonne","LME"),("2025-01-17","Copper",9180.0,"USD/tonne","LME"),("2025-01-15","Iron Ore",105.5,"USD/tonne","SGX"),("2025-01-16","Iron Ore",108.2,"USD/tonne","SGX"),("2025-01-17","Iron Ore",103.8,"USD/tonne","SGX")]
df = spark.createDataFrame(data, ps).withColumn("ingestion_ts",current_timestamp())
df.writeTo(f"{CATALOG}.risk_bronze.commodity_prices").using("delta").createOrReplace()
print(f"commodity_prices: {df.count()} rows")

fxs = StructType([StructField("date",StringType(),False),StructField("currency",StringType(),False),StructField("rate_to_usd",DoubleType(),False)])
fxd = [("2025-01-15","AUD",0.645),("2025-01-16","AUD",0.648),("2025-01-17","AUD",0.642),("2025-01-15","BRL",0.195),("2025-01-16","BRL",0.197),("2025-01-17","BRL",0.193),("2025-01-15","EUR",1.085),("2025-01-16","EUR",1.088),("2025-01-17","EUR",1.082)]
dfx = spark.createDataFrame(fxd, fxs).withColumn("ingestion_ts",current_timestamp())
dfx.writeTo(f"{CATALOG}.risk_bronze.fx_rates").using("delta").createOrReplace()
print(f"fx_rates: {dfx.count()} rows")

cs = StructType([StructField("contract_id",StringType(),False),StructField("commodity",StringType(),False),StructField("quantity_mt",DoubleType(),False),StructField("contract_price",DoubleType(),False),StructField("margin_pct",DoubleType(),False),StructField("customer",StringType(),False),StructField("start_date",StringType(),False)])
cd = [("CTR001","Nickel",500.0,15850.0,8.5,"Toyota","2025-01-15"),("CTR002","Cobalt",100.0,28500.0,6.2,"Samsung SDI","2025-01-15"),("CTR003","Lithium Carbonate",200.0,7500.0,5.8,"CATL","2025-01-15"),("CTR004","MHP",1000.0,420.0,7.5,"Posco","2025-01-15"),("CTR005","Copper",1000.0,9250.0,4.2,"GM","2025-01-15"),("CTR006","Iron Ore",50000.0,105.5,3.8,"ArcelorMittal","2025-01-15"),("CTR007","Nickel",300.0,15850.0,7.8,"LG Energy","2025-01-15"),("CTR008","Cobalt",50.0,28500.0,8.0,"BYD","2025-01-15"),("CTR009","Copper",2000.0,9250.0,5.5,"Tesla","2025-01-15"),("CTR010","Nickel",800.0,15850.0,6.0,"Panasonic","2025-01-15")]
dfc = spark.createDataFrame(cd, cs).withColumn("ingestion_ts",current_timestamp())
dfc.writeTo(f"{CATALOG}.risk_bronze.contracts").using("delta").createOrReplace()
print(f"contracts: {dfc.count()} rows")
print("Bronze layer complete")
