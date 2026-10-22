"""Check the organisational rules of the Gaia analysis (§7) on a run's event log.

    python -m cemr.metrics.check runs/<run>            # prints a table, exit code 1 if anything is violated

Each rule is re-derived from what the agents logged (the audit log, OS10), independently of the code
that is supposed to enforce it. Rules that the B1 baseline breaks on purpose (OS4) are skipped for it.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from ..behaviours.guidance import STEPS
from ..config import deep_merge, load_config
from ..protocol.ontology import ON_SCENE_STATUSES, Qualification
from .eventlog import read_events

RULES = {
    "OS1": "exactly one hub owns each case at any time",
    "OS2": "no responder is committed to two cases at once",
    "OS3": "an AED has at most one active reservation",
    "OS4": "declaration needs tau(p) and an OS4 branch",
    "OS5": "precise location / clinical data only to need-to-know recipients",
    "OS6": "an ambulance is cancelled only for a human-confirmed false alarm",
    "OS8": "at most A_max alerts per volunteer per hour",
    "OS9": "no ambulance is preempted except P3 -> P1",
    "OS11": "personal data purged within T_ret of closure",
    "OS12": "guidance instructions only from guidanceProtocol",
    "OS13": "GO_TO_PATIENT only to qualified volunteers",
    "OL1": "every candidate ends discarded or closed; closed cases get one outcome label set",
    "OL2": "P1/P2: ambulance requested right after declaration",
    "OL3": "triage 'not responding' -> guidance activated",
    "OL5": "guidance only for witnesses who answered the triage",
    "OL6": "a failed or late award is followed by re-recruitment",
    "OL7": "volunteers released only after the EMS took over (when they are)",
    "OL9": "outcome feedback exactly once per closed case",
}


def check(events: list[dict], cfg: dict) -> dict[str, list[str]]:
    v: dict[str, list[str]] = {rule: [] for rule in RULES}
    naive = cfg["policy"]["allocation"] == "naive"
    end = max(e["t"] for e in events) if events else 0.0
    by_kind = defaultdict(list)
    for e in events:
        by_kind[e["kind"]].append(e)
    msgs = by_kind["msg"]

    # --- OS1: ownership -------------------------------------------------------------------------
    crashes = {e["agent"]: e["t"] for e in by_kind["fault_hub_crash"]}
    owner = {e["case"]: e["agent"] for e in by_kind["candidate_opened"]}
    owner_changes = defaultdict(list)                       # case -> [(t, new owner)]
    for e in by_kind["case_taken_over"]:
        prev = e["previous"]
        if prev not in crashes or crashes[prev] > e["t"]:
            v["OS1"].append(f"{e['case']}: {e['agent']} took over from {prev}, which had not crashed")
        owner_changes[e["case"]].append((e["t"], e["agent"]))
    acting = {"award", "release", "ems_award", "ambulance_requested", "case_closed", "recruit", "case_declared",
              "case_retracted", "responders_called"}
    for e in events:
        case = e.get("case")
        if e["kind"] in acting and case in owner:
            current = owner[case]
            for t, new in owner_changes.get(case, []):
                if e["t"] >= t:
                    current = new
            if e["agent"] != current:
                v["OS1"].append(f"{case}: {e['agent']} acted ({e['kind']}) at {e['t']:.0f} s but {current} owns it")
            if e["agent"] in crashes and e["t"] > crashes[e["agent"]]:
                v["OS1"].append(f"{case}: crashed {e['agent']} acted at {e['t']:.0f} s")

    # --- OS2: one commitment per responder --------------------------------------------------------
    active = {}
    for e in events:
        if e["kind"] == "committed":
            if e["agent"] in active:
                v["OS2"].append(f"{e['agent']} committed to {e['case']} while on {active[e['agent']]}")
            active[e["agent"]] = e["case"]
        elif e["kind"] == "mission_end":
            active.pop(e["agent"], None)

    # --- OS3: AED reservations --------------------------------------------------------------------
    for e in by_kind["aed_reserve"]:
        if e["granted"] and e.get("prior_state") in ("RESERVED", "IN_USE"):
            v["OS3"].append(f"AED {e['aed']} reserved for {e['case']} while {e['prior_state']}")

    # --- OS4: declaration -------------------------------------------------------------------------
    tau = cfg["verification"]["tau_declare"]
    if not naive:
        for e in by_kind["case_declared"]:
            if not e.get("rule") or e["p"] < tau[e["priority"]]:
                v["OS4"].append(f"{e['case']} declared with p={e['p']} rule={e.get('rule')}")

    # --- OS5: need to know --------------------------------------------------------------------------
    awarded = defaultdict(set)
    for e in by_kind["award"]:
        awarded[e["case"]].add(e["responder"])
    ems_of = {e["case"]: e["unit"] for e in by_kind["ems_award"]}
    for m in msgs:
        if m["msg_type"] == "Award" and m["dst"] not in awarded.get(m["thread"], set()):
            v["OS5"].append(f"location sent to non-awardee {m['dst']} in {m['thread']}")
        if m["msg_type"] == "AmbulanceAward" and m["dst"] != ems_of.get(m["thread"]):
            v["OS5"].append(f"location sent to {m['dst']}, not the case's EMS, in {m['thread']}")
        if m["msg_type"] == "Disclosure" and not m["dst"].startswith(("hub", "ems")):
            v["OS5"].append(f"disclosure to {m['dst']} in {m['thread']}")
        if m["msg_type"] == "HandoverSummary" and not m["dst"].startswith("ems"):
            v["OS5"].append(f"clinical summary to {m['dst']} in {m['thread']}")

    # --- OS6: ambulance cancellation ---------------------------------------------------------------
    human_retracted = {e["case"] for e in by_kind["case_retracted"] if e.get("human_confirmed")}
    for m in msgs:
        if m["msg_type"] == "Release" and m["dst"].startswith("ems") and m["thread"] not in human_retracted:
            v["OS6"].append(f"ambulance {m['dst']} released in {m['thread']} without a human-confirmed false alarm")

    # --- OS8: alert fatigue -------------------------------------------------------------------------
    a_max = cfg["volunteers"]["max_alerts_per_hour"]
    shown = defaultdict(list)
    for e in by_kind["alert_shown"]:
        times = [t for t in shown[e["agent"]] if e["t"] - t < 3600] + [e["t"]]
        shown[e["agent"]] = times
        if len(times) > a_max:
            v["OS8"].append(f"{e['agent']} shown {len(times)} alerts within an hour at {e['t']:.0f} s")

    # --- OS9: preemption (vacuous: P3 cases get no ambulance) ---------------------------------------
    priority_of = {e["case"]: e["priority"] for e in by_kind["case_declared"]}
    for e in by_kind["ems_award"]:
        if priority_of.get(e["case"]) == "P3":
            v["OS9"].append(f"ambulance sent to P3 case {e['case']}")

    # --- OS11: retention ----------------------------------------------------------------------------
    t_ret = cfg["privacy"]["retention_s"]
    closed_at = {e["case"]: e["t"] for e in by_kind["case_closed"]}
    disclosed = {(e["agent"], e["case"]) for e in by_kind["disclosure"] if e["granted"]}
    purged = {(e["agent"], e["case"]): e["t"] for e in by_kind["purge"]}
    for guardian, case in disclosed:
        if case in closed_at and closed_at[case] + t_ret <= end:
            t = purged.get((guardian, case))
            if t is None or t - closed_at[case] > t_ret:
                v["OS11"].append(f"{guardian} kept data of {case} "
                                 f"{'past the end of the run' if t is None else f'{t - closed_at[case]:.0f} s'} after closure")

    # --- OS12: guidance protocol ---------------------------------------------------------------------
    for e in by_kind["local_msg"]:
        if e["msg_type"] == "Instruction" and json.loads(e["body"])["step"] not in STEPS:
            v["OS12"].append(f"{e['agent']} gave an instruction outside guidanceProtocol")

    # --- OS13: qualification ------------------------------------------------------------------------
    for e in by_kind["award"]:
        if e["task"] == "GO_TO_PATIENT" and e.get("qualification") and \
                Qualification(e["qualification"]).rank < Qualification.BLS.rank:
            v["OS13"].append(f"{e['responder']} ({e['qualification']}) sent to the patient in {e['case']}")

    # --- OL1 / OL9: life cycle and outcome feedback ---------------------------------------------------
    finished = {e["case"] for e in by_kind["candidate_discarded"]} | set(closed_at)
    timeout = cfg["dispatch"]["case_timeout_s"]
    for e in by_kind["candidate_opened"]:
        taken = any(c == e["case"] for c in owner_changes)
        if e["case"] not in finished and e["t"] + timeout < end and not taken:
            v["OL1"].append(f"{e['case']} never closed nor discarded")
    labels = defaultdict(int)
    for e in by_kind["local_msg"]:
        if e["msg_type"] == "OutcomeLabels":
            labels[e["thread"]] += 1
    for case in closed_at:
        if labels[case] != 1:
            v["OL9"].append(f"{case} has {labels[case]} outcome label sets")

    # --- OL2: ambulance right after declaration -------------------------------------------------------
    requested = defaultdict(list)
    for e in by_kind["ambulance_requested"]:
        requested[e["case"]].append(e["t"])
    for e in by_kind["case_declared"]:
        if e["priority"] in ("P1", "P2") and not any(0 <= t - e["t"] <= 5 for t in requested[e["case"]]):
            v["OL2"].append(f"{e['case']} ({e['priority']}) declared without an immediate ambulance request")

    # --- OL3 / OL5: triage and guidance ---------------------------------------------------------------
    answers = defaultdict(dict)
    for e in by_kind["triage_answer"]:
        answers[(e["case"], e["source"])][e["question"]] = e["answer"]
    guided = {(m["thread"], m["dst"]) for m in msgs if m["msg_type"] == "GuidanceActivation"}
    incoherent = {(e["case"], e["source"]) for e in by_kind["triage_incoherent"] if e.get("action") != "re-ask"}
    if not naive:
        for key, ans in answers.items():
            complete = ans.get("responsive") in ("yes", "no") and ans.get("breathing_normally") in ("yes", "no")
            if complete and ans["responsive"] == "no" and key not in guided and key not in incoherent:
                v["OL3"].append(f"{key[1]} answered 'not responding' in {key[0]} but was not guided")
    for case, witness in guided:
        if (case, witness) not in answers:
            v["OL5"].append(f"{witness} guided in {case} without having answered the triage")

    # --- OL6: re-recruitment after a failure or delay ------------------------------------------------
    followups = defaultdict(list)
    for e in events:
        if e["kind"] in ("award", "recruit", "responders_called", "case_closed", "release") and "case" in e:
            followups[e["case"]].append(e["t"])
    took_over = {e["case"]: e["t"] for e in by_kind["status"] if e.get("status") == "EMS_TOOK_OVER"}
    for e in by_kind["award_failed"] + by_kind["award_at_risk"]:
        case = e["case"]
        if case in took_over and took_over[case] <= e["t"]:
            continue
        if not any(e["t"] <= t <= e["t"] + 60 for t in followups[case]) and e["t"] + 60 < end:
            v["OL6"].append(f"{case}: {e['responder']} {e['kind']} at {e['t']:.0f} s with no follow-up")

    # --- OL7: release after the EMS took over -----------------------------------------------------------
    for e in by_kind["release"]:
        if e.get("reason") == "ems_took_over" and e["case"] in took_over and e["t"] < took_over[e["case"]]:
            v["OL7"].append(f"{e['responder']} released in {e['case']} before the EMS took over")
    return v


def summary_line(violations: dict[str, list[str]]) -> dict:
    return {"violations": sum(len(x) for x in violations.values()),
            "by_rule": {rule: len(x) for rule, x in violations.items() if x}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check organisational rules on a run's event log.")
    parser.add_argument("run", type=Path, help="run directory (with events.jsonl and config.json)")
    parser.add_argument("-v", "--verbose", action="store_true", help="list every violation")
    args = parser.parse_args(argv)
    events = read_events(args.run / "events.jsonl")
    cfg = deep_merge(load_config(), json.loads((args.run / "config.json").read_text()))   # older runs lack new keys
    violations = check(events, cfg)
    for rule, text in RULES.items():
        found = violations[rule]
        print(f"{'FAIL' if found else ' ok '}  {rule:5} {text}" + (f"  ({len(found)})" if found else ""))
        if args.verbose:
            for item in found:
                print(f"         - {item}")
    total = summary_line(violations)["violations"]
    print(f"\n{total} violation(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
