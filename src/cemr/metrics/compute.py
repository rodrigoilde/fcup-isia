"""Métricas M1-M13 a partir do registo de eventos (análise §8.1).

Os casos são associados aos incidentes da verdade de referência pela localização exata divulgada
ao coordenador ("case_located"): um caso declarado localizado onde não há doente conta como falso
despacho. As métricas de tempo (M1, M3-M7, M9, M13) usam os incidentes **detetáveis**, os que têm
um dispositivo ou uma testemunha: os outros só seriam apanhados por uma chamada para o 112, que não
é simulada (A7). Continuam a contar contra o recall.
"""

import math
import statistics
from collections import Counter, defaultdict

from ..protocol.ontology import ON_SCENE_STATUSES
from ..sim.patient import PatientState, estimated_survival

BACKGROUND_PROTOCOLS = ("P23", "P25", "P27")       # gossip, registos e heartbeats: não dependem dos casos
LOCATION_MESSAGES = ("Award", "AmbulanceAward", "HandoverSummary", "Disclosure")


# --- estatísticas simples ------------------------------------------------------------------------
def median(values: list) -> float | None:
    """Mediana arredondada às décimas, ou None sem valores."""
    return round(statistics.median(values), 1) if values else None


def p90(values: list) -> float | None:
    """Percentil 90 (o valor da posição mais próxima), ou None sem valores."""
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(0.9 * (len(ordered) - 1) + 0.5))
    return round(ordered[index], 1)


def pct(part: float, whole: float) -> float | None:
    """Percentagem arredondada às décimas, ou None se o total é 0."""
    return round(100.0 * part / whole, 1) if whole else None


def mean(values: list) -> float | None:
    """Média arredondada às centésimas, ou None sem valores."""
    return round(statistics.fmean(values), 2) if values else None


def jain(values) -> float | None:
    """Índice de equidade de Jain: 1 quando todos têm a mesma carga, 1/n quando um tem tudo."""
    values = list(values)
    if not values or not any(values):
        return None
    return round(sum(values) ** 2 / (len(values) * sum(v * v for v in values)), 3)


# --- associação dos casos aos incidentes -----------------------------------------------------------
def group_by_kind(events: list[dict]) -> dict[str, list[dict]]:
    """Agrupa os eventos pelo seu tipo."""
    by_kind = defaultdict(list)
    for e in events:
        by_kind[e["kind"]].append(e)
    return by_kind


def nearest_incident(incidents: dict, location, radius: float) -> str | None:
    """Incidente mais próximo de uma localização divulgada (a testemunha está a poucos metros)."""
    best = None
    best_dist = 0.0
    for name, inc in incidents.items():
        dist = abs(inc["pos"][0] - location[0]) + abs(inc["pos"][1] - location[1])
        if best is None or (dist, name) < (best_dist, best):
            best = name
            best_dist = dist
    if best is not None and best_dist <= radius:
        return best
    return None


def match_incident(incidents: dict, located: dict, radius: float) -> str | None:
    """Incidente de um caso, a partir do evento "case_located".

    Se quem divulgou a localização é o dispositivo ou a testemunha de um incidente próximo, o caso é
    desse incidente. Só depois se usa o doente mais próximo: num pico (C3) dois doentes podem estar a
    poucos metros, e a testemunha de um pode estar mais perto do outro.
    """
    for name, inc in incidents.items():
        own_source = located.get("by") in (inc["device"], inc["witness"])
        near = abs(inc["pos"][0] - located["location"][0]) + abs(inc["pos"][1] - located["location"][1]) <= radius
        if own_source and near:
            return name
    return nearest_incident(incidents, located["location"], radius)


def incident_table(events: list[dict], radius: float) -> tuple[dict[str, dict], dict[str, str]]:
    """Tabela dos incidentes com o instante de cada marco e a associação caso -> incidente."""
    incidents = {}
    for e in events:
        if e["kind"] == "gt_collapse":
            incidents[e["incident"]] = {"t_collapse": e["t"], "priority": e["priority"], "shockable": e["shockable"],
                                        "pos": e["pos"], "cases": [], "device": e.get("device"),
                                        "witness": e.get("witness"),
                                        "detectable": e.get("device") is not None or e.get("witness") is not None}
    declared = {e["case"]: e for e in events if e["kind"] == "case_declared"}
    case_incident: dict[str, str] = {}
    for e in events:
        kind = e["kind"]
        if kind == "case_located":
            incident = match_incident(incidents, e, radius)
            if incident and e["case"] in declared:
                case_incident[e["case"]] = incident
                if e["case"] not in incidents[incident]["cases"]:
                    incidents[incident]["cases"].append(e["case"])
                incidents[incident].setdefault("t_declared", declared[e["case"]]["t"])
        elif kind in ("cpr_started", "aed_attached", "shock", "ems_arrived") and e.get("incident") in incidents:
            incidents[e["incident"]].setdefault(f"t_{kind}", e["t"])
        elif kind == "status" and is_volunteer_on_scene(e) and e.get("case") in case_incident:
            incidents[case_incident[e["case"]]].setdefault("t_volunteer", e["t"])
    return incidents, case_incident


