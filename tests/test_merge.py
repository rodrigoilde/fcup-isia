"""Testes da fusão de alertas por área (T1.1), da deduplicação P26 simétrica e da regra DUP (T1.2)."""

import random

from cemr.agents.base import envelope
from cemr.behaviours.privacy import coarse_area
from cemr.behaviours.verification import Candidate, close_areas, notice_decision, same_incident
from cemr.config import load_config
from cemr.metrics.check import check
from cemr.metrics.compute import summarize
from cemr.protocol.messages_dispatch import CallForProposals
from cemr.protocol.messages_response import ReleaseAck
from cemr.sim.geometry import CityGrid
from cemr.sim.incidents import generate_trace
from cemr.sim.layout import generate_layout

CFG = load_config("c1")
WINDOW = CFG["verification"]["merge_window_s"]
RADIUS = CFG["verification"]["merge_radius_m"]
SPACING = CFG["city"]["grid_spacing_m"]


def test_area_is_the_nearest_grid_crossing():
    assert coarse_area([1449.0, 1551.0], SPACING) == [1400, 1600]


def test_device_and_witness_of_the_same_patient_merge():
    device = coarse_area([1520.0, 1480.0], SPACING)           # o doente usa o dispositivo
    witness = coarse_area([1531.0, 1470.0], SPACING)          # a testemunha está a ~15 m
    assert same_incident(device, 100.0, witness, 140.0, WINDOW, RADIUS)


def test_patients_300_m_apart_do_not_merge():
    a = coarse_area([1500.0, 1500.0], SPACING)
    b = coarse_area([1500.0, 1800.0], SPACING)
    assert not same_incident(a, 100.0, b, 110.0, WINDOW, RADIUS)


def test_alerts_outside_the_window_do_not_merge():
    area = coarse_area([1500.0, 1500.0], SPACING)
    assert not same_incident(area, 100.0, area, 100.0 + WINDOW + 1, WINDOW, RADIUS)


def test_unknown_area_is_never_close():
    assert not close_areas(None, [100, 100], RADIUS)


def test_newer_candidate_is_dropped():
    ours = Candidate(140.0, 1, [1500, 1500])
    theirs = Candidate(100.0, 3, [1500, 1500])
    assert notice_decision(ours, theirs, WINDOW, RADIUS) == "drop"


def test_older_candidate_replies_so_the_other_hub_drops_its_own():
    ours = Candidate(100.0, 3, [1500, 1500])
    theirs = Candidate(140.0, 1, [1500, 1500])
    assert notice_decision(ours, theirs, WINDOW, RADIUS) == "reply"


def test_tie_goes_to_the_lower_hub_id():
    assert notice_decision(Candidate(100.0, 5, [0, 0]), Candidate(100.0, 2, [0, 0]), WINDOW, RADIUS) == "drop"
    assert notice_decision(Candidate(100.0, 2, [0, 0]), Candidate(100.0, 5, [0, 0]), WINDOW, RADIUS) == "reply"


def test_notice_outside_the_window_is_ignored():
    ours = Candidate(100.0, 1, [1500, 1500])
    theirs = Candidate(100.0 + WINDOW + 1, 3, [1500, 1500])
    assert notice_decision(ours, theirs, WINDOW, RADIUS) is None


def test_notice_of_a_far_candidate_is_ignored():
    ours = Candidate(100.0, 1, [1500, 1500])
    theirs = Candidate(110.0, 3, [1500, 1900])
    assert notice_decision(ours, theirs, WINDOW, RADIUS) is None


def ev(t, kind, **fields):
    return {"t": t, "kind": kind, **fields}


def test_dup_rule_flags_two_declared_cases_for_one_patient():
    events = [ev(0, "gt_collapse", incident="I1", pos=[1000, 1000]),
              ev(10, "case_declared", agent="hub1", case="hub1-c1", priority="P1", p=0.9, rule="reliable_human"),
              ev(11, "case_declared", agent="hub3", case="hub3-c1", priority="P1", p=0.9, rule="reliable_human"),
              ev(12, "case_located", agent="hub1", case="hub1-c1", location=[1000, 1010]),
              ev(13, "case_located", agent="hub3", case="hub3-c1", location=[1005, 1000])]
    assert check(events, CFG)["DUP"]


def test_dup_rule_accepts_one_case_per_patient():
    events = [ev(0, "gt_collapse", incident="I1", pos=[1000, 1000]),
              ev(0, "gt_collapse", incident="I2", pos=[1300, 1000]),
              ev(10, "case_declared", agent="hub1", case="hub1-c1", priority="P1", p=0.9, rule="reliable_human"),
              ev(11, "case_declared", agent="hub1", case="hub1-c2", priority="P1", p=0.9, rule="reliable_human"),
              ev(12, "case_located", agent="hub1", case="hub1-c1", location=[1000, 1010]),
              ev(13, "case_located", agent="hub1", case="hub1-c2", location=[1300, 1010])]
    assert not check(events, CFG)["DUP"]


