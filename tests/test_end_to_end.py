"""Testes ponta a ponta: simulações SPADE reais num subprocesso, com o servidor XMPP embutido (~50 s cada).

Saltam-se com `pytest -m "not slow"`.
"""

import json
import subprocess
import sys

import pytest

from cemr.metrics.eventlog import read_events


def run_simulation(out, scenario: str, duration: int) -> list[dict]:
    """Corre um run curto e devolve o registo de eventos (o run tem de acabar com código 0)."""
    proc = subprocess.run(
        [sys.executable, "-m", "cemr.run", "--scenario", scenario, "--seed", "1", "--duration", str(duration),
         "--factor", "30", "--out", str(out), "--quiet"],
        capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr[-3000:]
    return read_events(out / "events.jsonl")


def pos_key(pos) -> tuple:
    return (round(pos[0], 1), round(pos[1], 1))


@pytest.mark.slow
def test_scripted_p1_case_completes_the_ol1_sequence(tmp_path):
    """C1: o P1 com guião (S1) passa por todo o ciclo de vida de um caso."""
    out = tmp_path / "run"
    events = run_simulation(out, "c1", 900)
    assert not [e for e in events if e["kind"] == "error"]

    s1 = next(e for e in events if e["kind"] == "gt_collapse" and e["incident"] == "S1")
    case = next(e["case"] for e in events if e["kind"] == "case_located" and pos_key(e["location"]) == pos_key(s1["pos"]))
    first = {}
    for e in events:
        if e.get("case") == case or (e.get("incident") == "S1" and e["kind"] != "gt_collapse"):
            first.setdefault(e["kind"], e["t"])

    # OL1: alerta -> verificação -> declaração -> despacho -> ajuda no local -> fecho
    order = ["candidate_opened", "case_declared", "ambulance_requested", "ems_award", "award",
             "cpr_started", "ems_arrived", "case_closed"]
    missing = [k for k in order if k not in first]
    assert not missing, f"missing events for {case}: {missing}"
    times = [first[k] for k in order]
    assert times == sorted(times), dict(zip(order, times))

    # OL2: em P1/P2 a ambulância é pedida logo a seguir à declaração
    assert first["ambulance_requested"] - first["case_declared"] < 1.0
    # OL7: os voluntários só são dispensados depois de a ambulância assumir
    releases = [e["t"] for e in events if e["kind"] == "release" and e.get("case") == case]
    took_over = [e["t"] for e in events if e["kind"] == "status" and e.get("case") == case
                 and e["status"] == "EMS_TOOK_OVER"]
    assert releases and took_over and min(releases) >= min(took_over)
    # OS5: a localização exata só chegou aos voluntários adjudicados e à ambulância
    awarded = {e["responder"] for e in events if e["kind"] == "award" and e.get("case") == case}
    location_msgs = {e["dst"] for e in events if e["kind"] == "msg" and e["thread"] == case
                     and e["msg_type"] in ("Award", "AmbulanceAward")}
    assert location_msgs <= awarded | {e["unit"] for e in events if e["kind"] == "ems_award"}
    # Todas as regras organizacionais se cumprem (metrics/check.py)
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["rules"]["violations"] == 0, summary["rules"]
    assert summary["valid"], summary["validity_problems"]


@pytest.mark.slow
def test_hub_crash_is_recovered_by_its_successor(tmp_path):
    """C4: o hub 2 falha em t=1200 a coordenar o F1; um vizinho tem de assumir o caso (D8)."""
    out = tmp_path / "run"
    events = run_simulation(out, "c4", 1500)
    crash = next(e for e in events if e["kind"] == "fault_hub_crash")
    takeover = next(e for e in events if e["kind"] == "takeover" and e["previous"] == crash["agent"])
    assert takeover["cases"], "the crashed hub had a case in progress"
    assert takeover["t"] - crash["t"] < 40                       # lease 15 s + margem 5 s + período do heartbeat
    assert any(e["kind"] == "coordinator_changed" for e in events)  # o P28 chegou aos participantes
    assert not [e for e in events if e.get("agent") == crash["agent"] and e["t"] > crash["t"] + 1]
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["rules"]["violations"] == 0, summary["rules"]
    assert summary["M12_robustness"]["orphaned_cases"] == 0
