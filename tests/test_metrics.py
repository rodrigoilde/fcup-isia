"""Testes das métricas e do verificador de regras: tem de apanhar violações, não só aceitar runs limpos."""

from cemr.config import load_config
from cemr.metrics.check import check
from cemr.metrics.compute import summarize

CFG = load_config("c1")


def ev(t: float, kind: str, **fields) -> dict:
    return {"t": t, "kind": kind, **fields}


def collapse(incident: str, pos: list, witness: str | None = None, device: str | None = None) -> dict:
    return ev(0, "gt_collapse", incident=incident, pos=pos, cell=1, priority="P1", shockable=False,
              device=device, witness=witness)


def declared(t: float, case: str, hub: str = "hub1") -> dict:
    return ev(t, "case_declared", agent=hub, case=case, priority="P1", p=0.9, rule="reliable_human")


# --- regras organizacionais -------------------------------------------------------------------------------
def test_checker_flags_a_second_owner_and_actions_after_a_crash():
    events = [ev(0, "candidate_opened", agent="hub1", case="c1"),
              ev(5, "award", agent="hub2", case="c1", responder="vol1", task="GO_TO_PATIENT"),
              ev(10, "fault_hub_crash", agent="hub1"),
              ev(20, "ambulance_requested", agent="hub1", case="c1")]
    found = check(events, CFG)["OS1"]
    assert any("hub2 acted" in v for v in found)
    assert any("crashed hub1 acted" in v for v in found)


def test_checker_flags_privacy_and_ambulance_cancellation():
    events = [ev(0, "candidate_opened", agent="hub1", case="c1"),
              ev(1, "msg", src="hub1", dst="vol9", msg_type="Award", thread="c1", dropped=None, protocol="P09"),
              ev(2, "msg", src="hub1", dst="ems0", msg_type="Release", thread="c1", dropped=None, protocol="P14")]
    result = check(events, CFG)
    assert result["OS5"] and result["OS6"]


def test_checker_passes_a_clean_minimal_case():
    events = [ev(0, "candidate_opened", agent="hub1", case="c1"),
              declared(1, "c1"),
              ev(1.5, "ambulance_requested", agent="hub1", case="c1"),
              ev(2, "award", agent="hub1", case="c1", responder="vol1", task="GO_TO_PATIENT", qualification="BLS"),
              ev(2, "msg", src="hub1", dst="vol1", msg_type="Award", thread="c1", dropped=None, protocol="P09"),
              ev(9, "case_closed", agent="hub1", case="c1", outcome="TRANSPORTED"),
              ev(9, "local_msg", agent="hub1", msg_type="OutcomeLabels", thread="c1", body="{}")]
    assert not any(check(events, CFG).values())


def test_dup_rule_flags_two_declared_cases_for_one_patient():
    events = [collapse("I1", [1000, 1000], witness="wit1"),
              declared(10, "hub1-c1"), declared(11, "hub3-c1", hub="hub3"),
              ev(12, "case_located", agent="hub1", case="hub1-c1", location=[1000, 1010], by="wit1"),
              ev(13, "case_located", agent="hub3", case="hub3-c1", location=[1005, 1000], by="wit1")]
    assert check(events, CFG)["DUP"]


def test_dup_rule_accepts_one_case_per_patient():
    events = [collapse("I1", [1000, 1000], witness="wit1"), collapse("I2", [1300, 1000], witness="wit2"),
              declared(10, "hub1-c1"), declared(11, "hub1-c2"),
              ev(12, "case_located", agent="hub1", case="hub1-c1", location=[1000, 1010], by="wit1"),
              ev(13, "case_located", agent="hub1", case="hub1-c2", location=[1300, 1010], by="wit2")]
    assert not check(events, CFG)["DUP"]


def triage_not_responding() -> list[dict]:
    return [ev(0, "candidate_opened", agent="hub1", case="c1"),
            ev(5, "triage_answer", agent="hub1", case="c1", source="wit1", question="responsive", answer="no"),
            ev(6, "triage_answer", agent="hub1", case="c1", source="wit1", question="breathing_normally",
               answer="no")]


def test_ol3_requires_guidance_after_a_not_responding_triage():
    assert check(triage_not_responding(), CFG)["OL3"]


def test_ol3_is_not_checked_without_guidance():
    cfg = load_config("c1", {"policy": {"guidance": False}})
    assert not check(triage_not_responding(), cfg)["OL3"]


# --- métricas ----------------------------------------------------------------------------------------------
def test_recall_reported_ignores_incidents_nobody_reported():
    events = [collapse("I1", [1000, 1000], witness="wit1"), collapse("I2", [2000, 2000], witness="wit2"),
              ev(30, "msg", src="wit1", dst="hub1", msg_type="AlertReport", thread="wit1-a1", dropped=None,
                 protocol="P01", bytes=10),
              declared(60, "hub1-c1"),
              ev(61, "case_located", agent="hub1", case="hub1-c1", location=[1000, 1010], by="wit1")]
    m2 = summarize(events, CFG)["M2_verification"]
    assert m2["recall_P1_P2_detectable"] == 50.0               # a testemunha de I2 viu mas não reportou
    assert m2["recall_P1_P2_reported"] == 100.0


def test_case_is_matched_to_the_incident_of_its_own_witness():
    # Dois doentes a poucos metros (pico do C3): a testemunha de I1 está mais perto de I2.
    events = [collapse("I1", [1000, 1000], witness="wit1"), collapse("I2", [1012, 1000]),
              declared(60, "hub1-c1"),
              ev(61, "case_located", agent="hub1", case="hub1-c1", location=[1010, 1000], by="wit1")]
    m2 = summarize(events, CFG)["M2_verification"]
    assert m2["recall_P1_P2_detectable"] == 100.0              # I1 é o único detetável e tem o seu caso


def test_a_case_located_where_nobody_collapsed_is_a_false_dispatch():
    events = [collapse("I1", [1000, 1000], witness="wit1"),
              declared(60, "hub1-c1"),
              ev(61, "case_located", agent="hub1", case="hub1-c1", location=[2500, 400], by="wit7")]
    assert summarize(events, CFG)["M2_verification"]["false_dispatches"] == 1
