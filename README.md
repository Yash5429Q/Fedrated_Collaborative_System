# CYBER-20: Federated Collaborative Threat Detection

[![Python 3.12](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4+-EE4C2C.svg)](https://pytorch.org/)
[![Flower](https://img.shields.io/badge/Flower-1.13-orange.svg)](https://flower.ai/)
[![React 19](https://img.shields.io/badge/React-19.2-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6.svg)](https://www.typescriptlang.org/)

An enterprise-grade federated learning platform designed for privacy-preserving collaborative cyber threat detection across distributed organizations. CYBER-20 enables institutions (banks, healthcare providers, critical infrastructure) to train shared anomaly detection models without exchanging raw network traffic or sensitive proprietary logs.

---

## Architecture Overview

```
                               ┌─────────────────────────────────┐
                               │       Central Aggregator        │
                               │  (Flower Server / FedAvg ML)    │
                               └──────────────┬──────────────────┘
                                              │ Global Weights (w_t)
                   ┌──────────────────────────┼──────────────────────────┐
                   ▼                          ▼                          ▼
         ┌───────────────────┐      ┌───────────────────┐      ┌───────────────────┐
         │   Org Alpha       │      │    Org Beta       │      │   Org Gamma       │
         │  (Enterprise A)   │      │ (Critical Infra)  │      │  (Financial Hub)  │
         │ Local Data (X_A)  │      │ Local Data (X_B)  │      │ Local Data (X_C)  │
         │ Gradient Clipping │      │ Gradient Clipping │      │ Gradient Clipping │
         └─────────┬─────────┘      └─────────┬─────────┘      └─────────┬─────────┘
                   │ Δw_A                     │ Δw_B                     │ Δw_C
                   └──────────────────────────┼──────────────────────────┘
                                              ▼
                               ┌─────────────────────────────────┐
                               │     FastAPI Backend Engine      │
                               │  - REST API & SQLite / Postgre  │
                               │  - Model Checkpoint Registry    │
                               │  - Real-time Threat Inference   │
                               └──────────────┬──────────────────┘
                                              │ HTTP / JSON
                                              ▼
                               ┌─────────────────────────────────┐
                               │   CYBER-20 React Dashboard      │
                               │  - Model Performance & ROC/AUC  │
                               │  - Threat Event Feed & Map      │
                               │  - Org Participation Telemetry  │
                               └─────────────────────────────────┘
```

---

## Key Features

- **Federated Training Orchestration:** Distributed FedAvg model training powered by Flower (`flwr`) and standalone multi-process simulation modes.
- **ThreatNet Deep Learning Architecture:** Deep neural network with Batch Normalization and Dropout tuned specifically for tabular network flow intrusion detection.
- **Non-IID Data Simulation:** Dirichlet distribution ($\alpha = 0.5$) simulation modeling real-world data skew across participating organizations.
- **Privacy Protections:** Client-side gradient norm clipping and perturbation noise to mitigate raw feature reconstruction from model weight updates.
- **Automated Inference & Telemetry:** Real-time 5-class network traffic classification (Normal, DoS, Brute Force, Port Scan, Malware) served via FastAPI.
- **Comprehensive Management UI:** Interactive React 19 dashboard displaying training rounds, confusion matrices, threat incidents, and organization health.

---

## Model Benchmark & Evaluation

The repository ships with the production checkpoint (`backend/models/latest/`) generated from experiment **`exp_20261013_042208_6fb2147a`**:

| Metric | Score | Evaluation Protocol |
| :--- | :--- | :--- |
| **Global Test Accuracy** | **78.94%** | Held-out stratified test set (never seen during training) |
| **Macro F1-Score** | **73.84%** | Unweighted average across all 5 classes |
| **Weighted F1-Score** | **78.65%** | Accounted for class distribution frequencies |
| **Evaluation Loss** | **0.7583** | Cross-entropy loss on held-out split |
| **Federated Clients** | 3 Organizations | Org Alpha, Org Beta, Org Gamma |
| **Rounds Completed** | 20 Rounds | Best global checkpoint selected at Round 14 |
| **Data Partitioning** | IID & Non-IID | Dirichlet $\alpha = 0.5$ skew comparison |

### Network Flow Class Mapping
- `0`: **Normal** (Benign baseline traffic)
- `1`: **DoS** (Denial of Service / DDoS)
- `2`: **Brute Force** (SSH / FTP / RDP credential stuffing)
- `3`: **Port Scan** (Reconnaissance scanning)
- `4`: **Malware** (Botnets / C2 communication)

---

## Repository Structure

```
Federated Collaborative Threat Detection/
├── backend/                        # FastAPI server & Federated Learning pipeline
│   ├── app/
│   │   ├── api/v1/                 # Endpoints (dashboard, training, threats, predict, etc.)
│   │   ├── core/                   # App configuration & logging
│   │   ├── database/               # SQLAlchemy engine, session & auto-seeder
│   │   ├── ml/                     # PyTorch ThreatNet model, data partitioner, privacy logic
│   │   │   └── cicids2017_clean.npz# Cleaned benchmark dataset (42,002 samples, 68 features)
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   ├── repositories/           # Database access layer
│   │   ├── schemas/                # Pydantic v2 validation models
│   │   └── services/               # Aggregation & business logic
│   ├── models/
│   │   └── latest/                 # Production model checkpoint, normalization & metadata
│   │       ├── global_model.pt     # PyTorch checkpoint (245 KB)
│   │       ├── normalization.npz   # Training-split z-score mean/std parameters
│   │       └── metadata.json       # Experiment hyperparameters & architecture definition
│   ├── tests/                      # Pytest test suite (199 test cases)
│   ├── client.py                   # Flower federated client node
│   ├── server.py                   # Flower federated aggregator server
│   ├── run_fl.py                   # Orchestration launcher (spawns server + 3 clients)
│   ├── run_experiment.py           # Standalone multi-round simulation & benchmark runner
│   ├── requirements.txt            # Python dependencies
│   └── .env.example                # Environment configuration template
│
├── frontend/                       # React 19 + TypeScript dashboard
│   ├── src/
│   │   ├── components/             # Reusable UI widgets & layout wrappers
│   │   ├── pages/                  # Dashboard, Training, Performance, Threats, Privacy, etc.
│   │   ├── services/               # API clients interfacing with backend
│   │   └── types/                  # TypeScript interface definitions
│   ├── package.json                # Frontend package dependencies
│   └── vite.config.ts              # Vite bundler configuration & backend API proxy
│
├── column_report.json              # CIC-IDS2017 68-feature column extraction report
├── dataset_report.json             # CIC-IDS2017 raw class distributions
├── db_schema.json                  # SQLite / PostgreSQL table definitions
├── db_dump.json                    # Benchmark metrics & reference seed data
└── .gitignore                      # Git exclusion rules
```

---

## Quick Start Guide

### Prerequisites
- **Python:** 3.12 or newer
- **Node.js:** 18.x or newer (npm 9+)

---

### 1. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file from template
copy .env.example .env    # On Windows CMD
# or: cp .env.example .env # On Bash / PowerShell

# Start backend server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

> **Note:** On first startup, the application automatically initializes the SQLite database (`cyber20.db`) and seeds baseline telemetry data via `app.database.init_db()`. No manual SQL migrations are required for local development.

Verify backend health:
```bash
curl http://127.0.0.1:8000/health
# Response: {"status":"healthy"}
```

API Documentation (Swagger UI) is available at: `http://127.0.0.1:8000/docs`

---

### 2. Frontend Setup

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies cleanly
npm ci

# Start the Vite development server
npm run dev
```

Open your browser at `http://localhost:5173`. Vite is preconfigured with an API reverse proxy forwarding `/api` calls directly to `http://127.0.0.1:8000`.

---

## Running Federated Learning Experiments

### Option A: Standalone Simulation (Recommended for Benchmarks)
Simulates FedAvg training rounds across organizations in a single process without needing gRPC ports:

```bash
cd backend
python run_experiment.py --rounds 20 --alpha 0.5
```
This updates `backend/experiment_results.json` and records round metrics into the database for the Performance dashboard.

### Option B: Distributed Flower Orchestration
Starts a Flower aggregation server and launches 3 client processes communicating via Flower RPC:

```bash
cd backend
python run_fl.py --rounds 5 --clients 3
```
Or start server and clients individually:
```bash
# Terminal 1 (Server):
python server.py --rounds 5 --min-clients 3

# Terminal 2, 3, 4 (Clients):
python client.py --partition 0
python client.py --partition 1
python client.py --partition 2
```

---

## Dataset Instructions

### Immediate Reproduction (Default)
The repository includes `backend/app/ml/cicids2017_clean.npz` (2.41 MB). This preprocessed array contains **42,002 network flow instances** (which resolve to **37,183 unique instances** upon runtime deduplication) with 68 features across all 5 classes. You do **not** need to download the raw dataset to run training, evaluation, tests, or live inference.

### Raw CIC-IDS2017 Dataset (Optional)
If you wish to re-extract the full raw PCAP-based CSV dataset from the Canadian Institute for Cybersecurity:
1. Clone the public dataset repository:
   ```bash
   git clone https://huggingface.co/datasets/muzom/CIC-IDS2017 data/CIC-IDS2017
   ```
2. The raw files (~843 MB total across 8 CSVs) are automatically ignored by `.gitignore` to prevent repository bloat.

---

## Testing

### Backend Unit & Integration Tests
Execute the full Pytest test suite:
```bash
cd backend
pytest tests -v
```
**Results:** 199 passed test cases covering API contracts, data partitioning, model inference, privacy noise, and repository queries.

### Live API Verification
With the backend server running, execute the verification utility:
```bash
cd backend
python tests/_full_verify.py
```

### Frontend Typecheck & Build
```bash
cd frontend
npm run build
npm run lint
```

---

## Known Limitations & Security Disclaimers

1. **No Live Packet Sniffing:** CYBER-20 performs inference on pre-extracted 68-dimensional statistical network flow features (packet lengths, flow duration, IAT, flag counts). It does not perform inline promiscuous packet capture (PCAP) from hardware network interfaces.
2. **Secure Aggregation (SecAgg) & mTLS:** The current federated pipeline implements FedAvg with gradient clipping and perturbation noise. Cryptographic Multi-Party Computation (MPC) Secure Aggregation (where the aggregator cannot observe individual client update vectors) and mutual TLS (mTLS) authentication between Flower clients and server are not implemented and represent architectural future work.
3. **Differential Privacy Guarantee:** While client-side gradient clipping and additive Gaussian noise mechanisms are implemented, the reported epsilon values do not constitute a formally verified mathematical (ε, δ)-Differential Privacy guarantee because a validated cumulative accountant (e.g. Moments Accountant / RDP) and its underlying subsampling assumptions have not been verified.
4. **Local Database:** The SQLite database is intended for local evaluation and demonstration. For production deployment, configure `DATABASE_URL` in `.env` to point to a high-availability PostgreSQL cluster.
