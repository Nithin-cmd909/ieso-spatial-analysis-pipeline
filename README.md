# Spatiotemporal Analysis of Ontario IESO Nodal Electricity Pricing

### A Spatial Autoregressive & Rolling Walk-Forward Machine Learning Pipeline Across 1,000+ Grid Nodes

---

## Executive Summary & Core Results

Wholesale electricity markets present severe non-stationarity, extreme price spikes, and spatial transmission constraints. Using high-frequency data from the Independent Electricity System Operator (IESO) in Ontario, this project implements a spatiotemporal classification pipeline to model Real-Time (RT) versus Day-Ahead (DA) price divergence across over 1,000 settlement nodes.

Rather than treating nodes as independent time series, the architecture models cross-sectional network diffusion via spatial econometrics and evaluates out-of-sample performance through a strictly causal rolling walk-forward framework.

### Quantitative KPIs & Findings

- **Market Baseline & Efficiency:** The unconstrained walk-forward directional accuracy across all nodes settles at **54.14%** (AUC-ROC: **0.5416**). This empirical ceiling reflects the structural efficiency of Ontario's Market Renewal Program (MRP) single-schedule market design.
- **Selective Execution Edge:** Filtering predictions through a dynamic probability threshold ($\tau \ge 0.60$) concentrates precision on high-conviction transmission mispricings, lifting realized execution accuracy to **~58.2%** while retaining 68% market coverage.
- **Spatial Dominance:** The cross-sectional spatial lag feature ($W \cdot P_{t-1}$) accounted for **18.37%** of total model feature importance—ranking as the single most predictive market feature and outperforming direct localized historical price lags ($P_{t-1}$ at 3.12%).
- **Topological Bottlenecks:** Congestion rents concentrate along identified transmission corridors, where localized equipment outages interact with spatial demand shocks to drive nodal spread divergence.

---

## Econometric & Mathematical Architecture

### 1. Spatial Network Diffusion Specification

To capture the physical flow of power and transmission line losses without access to the proprietary real-time bus admittance matrix ($B$), we construct a row-standardized spatial weight matrix $W$ based on geographic inverse-distance metrics between nodes $i$ and $j$:

$$w_{ij} = \frac{d_{ij}^{-\alpha}}{\sum_{j \neq i} d_{ij}^{-\alpha}} \quad \text{for } i \neq j, \quad w_{ii} = 0$$

Where $d_{ij}$ represents the geodesic distance between grid connection points, and $\alpha \ge 1$ governs spatial attenuation. The first-order spatiotemporal lag feature for node $i$ at time $t$ is calculated as:

$$[W \cdot P_{t-1}]_i = \sum_{j=1}^{N} w_{ij} P_{j, t-1}$$

This isolates whether localized price divergence at node $i$ is driven by system-wide regional price diffusion or isolated nodal constraints.

### 2. Walk-Forward Classification Objective

Electricity spreads exhibit heavy-tailed distributions and structural regime shifts, rendering continuous mean-squared error minimization unstable. We frame nodal divergence as a binary directional spread classification:

$$y_{i,t} = \mathbb{I}(P^{\text{RT}}_{i,t} - P^{\text{DA}}_{i,t} > 0)$$

The model estimates the conditional class probability:

$$\hat{p}_{i,t} = \mathbb{P}(y_{i,t} = 1 \mid X_{i,t}, [W \cdot P_{t-1}]_i, \Omega_{t})$$

Where $X_{i,t}$ denotes local node attributes, and $\Omega_{t}$ contains systemic covariates (provincial demand delta, temperature, relative humidity, wind speed).

### 3. Execution Signal & Thresholding Engine

Instead of executing trades across all intervals, trades are placed only when the predicted class probability clears an asymmetric execution threshold:

$$\text{Signal}_{i,t} = \begin{cases} 1 \quad (\text{Long Spread}) & \text{if } \hat{p}_{i,t} \ge \tau_{\text{upper}} \\ 0 \quad (\text{No Trade}) & \text{if } \tau_{\text{lower}} < \hat{p}_{i,t} < \tau_{\text{upper}} \\ -1 \quad (\text{Short Spread}) & \text{if } \hat{p}_{i,t} \le \tau_{\text{lower}} \end{cases}$$

Setting $\tau_{\text{upper}} = 0.60$ and $\tau_{\text{lower}} = 0.40$ isolates structural tail divergence from market noise.

---

## Data Engineering & System Architecture

```text
├── .gitignore
├── dashboard.py               # Streamlit GIS dashboard with real-time probability filters
├── ieso_ingestion.py          # High-frequency XML/JSON parser for IESO RT/DA endpoints
├── weather_ingestion.py       # Automated ingestion pipeline for Environment Canada API
├── topology_mapper.py         # NLP fuzzy matcher mapping text outage logs to grid nodes
├── feature_engineering.py     # Matrix operations computing spatial lags and demand deltas
├── train_model.py             # 14-day rolling walk-forward XGBoost evaluation engine
├── ieso_nodal_data.db         # SQLite backend storing multi-year nodal panel (local only)
└── README.md
```

### Ingestion & Database Design
*   **Normalized Storage:** Python pipelines query IESO automated report endpoints and load raw 5-minute and hourly dispatch records into a structured SQLite database.
*   **NLP Topology Mapping:** Equipment outage logs are published as unstructured strings. `topology_mapper.py` uses Levenshtein distance metrics (`difflib`) to resolve station text descriptions to standardized IESO bus IDs.

### Rolling Walk-Forward Validation
Standard k-fold cross-validation introduces severe look-ahead bias in financial and power time-series. The evaluation pipeline enforces a strict 14-day expanding/rolling window:
1. Train on day $t - 14$ through $t - 1$.
2. Predict strictly out-of-sample on day $t$.
3. Shift the window forward by 24 hours and re-estimate parameters.

---

## Tech Stack

*   **Language:** Python 3.10+
*   **Database:** SQLite3
*   **Quantitative ML:** XGBoost, Scikit-Learn, SciPy
*   **Spatial & Vector Computing:** NumPy, Pandas
*   **Visualization & Deployment:** Streamlit, Plotly Express
