"""Verificação das regras organizacionais da análise Gaia (§7) no registo de eventos de um run.

    python -m cemr.metrics.check runs/<run> -v     # tabela das regras; código de saída 1 se alguma falhar

Cada regra é deduzida de novo a partir do que os agentes registaram (o auditLog, OS10), de forma
independente do código que a devia fazer cumprir. As regras que a linha de base B1 viola de
propósito (OS4) não são verificadas nela. As regras de safety (OS) estão em `rules_safety` e as
de liveness (OL) em `rules_liveness`. Desenho em docs/02-architectural-design.md §6.
"""

import argparse
import json
import sys
from pathlib import Path

from ..config import deep_merge, load_config
from .eventlog import AuditLog, read_events
from .rules_liveness import check_ol1, check_ol2, check_ol3, check_ol5, check_ol6, check_ol7, check_ol9
from .rules_safety import (check_dup, check_os1, check_os2, check_os3, check_os4, check_os5, check_os6, check_os8,
                           check_os9, check_os11, check_os12, check_os13)

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
    "DUP": ("no incident is handled by two declared cases", check_dup),
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
