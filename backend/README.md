# CYBER-20 Backend Service

High-performance FastAPI service and Federated Learning execution engine for CYBER-20 Federated Collaborative Threat Detection.

---

## 1. Environment Setup

### Prerequisites
- Python 3.12+ (tested with Python 3.12.10)
- `pip` package manager

### Installation
```bash
# From the backend directory
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 2. Configuration & Environment Variables

Copy the template configuration file:
```bash
# Windows:
copy .env.example .env
# Linux/macOS:
cp .env.example .env
```

Key environment configuration variables in `.env`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `"CYBER-20 Federated Threat Detection"` | Service name |
| `ENVIRONMENT` | `"development"` | `development` / `production` |
| `DEBUG` | `true` | Enable debug logs & reload |
| `HOST` | `"0.0.0.0"` | Bind interface |
| `PORT` | `8000` | HTTP port |
| `DATABASE_URL` | `"sqlite+aiosqlite:///./cyber20.db"` | Async SQLAlchemy database URI |
| `CORS_ORIGINS` | `"http://localhost:5173,http://localhost:4173"` | Allowed frontend URLs |
| `LOG_LEVEL` | `"INFO"` | Logging verbosity |

> **Security Rule:** Never commit the active `.env` file to version control. Only keep `.env.example` with benign placeholder settings.

---

## 3. Database Initialisation & Auto-Seeding

- The backend uses async SQLAlchemy with SQLite for local development (`cyber20.db`).
- **No manual SQL migrations are required.** On application startup, `app.database.init_db()` automatically runs `Base.metadata.create_all` to create all tables if they do not exist.
- If the database is empty, `app.database.seed.seed_if_empty()` automatically populates default organizations (`org-alpha`, `org-beta`, `org-gamma`), baseline validation test cases, and historical training rounds.

---

## 4. Running the Backend Server

Start the API server with live reloading:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API Base URL: `http://127.0.0.1:8000`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- Health check endpoint: `http://127.0.0.1:8000/health`

### REST API Endpoints Overview
- `GET /api/dashboard` — Aggregated metrics, active threat counts, and current model status
- `GET /api/training` — Federated training rounds and organization participation
- `GET /api/performance` — Model performance charts, confusion matrices, and IID vs Non-IID benchmarks
- `GET /api/threats` — Detected threat incident feed, filtering, and timeline
- `GET /api/organizations` — Participating organizations and their local model states
- `GET /api/privacy` — Privacy event logs, gradient clipping stats, and telemetry
- `GET /api/tests` — Automated validation test suite status
- `POST /api/predict` — Real-time inference on 68-dimensional network flow vectors
- `GET /api/experiments/latest` — Full metadata and metrics for the latest model checkpoint

---

## 5. Federated Learning Workflows

### A. Standalone Simulation (`run_experiment.py`)
Runs an end-to-end multi-round Federated Learning experiment across organizations in a single process, evaluating both IID and Non-IID Dirichlet skew:

```bash
python run_experiment.py --rounds 20 --alpha 0.5
```
- Fits normalization strictly on the training partition.
- Uses class-weighted Cross-Entropy loss for imbalanced classes (e.g. Malware).
- Saves checkpoint, normalization parameters, and metadata into `models/latest/`.
- Records benchmark metrics to `experiment_results.json` and updates SQLite database tables.

### B. Distributed Flower Orchestration (`run_fl.py`)
Launches the full Flower federated learning pipeline:
```bash
python run_fl.py --rounds 5 --clients 3
```
Or start server and client nodes independently:
```bash
# Server:
python server.py --rounds 5 --min-clients 3

# Clients:
python client.py --partition 0
python client.py --partition 1
python client.py --partition 2
```

---

## 6. Dataset & Checkpoint Artifacts

- **Clean Dataset:** `backend/app/ml/cicids2017_clean.npz` (2.41 MB). Contains 42,002 preprocessed network flow samples across 5 classes with 68 tabular features.
- **Production Checkpoint:** `backend/models/latest/`
  - `global_model.pt` — PyTorch ThreatNet state dictionary (245 KB)
  - `normalization.npz` — Training-set mean and standard deviation vectors
  - `metadata.json` — Architecture hyperparameters, feature ordering, and benchmark accuracy

---

## 7. Testing & Verification

### Pytest Suite
Run the 199 unit and repository integration tests:
```bash
pytest tests -v
```

### Live API Smoke Tests
With the backend server running on port 8000, verify all endpoints:
```bash
# Quick check:
python tests/_check_api.py

# Complete verification:
python tests/_full_verify.py
```
Both verification scripts include graceful error handling if the server is offline.
