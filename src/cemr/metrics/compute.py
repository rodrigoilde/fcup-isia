"""Metrics M1–M13 from the event log (analysis §8.1).

Cases are matched to ground-truth incidents through the precise location disclosed to the
coordinator ("case_located"): a declared case located where no patient is counts as a false dispatch.
Time metrics (M1, M3–M7, M9, M13) are computed over **detectable** incidents, those with a wearable
or a witness: the others can only be caught by a 112 call, which is not simulated (A7). They still
count against recall.
"""

import math
import statistics
from collections import Counter, defaultdict

from ..protocol.ontology import ON_SCENE_STATUSES
from ..sim.patient import PatientState, estimated_survival

CENTRAL_RADIUS_M = 1000.0             # M13: incidents within this distance of the city centre are "central"


def _median(values):
    return round(statistics.median(values), 1) if values else None


def _p90(values):
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(0.9 * (len(ordered) - 1) + 0.5))], 1)


def _pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else None


def _mean(values):
    return round(statistics.fmean(values), 2) if values else None


def jain(values) -> float | None:
    """Jain's fairness index: 1 when everyone carries the same load, 1/n when one carries all."""
    values = list(values)
    if not values or not any(values):
        return None
    return round(sum(values) ** 2 / (len(values) * sum(v * v for v in values)), 3)


def nearest_incident(incidents: dict, location, radius: float = 50.0) -> str | None:
    """Match a disclosed location to a ground-truth patient (a witness stands a few metres away)."""
    best = min(((abs(i["pos"][0] - location[0]) + abs(i["pos"][1] - location[1]), name)
                for name, i in incidents.items()), default=None)
    return best[1] if best and best[0] <= radius else None


def incident_table(events: list[dict]) -> tuple[dict[str, dict], dict[str, str]]:
    incidents = {e["incident"]: {"t_collapse": e["t"], "priority": e["priority"], "shockable": e["shockable"],
                                 "pos": e["pos"], "cases": [],
                                 "detectable": e.get("device") is not None or e.get("witness") is not None}
                 for e in events if e["kind"] == "gt_collapse"}
    declared = {e["case"]: e for e in events if e["kind"] == "case_declared"}
    case_incident: dict[str, str] = {}
    for e in events:
        kind = e["kind"]
        if kind == "case_located":
            incident = nearest_incident(incidents, e["location"])
            if incident and e["case"] in declared:
                case_incident[e["case"]] = incident
                if e["case"] not in incidents[incident]["cases"]:
                    incidents[incident]["cases"].append(e["case"])
                incidents[incident].setdefault("t_declared", declared[e["case"]]["t"])
        elif kind in ("cpr_started", "aed_attached", "shock", "ems_arrived") and e.get("incident") in incidents:
            incidents[e["incident"]].setdefault(f"t_{kind}", e["t"])
        elif (kind == "status" and e.get("status") in ON_SCENE_STATUSES and e.get("source", "").startswith("vol")
              and e.get("case") in case_incident):
            incidents[case_incident[e["case"]]].setdefault("t_volunteer", e["t"])
    return incidents, case_incident


