# ⚠️ Databricks Commodity Risk Engine

**Delta Lake + MLflow + Feature Store + Model Serving for Commodity Risk Analytics**

<p align="center">
  <img src="https://img.shields.io/badge/Databricks-Free%20Edition-orange" alt="Databricks Edition">
  <img src="https://img.shields.io/badge/Risk-VaR%20%2B%20Margin-red" alt="Risk Engine">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Python-3.11+-yellow" alt="Python">
</p>

---

## 📋 Overview

The **Commodity Risk Engine** is a comprehensive risk analytics platform for commodity trading built on Databricks Community Edition. It implements Value-at-Risk (VaR) computation, margin impact analysis, and real-time risk monitoring for critical metals and energy commodities.

This project processes commodity price data (Ni, Co, Li, MHP, Cu, Fe) through a medallion pipeline to produce actionable risk metrics, margin impact assessments, and ML-powered price predictions.

### Key Capabilities

- **Medallion Architecture**: Bronze (raw prices) → Silver (cleaned) → Gold (risk metrics)
- **Value-at-Risk (VaR)**: Parametric & Historical Simulation methods
- **Margin Impact Engine**: Contract-level margin analysis for Ni, Co, Li, MHP
- **FX Risk**: Multi-currency exposure tracking
- **MLflow Tracking**: Margin prediction model experiments
- **SQL Analytics**: Dashboard queries for risk monitoring

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATABRICKS WORKSPACE                          │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   BRONZE      │    │   SILVER     │    │    GOLD      │       │
│  │   (Raw)       │───▶│   (Cleaned)  │───▶│ (Risk Metrics│       │
│  │               │    │              │    │              │       │
│  │ • Prices      │    │ • Validated  │    │ • VaR        │       │
│  │ • Contracts   │    │ • Normalized │    │ • Margin     │       │
│  │ • FX Rates    │    │ • Returns    │    │ • Exposure   │       │
│  └──────────────┘    └──────────────┘    └──────┬───────┘       │
│                                                   │               │
│                                                   ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   MLFLOW     │    │   SQL DASH   │    │   MODEL      │       │
│  │   TRACKING   │◀───│   QUERIES    │───▶│   SERVING    │       │
│  │              │    │              │    │              │       │
│  │ • VaR Models │    │ • Risk Heat  │    │ • Margin     │       │
│  │ • Margin Pred│    │ • VaR Breach │    │   Predictions│       │
│  │ • FX Exposure│    │ • P&L Dist   │    │ • Anomalies  │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    RISK ENGINE (Python)                   │   │
│  │  VaR Calculator │ Margin Engine │ FX Hedging │ Alerts    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    UNITY CATALOG                           │   │
│  │  workspace.risk_bronze │ workspace.risk_silver │ ...      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Pipeline

```
Raw Prices ──▶ Bronze ──▶ Silver ──▶ Gold ──▶ ML ──▶ Serving ──▶ Reporting
     │                          │           │
     ▼                          ▼           ▼
  FX Rates               Returns Calc    VaR / Margin
  Contracts              Volatility     MLflow Models
```

### Medallion Layers

| Layer | Schema | Purpose | Operations |
|-------|--------|---------|------------|
| **Bronze** | `workspace.risk_bronze` | Raw market data ingestion | Append prices, contracts, FX |
| **Silver** | `workspace.risk_silver` | Cleaned & enriched data | Validate, compute returns, normalize |
| **Gold** | `workspace.risk_gold` | Risk metrics | VaR, margin impact, exposure summaries |

---

## ⚡ Databricks Features Used

| Feature | Implementation | Status |
|---------|---------------|--------|
| **Unity Catalog** | 11 schemas under `workspace` catalog | ✅ Configured |
| **Managed Delta Tables** | Bronze, Silver, Gold risk layers | ✅ Active |
| **Medallion Architecture** | 3-tier risk pipeline | ✅ Implemented |
| **MLflow Tracking** | Margin & VaR experiments | ✅ Configured |
| **SQL Warehouses** | Risk dashboard queries | ✅ Available |
| **Lakeview Dashboards** | Risk KPI dashboards | ✅ Ready |
| **Notebook Workflows** | Sequential risk pipeline | ✅ Linked |
| **DBSQL** | Ad-hoc risk analytics | ✅ Enabled |
| **Job Scheduler** | Automated risk runs | ✅ Available |

---

## 🛠️ Workspace Setup

The Databricks workspace was configured via the **Workspace API**:

### Unity Catalog Schemas

```python
schemas = [
    "mining_bronze", "mining_silver", "mining_gold",
    "risk_bronze", "risk_silver", "risk_gold",
    "ml_experiments", "ml_models",
    "dashboards", "reporting", "staging"
]

for schema in schemas:
    requests.post(
        f"{BASE}/api/2.1/unity-catalog/schemas",
        headers=HEADERS,
        json={"name": schema, "catalog_name": "workspace"}
    )
```

### Notebook Uploads

```python
for nb_name in notebooks:
    requests.post(
        f"{BASE}/api/2.0/workspace/import",
        headers=HEADERS,
        json={
            "path": f"/Shared/Commodity_Risk/{nb_name}",
            "content": base64_encoded_content,
            "language": "PYTHON",
            "format": "SOURCE",
            "overwrite": True
        }
    )
```

---

## 📓 Notebook Guide

| # | Notebook | Description | Key Operations |
|---|----------|-------------|----------------|
| 00 | `00_setup.py` | Environment setup & risk schema init | Initialize Spark, create risk schemas |
| 01 | `01_bronze_ingest.py` | Raw commodity data ingestion | Create Delta tables: prices, contracts, FX |
| 02 | `02_silver_transform.py` | Data cleaning & return computation | Validate, compute log returns, volatility |
| 03 | `03_gold_risk_metrics.py` | VaR & margin impact computation | Parametric VaR, historical simulation |
| 04 | `04_mlflow_training.py` | ML margin prediction | Train gradient boosting margin predictor |
| 05 | `05_dashboard_sql.py` | Risk dashboard SQL queries | Top risks, VaR breach, P&L queries |

### Notebook Workflow

```
00_setup ──▶ 01_bronze_ingest ──▶ 02_silver_transform
                                     │
                                     ▼
                        03_gold_risk_metrics ──▶ 04_mlflow_training
                                     │
                                     ▼
                          05_dashboard_sql
```

---

## 📊 Sample Data

### Commodity Prices (Ni, Co, Li, MHP, Cu, Fe)

| Commodity | Unit | Price Range | Data Points |
|-----------|------|-------------|-------------|
| Nickel (Ni) | USD/t | $15,000 - $22,000 | Daily |
| Cobalt (Co) | USD/t | $28,000 - $45,000 | Daily |
| Lithium (Li) | USD/t | $70,000 - $130,000 | Daily |
| MHP | USD/t | $30,000 - $50,000 | Daily |
| Copper (Cu) | USD/t | $8,000 - $11,000 | Daily |
| Iron Ore (Fe) | USD/t | $100 - $160 | Daily |

### Contracts (10 records)
- Physical and derivative contracts
- Notional values, contract dates, commodity exposure
- Counterparty information

### FX Rates (9 records)
- USD/AUD, USD/CAD, USD/CNY, USD/EUR, USD/JPY, USD/GBP, USD/ZAR, USD/CHF, USD/BRL
- Bid/ask spreads, daily rates

---

## 🚀 Quick Start

### Prerequisites
- Databricks Community Edition account (free)
- Python 3.11+ with Databricks Connect (optional)

### Step 1: Clone & Upload

```bash
git clone https://github.com/Cubiczan/databricks-commodity-risk-engine.git
cd databricks-commodity-risk-engine
```

### Step 2: Upload to Databricks

```bash
pip install databricks-cli
databricks configure --token

for nb in notebooks/*.py; do
    databricks workspace import "$nb" "/Shared/Commodity_Risk/$(basename $nb)" --language PYTHON --format SOURCE
done
```

### Step 3: Run the Pipeline

1. Open notebook `00_setup.py` in Databricks
2. Run sequentially: `00` → `01` → `02` → `03` → `04` → `05`
3. Each notebook creates/updates Delta tables in Unity Catalog

### Step 4: Risk Dashboard

1. Navigate to **Dashboards** → **Create Dashboard**
2. Use SQL queries from `05_dashboard_sql.py`
3. Add VaR breach alerts, margin impact charts, P&L heatmaps

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Platform** | Databricks Community Edition |
| **Compute** | Serverless / Shared clusters |
| **Catalog** | Unity Catalog (workspace) |
| **Storage** | Delta Lake (managed tables) |
| **ML Tracking** | MLflow |
| **Language** | Python / PySpark / SQL |
| **Risk Engine** | NumPy / SciPy (VaR computation) |
| **Visualization** | Lakeview Dashboards |

### Python Package (src/risk_engine/)

```python
from src.risk_engine.va_calculator import VaRCalculator
from src.risk_engine.margin_engine import MarginEngine

# Value-at-Risk
var_calc = VaRCalculator(confidence=0.99)
var_result = var_calc.historical_simulation(returns, portfolio_weights)

# Margin Impact
margin_engine = MarginEngine()
impact = margin_engine.compute_contract_margin(contract, current_prices, fx_rates)
```

### Dependencies

```toml
[project]
name = "databricks-commodity-risk-engine"
requires-python = ">=3.11"
dependencies = [
    "databricks-sdk",
    "mlflow",
    "pandas",
    "pydantic>=2.0",
    "numpy",
    "scipy",
]
```

---

## 📁 Project Structure

```
databricks-commodity-risk-engine/
├── README.md
├── pyproject.toml
├── .gitignore
├── notebooks/
│   ├── 00_setup.py
│   ├── 01_bronze_ingest.py
│   ├── 02_silver_transform.py
│   ├── 03_gold_risk_metrics.py
│   ├── 04_mlflow_training.py
│   └── 05_dashboard_sql.py
├── src/
│   └── risk_engine/
│       ├── __init__.py
│       ├── config.py
│       ├── models.py
│       ├── va_calculator.py
│       ├── margin_engine.py
│       └── sql_queries.py
└── data/
    ├── sample_commodity_prices.csv
    ├── sample_contracts.csv
    └── sample_fx_rates.csv
```

---

## 🌐 Workspace

**Databricks Workspace**: [https://REDACTED_DATABRICKS_WORKSPACE](https://REDACTED_DATABRICKS_WORKSPACE)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 👤 Author

**Shyam Desigan**
- Email: sam@cubiczan.com
- GitHub: [Cubiczan](https://github.com/Cubiczan)
- Specialization: Commodity Risk, Quantitative Analytics, Cloud Architecture
