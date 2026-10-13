# CYBER-20 Frontend Dashboard

Modern, responsive web interface for the CYBER-20 Federated Collaborative Threat Detection system, built with React 19, TypeScript, Vite, TailwindCSS, and Recharts.

---

## 1. Getting Started

### Prerequisites
- Node.js 18.x or newer (tested with Node 20 / 22)
- npm 9+

### Installation
From the `frontend/` directory, perform a clean install:
```bash
npm ci
# Or if package-lock needs updating:
# npm install
```

---

## 2. Available Scripts

| Command | Purpose |
| :--- | :--- |
| `npm run dev` | Starts Vite local development server with Hot Module Replacement (HMR) at `http://localhost:5173` |
| `npm run build` | Runs TypeScript typechecker (`tsc -b`) and produces optimized production bundle in `dist/` |
| `npm run lint` | Fast codebase linting using Oxlint |
| `npm run preview` | Locally serves the production build from `dist/` |

---

## 3. Backend Proxy Configuration

The development server is pre-configured via `vite.config.ts` to forward all `/api` requests directly to the local FastAPI backend:

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- When making calls to `/api/dashboard`, the browser requests `http://localhost:5173/api/dashboard` and Vite transparently proxies it to `http://127.0.0.1:8000/api/dashboard`.
- Ensure the FastAPI backend is running on port 8000 before starting the frontend.

---

## 4. Dashboard Pages & Key Functions

| Route | Page | Purpose & Capabilities |
| :--- | :--- | :--- |
| `/` | **Dashboard** | High-level threat intelligence summary, global accuracy, active threats count, federated training round timeline, and model comparison. |
| `/training` | **Training** | Real-time monitoring of federated learning rounds, client upload updates, training duration, and loss convergence. |
| `/performance` | **Performance** | In-depth model evaluation: confusion matrix, precision/recall per class, ROC curves, and IID vs Non-IID performance comparison. |
| `/threats` | **Threats** | Incident response console: real-time stream of classified attacks (DoS, Brute Force, Port Scan, Malware) with severity filters and status toggles. |
| `/organizations` | **Organizations** | Participant telemetry for Organization Alpha, Organization Beta, and Organization Gamma — showing dataset size, local model accuracy, and participation history. |
| `/privacy` | **Privacy** | Privacy monitoring dashboard: gradient clipping threshold tracking, noise multiplier logs, and security audit events. |
| `/testing` | **Testing** | System test runner and validation test registry showing execution status of core platform capabilities. |
| `/predict` | **Predict** | Live inference playground allowing operators to input flow features (packet lengths, flow duration, flags) and receive instant threat classification with confidence scores. |

---

## 5. Production Deployment

To generate a standalone production bundle:
```bash
npm run build
```
The optimized static assets will be output to `frontend/dist/`. These files can be hosted on Nginx, Cloudflare Pages, AWS S3, or any standard static file host, configured to proxy `/api` requests to the production backend.
