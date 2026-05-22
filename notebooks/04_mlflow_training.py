# Databricks notebook source
# MLflow - Margin Prediction (Serverless Compatible)
import mlflow
import mlflow.sklearn
from pyspark.sql.functions import *
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

CATALOG = "workspace"
mlflow.set_tracking_uri("databricks")
mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment("/Shared/Commodity_Risk_Engine/experiments/margin_prediction_v1")

df = spark.read.table(f"{CATALOG}.risk_silver.contracts").toPandas()
print(f"Loaded {len(df)} contracts")

X = df[["quantity_mt", "contract_price"]]
y = df["margin_pct"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

try:
    with mlflow.start_run(run_name="sklearn_lr_v1"):
        lr = LinearRegression()
        lr.fit(X_train, y_train)
        y_pred = lr.predict(X_test)

        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        mlflow.log_param("model_type", "LinearRegression")
        mlflow.log_param("features", "quantity_mt,contract_price")
        mlflow.log_metric("rmse", float(rmse))
        mlflow.log_metric("r2", float(r2))
        mlflow.sklearn.log_model(lr, "model")
        print(f"RMSE: {rmse:.4f}, R2: {r2:.4f}")
except Exception as e:
    print(f"MLflow error: {e}")

print("MLflow training complete")
