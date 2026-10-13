"""
Full website verification script.
Fetches all API endpoints and prints structured output for comparison.
"""
import asyncio, json
import httpx

BASE = "http://localhost:8000"

async def fetch(client, path, timeout=15, **params):
    try:
        r = await client.get(path, params=params, timeout=timeout)
        return r.status_code, r.json()
    except Exception as e:
        return 0, {"error": str(e)}

async def main():
    async with httpx.AsyncClient(base_url=BASE) as c:
        st, _ = await fetch(c, "/health", timeout=2)
        if st == 0:
            print(f"[!] Unable to connect to {BASE}. Is the backend server running?")
            print("    Please start the server first: cd backend && uvicorn app.main:app --reload")
            return

        # ── Dashboard ──────────────────────────────────────────────────────────
        st, d = await fetch(c, "/api/dashboard")
        print(f"\n{'='*60}")
        print(f"=== /api/dashboard [{st}] ===")
        if st == 200:
            print(f"  experiment_id         : {d.get('experiment_id')!r}")
            print(f"  data_source           : {d.get('data_source')!r}")
            print(f"  global_model_accuracy : {d.get('global_model_accuracy')}")
            print(f"  f1_score              : {d.get('f1_score')}")
            print(f"  false_positive_rate   : {d.get('false_positive_rate')}")
            print(f"  total_rounds          : {d.get('total_rounds')}")
            print(f"  experiment_clients    : {d.get('experiment_clients')}")
            print(f"  threats_detected      : {d.get('threats_detected')}")
            print(f"  privacy_status        : {d.get('privacy_status')!r}")
            print(f"  training_rounds       : {len(d.get('training_rounds', []))}")
            print(f"  model_comparison      : {len(d.get('model_comparison', []))}")
            mc = {x['metric']: x for x in d.get('model_comparison', [])}
            print(f"  mc Accuracy           : federated={mc.get('Accuracy',{}).get('federated')} local={mc.get('Accuracy',{}).get('local')}")
            print(f"  mc F1 Score           : federated={mc.get('F1 Score',{}).get('federated')} local={mc.get('F1 Score',{}).get('local')}")
            print(f"  mc FPR                : federated={mc.get('False Positive Rate',{}).get('federated')} local={mc.get('False Positive Rate',{}).get('local')}")
            trs = d.get('training_rounds', [])
            if trs:
                print(f"  training_rounds[0]    : round={trs[0].get('round')} acc={trs[0].get('accuracy')} f1={trs[0].get('f1')}")
                print(f"  training_rounds[-1]   : round={trs[-1].get('round')} acc={trs[-1].get('accuracy')} f1={trs[-1].get('f1')}")
        else:
            print(f"  RESPONSE: {d}")

        # ── Organizations ──────────────────────────────────────────────────────
        st, d = await fetch(c, "/api/organizations")
        print(f"\n{'='*60}")
        print(f"=== /api/organizations [{st}] ===")
        if st == 200:
            orgs = d.get('organizations', [])
            print(f"  total orgs: {len(orgs)}")
            for o in orgs:
                print(f"  org {o.get('id')!r}: name={o.get('name')!r} status={o.get('status')!r} "
                      f"dataset={o.get('dataset_size')} acc={o.get('local_model_accuracy')} "
                      f"round={o.get('current_round')} participation={o.get('participation_rate')}")
            summ = d.get('summary', {})
            print(f"  summary: total={summ.get('total')} active={summ.get('active')} training={summ.get('training')} idle={summ.get('idle')}")
        else:
            print(f"  RESPONSE: {d}")

        # ── Training ───────────────────────────────────────────────────────────
        st, d = await fetch(c, "/api/training")
        print(f"\n{'='*60}")
        print(f"=== /api/training [{st}] ===")
        if st == 200:
            rounds = d.get('rounds', [])
            print(f"  total rounds in response: {len(rounds)}")
            meta = d.get('metadata', {})
            print(f"  metadata: {json.dumps(meta, indent=4)}")
            parts = d.get('participation_by_round', [])
            print(f"  participation_by_round count: {len(parts)}")
            if parts:
                print(f"  participation[0]: {parts[0]}")
                print(f"  participation[-1]: {parts[-1]}")
            if rounds:
                r0 = rounds[0]
                print(f"  rounds[0]: round={r0.get('round_number')} status={r0.get('status')} acc={r0.get('accuracy')} f1={r0.get('f1')}")
                rl = rounds[-1]
                print(f"  rounds[-1]: round={rl.get('round_number')} status={rl.get('status')} acc={rl.get('accuracy')} f1={rl.get('f1')}")
        else:
            print(f"  RESPONSE: {d}")

        # ── Performance ────────────────────────────────────────────────────────
        st, d = await fetch(c, "/api/performance")
        print(f"\n{'='*60}")
        print(f"=== /api/performance [{st}] ===")
        if st == 200:
            print(f"  experiment_id: {d.get('experiment_id')!r}")
            print(f"  keys: {list(d.keys())}")
            # round_metrics
            rm = d.get('round_metrics', [])
            print(f"  round_metrics count: {len(rm)}")
            if rm:
                print(f"  round_metrics[-1]: {rm[-1]}")
            # org_metrics
            om = d.get('org_metrics', [])
            print(f"  org_metrics count: {len(om)}")
            for o in om:
                print(f"  org {o.get('org_id')!r}: acc={o.get('accuracy')} f1={o.get('f1')}")
            # model comparison / confusion matrix
            for key in ['model_comparison', 'confusion_matrix', 'iid_comparison', 'class_metrics']:
                val = d.get(key)
                if val is not None:
                    if isinstance(val, (int, float, str, bool)):
                        desc = repr(val)
                    elif hasattr(val, '__len__'):
                        desc = f'({type(val).__name__}, len={len(val)})'
                    else:
                        desc = type(val).__name__
                    print(f'  {key}: {desc}')
        else:
            print(f"  RESPONSE: {d}")

        # ── Privacy ────────────────────────────────────────────────────────────
        st, d = await fetch(c, "/api/privacy")
        print(f"\n{'='*60}")
        print(f"=== /api/privacy [{st}] ===")
        if st == 200:
            print(f"  experiment_id: {d.get('experiment_id')!r}")
            s = d.get('summary', {})
            print(f"  summary keys: {list(s.keys())}")
            for k, v in s.items():
                print(f"    {k}: {v!r}")
            orgs = d.get('org_update_statuses', [])
            print(f"  org_update_statuses count: {len(orgs)}")
            for o in orgs:
                print(f"  org {o.get('org_id')!r}: round={o.get('round')} status={o.get('status')!r}")
            evts = d.get('security_events', [])
            print(f"  security_events count: {len(evts)}")
            if evts:
                print(f"  events[0]: {evts[0]}")
        else:
            print(f"  RESPONSE: {d}")

        # ── Threats ────────────────────────────────────────────────────────────
        st, d = await fetch(c, "/api/threats")
        print(f"\n{'='*60}")
        print(f"=== /api/threats [{st}] ===")
        if st == 200:
            s = d.get('summary', {})
            print(f"  total={s.get('total')} blocked={s.get('blocked')} investigating={s.get('investigating')}")
            print(f"  critical={s.get('critical')} high={s.get('high')} medium={s.get('medium')} low={s.get('low')}")
            tl = d.get('timeline', [])
            print(f"  timeline count: {len(tl)}")
            if tl:
                print(f"  timeline[0]: {tl[0]}")
            threats = d.get('threats', [])
            print(f"  threats list count: {len(threats)}")
            if threats:
                print(f"  threats[0] id={threats[0].get('id')!r} type={threats[0].get('threat_type')!r} sev={threats[0].get('severity')!r}")
        else:
            print(f"  RESPONSE: {d}")

        # Threats with filter
        st, d = await fetch(c, "/api/threats", severity="critical")
        print(f"  /api/threats?severity=critical -> total={d.get('summary',{}).get('total')} count={len(d.get('threats',[]))}")

        # ── Testing ────────────────────────────────────────────────────────────
        st, d = await fetch(c, "/api/tests")
        print(f"\n{'='*60}")
        print(f"=== /api/tests [{st}] ===")
        if st == 200:
            s = d.get('summary', {})
            print(f"  summary: {json.dumps(s)}")
            tests = d.get('tests', [])
            print(f"  tests count: {len(tests)}")
            statuses = {}
            exec_states = {}
            for t in tests:
                statuses[t.get('status')] = statuses.get(t.get('status'), 0) + 1
                exec_states[t.get('execution_state')] = exec_states.get(t.get('execution_state'), 0) + 1
            print(f"  status breakdown: {statuses}")
            print(f"  execution_state breakdown: {exec_states}")
        else:
            print(f"  RESPONSE: {d}")

        # ── Experiments ────────────────────────────────────────────────────────
        st, d = await fetch(c, "/api/experiments/latest")
        print(f"\n{'='*60}")
        print(f"=== /api/experiments/latest [{st}] ===")
        if st == 200:
            for k, v in d.items():
                print(f"  {k}: {v!r}")
        else:
            print(f"  RESPONSE: {d}")

        # ── Predict (GET — model info) ─────────────────────────────────────────
        st, d = await fetch(c, "/api/predict")
        print(f"\n{'='*60}")
        print(f"=== /api/predict (GET) [{st}] ===")
        if st == 200:
            print(f"  keys: {list(d.keys())}")
            for k, v in d.items():
                print(f"  {k}: {v!r}")
        else:
            print(f"  RESPONSE: {d}")

        print(f"\n{'='*60}")
        print("=== DONE ===")

asyncio.run(main())