# --- T1.3: variante sem orientação ----------------------------------------------------------------
def triage_not_responding():
    return [ev(0, "candidate_opened", agent="hub1", case="c1"),
            ev(5, "triage_answer", agent="hub1", case="c1", source="wit1", question="responsive", answer="no"),
            ev(6, "triage_answer", agent="hub1", case="c1", source="wit1", question="breathing_normally",
               answer="no")]


def test_ol3_requires_guidance_after_a_not_responding_triage():
    assert check(triage_not_responding(), CFG)["OL3"]


def test_ol3_is_not_checked_without_guidance():
    cfg = load_config("c1", {"policy": {"guidance": False}})
    assert not check(triage_not_responding(), cfg)["OL3"]


# --- T1.4: cenário C5 com fontes reincidentes -----------------------------------------------------
def make_trace(scenario: str, seed: int = 1) -> dict:
    cfg = load_config(scenario)
    layout = generate_layout(cfg, random.Random(f"{seed}/layout"))
    grid = CityGrid(cfg["city"]["size_m"], cfg["city"]["grid_spacing_m"], layout.hub_positions)
    return generate_trace(cfg, layout, grid, random.Random(f"{seed}/trace"), cfg["run"]["duration_s"])


def test_c5_pranksters_are_two_citizens_who_always_report():
    pranks = [s for s in make_trace("c5")["stimuli"] if s.get("prankster")]
    assert len({s["bystander"] for s in pranks}) == 2
    assert len(pranks) > 2                                     # reincidentes: mais do que um relato cada
    assert all(s["will_report"] for s in pranks)


def test_scenarios_without_pranksters_have_none():
    assert not [s for s in make_trace("c1")["stimuli"] if s.get("prankster")]


# --- T1.5: recall sobre os incidentes reportados --------------------------------------------------
def test_recall_reported_ignores_incidents_nobody_reported():
    cfg = load_config("c1")
    events = [ev(0, "gt_collapse", incident="I1", pos=[1000, 1000], cell=1, priority="P1", shockable=False,
                 device=None, witness="wit1"),
              ev(0, "gt_collapse", incident="I2", pos=[2000, 2000], cell=2, priority="P1", shockable=False,
                 device=None, witness="wit2"),
              ev(30, "msg", src="wit1", dst="hub1", msg_type="AlertReport", thread="wit1-a1", dropped=None,
                 protocol="P01", bytes=10),
              ev(60, "case_declared", agent="hub1", case="hub1-c1", priority="P1", p=0.9, rule="reliable_human"),
              ev(61, "case_located", agent="hub1", case="hub1-c1", location=[1000, 1010])]
    m2 = summarize(events, cfg)["M2_verification"]
    assert m2["recall_P1_P2_detectable"] == 50.0               # a testemunha de I2 viu mas não reportou
    assert m2["recall_P1_P2_reported"] == 100.0


def test_case_is_matched_to_the_incident_of_its_own_witness():
    # Dois doentes a poucos metros (pico do C3): a testemunha de I1 está mais perto de I2.
    cfg = load_config("c3")
    events = [ev(0, "gt_collapse", incident="I1", pos=[1000, 1000], cell=1, priority="P1", shockable=False,
                 device=None, witness="wit1"),
              ev(0, "gt_collapse", incident="I2", pos=[1012, 1000], cell=1, priority="P1", shockable=False,
                 device=None, witness=None),
              ev(60, "case_declared", agent="hub1", case="hub1-c1", priority="P1", p=0.9, rule="reliable_human"),
              ev(61, "case_located", agent="hub1", case="hub1-c1", location=[1010, 1000], by="wit1")]
    m2 = summarize(events, cfg)["M2_verification"]
    assert m2["recall_P1_P2_detectable"] == 100.0              # I1 é o único detetável e tem o seu caso


# --- T1.7: reply-by na metadata ---------------------------------------------------------------------
def test_call_for_proposals_carries_fipa_reply_by():
    cfp = CallForProposals("hub1-c1", {"GO_TO_PATIENT": 2}, 1, "P1", "BLS", 112.5)
    metadata = envelope(cfp, "cfp", 7)
    assert metadata["reply-by"] == "112.5"
    assert metadata["protocol"] == "P08-CallForResponders" and metadata["ontology"] == "cemr-v1"


def test_messages_without_a_deadline_have_no_reply_by():
    assert "reply-by" not in envelope(ReleaseAck("hub1-c1"), "inform", 8)
