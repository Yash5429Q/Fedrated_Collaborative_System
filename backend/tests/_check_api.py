"""Quick live API verifier — run from backend dir."""
import asyncio
import httpx

async def check():
    base = "http://localhost:8000"
    async with httpx.AsyncClient(base_url=base) as c:
        try:
            health_check = await c.get("/health", timeout=2)
        except Exception:
            print(f"[!] Unable to connect to {base}. Is the backend server running?")
            print("    Please start the server first: cd backend && uvicorn app.main:app --reload")
            return

        # /api/dashboard
        r = await c.get("/api/dashboard", timeout=10)
        d = r.json()
        print(f"=== /api/dashboard [{r.status_code}] ===")
        print(f"  global_model_accuracy : {d.get('global_model_accuracy')}")
        print(f"  f1_score              : {d.get('f1_score')}")
        print(f"  false_positive_rate   : {d.get('false_positive_rate')}")
        print(f"  total_rounds          : {d.get('total_rounds')}")
        print(f"  experiment_clients    : {d.get('experiment_clients')}")
        print(f"  threats_detected      : {d.get('threats_detected')}")
        print(f"  privacy_status        : {d.get('privacy_status')!r}")
        print(f"  experiment_id         : {d.get('experiment_id')!r}")
        print(f"  data_source           : {d.get('data_source')!r}")
        print(f"  training_rounds count : {len(d.get('training_rounds', []))}")
        print(f"  model_comparison count: {len(d.get('model_comparison', []))}")
        print(f"  org_activity count    : {len(d.get('org_activity', []))}")
        has_hardcoded_trend = "daily_threat_increase" in d
        print(f"  has daily_threat_increase (BAD): {has_hardcoded_trend}")
        if d.get("model_comparison"):
            acc = next((x for x in d["model_comparison"] if x.get("metric") == "Accuracy"), None)
            if acc:
                print(f"  Accuracy federated    : {acc.get('federated')}  local: {acc.get('local')}")

        # /api/threats
        r = await c.get("/api/threats", timeout=10)
        d = r.json()
        print(f"\n=== /api/threats [{r.status_code}] ===")
        s = d.get("summary", {})
        print(f"  total   : {s.get('total')}")
        print(f"  critical: {s.get('critical')}  high: {s.get('high')}  medium: {s.get('medium')}  low: {s.get('low')}")
        print(f"  blocked : {s.get('blocked')}  investigating: {s.get('investigating')}")
        print(f"  sev_sum : {(s.get('critical') or 0) + (s.get('high') or 0) + (s.get('medium') or 0) + (s.get('low') or 0)}")
        print(f"  timeline pts: {len(d.get('timeline', []))}")

        # /api/privacy
        r = await c.get("/api/privacy", timeout=10)
        d = r.json()
        print(f"\n=== /api/privacy [{r.status_code}] ===")
        s = d.get("summary", {})
        print(f"  raw_data_shared: {s.get('raw_data_shared')}")
        print(f"  experiment_id  : {d.get('experiment_id')!r}")
        orgs = d.get("org_update_statuses", [])
        for o in orgs:
            print(f"  org {o.get('org_id')!r} round={o.get('round')}")

        # /api/experiments/latest
        r = await c.get("/api/experiments/latest", timeout=10)
        d = r.json()
        print(f"\n=== /api/experiments/latest [{r.status_code}] ===")
        print(f"  experiment_id    : {d.get('experiment_id')!r}")
        print(f"  is_latest        : {d.get('is_latest')}")
        print(f"  number_of_rounds : {d.get('number_of_rounds')}")
        print(f"  number_of_clients: {d.get('number_of_clients')}")
        print(f"  total_samples    : {d.get('total_samples')}")
        print(f"  dirichlet_alpha  : {d.get('dirichlet_alpha')}")

asyncio.run(check())
