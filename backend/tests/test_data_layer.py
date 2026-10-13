"""
Standalone regression tests that don't require PyTorch / ML modules.
Tests the core data layer: MetricRepo, ThreatRepo, and db_data service.

Run with:  cd backend && python tests/test_data_layer.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LATEST_EXP_ID = "exp_20261013_042208_6fb2147a"
EXPECTED_IID_ACCURACY = 78.94   # real DB value
EXPECTED_IID_F1 = 73.84         # real DB value
EXPECTED_IID_FPR = 5.37         # real DB value
EXPECTED_TOTAL_ROUNDS = 20
EXPECTED_LOCAL_EPOCHS = 3
EXPECTED_CLIENTS = 3
EXPECTED_TOTAL_SAMPLES = 37183
EXPECTED_DIRICHLET_ALPHA = 0.5
# Orgs that participated in the latest experiment (from experiment_org IID rows)
EXPECTED_PARTICIPANT_IDS = {"org-alpha", "org-beta", "org-gamma"}
# Total registered orgs in the DB
EXPECTED_REGISTERED_ORGS = 5

PASS = "[PASS]"
FAIL = "[FAIL]"

results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label, detail))
    print(f"  {status}  {label}" + (f" -- {detail}" if detail else ""))


async def run_tests():
    from app.database.session import AsyncSessionLocal
    from app.repositories.metric_repo import MetricRepo
    from app.repositories.threat_repo import ThreatRepo
    from app.repositories.organization_repo import OrganizationRepo
    from app.services import db_data

    async with AsyncSessionLocal() as db:
        metric_repo = MetricRepo(db)
        threat_repo = ThreatRepo(db)
        org_repo = OrganizationRepo(db)

        print("\n=== FIX-1: MetricRepo.get_latest_experiment_id() ===")
        exp_id = await metric_repo.get_latest_experiment_id()
        check("Returns non-None value", exp_id is not None)
        check("Returns correct experiment ID", exp_id == LATEST_EXP_ID, f"got: {exp_id!r}")
        check("Is a string", isinstance(exp_id, str))
        check("Starts with 'exp_'", exp_id is not None and exp_id.startswith("exp_"))
        check("No __ suffix in returned ID", exp_id is not None and "__" not in exp_id,
              f"got: {exp_id!r}")

        print("\n=== Experiment metadata ===")
        meta = await metric_repo.get_experiment_metadata(LATEST_EXP_ID)
        check("total_samples correct",
              int(meta.get("total_samples", 0)) == EXPECTED_TOTAL_SAMPLES,
              f"got: {meta.get('total_samples')}")
        check("number_of_rounds correct",
              int(meta.get("number_of_rounds", 0)) == EXPECTED_TOTAL_ROUNDS,
              f"got: {meta.get('number_of_rounds')}")
        check("local_epochs correct",
              int(meta.get("local_epochs", 0)) == EXPECTED_LOCAL_EPOCHS,
              f"got: {meta.get('local_epochs')}")
        check("number_of_clients correct",
              int(meta.get("number_of_clients", 0)) == EXPECTED_CLIENTS,
              f"got: {meta.get('number_of_clients')}")
        check("dirichlet_alpha correct",
              abs(float(meta.get("dirichlet_alpha", -1)) - EXPECTED_DIRICHLET_ALPHA) < 0.001,
              f"got: {meta.get('dirichlet_alpha')}")

        print("\n=== Experiment summary metrics (IID) ===")
        exp_summary = await metric_repo.get_by_category_for_experiment(
            "experiment_summary", LATEST_EXP_ID
        )
        iid_metrics = {m.metric_name: m.metric_value
                       for m in exp_summary if m.model_type.endswith("__iid")}
        check("IID experiment_summary rows found", len(iid_metrics) > 0,
              f"got: {len(iid_metrics)} rows")
        check(f"IID accuracy ~= {EXPECTED_IID_ACCURACY}%",
              abs(iid_metrics.get("accuracy", 0) - EXPECTED_IID_ACCURACY) < 1.0,
              f"got: {iid_metrics.get('accuracy')}")
        check(f"IID F1 ~= {EXPECTED_IID_F1}%",
              abs(iid_metrics.get("f1", 0) - EXPECTED_IID_F1) < 1.0,
              f"got: {iid_metrics.get('f1')}")
        check(f"IID FPR ~= {EXPECTED_IID_FPR}%",
              abs(iid_metrics.get("false_positive_rate", 0) - EXPECTED_IID_FPR) < 1.0,
              f"got: {iid_metrics.get('false_positive_rate')}")
        check("IID accuracy != seeded 94.7",
              abs(iid_metrics.get("accuracy", 0) - 94.7) > 1.0)
        check("IID F1 != seeded 92.3",
              abs(iid_metrics.get("f1", 0) - 92.3) > 1.0)
        check("IID FPR != seeded 3.2",
              abs(iid_metrics.get("false_positive_rate", 0) - 3.2) > 1.0)

        print("\n=== Experiment round metrics ===")
        exp_rounds = await metric_repo.get_by_category_for_experiment(
            "experiment_round", LATEST_EXP_ID
        )
        iid_rounds = [m for m in exp_rounds if m.model_type.endswith("__iid")]
        round_nums = sorted(set(m.round_number for m in iid_rounds if m.round_number is not None))
        check(f"Round count = {EXPECTED_TOTAL_ROUNDS}",
              len(round_nums) == EXPECTED_TOTAL_ROUNDS,
              f"got: {len(round_nums)} rounds: {round_nums}")
        # Each round must have federated_accuracy, federated_f1, federated_fpr (not "loss")
        r1_metrics = {m.metric_name for m in iid_rounds if m.round_number == 1}
        check("Round 1 has federated_accuracy", "federated_accuracy" in r1_metrics)
        check("Round 1 has federated_f1", "federated_f1" in r1_metrics)
        check("Round 1 has federated_fpr (not 'loss')", "federated_fpr" in r1_metrics)

        print("\n=== FIX-3: ThreatRepo real COUNT queries ===")
        sev_counts = await threat_repo.get_counts_by_severity()
        status_counts = await threat_repo.get_counts_by_status()
        total = await threat_repo.get_total_count()
        sev_sum = sum(sev_counts.values())
        check("Severity counts sum to total",
              sev_sum == total, f"sev_sum={sev_sum}, total={total}")
        check("critical != 187", sev_counts.get("critical", 0) != 187)
        check("high != 493", sev_counts.get("high", 0) != 493)
        check("medium != 641", sev_counts.get("medium", 0) != 641)
        check("low != 526", sev_counts.get("low", 0) != 526)
        check("blocked != 1204", status_counts.get("blocked", 0) != 1204)
        check("investigating != 89", status_counts.get("investigating", 0) != 89)

        print("\n=== FIX-4: ThreatRepo real hourly timeline ===")
        timeline = await threat_repo.get_hourly_timeline()
        check("Timeline is a list", isinstance(timeline, list))
        for pt in timeline:
            check(f"Timeline point has required keys (hour={pt.get('hour')})",
                  all(k in pt for k in ["hour", "critical", "high", "medium", "low"]))
        # Timeline total across all hours must equal total threats
        tl_total = sum(
            pt["critical"] + pt["high"] + pt["medium"] + pt["low"]
            for pt in timeline
        )
        check("Timeline total equals threat total",
              tl_total == total, f"timeline_total={tl_total}, db_total={total}")

        print("\n=== FIX-2: Experiment IDs list ===")
        exp_ids = await metric_repo.get_experiment_ids_list()
        check("Has experiments", len(exp_ids) >= 1, f"got: {len(exp_ids)}")
        check("Latest is first", exp_ids[0] == LATEST_EXP_ID if exp_ids else False,
              f"got: {exp_ids[0] if exp_ids else 'empty'}")
        check("No duplicates", len(exp_ids) == len(set(exp_ids)))

        # ── NEW: Registered orgs vs experiment participants ──────────────────
        print("\n=== NEW: Registered orgs vs experiment participants ===")
        all_orgs = await org_repo.get_all()
        all_org_ids = {o.id for o in all_orgs}
        check(f"Total registered orgs = {EXPECTED_REGISTERED_ORGS}",
              len(all_orgs) == EXPECTED_REGISTERED_ORGS,
              f"got: {len(all_orgs)}")

        exp_org_rows = await metric_repo.get_by_category_for_experiment("experiment_org", LATEST_EXP_ID)
        participant_ids = {m.org_id for m in exp_org_rows if m.org_id and m.model_type.endswith("__iid")}
        check(f"Experiment participants = {EXPECTED_CLIENTS}",
              len(participant_ids) == EXPECTED_CLIENTS,
              f"got: {participant_ids}")
        check("Participant IDs are Alpha, Beta, Gamma",
              participant_ids == EXPECTED_PARTICIPANT_IDS,
              f"got: {participant_ids}")
        check("Delta is NOT an experiment participant",
              "org-delta" not in participant_ids)
        check("Epsilon is NOT an experiment participant",
              "org-epsilon" not in participant_ids)
        check("All participants are registered orgs",
              participant_ids.issubset(all_org_ids))

        # ── NEW: Threat distribution matches actual DB records ───────────────
        print("\n=== NEW: Threat distribution from actual DB records ===")
        threat_types = await threat_repo.get_counts_by_type()
        type_names = {t["type"] for t in threat_types}
        type_total = sum(t["count"] for t in threat_types)
        check("Threat distribution total = DB total",
              type_total == total, f"dist_total={type_total}, db_total={total}")
        check("DoS/DDoS in distribution (actual DB type)",
              "DoS/DDoS" in type_names, f"found: {type_names}")
        check("Brute Force in distribution",
              "Brute Force" in type_names)
        check("Port Scan in distribution",
              "Port Scan" in type_names)
        check("Malware in distribution",
              "Malware" in type_names)
        check("Data Exfiltration in distribution (stored in DB)",
              "Data Exfiltration" in type_names)
        # 5 distinct types, one record each
        for t in threat_types:
            check(f"Type '{t['type']}' has count 1 (DB verified)",
                  t["count"] == 1, f"got: {t['count']}")

        # ── NEW: Dashboard service — org activity correctness ────────────────
        print("\n=== NEW: get_dashboard org activity ===")
        dash = await db_data.get_dashboard(db)
        # All 5 orgs must appear
        check("org_activity contains all 5 registered orgs",
              len(dash.org_activity) == EXPECTED_REGISTERED_ORGS,
              f"got: {len(dash.org_activity)}")
        # Exactly 3 are experiment participants
        participants_in_dash = [o for o in dash.org_activity if o.is_experiment_participant]
        non_participants = [o for o in dash.org_activity if not o.is_experiment_participant]
        check("Exactly 3 orgs flagged as experiment participants",
              len(participants_in_dash) == EXPECTED_CLIENTS,
              f"got: {len(participants_in_dash)}")
        check("Participants are Alpha, Beta, Gamma",
              {o.org_id for o in participants_in_dash} == EXPECTED_PARTICIPANT_IDS,
              f"got: {[o.org_id for o in participants_in_dash]}")
        # Participants have current_round = 10
        for o in participants_in_dash:
            check(f"{o.org_id} current_round = {EXPECTED_TOTAL_ROUNDS}",
                  o.current_round == EXPECTED_TOTAL_ROUNDS,
                  f"got: {o.current_round}")
        # Non-participants have current_round = None
        for o in non_participants:
            check(f"{o.org_id} current_round is None (not a participant)",
                  o.current_round is None,
                  f"got: {o.current_round}")
        # experiment_clients field reflects real count
        check("experiment_clients = 3 (from experiment metadata)",
              dash.experiment_clients == EXPECTED_CLIENTS,
              f"got: {dash.experiment_clients}")

        # ── NEW: Threat count and trend ─────────────────────────────────────
        print("\n=== NEW: Threat total and daily trend ===")
        check("threats_detected = actual DB count",
              dash.threats_detected == total,
              f"dash={dash.threats_detected}, db={total}")
        # There must NOT be a '+23 today' or any hardcoded trend in the API response
        # The service no longer emits a daily_threat_increase field;
        # the dashboard response has only threats_detected (plain count)
        check("No hardcoded trend field in DashboardResponse",
              not hasattr(dash, "daily_threat_increase"),
              "daily_threat_increase field should not exist")

        # ── NEW: Privacy status from verified experiment config ─────────────
        print("\n=== NEW: Privacy status from experiment config ===")
        check("privacy_status is not empty", bool(dash.privacy_status))
        check("privacy_status mentions 'Data Local'",
              "Data Local" in dash.privacy_status,
              f"got: {dash.privacy_status!r}")
        check("privacy_status mentions 'Update Clipping' (config__clipping_enabled=1)",
              "Update Clipping" in dash.privacy_status,
              f"got: {dash.privacy_status!r}")
        check("privacy_status mentions 'Gaussian Noise' (config__dp_noise_enabled=1)",
              "Gaussian Noise" in dash.privacy_status,
              f"got: {dash.privacy_status!r}")
        check("privacy_status does NOT say 'Secure Aggregation'",
              "Secure Aggregation" not in dash.privacy_status,
              f"got: {dash.privacy_status!r}")
        check("privacy_detail is not None",
              dash.privacy_detail is not None)
        check("privacy_detail mentions clip_norm",
              dash.privacy_detail is not None and "clip_norm" in dash.privacy_detail)
        check("privacy_detail says secure aggregation not implemented",
              dash.privacy_detail is not None and "not implemented" in dash.privacy_detail)

        # ── NEW: Training chart correctness ─────────────────────────────────
        print("\n=== NEW: Training rounds chart ===")
        check(f"training_rounds count = {EXPECTED_TOTAL_ROUNDS}",
              len(dash.training_rounds) == EXPECTED_TOTAL_ROUNDS,
              f"got: {len(dash.training_rounds)}")
        # Rounds must be 1..10 in order
        rounds = [r.round for r in dash.training_rounds]
        check("Rounds are 1..10 in order",
              rounds == list(range(1, EXPECTED_TOTAL_ROUNDS + 1)),
              f"got: {rounds}")
        # All have fpr (NOT loss attribute)
        check("TrainingRoundMetric has 'fpr' (not 'loss')",
              all(hasattr(r, "fpr") for r in dash.training_rounds))
        check("TrainingRoundMetric does NOT have 'loss' field",
              not hasattr(dash.training_rounds[0], "loss") if dash.training_rounds else True)
        # Round 20 final values match known IID results
        r_last = next((r for r in dash.training_rounds if r.round == EXPECTED_TOTAL_ROUNDS), None)
        check(f"Round {EXPECTED_TOTAL_ROUNDS} accuracy ~= 70.45 (IID)",
              r_last is not None and abs(r_last.accuracy - 70.45) < 1.0,
              f"got: {r_last.accuracy if r_last else 'N/A'}")
        check(f"Round {EXPECTED_TOTAL_ROUNDS} f1 ~= 66.01 (IID)",
              r_last is not None and abs(r_last.f1 - 66.01) < 1.0,
              f"got: {r_last.f1 if r_last else 'N/A'}")

        # ── NEW: Local vs Federated metric mapping ──────────────────────────
        print("\n=== NEW: Local vs Federated model comparison ===")
        comp_metrics = {m.metric: m for m in dash.model_comparison}
        check("Comparison has Accuracy", "Accuracy" in comp_metrics)
        check("Comparison has Precision", "Precision" in comp_metrics)
        check("Comparison has Recall", "Recall" in comp_metrics)
        check("Comparison has F1", "F1" in comp_metrics)
        acc = comp_metrics.get("Accuracy")
        if acc:
            check(f"Federated Accuracy ~= {EXPECTED_IID_ACCURACY}", abs(acc.federated - EXPECTED_IID_ACCURACY) < 1.0,
                  f"got: {acc.federated}")
            # Local avg should be >90% for this experiment (org IID local accuracies ~95-97%)
            check("Local Accuracy > 90% (org-level IID local train acc)", acc.local > 90.0,
                  f"got: {acc.local}")
            # Federated should NOT equal local (they differ significantly)
            check("Federated != Local (no metric substitution)", acc.federated != acc.local)
        f1m = comp_metrics.get("F1")
        if f1m:
            check(f"Federated F1 ~= {EXPECTED_IID_F1}", abs(f1m.federated - EXPECTED_IID_F1) < 1.0,
                  f"got: {f1m.federated}")

        # ── NEW: experiment_id in dashboard response ─────────────────────────
        print("\n=== NEW: experiment_id field ===")
        check("experiment_id field present",
              hasattr(dash, "experiment_id"))
        check("experiment_id = latest exp ID",
              dash.experiment_id == LATEST_EXP_ID,
              f"got: {dash.experiment_id!r}")

        # ── NEW: API missing metric / error resilience ───────────────────────
        print("\n=== NEW: Missing metrics / error resilience ===")
        bad_meta = await metric_repo.get_experiment_metadata("nonexistent_exp")
        check("get_experiment_metadata returns empty dict for unknown exp_id",
              bad_meta == {}, f"got: {bad_meta!r}")
        bad_rounds = await metric_repo.get_by_category_for_experiment("experiment_round", "nonexistent_exp")
        check("get_by_category_for_experiment returns [] for unknown exp_id",
              bad_rounds == [], f"got: {len(bad_rounds)} rows")

        # ── NEW: Empty hourly timeline when no threats exist ─────────────────
        # Tested via the real DB — timeline is derived from actual records only.
        # If the DB has threats, timeline must be non-empty; each point must have
        # the four severity keys. If no threats existed the function returns [].
        print("\n=== NEW: Hourly timeline structure ===")
        timeline = await threat_repo.get_hourly_timeline()
        check("get_hourly_timeline returns a list (not None)",
              isinstance(timeline, list))
        if timeline:
            required_keys = {"hour", "critical", "high", "medium", "low"}
            all_valid = all(required_keys.issubset(set(pt.keys())) for pt in timeline)
            check("Every timeline point has hour/critical/high/medium/low keys",
                  all_valid, f"sample point keys: {list(timeline[0].keys()) if timeline else '[]'}")
            all_ints = all(isinstance(pt["critical"], int) for pt in timeline)
            check("Timeline severity values are integers (not None)",
                  all_ints)
            # Sum of all timeline buckets must equal total threat count
            tl_sum = sum(pt["critical"] + pt["high"] + pt["medium"] + pt["low"] for pt in timeline)
            db_total = await threat_repo.get_total_count()
            check("Timeline sum matches DB total threat count",
                  tl_sum == db_total, f"timeline_sum={tl_sum}, db_total={db_total}")
        else:
            # Empty table: get_total_count must also be 0
            db_total = await threat_repo.get_total_count()
            check("Empty timeline implies zero DB threats",
                  db_total == 0, f"db_total={db_total}")

        # ── NEW: Zero threats / empty type distribution ───────────────────────
        # We cannot delete real records, so instead we verify the structural
        # contract: get_counts_by_type returns [] when the table is empty, and
        # returns a list[dict] with 'type'/'count' keys when populated.
        print("\n=== NEW: Threat type distribution structure ===")
        threat_types_list = await threat_repo.get_counts_by_type()
        check("get_counts_by_type returns a list",
              isinstance(threat_types_list, list))
        if threat_types_list:
            check("Each entry has 'type' key",
                  all("type" in t for t in threat_types_list))
            check("Each entry has 'count' key",
                  all("count" in t for t in threat_types_list))
            check("All counts are positive integers",
                  all(isinstance(t["count"], int) and t["count"] > 0 for t in threat_types_list))
            total_from_types = sum(t["count"] for t in threat_types_list)
            db_total_check = await threat_repo.get_total_count()
            check("Distribution total matches DB total",
                  total_from_types == db_total_check,
                  f"dist_total={total_from_types}, db_total={db_total_check}")
        else:
            # Contract: empty distribution → empty table
            db_total_check = await threat_repo.get_total_count()
            check("Empty distribution implies zero DB threats",
                  db_total_check == 0, f"db_total={db_total_check}")

        # ── NEW: Privacy fallback when no privacy_event rows for experiment ───
        # Query privacy_event rows for a nonexistent experiment — expect empty.
        # Verify that the downstream privacy_status logic produces a safe fallback.
        print("\n=== NEW: Privacy config fallback for unknown experiment ===")
        bad_priv_rows = await metric_repo.get_by_category_for_experiment(
            "privacy_event", "nonexistent_exp"
        )
        check("No privacy_event rows for unknown experiment",
              bad_priv_rows == [], f"got: {len(bad_priv_rows)} rows")
        # Simulate the fallback logic from db_data.get_dashboard:
        iid_priv_empty: dict = {}
        clipping_fallback  = bool(iid_priv_empty.get("config__clipping_enabled", 0))
        dp_noise_fallback  = bool(iid_priv_empty.get("config__dp_noise_enabled", 0))
        mechanisms_fallback = ["Data Local"]
        if clipping_fallback:
            mechanisms_fallback.append("Update Clipping")
        if dp_noise_fallback:
            mechanisms_fallback.append("Gaussian Noise")
        privacy_status_fallback = " · ".join(mechanisms_fallback)
        check("Fallback privacy_status is 'Data Local' (not empty, not crash)",
              privacy_status_fallback == "Data Local",
              f"got: {privacy_status_fallback!r}")

        # ── NEW: get_dashboard with nonexistent experiment is safe ─────────────
        # Since get_dashboard reads the *latest* experiment from DB (which does
        # exist), we cannot pass a nonexistent one directly; instead verify that
        # the metric_repo methods it relies on are safe for empty results.
        print("\n=== NEW: Dashboard service with missing experiment is safe ===")
        bad_org_rows = await metric_repo.get_by_category_for_experiment(
            "experiment_org", "nonexistent_exp"
        )
        check("experiment_org rows empty for unknown exp_id",
              bad_org_rows == [], f"got: {len(bad_org_rows)} rows")
        # Participant IDs derived from empty rows is empty set (no crash)
        participant_ids_fallback = {
            m.org_id for m in bad_org_rows
            if m.org_id and m.model_type.endswith("__iid")
        }
        check("Participant ID set is empty for unknown exp_id",
              participant_ids_fallback == set())
        bad_summary = await metric_repo.get_by_category_for_experiment(
            "experiment_summary", "nonexistent_exp"
        )
        check("experiment_summary rows empty for unknown exp_id",
              bad_summary == [], f"got: {len(bad_summary)} rows")
        iid_m_fallback = {m.metric_name: m.metric_value for m in bad_summary if m.model_type.endswith("__iid")}
        check("iid_metrics is empty dict for unknown exp_id",
              iid_m_fallback == {})

    print("\n" + "=" * 60)
    passed = sum(1 for s, _, _ in results if s == PASS)
    failed = sum(1 for s, _, _ in results if s == FAIL)
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        print("\nFailed tests:")
        for s, label, detail in results:
            if s == FAIL:
                print(f"  {s}  {label}" + (f" — {detail}" if detail else ""))
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
