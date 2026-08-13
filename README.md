# 🪙 Real-Time Cryptocurrency Trading Signal Pipeline
> **A Modular, Secure, and Observed MLOps Architecture**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![Prometheus](https://img.shields.io/badge/Prometheus-Monitoring-E6522C?logo=prometheus)
![Grafana](https://img.shields.io/badge/Grafana-Visualization-F46800?logo=grafana)

---

##  Overview

This project presents an end-to-end MLOps and Data Engineering system designed to ingest, process, predict, and monitor cryptocurrency market movements in real time. 

The application captures live market feeds from **Binance WebSockets**, stores unstructured streaming windows in **MongoDB** and structured historical data in **PostgreSQL**, executes real-time Machine Learning inferences using a **Random Forest Classifier**, and serves analytical endpoints via a containerized **FastAPI** backend secured with **JWT Authentication & Role-Based Access Control (RBAC)**.

Complete operational system health, throughput, and latency are monitored using **Prometheus** metrics scraping and dynamic **Grafana** dashboards.

---

##  System Architecture

```
                       +-----------------------------------+
                       |    Binance WebSocket Stream       |
                       +-----------------------------------+
                                         |
                                         v
+------------------+         +-----------------------+         +--------------------+
|  PostgreSQL DB   | <------ |  streaming_pipeline   | ------> |     MongoDB DB     |
| (Historical/KPIs)|         |  (50-Candle Warm-up)  |         |  (Sliding Buffer)  |
+------------------+         +-----------------------+         +--------------------+
                                         |                               |
                                         +---------------+---------------+
                                                         |
                                                         v
                                              +---------------------+
                                              |    FastAPI Engine   |
                                              |  (Inference + RBAC) |
                                              +---------------------+
                                                         |
                   +-------------------------------------+-------------------------------------+
                   |                                     |                                     |
                   v                                     v                                     v
        +--------------------+                +--------------------+                +--------------------+
        |    Streamlit UI    |                | Prometheus Server  |                | Grafana Dashboard  |
        | (Live UI / Stats)  |                |  (Scrapes /metrics)|                |  (Port 3000 Viz)   |
        +--------------------+                +--------------------+                +--------------------+
```

---

##  Key Features

1. **Polyglot Persistence:**
   * **PostgreSQL:** Handles historical 1-minute candlestick data, aggregations, and analytical queries.
   * **MongoDB:** Serves as a high-throughput sliding window buffer for low-latency live streaming predictions.
2. **Cold-Start Resilience:**
   * Automated **50-candle warm-up strategy** executed upon streaming service startup via Binance REST API to prevent cold-start inference delays.
3. **ML Inference & Risk Management:**
   * Machine Learning pipeline trained on technical indicators (RSI_14, EMA_9, EMA_21, VWAP).
   * Decision confidence thresholding (tau >= 0.65) to minimize false positives and downgrade uncertain signals to `SELL/HOLD`.
4. **Enterprise Security (RBAC & JWT):**
   * Role-based authorization matrix protecting sensitive endpoints across 3 tiers: `admin`, `trader`, and `viewer`.
5. **Full MLOps Observability:**
   * Automated API instrumentation with `prometheus_fastapi_instrumentator`.
   * Public `/metrics` scraping by Prometheus every 5 seconds.
   * Pre-configured Grafana visualization boards monitoring request rates, error codes, and sub-50ms inference latencies.

---

##  Tech Stack

| Domain | Technologies |
| :--- | :--- |
| **Languages & Core** | Python 3.10+, Pandas, Scikit-Learn |
| **Backend & API** | FastAPI, Uvicorn, Pydantic, PyJWT |
| **Databases** | PostgreSQL, MongoDB |
| **Frontend** | Streamlit |
| **Containerization** | Docker, Docker Compose |
| **Observability** | Prometheus, Grafana |
| **CI/CD & Quality** | GitHub Actions, Pytest, Flake8 |

---

##  API Access Control (RBAC)

Authentication is handled via OAuth2 Password Bearer JSON Web Tokens (`/token`).

| Endpoint | Method | Allowed Roles | Description |
| :--- | :---: | :--- | :--- |
| `/health` | `GET` | *Public* | System sanity check |
| `/stats` | `GET` | *Public / Viewer* | Historical market analytics & KPIs |
| `/latest-prediction` | `GET` | *Public* | Frontend Streamlit prediction sync |
| `/predict` | `POST` | `trader`, `admin` | Executes ML inference on live candle vectors |
| `/admin/retrain` | `POST` | `admin` | Triggers background model retraining |
| `/metrics` | `GET` | *Public / Prometheus* | System observability metrics exposition |

---

## Quick Start & Deployment

### Prerequisites
* Docker Desktop installed and running.
* Git installed.

### 1. Clone the Repository
```bash
git clone [https://github.com/DianeTuma/apr26_bde_opa_group_a.git](https://github.com/DianeTuma/apr26_bde_opa_group_a.git)
cd crypto_bot_projet
```

### 2. Launch the Microservices Ecosystem
Run all containers in detached mode using Docker Compose:
```bash
docker compose up --build -d
```

### 3. Verify Service Availability

Once all containers are healthy, access the individual services:

* **Streamlit User Interface:** `http://localhost:8501`
* **FastAPI Swagger Documentation:** `http://localhost:8000/docs`
* **Prometheus Metrics Stream:** `http://localhost:8000/metrics`
* **Prometheus Server UI:** `http://localhost:9090`
* **Grafana Observability Dashboard:** `http://localhost:3000` *(Default login: admin / admin)*

---

## Prometheus & Grafana Configuration

1. **Prometheus Scraping:**
   The `prometheus.yml` configuration targets the FastAPI container (`api:8000/metrics`) on a 15-second interval:
   ```yaml
   scrape_configs:
     - job_name: "crypto-fastapi-service"
       scrape_interval: 15s
       metrics_path: "/metrics"
       static_configs:
         - targets: ["api:8000"]
   ```

2. **Grafana Data Source:**
   Grafana connects automatically to Prometheus via the container network URL:
   `http://prometheus:9090`

3. **Key PromQL Queries for Exploration:**
   * **Total Requests (HTTP 200 OK):**
     `http_requests_total{status="2xx"}`
   * **Prediction Endpoint Latency (95th Percentile):**
     `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{handler="/predict"}[5m])) by (le))`

---

## Running Automated Tests

Run unit and integration tests inside the API container context using `pytest`:

```bash
docker compose exec api pytest
```

---

##  License

Distributed under the MIT License. See `LICENSE` for more information.