def summarize(events: list[dict], duration_s: float, oracle: dict | None = None, city_size: float = 3000.0) -> dict:
    incidents, case_incident = incident_table(events)
    by_kind = defaultdict(list)
    for e in events:
        by_kind[e["kind"]].append(e)
    declared = {e["case"]: e for e in by_kind["case_declared"]}
    located = {e["case"]: e["location"] for e in by_kind["case_located"]}
    false_dispatches = [c for c, loc in located.items() if c in declared and nearest_incident(incidents, loc) is None]

    urgent_all = [i for i in incidents.values() if i["priority"] in ("P1", "P2")]
    urgent = [i for i in urgent_all if i["detectable"]]
    p1 = [i for i in urgent if i["priority"] == "P1"]
    rel = lambda i, k: i[k] - i["t_collapse"] if k in i else None  # noqa: E731
    vals = lambda group, k: [v for v in (rel(i, k) for i in group) if v is not None]  # noqa: E731

    def survival(group):
        out = []
        for i in group:
            if i["shockable"]:
                patient = PatientState("", "P1", True, i["t_collapse"], tuple(i["pos"]), i.get("t_cpr_started"),
                                       i.get("t_aed_attached"), i.get("t_shock"), 0, i.get("t_ems_arrived"))
                out.append(estimated_survival(patient, horizon_t=duration_s))
        return out

    def before_ems(i, k):
        return k in i and ("t_ems_arrived" not in i or i[k] < i["t_ems_arrived"])

    # M8 messages
    msgs = by_kind["msg"]
    sent = [m for m in msgs if not m["dropped"]]
    background = [m for m in sent if m["protocol"] in ("P23", "P25", "P27")]   # gossip, registry, heartbeats
    n_candidates = len(by_kind["candidate_opened"])

    # M9 gap to the oracle B0 (time until the first volunteer is on scene)
    gaps = []
    if oracle:
        for name, i in incidents.items():
            if i in p1 and "t_volunteer" in i and oracle.get(name, {}).get("first_responder_s") is not None:
                gaps.append(i["t_volunteer"] - i["t_collapse"] - oracle[name]["first_responder_s"])

    # M10 volunteer load and fairness
    volunteers = {e["agent"] for e in by_kind["agent"] if e.get("agent_kind") == "volunteer"}
    alerts = Counter(e["agent"] for e in by_kind["alert_shown"])
    tasks = Counter(e["agent"] for e in by_kind["committed"])
    outcome = {e["case"]: e["outcome"] for e in by_kind["case_closed"]}
    retracted = {e["case"] for e in by_kind["case_retracted"]}
    started = {(e["agent"], e["case"]): e["t"] for e in by_kind["committed"]}
    wasted = 0.0
    for e in by_kind["mission_end"]:
        t0 = started.get((e["agent"], e["case"]))
        if t0 is not None and (outcome.get(e["case"]) == "FALSE_ALARM" or e["case"] in retracted
                               or (e["case"] in located and e["case"] not in case_incident)):
            wasted += e["t"] - t0

    # M11 privacy exposure: who received the precise location (or clinical data) per declared case
    exposed = defaultdict(set)
    for m in sent:
        if m["msg_type"] in ("Award", "AmbulanceAward", "HandoverSummary") and m["thread"] in declared:
            exposed[m["thread"]].add(m["dst"])
        if m["msg_type"] == "Disclosure" and m["thread"] in declared:
            exposed[m["thread"]].add(m["dst"])

    # M12 robustness: recovery after hub crashes
    crashes = {e["agent"]: e["t"] for e in by_kind["fault_hub_crash"]}
    recoveries = [e["t"] - crashes[e["previous"]] for e in by_kind["takeover"] if e["previous"] in crashes]
    orphaned = 0
    for hub, t_crash in crashes.items():
        owned = {e["case"] for e in by_kind["candidate_opened"] if e["agent"] == hub and e["t"] < t_crash}
        ended = {e["case"] for e in by_kind["case_closed"] + by_kind["candidate_discarded"] if e["t"] <= t_crash}
        taken = {e["case"] for e in by_kind["case_taken_over"]}
        orphaned += len({c for c in owned - ended if c in declared} - taken)

    # M13 territorial equity
    centre = (city_size / 2, city_size / 2)
    central = [i for i in p1 if math.dist(i["pos"], centre) <= CENTRAL_RADIUS_M]
    peripheral = [i for i in p1 if math.dist(i["pos"], centre) > CENTRAL_RADIUS_M]

    return {
        "incidents": dict(Counter(i["priority"] for i in incidents.values())),
        "undetectable": sum(1 for i in incidents.values() if not i["detectable"]),
        "false_alarm_events": len(by_kind["gt_false_alarm"]),
        "false_witness_events": len(by_kind["gt_false_witness"]),
        "candidates": n_candidates,
        "declared": len(declared),
        "discarded": len(by_kind["candidate_discarded"]),
        "retracted": len(retracted),
        "closed": dict(Counter(outcome.values())),
        "M1_verification_latency_s": {"median": _median(vals(urgent, "t_declared")),
                                      "p90": _p90(vals(urgent, "t_declared"))},
        "M2_verification": {"precision": _pct(len(declared) - len(false_dispatches), len(declared)),
                            "recall_P1_P2": _pct(sum(1 for i in urgent_all if i["cases"]), len(urgent_all)),
                            "recall_P1_P2_detectable": _pct(sum(1 for i in urgent if i["cases"]), len(urgent)),
                            "false_dispatches": len(false_dispatches),
                            "false_dispatches_per_100_cases": _pct(len(false_dispatches), len(declared))},
        "M3_time_to_cpr_s": {"median": _median(vals(p1, "t_cpr_started")),
                             "by_bystander_pct": _pct(sum(1 for e in by_kind["cpr_started"]
                                                          if e["by"].startswith("wit")), len(by_kind["cpr_started"]))},
        "M4_time_to_aed_s": {"median": _median(vals(p1, "t_aed_attached")),
                             "first_shock_median": _median(vals(p1, "t_shock"))},
        "M5_time_to_ems_s": {"median": _median(vals(urgent, "t_ems_arrived"))},
        "M6_survival_pct": {"mean": _mean(survival(p1)), "n": len(survival(p1))},
        "M7_coverage_before_ems_pct": {"volunteer": _pct(sum(before_ems(i, "t_volunteer") for i in p1), len(p1)),
                                       "cpr": _pct(sum(before_ems(i, "t_cpr_started") for i in p1), len(p1)),
                                       "aed": _pct(sum(before_ems(i, "t_aed_attached") for i in p1), len(p1))},
        "M8_messages": {"sent": len(sent), "dropped": len(msgs) - len(sent),
                        "background": len(background), "bytes": sum(m["bytes"] for m in sent),
                        "per_candidate": round((len(sent) - len(background)) / n_candidates, 1)
                        if n_candidates else None},
        "M9_gap_to_oracle_s": {"median": _median(gaps), "n": len(gaps)},
        "B0_oracle_s": {k: _median([oracle[n][k] for n, i in incidents.items() if i in p1 and oracle.get(n)
                                    and oracle[n][k] is not None]) if oracle else None
                        for k in ("first_responder_s", "aed_s", "ems_s")},
        "M10_volunteer_load": {"alerts_per_volunteer": _mean([alerts.get(v, 0) for v in volunteers]),
                               "max_alerts": max(alerts.values(), default=0),
                               "tasks_per_volunteer": _mean([tasks.get(v, 0) for v in volunteers]),
                               "jain_tasks": jain(tasks.get(v, 0) for v in volunteers),
                               "false_alarm_minutes": round(wasted / 60.0, 1)},
        "M11_privacy_exposure": {"recipients_per_case": _mean([len(r) for r in exposed.values()]),
                                 "max": max((len(r) for r in exposed.values()), default=0)},
        "M12_robustness": {"crashes": len(crashes), "recovery_s": _median(recoveries), "orphaned_cases": orphaned,
                           "drop_rate_pct": _pct(len(msgs) - len(sent), len(msgs))},
        "M13_equity": {"cpr_central_s": _median(vals(central, "t_cpr_started")),
                       "cpr_peripheral_s": _median(vals(peripheral, "t_cpr_started")),
                       "volunteer_before_ems_central_pct": _pct(sum(before_ems(i, "t_volunteer") for i in central),
                                                                len(central)),
                       "volunteer_before_ems_peripheral_pct": _pct(sum(before_ems(i, "t_volunteer") for i in peripheral),
                                                                   len(peripheral))},
        "errors": len(by_kind["error"]),
    }
