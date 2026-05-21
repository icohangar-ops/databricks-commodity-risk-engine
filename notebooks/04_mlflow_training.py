# Databricks notebook source
# MLflow - Margin Prediction
import mlflow
from pyspark.sql.functions import *
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression
from pyspark.ml.evaluation import RegressionEvaluator
CATALOG = "workspace"
mlflow.set_experiment("/Commodity_Risk/margin_prediction_v1")
df = spark.read.table(f"{CATALOG}.risk_silver.contracts").withColumn("label",col("margin_pct"))
va = VectorAssembler(inputCols=["quantity_mt","contract_price","margin_pct"],outputCol="features")
df_ml = va.transform(df).select("features","label")
train, test = df_ml.randomSplit([0.8, 0.2], seed=42)
with mlflow.start_run(run_name="lr_v1"):
    lr = LinearRegression(featuresCol="features", labelCol="label")
    model = lr.fit(train)
    preds = model.transform(test)
    rmse = RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="rmse").evaluate(preds)
    r2 = RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="r2").evaluate(preds)
    mlflow.log_metric("rmse", round(rmse, 4))
    mlflow.log_metric("r2", round(r2, 4))
    print(f"RMSE: {rmse:.4f}, R2: {r2:.4f}")
print("MLflow training complete")
