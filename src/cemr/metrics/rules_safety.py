"""Regras de safety da análise Gaia (OS1-OS13), verificadas no registo de eventos de um run.

Uma regra de safety diz o que nunca pode acontecer; cada função devolve a descrição de cada vez
que aconteceu. Desenho em docs/02-architectural-design.md §6.
"""

import json
from collections import defaultdict

from ..behaviours.guidance import STEPS
from ..protocol.ontology import Qualification
from .eventlog import AuditLog

# Eventos que só o dono de um caso pode registar (OS1)
ACTING = {"award", "release", "ems_award", "ambulance_requested", "case_closed", "recruit", "case_declared",
          "case_retracted", "responders_called"}


def is_naive(cfg: dict) -> bool:
    """Se o run é da linha de base B1."""
    return cfg["policy"]["allocation"] == "naive"


def check_os1(log: AuditLog, cfg: dict) -> list[str]:
    """OS1: só um hub é dono de cada caso de cada vez, e um hub que falhou não age."""
    found = []
    crashes = log.crashes()
    owner = {e["case"]: e["agent"] for e in log.of("candidate_opened")}
    changes = defaultdict(list)                     # caso -> [(t, novo dono)]
    for e in log.of("case_taken_over"):
        previous = e["previous"]
        if previous not in crashes or crashes[previous] > e["t"]:
            found.append(f"{e['case']}: {e['agent']} took over from {previous}, which had not crashed")
        changes[e["case"]].append((e["t"], e["agent"]))
    for e in log.events:
        case = e.get("case")
        if e["kind"] not in ACTING or case not in owner:
            continue
        current = owner[case]
        for t, new_owner in changes.get(case, []):
            if e["t"] >= t:
                current = new_owner
        if e["agent"] != current:
            found.append(f"{case}: {e['agent']} acted ({e['kind']}) at {e['t']:.0f} s but {current} owns it")
        if e["agent"] in crashes and e["t"] > crashes[e["agent"]]:
            found.append(f"{case}: crashed {e['agent']} acted at {e['t']:.0f} s")
    return found


def check_os2(log: AuditLog, cfg: dict) -> list[str]:
    """OS2: nenhum voluntário está comprometido com dois casos ao mesmo tempo."""
    found = []
    active = {}
    for e in log.events:
        if e["kind"] == "committed":
            if e["agent"] in active:
                found.append(f"{e['agent']} committed to {e['case']} while on {active[e['agent']]}")
            active[e["agent"]] = e["case"]
        elif e["kind"] == "mission_end":
            active.pop(e["agent"], None)
    return found


def check_os3(log: AuditLog, cfg: dict) -> list[str]:
    """OS3: um DAE tem no máximo uma reserva ativa."""
    found = []
    for e in log.of("aed_reserve"):
        if e["granted"] and e.get("prior_state") in ("RESERVED", "IN_USE"):
            found.append(f"AED {e['aed']} reserved for {e['case']} while {e['prior_state']}")
    return found


def check_os4(log: AuditLog, cfg: dict) -> list[str]:
    """OS4: só se declara com a crença acima de tau(p) e com um ramo da regra satisfeito."""
    if is_naive(cfg):
        return []
    tau = cfg["verification"]["tau_declare"]
    found = []
    for e in log.of("case_declared"):
        if not e.get("rule") or e["p"] < tau[e["priority"]]:
            found.append(f"{e['case']} declared with p={e['p']} rule={e.get('rule')}")
    return found