def is_volunteer_on_scene(e: dict) -> bool:
    """Se um evento "status" é de um voluntário que chegou ao local."""
    return e.get("status") in ON_SCENE_STATUSES and e.get("source", "").startswith("vol")


def since_collapse(group: list[dict], key: str) -> list[float]:
    """Tempo desde o colapso até ao marco `key`, para os incidentes que o atingiram."""
    return [i[key] - i["t_collapse"] for i in group if key in i]


def before_ems(incident: dict, key: str) -> bool:
    """Se o marco `key` aconteceu antes de a ambulância chegar (ou sem ambulância)."""
    return key in incident and ("t_ems_arrived" not in incident or incident[key] < incident["t_ems_arrived"])


def share_before_ems(group: list[dict], key: str) -> float | None:
    """Percentagem dos incidentes em que o marco `key` aconteceu antes da ambulância (M7)."""
    return pct(sum(1 for i in group if before_ems(i, key)), len(group))


def survival_values(group: list[dict], cfg: dict) -> list[float]:
    """M6 para os P1 desfibrilháveis de um grupo de incidentes."""
    values = []
    for i in group:
        if i["shockable"]:
            patient = PatientState("", "P1", True, i["t_collapse"], tuple(i["pos"]), i.get("t_cpr_started"),
                                   i.get("t_aed_attached"), i.get("t_shock"), 0, i.get("t_ems_arrived"))
            values.append(estimated_survival(patient, cfg["ems"]["first_shock_delay_s"], cfg["run"]["duration_s"]))
    return values


# --- métricas por grupo -----------------------------------------------------------------------------
def reported_incidents(incidents: dict, by_kind: dict, window_s: float) -> set[str]:
    """Incidentes cujo dispositivo ou testemunha enviou pelo menos um alerta (P01) logo depois do colapso."""
    reported = set()
    for m in by_kind["msg"]:
        if m["msg_type"] != "AlertReport":
            continue
        for name, inc in incidents.items():
            from_source = m["src"] in (inc["device"], inc["witness"])
            if from_source and inc["t_collapse"] <= m["t"] <= inc["t_collapse"] + window_s:
                reported.add(name)
    return reported


def verification_metrics(incidents: dict, declared: dict, false_dispatches: list, reported: set) -> dict:
    """M2: precisão e recall da verificação.

    Há três recalls. O de todos os P1/P2 inclui os que só uma chamada para o 112 apanharia (A7); o dos
    detetáveis exclui-os; o dos reportados exclui também os que nenhuma fonte chegou a reportar (a
    testemunha decidiu não o fazer, ou o sensor falhou), e por isso mede só a fusão e a verificação.
    """
    urgent_all = [i for i in incidents.values() if i["priority"] in ("P1", "P2")]
    urgent = [i for i in urgent_all if i["detectable"]]
    urgent_reported = [i for name, i in incidents.items() if i in urgent_all and name in reported]
    return {"precision": pct(len(declared) - len(false_dispatches), len(declared)),
            "recall_P1_P2": pct(sum(1 for i in urgent_all if i["cases"]), len(urgent_all)),
            "recall_P1_P2_detectable": pct(sum(1 for i in urgent if i["cases"]), len(urgent)),
            "recall_P1_P2_reported": pct(sum(1 for i in urgent_reported if i["cases"]), len(urgent_reported)),
            "false_dispatches": len(false_dispatches),
            "false_dispatches_per_100_cases": pct(len(false_dispatches), len(declared))}


