"""End-to-end smoke test: the scripted P1 case of C1 (incident S1) goes through the whole life cycle.

Runs a real SPADE simulation in a subprocess (embedded XMPP server, ~40 s). Skip with -m "not slow".
"""

import json
import subprocess
import sys

import pytest

from cemr.metrics.eventlog import read_events


def _key(pos):
    return (round(pos[0], 1), round(pos[1], 1))


@pytest.mark.slow
def test_scripted_p1_case_completes_the_ol1_sequence(tmp_path):
    out = tmp_path / "run"
    proc = subprocess.run(
        [sys.executable, "-m", "cemr.run", "--scenario", "c1", "--seed", "1", "--duration", "900",
         "--factor", "30", "--out", str(out), "--quiet"],
        capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr[-3000:]
    events = read_events(out / "events.jsonl")
    assert not [e for e in events if e["kind"] == "error"]

    s1 = next(e for e in events if e["kind"] == "gt_collapse" and e["incident"] == "S1")
    case = next(e["case"] for e in events if e["kind"] == "case_located" and _key(e["location"]) == _key(s1["pos"]))
    first = {}
    for e in events:
        if e.get("case") == case or (e.get("incident") == "S1" and e["kind"] != "gt_collapse"):
            first.setdefault(e["kind"], e["t"])

    # OL1: alert -> verification -> declaration -> dispatch -> help on scene -> closure
    order = ["candidate_opened", "case_declared", "ambulance_requested", "ems_award", "award",
             "cpr_started", "ems_arrived", "case_closed"]
    missing = [k for k in order if k not in first]
    assert not missing, f"missing events for {case}: {missing}"
    times = [first[k] for k in order]
    assert times == sorted(times), dict(zip(order, times))

    # OL2: in P1/P2 the ambulance is requested right after declaration
    assert first["ambulance_requested"] - first["case_declared"] < 1.0
    # OL7: volunteers are released only after the EMS took over
    releases = [e["t"] for e in events if e["kind"] == "release" and e.get("case") == case]
    took_over = [e["t"] for e in events if e["kind"] == "status" and e.get("case") == case
                 and e["status"] == "EMS_TOOK_OVER"]
    assert releases and took_over and min(releases) >= min(took_over)
    # OS5: the precise location reached only awarded responders and the EMS unit
    awarded = {e["responder"] for e in events if e["kind"] == "award" and e.get("case") == case}
    location_msgs = {e["dst"] for e in events if e["kind"] == "msg" and e["thread"] == case
                     and e["msg_type"] in ("Award", "AmbulanceAward")}
    assert location_msgs <= awarded | {e["unit"] for e in events if e["kind"] == "ems_award"}
    # Every organisational rule holds (metrics/check.py)
    summary = json.loads((out / "summary.json").read_text())
    assert summary["rules"]["violations"] == 0, summary["rules"]
    assert summary["valid"], summary["validity_problems"]


@pytest.mark.slow
def test_hub_crash_is_recovered_by_its_successor(tmp_path):
    """C4: hub 2 crashes at t=1200 while coordinating F1; a neighbour must take the case over (D8)."""
    out = tmp_path / "run"
    proc = subprocess.run(
        [sys.executable, "-m", "cemr.run", "--scenario", "c4", "--seed", "1", "--duration", "1500",
         "--factor", "30", "--out", str(out), "--quiet"],
        capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr[-3000:]
    events = read_events(out / "events.jsonl")
    crash = next(e for e in events if e["kind"] == "fault_hub_crash")
    takeover = next(e for e in events if e["kind"] == "takeover" and e["previous"] == crash["agent"])
    assert takeover["cases"], "the crashed hub had a case in progress"
    assert takeover["t"] - crash["t"] < 40                       # lease 15 s + margin 5 s + heartbeat period
    assert any(e["kind"] == "coordinator_changed" for e in events)  # P28 reached the participants
    assert not [e for e in events if e.get("agent") == crash["agent"] and e["t"] > crash["t"] + 1]
    summary = json.loads((out / "summary.json").read_text())
    assert summary["rules"]["violations"] == 0, summary["rules"]
    assert summary["M12_robustness"]["orphaned_cases"] == 0
