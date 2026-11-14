"""Verificação das regras organizacionais da análise Gaia (§7) no registo de eventos de um run.

    python -m cemr.metrics.check runs/<run> -v     # tabela das regras; código de saída 1 se alguma falhar

Cada regra é deduzida de novo a partir do que os agentes registaram (o auditLog, OS10), de forma
independente do código que a devia fazer cumprir. As regras que a linha de base B1 viola de
propósito (OS4) não são verificadas nela. Desenho em docs/02-architectural-design.md §6.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from ..behaviours.guidance import STEPS
from ..config import deep_merge, load_config
from ..protocol.ontology import Qualification
from .eventlog import read_events

# Eventos que só o dono de um caso pode registar (OS1)
ACTING = {"award", "release", "ems_award", "ambulance_requested", "case_closed", "recruit", "case_declared",
          "case_retracted", "responders_called"}
# Eventos que contam como resposta a uma adjudicação falhada ou atrasada (OL6). "recruit_skipped" é o
# registo do motivo por que o hub não recrutou (tarefa coberta, chamada em curso, ninguém para chamar).
OL6_FOLLOWUPS = {"award", "recruit", "responders_called", "case_closed", "release", "recruit_skipped"}
OL6_WINDOW_S = 60


class AuditLog:
    """Eventos de um run, agrupados por tipo para as verificações.

    Attributes:
        events (list[dict]): Todos os eventos, pela ordem do registo.
        end (float): Instante do último evento.
    """

    def __init__(self, events: list[dict]):
        self.events = events
        self.end = max((e["t"] for e in events), default=0.0)
        self.by_kind = defaultdict(list)
        for e in events:
            self.by_kind[e["kind"]].append(e)

    def of(self, kind: str) -> list[dict]:
        """Eventos de um tipo."""
        return self.by_kind.get(kind, [])

    def crashes(self) -> dict[str, float]:
        """Instante da falha de cada hub que falhou."""
        return {e["agent"]: e["t"] for e in self.of("fault_hub_crash")}


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
    """OL3: uma testemunha que diz "não responde" recebe orientação."""
    if is_naive(cfg):
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


# Código da regra -> (descrição, verificação)
RULES = {
    "OS1": ("exactly one hub owns each case at any time", check_os1),
    "OS2": ("no responder is committed to two cases at once", check_os2),
    "OS3": ("an AED has at most one active reservation", check_os3),
    "OS4": ("declaration needs tau(p) and an OS4 branch", check_os4),
    "OS5": ("precise location / clinical data only to need-to-know recipients", check_os5),
    "OS6": ("an ambulance is cancelled only for a human-confirmed false alarm", check_os6),
    "OS8": ("at most A_max alerts per volunteer per hour", check_os8),
    "OS9": ("no ambulance is preempted except P3 -> P1", check_os9),
    "OS11": ("personal data purged within T_ret of closure", check_os11),
    "OS12": ("guidance instructions only from guidanceProtocol", check_os12),
    "OS13": ("GO_TO_PATIENT only to qualified volunteers", check_os13),
    "OL1": ("every candidate ends discarded or closed", check_ol1),
    "OL2": ("P1/P2: ambulance requested right after declaration", check_ol2),
    "OL3": ("triage 'not responding' -> guidance activated", check_ol3),
    "OL5": ("guidance only for witnesses who answered the triage", check_ol5),
    "OL6": ("a failed or late award is followed by re-recruitment", check_ol6),
    "OL7": ("volunteers released only after the EMS took over (when they are)", check_ol7),
    "OL9": ("outcome feedback exactly once per closed case", check_ol9),
}


def check(events: list[dict], cfg: dict) -> dict[str, list[str]]:
    """Verifica todas as regras.

    Returns:
        dict[str, list[str]]: Código da regra -> descrição de cada violação encontrada.
    """
    log = AuditLog(events)
    return {code: verify(log, cfg) for code, (_, verify) in RULES.items()}


def summary_line(violations: dict[str, list[str]]) -> dict:
    """Resumo para o summary.json: total de violações e contagem por regra."""
    return {"violations": sum(len(x) for x in violations.values()),
            "by_rule": {rule: len(x) for rule, x in violations.items() if x}}


def main(argv=None) -> int:
    """Ponto de entrada da linha de comandos."""
    parser = argparse.ArgumentParser(description="Check organisational rules on a run's event log.")
    parser.add_argument("run", type=Path, help="run directory (with events.jsonl and config.json)")
    parser.add_argument("-v", "--verbose", action="store_true", help="list every violation")
    args = parser.parse_args(argv)
    events = read_events(args.run / "events.jsonl")
    run_cfg = json.loads((args.run / "config.json").read_text(encoding="utf-8"))
    cfg = deep_merge(load_config(), run_cfg)          # os runs antigos não têm as chaves novas
    violations = check(events, cfg)
    for rule, (text, _) in RULES.items():
        found = violations[rule]
        status = "FAIL" if found else " ok "
        count = f"  ({len(found)})" if found else ""
        print(f"{status}  {rule:5} {text}{count}")
        if args.verbose:
            for item in found:
                print(f"         - {item}")
    total = summary_line(violations)["violations"]
    print(f"\n{total} violation(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
