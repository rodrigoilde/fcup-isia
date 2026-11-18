"""Porque é que um incidente P1/P2 ficou sem caso: diagnóstico do recall da métrica M2.

Um P1/P2 é falhado quando nenhum caso declarado foi localizado junto do doente (`compute.incident_table`).
Para cada um, seguimos no registo de eventos os alertas (P01) do seu dispositivo e da sua testemunha e
dizemos até onde chegaram: se houve alerta, se um hub abriu um candidato com ele, como o candidato
terminou (incluindo a fusão P26 noutro hub) e, se foi declarado, porque não ficou associado a este doente.

O cálculo é feito depois do run, só a partir do registo, e não muda o comportamento dos agentes.
Motivos e o seu significado em docs/03-detailed-design.md §7.
"""

from collections import defaultdict

# Motivos pela ordem do percurso de um alerta. Um incidente cujos alertas chegaram a vários candidatos
# fica com o motivo do candidato que foi mais longe, isto é, o que aparece mais abaixo nesta lista.
REASONS = (
    "undetectable",          # sem dispositivo nem testemunha: só uma chamada para o 112 o apanharia (A7)
    "not_reported",          # nenhuma fonte enviou alerta (a testemunha não reportou ou o sensor falhou)
    "alert_lost",            # houve alerta, mas nenhum hub abriu ou juntou um candidato com ele
    "discarded_low_belief",  # descartado porque a crença caiu abaixo de discard_below
    "discarded_as_p3",       # W_max acabou com o candidato em P3 (pela triagem ou pelo tipo de alerta),
                             # cujo limiar de declaração é o mais alto
    "discarded_window",      # W_max acabou sem a crença chegar ao limiar ou sem cumprir OS4
    "undecided_at_end",      # o run acabou com o candidato ainda em verificação
    "declared_p3",           # declarado como P3: só contacto, sem despacho nem pedido de localização
    "retracted",             # declarado e retirado (P07) antes de a localização chegar
    "not_located",           # declarado como P1/P2, mas a localização exata (P24) nunca chegou
    "other_incident",        # declarado e localizado, mas associado a outro doente (ou a nenhum)
)


def incident_alerts(events: list[dict], incidents: dict, window_s: float) -> dict[str, set[str]]:
    """Alertas (P01) que as fontes de cada incidente enviaram logo depois do colapso.

    Conta também os alertas que a rede perdeu: o que interessa é se a fonte reportou.

    Args:
        events (list[dict]): Registo de eventos do run.
        incidents (dict): Tabela dos incidentes (`compute.incident_table`).
        window_s (float): Tempo máximo entre o colapso e o alerta (`metrics.report_window_s`).

    Returns:
        dict[str, set[str]]: Incidente -> ids dos alertas, só para os incidentes com pelo menos um.
    """
    alerts = defaultdict(set)
    for e in events:
        if e["kind"] != "msg" or e["msg_type"] != "AlertReport":
            continue
        for name, inc in incidents.items():
            from_source = e["src"] in (inc["device"], inc["witness"])
            if from_source and inc["t_collapse"] <= e["t"] <= inc["t_collapse"] + window_s:
                alerts[name].add(e["thread"])          # a thread de um P01 é o id do alerta
    return alerts


def alert_cases(events: list[dict]) -> dict[str, set[str]]:
    """Candidatos em que cada alerta entrou, aberto por ele ou fundido num candidato já aberto.

    Um alerta reenviado ao sucessor de um hub sem resposta (F6) pode entrar em dois candidatos.
    """
    cases = defaultdict(set)
    for e in events:
        if e["kind"] in ("candidate_opened", "alert_merged"):
            cases[e["alert"]].add(e["case"])
    return cases


def case_outcomes(events: list[dict]) -> dict[str, dict]:
    """Como terminou cada candidato: prioridade declarada, motivo do descarte, retirada e localização."""
    outcomes = defaultdict(dict)
    for e in events:
        kind = e["kind"]
        if kind == "case_declared":
            outcomes[e["case"]]["priority"] = e["priority"]
        elif kind == "candidate_discarded":
            outcomes[e["case"]]["discarded"] = e["reason"]
            outcomes[e["case"]]["discard_priority"] = e.get("priority")
            outcomes[e["case"]]["keeper"] = e.get("keeper")
        elif kind == "case_retracted":
            outcomes[e["case"]]["retracted"] = True
        elif kind == "case_located":
            outcomes[e["case"]]["located"] = True
    return outcomes


def final_case(case: str, outcomes: dict) -> str:
    """Segue as fusões P26: um candidato descartado por ser duplicado passou os alertas ao mais antigo."""
    seen = set()
    while outcomes.get(case, {}).get("discarded") == "merged" and case not in seen:
        seen.add(case)
        keeper = outcomes[case].get("keeper")
        if keeper is None:
            break
        case = keeper
    return case


def case_reason(outcome: dict) -> str:
    """Motivo pelo qual um candidato não serviu um incidente falhado.

    Um candidato declarado e localizado só aparece aqui se o incidente foi falhado, por isso a sua
    localização ficou associada a outro doente.
    """
    if "priority" in outcome:
        if outcome.get("located"):
            return "other_incident"
        if outcome["priority"] == "P3":
            return "declared_p3"
        if outcome.get("retracted"):
            return "retracted"
        return "not_located"
    if outcome.get("discarded") == "belief_too_low":
        return "discarded_low_belief"
    if outcome.get("discarded") == "window_expired" and outcome.get("discard_priority") == "P3":
        return "discarded_as_p3"
    if outcome.get("discarded") == "window_expired":
        return "discarded_window"
    return "undecided_at_end"


def miss_reason(incident: dict, alert_ids: set[str], cases_of_alert: dict, outcomes: dict) -> str:
    """Motivo de um incidente falhado: o ponto mais avançado a que os seus alertas chegaram."""
    if not incident["detectable"]:
        return "undetectable"
    if not alert_ids:
        return "not_reported"
    cases = set()
    for alert in alert_ids:
        for case in cases_of_alert.get(alert, ()):
            cases.add(final_case(case, outcomes))
    if not cases:
        return "alert_lost"
    reasons = [case_reason(outcomes.get(case, {})) for case in cases]
    return max(reasons, key=REASONS.index)


def missed_summary(events: list[dict], incidents: dict, alerts: dict[str, set[str]]) -> dict:
    """Conta os P1/P2 falhados por motivo e lista cada um (diagnóstico do recall da M2).

    Args:
        events (list[dict]): Registo de eventos do run.
        incidents (dict): Tabela dos incidentes, com os casos associados a cada um.
        alerts (dict[str, set[str]]): Alertas de cada incidente (`incident_alerts`).

    Returns:
        dict: Uma contagem por motivo (todos os motivos, mesmo a zero, para as colunas do runs.csv
        serem as mesmas em todos os runs) e, em "incidents", a lista dos incidentes falhados.
    """
    cases_of_alert = alert_cases(events)
    outcomes = case_outcomes(events)
    summary = {reason: 0 for reason in REASONS}
    missed = []
    for name, inc in sorted(incidents.items()):
        if inc["priority"] not in ("P1", "P2") or inc["cases"]:
            continue
        reason = miss_reason(inc, alerts.get(name, set()), cases_of_alert, outcomes)
        summary[reason] += 1
        missed.append({"incident": name, "priority": inc["priority"], "reason": reason})
    summary["incidents"] = missed
    return summary