def check_os5(log: AuditLog, cfg: dict) -> list[str]:
    """OS5: a localização exata e os dados clínicos só vão para quem precisa de saber."""
    awarded = defaultdict(set)
    for e in log.of("award"):
        awarded[e["case"]].add(e["responder"])
    ems_of = defaultdict(set)                       # todas as ambulâncias adjudicadas ao caso
    for e in log.of("ems_award"):
        ems_of[e["case"]].add(e["unit"])
    found = []
    for m in log.of("msg"):
        kind, dst, case = m["msg_type"], m["dst"], m["thread"]
        if kind == "Award" and dst not in awarded.get(case, set()):
            found.append(f"location sent to non-awardee {dst} in {case}")
        if kind == "AmbulanceAward" and dst not in ems_of.get(case, set()):
            found.append(f"location sent to {dst}, not the case's EMS, in {case}")
        if kind == "Disclosure" and not dst.startswith(("hub", "ems")):
            found.append(f"disclosure to {dst} in {case}")
        if kind == "HandoverSummary" and not dst.startswith("ems"):
            found.append(f"clinical summary to {dst} in {case}")
    return found


def check_os6(log: AuditLog, cfg: dict) -> list[str]:
    """OS6: uma ambulância só é dispensada num falso alarme confirmado por um humano."""
    human_retracted = {e["case"] for e in log.of("case_retracted") if e.get("human_confirmed")}
    found = []
    for m in log.of("msg"):
        if m["msg_type"] == "Release" and m["dst"].startswith("ems") and m["thread"] not in human_retracted:
            found.append(f"ambulance {m['dst']} released in {m['thread']} without a human-confirmed false alarm")
    return found


def check_os8(log: AuditLog, cfg: dict) -> list[str]:
    """OS8: cada voluntário vê no máximo A_max alertas por hora."""
    a_max = cfg["volunteers"]["max_alerts_per_hour"]
    shown = defaultdict(list)
    found = []
    for e in log.of("alert_shown"):
        times = [t for t in shown[e["agent"]] if e["t"] - t < 3600] + [e["t"]]
        shown[e["agent"]] = times
        if len(times) > a_max:
            found.append(f"{e['agent']} shown {len(times)} alerts within an hour at {e['t']:.0f} s")
    return found


def check_os9(log: AuditLog, cfg: dict) -> list[str]:
    """OS9: nenhuma ambulância é desviada, exceto de P3 para P1 (aqui os P3 não recebem ambulância)."""
    priority_of = {e["case"]: e["priority"] for e in log.of("case_declared")}
    return [f"ambulance sent to P3 case {e['case']}" for e in log.of("ems_award")
            if priority_of.get(e["case"]) == "P3"]


def check_os11(log: AuditLog, cfg: dict) -> list[str]:
    """OS11: os dados pessoais são apagados até T_ret depois do fecho do caso."""
    t_ret = cfg["privacy"]["retention_s"]
    closed_at = {e["case"]: e["t"] for e in log.of("case_closed")}
    disclosed = {(e["agent"], e["case"]) for e in log.of("disclosure") if e["granted"]}
    purged = {(e["agent"], e["case"]): e["t"] for e in log.of("purge")}
    found = []
    for guardian, case in sorted(disclosed):
        if case not in closed_at or closed_at[case] + t_ret > log.end:
            continue
        t = purged.get((guardian, case))
        if t is None:
            found.append(f"{guardian} kept data of {case} past the end of the run")
        elif t - closed_at[case] > t_ret:
            found.append(f"{guardian} kept data of {case} {t - closed_at[case]:.0f} s after closure")
    return found


def check_os12(log: AuditLog, cfg: dict) -> list[str]:
    """OS12: as instruções de orientação vêm só do guidanceProtocol."""
    found = []
    for e in log.of("local_msg"):
        if e["msg_type"] == "Instruction" and json.loads(e["body"])["step"] not in STEPS:
            found.append(f"{e['agent']} gave an instruction outside guidanceProtocol")
    return found


def check_os13(log: AuditLog, cfg: dict) -> list[str]:
    """OS13: GO_TO_PATIENT só para voluntários qualificados."""
    found = []
    for e in log.of("award"):
        qualification = e.get("qualification")
        if e["task"] == "GO_TO_PATIENT" and qualification and \
                Qualification(qualification).rank < Qualification.BLS.rank:
            found.append(f"{e['responder']} ({qualification}) sent to the patient in {e['case']}")
    return found