def message_metrics(by_kind: dict) -> dict:
    """M8: mensagens enviadas, perdidas e por candidato (sem as de fundo)."""
    msgs = by_kind["msg"]
    sent = [m for m in msgs if not m["dropped"]]
    background = [m for m in sent if m["protocol"] in BACKGROUND_PROTOCOLS]
    n_candidates = len(by_kind["candidate_opened"])
    per_candidate = None
    if n_candidates:
        per_candidate = round((len(sent) - len(background)) / n_candidates, 1)
    return {"sent": len(sent), "dropped": len(msgs) - len(sent), "background": len(background),
            "bytes": sum(m["bytes"] for m in sent), "per_candidate": per_candidate}


def oracle_metrics(incidents: dict, p1_names: set, oracle: dict | None) -> tuple[dict, dict]:
    """M9 (distância ao oráculo B0 no primeiro voluntário) e as medianas do próprio B0."""
    if not oracle:
        return {"median": None, "n": 0}, {"first_responder_s": None, "aed_s": None, "ems_s": None}
    gaps = []
    for name in p1_names:
        best = oracle.get(name, {}).get("first_responder_s")
        if "t_volunteer" in incidents[name] and best is not None:
            gaps.append(incidents[name]["t_volunteer"] - incidents[name]["t_collapse"] - best)
    b0 = {}
    for key in ("first_responder_s", "aed_s", "ems_s"):
        b0[key] = median([oracle[n][key] for n in p1_names if oracle.get(n) and oracle[n][key] is not None])
    return {"median": median(gaps), "n": len(gaps)}, b0


def volunteer_load(by_kind: dict, located: dict, case_incident: dict) -> dict:
    """M10: alertas e tarefas por voluntário, equidade de Jain e minutos gastos em falsos alarmes."""
    volunteers = {e["agent"] for e in by_kind["agent"] if e.get("agent_kind") == "volunteer"}
    alerts = Counter(e["agent"] for e in by_kind["alert_shown"])
    tasks = Counter(e["agent"] for e in by_kind["committed"])
    outcome = {e["case"]: e["outcome"] for e in by_kind["case_closed"]}
    retracted = {e["case"] for e in by_kind["case_retracted"]}
    started = {(e["agent"], e["case"]): e["t"] for e in by_kind["committed"]}
    wasted = 0.0
    for e in by_kind["mission_end"]:
        t0 = started.get((e["agent"], e["case"]))
        case = e["case"]
        false_alarm = (outcome.get(case) == "FALSE_ALARM" or case in retracted
                       or (case in located and case not in case_incident))
        if t0 is not None and false_alarm:
            wasted += e["t"] - t0
    return {"alerts_per_volunteer": mean([alerts.get(v, 0) for v in volunteers]),
            "max_alerts": max(alerts.values(), default=0),
            "tasks_per_volunteer": mean([tasks.get(v, 0) for v in volunteers]),
            "jain_tasks": jain(tasks.get(v, 0) for v in volunteers),
            "false_alarm_minutes": round(wasted / 60.0, 1)}


def privacy_exposure(by_kind: dict, declared: dict) -> dict:
    """M11: quantos agentes receberam a localização exata (ou dados clínicos) por caso declarado."""
    exposed = defaultdict(set)
    for m in by_kind["msg"]:
        if not m["dropped"] and m["msg_type"] in LOCATION_MESSAGES and m["thread"] in declared:
            exposed[m["thread"]].add(m["dst"])
    sizes = [len(r) for r in exposed.values()]
    return {"recipients_per_case": mean(sizes), "max": max(sizes, default=0)}


def robustness(by_kind: dict, declared: dict) -> dict:
    """M12: tempo de recuperação depois da falha de um hub e casos que ficaram sem dono."""
    crashes = {e["agent"]: e["t"] for e in by_kind["fault_hub_crash"]}
    recoveries = [e["t"] - crashes[e["previous"]] for e in by_kind["takeover"] if e["previous"] in crashes]
    taken = {e["case"] for e in by_kind["case_taken_over"]}
    orphaned = 0
    for hub, t_crash in crashes.items():
        owned = {e["case"] for e in by_kind["candidate_opened"] if e["agent"] == hub and e["t"] < t_crash}
        ended = {e["case"] for e in by_kind["case_closed"] + by_kind["candidate_discarded"] if e["t"] <= t_crash}
        orphaned += len({c for c in owned - ended if c in declared} - taken)
    msgs = by_kind["msg"]
    dropped = sum(1 for m in msgs if m["dropped"])
    return {"crashes": len(crashes), "recovery_s": median(recoveries), "orphaned_cases": orphaned,
            "drop_rate_pct": pct(dropped, len(msgs))}


