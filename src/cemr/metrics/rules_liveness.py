"""Regras de liveness da análise Gaia (OL1-OL9), verificadas no registo de eventos de um run.

Uma regra de liveness diz o que tem de acabar por acontecer; cada função devolve a descrição de
cada vez que não aconteceu. Desenho em docs/02-architectural-design.md §6.
"""

from collections import defaultdict

from .eventlog import AuditLog
from .rules_safety import is_naive

# Eventos que contam como resposta a uma adjudicação falhada ou atrasada (OL6). "recruit_skipped" é o
# registo do motivo por que o hub não recrutou (tarefa coberta, chamada em curso, ninguém para chamar).
OL6_FOLLOWUPS = {"award", "recruit", "responders_called", "case_closed", "release", "recruit_skipped"}
OL6_WINDOW_S = 60


def check_ol1(log: AuditLog, cfg: dict) -> list[str]:
    """OL1: todo o candidato acaba descartado ou fechado (salvo se o run acabou antes do timeout)."""
    finished = {e["case"] for e in log.of("candidate_discarded")} | {e["case"] for e in log.of("case_closed")}
    taken = {e["case"] for e in log.of("case_taken_over")}
    timeout = cfg["dispatch"]["case_timeout_s"]
    return [f"{e['case']} never closed nor discarded" for e in log.of("candidate_opened")
            if e["case"] not in finished and e["t"] + timeout < log.end and e["case"] not in taken]


def check_ol2(log: AuditLog, cfg: dict) -> list[str]:
    """OL2: em P1/P2 a ambulância é pedida logo a seguir à declaração."""
    requested = defaultdict(list)
    for e in log.of("ambulance_requested"):
        requested[e["case"]].append(e["t"])
    found = []
    for e in log.of("case_declared"):
        immediate = any(0 <= t - e["t"] <= 5 for t in requested[e["case"]])
        if e["priority"] in ("P1", "P2") and not immediate:
            found.append(f"{e['case']} ({e['priority']}) declared without an immediate ambulance request")
    return found


def triage_answers(log: AuditLog) -> dict[tuple[str, str], dict]:
    """Respostas da triagem por (caso, testemunha)."""
    answers = defaultdict(dict)
    for e in log.of("triage_answer"):
        answers[(e["case"], e["source"])][e["question"]] = e["answer"]
    return answers


def guided_pairs(log: AuditLog) -> set[tuple[str, str]]:
    """Pares (caso, testemunha) a quem foi pedida orientação (P05)."""
    return {(m["thread"], m["dst"]) for m in log.of("msg") if m["msg_type"] == "GuidanceActivation"}


def check_ol3(log: AuditLog, cfg: dict) -> list[str]:
    """OL3: uma testemunha que diz "não responde" recebe orientação (exceto na B1 e na variante sem orientação)."""
    if is_naive(cfg) or not cfg["policy"]["guidance"]:
        return []
    guided = guided_pairs(log)
    incoherent = {(e["case"], e["source"]) for e in log.of("triage_incoherent") if e.get("action") != "re-ask"}
    found = []
    for (case, witness), ans in triage_answers(log).items():
        complete = ans.get("responsive") in ("yes", "no") and ans.get("breathing_normally") in ("yes", "no")
        not_responding = complete and ans["responsive"] == "no"
        if not_responding and (case, witness) not in guided and (case, witness) not in incoherent:
            found.append(f"{witness} answered 'not responding' in {case} but was not guided")
    return found


def check_ol5(log: AuditLog, cfg: dict) -> list[str]:
    """OL5: só recebe orientação quem respondeu à triagem."""
    answers = triage_answers(log)
    return [f"{witness} guided in {case} without having answered the triage"
            for case, witness in sorted(guided_pairs(log)) if (case, witness) not in answers]


def check_ol6(log: AuditLog, cfg: dict) -> list[str]:
    """OL6: uma adjudicação falhada ou atrasada tem resposta (novo recrutamento ou motivo registado)."""
    followups = defaultdict(list)
    for e in log.events:
        if e["kind"] in OL6_FOLLOWUPS and "case" in e:
            followups[e["case"]].append(e["t"])
    took_over = {e["case"]: e["t"] for e in log.of("status") if e.get("status") == "EMS_TOOK_OVER"}
    found = []
    for e in log.of("award_failed") + log.of("award_at_risk"):
        case = e["case"]
        if case in took_over and took_over[case] <= e["t"]:
            continue
        answered = any(e["t"] <= t <= e["t"] + OL6_WINDOW_S for t in followups[case])
        if not answered and e["t"] + OL6_WINDOW_S < log.end:
            found.append(f"{case}: {e['responder']} {e['kind']} at {e['t']:.0f} s with no follow-up")
    return found


def check_ol7(log: AuditLog, cfg: dict) -> list[str]:
    """OL7: os voluntários só são dispensados depois de a ambulância assumir (quando assume)."""
    took_over = {e["case"]: e["t"] for e in log.of("status") if e.get("status") == "EMS_TOOK_OVER"}
    found = []
    for e in log.of("release"):
        if e.get("reason") == "ems_took_over" and e["case"] in took_over and e["t"] < took_over[e["case"]]:
            found.append(f"{e['responder']} released in {e['case']} before the EMS took over")
    return found


def check_ol9(log: AuditLog, cfg: dict) -> list[str]:
    """OL9: há exatamente um conjunto de rótulos de resultado por caso fechado."""
    labels = defaultdict(int)
    for e in log.of("local_msg"):
        if e["msg_type"] == "OutcomeLabels":
            labels[e["thread"]] += 1
    closed = sorted({e["case"] for e in log.of("case_closed")})
    return [f"{case} has {labels[case]} outcome label sets" for case in closed if labels[case] != 1]