def equity(p1: list[dict], cfg: dict) -> dict:
    """M13: tempos no centro da cidade contra a periferia."""
    size = cfg["city"]["size_m"]
    radius = cfg["metrics"]["central_radius_m"]
    centre = (size / 2, size / 2)
    central = [i for i in p1 if math.dist(i["pos"], centre) <= radius]
    peripheral = [i for i in p1 if math.dist(i["pos"], centre) > radius]
    return {"cpr_central_s": median(since_collapse(central, "t_cpr_started")),
            "cpr_peripheral_s": median(since_collapse(peripheral, "t_cpr_started")),
            "volunteer_before_ems_central_pct": share_before_ems(central, "t_volunteer"),
            "volunteer_before_ems_peripheral_pct": share_before_ems(peripheral, "t_volunteer")}


def counts(incidents: dict, by_kind: dict, declared: dict) -> dict:
    """Contagens gerais do run: incidentes, falsos alarmes, candidatos e casos por resultado."""
    return {"incidents": dict(Counter(i["priority"] for i in incidents.values())),
            "undetectable": sum(1 for i in incidents.values() if not i["detectable"]),
            "false_alarm_events": len(by_kind["gt_false_alarm"]),
            "false_witness_events": len(by_kind["gt_false_witness"]),
            "candidates": len(by_kind["candidate_opened"]),
            "declared": len(declared),
            "discarded": len(by_kind["candidate_discarded"]),
            "retracted": len({e["case"] for e in by_kind["case_retracted"]}),
            "closed": dict(Counter(e["outcome"] for e in by_kind["case_closed"]))}


def summarize(events: list[dict], cfg: dict, oracle: dict | None = None) -> dict:
    """Calcula todas as métricas de um run.

    Args:
        events (list[dict]): Registo de eventos do run.
        cfg (dict): Configuração do run.
        oracle (dict | None): Tempos do oráculo B0 por incidente (`baselines.oracle_b0`).

    Returns:
        dict: Contagens gerais e as métricas M1-M13, uma chave por métrica.
    """
    radius = cfg["metrics"]["match_radius_m"]
    incidents, case_incident = incident_table(events, radius)
    by_kind = group_by_kind(events)
    declared = {e["case"]: e for e in by_kind["case_declared"]}
    located = {e["case"]: e for e in by_kind["case_located"]}
    false_dispatches = [c for c, e in located.items() if c in declared and match_incident(incidents, e, radius) is None]
    urgent = [i for i in incidents.values() if i["priority"] in ("P1", "P2") and i["detectable"]]
    p1 = [i for i in urgent if i["priority"] == "P1"]
    p1_names = {name for name, i in incidents.items() if i["priority"] == "P1" and i["detectable"]}
    reported = reported_incidents(incidents, by_kind, cfg["metrics"]["report_window_s"])
    survival = survival_values(p1, cfg)
    m9, b0 = oracle_metrics(incidents, p1_names, oracle)
    cpr_events = by_kind["cpr_started"]
    by_bystander = sum(1 for e in cpr_events if e["by"].startswith("wit"))
    return {
        **counts(incidents, by_kind, declared),
        "M1_verification_latency_s": {"median": median(since_collapse(urgent, "t_declared")),
                                      "p90": p90(since_collapse(urgent, "t_declared"))},
        "M2_verification": verification_metrics(incidents, declared, false_dispatches, reported),
        "M3_time_to_cpr_s": {"median": median(since_collapse(p1, "t_cpr_started")),
                             "by_bystander_pct": pct(by_bystander, len(cpr_events))},
        "M4_time_to_aed_s": {"median": median(since_collapse(p1, "t_aed_attached")),
                             "first_shock_median": median(since_collapse(p1, "t_shock"))},
        "M5_time_to_ems_s": {"median": median(since_collapse(urgent, "t_ems_arrived"))},
        "M6_survival_pct": {"mean": mean(survival), "n": len(survival)},
        "M7_coverage_before_ems_pct": {"volunteer": share_before_ems(p1, "t_volunteer"),
                                       "cpr": share_before_ems(p1, "t_cpr_started"),
                                       "aed": share_before_ems(p1, "t_aed_attached")},
        "M8_messages": message_metrics(by_kind),
        "M9_gap_to_oracle_s": m9,
        "B0_oracle_s": b0,
        "M10_volunteer_load": volunteer_load(by_kind, located, case_incident),
        "M11_privacy_exposure": privacy_exposure(by_kind, declared),
        "M12_robustness": robustness(by_kind, declared),
        "M13_equity": equity(p1, cfg),
        "errors": len(by_kind["error"]),
    }
