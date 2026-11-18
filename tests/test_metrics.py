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


def declared(t: float, case: str, hub: str = "hub1", sources: list | None = None) -> dict:
    return ev(t, "case_declared", agent=hub, case=case, priority="P1", p=0.9, rule="reliable_human",
              sources=sources or [])


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


def test_false_dispatches_are_split_by_source_kind():
    events = [collapse("I1", [1000, 1000], witness="wit1"),
              declared(60, "hub1-c1", sources=["wit7"]),
              declared(70, "hub1-c2", sources=["dev3"]),
              ev(61, "case_located", agent="hub1", case="hub1-c1", location=[2500, 400], by="wit7"),
              ev(71, "case_located", agent="hub1", case="hub1-c2", location=[400, 2500], by="dev3")]
    m2 = summarize(events, CFG)["M2_verification"]
    assert m2["false_dispatches_witness"] == 1
    assert m2["false_dispatches_sensor_only"] == 1


def alert(t: float, source: str, alert_id: str, dropped: str | None = None) -> dict:
    return ev(t, "msg", src=source, dst="hub1", msg_type="AlertReport", thread=alert_id, dropped=dropped,
              protocol="P01", bytes=10)


def opened(t: float, case: str, alert_id: str, hub: str = "hub1") -> dict:
    return ev(t, "candidate_opened", agent=hub, case=case, alert=alert_id)


def discarded(t: float, case: str, reason: str, priority: str = "P1", keeper: str | None = None) -> dict:
    return ev(t, "candidate_discarded", agent="hub1", case=case, reason=reason, priority=priority, keeper=keeper)


def missed_reasons(events: list[dict]) -> dict[str, str]:
    """Incidente falhado -> motivo, como fica no summary.json."""
    return {m["incident"]: m["reason"] for m in summarize(events, CFG)["M2_missed"]["incidents"]}


def test_missed_separates_incidents_nobody_could_report_from_those_nobody_did():
    events = [collapse("I1", [1000, 1000]), collapse("I2", [2000, 2000], witness="wit2")]
    assert missed_reasons(events) == {"I1": "undetectable", "I2": "not_reported"}


def test_missed_alert_that_never_opened_a_candidate_is_lost():
    events = [collapse("I1", [1000, 1000], witness="wit1"), alert(30, "wit1", "wit1-a1", dropped="loss")]
    assert missed_reasons(events) == {"I1": "alert_lost"}


def test_missed_candidate_lowered_to_p3_by_the_triage():
    events = [collapse("I1", [1000, 1000], witness="wit1"), alert(30, "wit1", "wit1-a1"),
              opened(31, "hub1-c1", "wit1-a1"), discarded(76, "hub1-c1", "window_expired", priority="P3")]
    assert missed_reasons(events) == {"I1": "discarded_as_p3"}


def test_missed_follows_a_p26_merge_to_the_older_candidate():
    events = [collapse("I1", [1000, 1000], witness="wit1"), alert(30, "wit1", "wit1-a1"),
              opened(31, "hub1-c1", "wit1-a1"), discarded(33, "hub1-c1", "merged", keeper="hub2-c1"),
              discarded(76, "hub2-c1", "belief_too_low")]
    assert missed_reasons(events) == {"I1": "discarded_low_belief"}


def test_missed_alert_fused_into_the_case_of_another_patient():
    # Pico do C3: o alerta da testemunha de I2 junta-se ao caso de I1, que fica localizado em I1.
    events = [collapse("I1", [1000, 1000], witness="wit1"), collapse("I2", [1080, 1000], witness="wit2"),
              alert(30, "wit1", "wit1-a1"), alert(35, "wit2", "wit2-a1"),
              opened(31, "hub1-c1", "wit1-a1"), ev(36, "alert_merged", agent="hub1", case="hub1-c1", alert="wit2-a1"),
              declared(60, "hub1-c1"),
              ev(61, "case_located", agent="hub1", case="hub1-c1", location=[1000, 1010], by="wit1")]
    assert missed_reasons(events) == {"I2": "other_incident"}


def test_missed_keeps_the_candidate_that_went_furthest():
    # O primeiro alerta foi descartado; o segundo chegou a ser declarado, mas a localização não chegou.
    events = [collapse("I1", [1000, 1000], witness="wit1", device="dev1"),
              alert(20, "dev1", "dev1-a1"), opened(21, "hub1-c1", "dev1-a1"),
              discarded(40, "hub1-c1", "belief_too_low"),
              alert(50, "wit1", "wit1-a1"), opened(51, "hub1-c2", "wit1-a1"), declared(70, "hub1-c2")]
    assert missed_reasons(events) == {"I1": "not_located"}


def test_missed_counts_have_every_reason_and_add_up_to_the_misses():
    events = [collapse("I1", [1000, 1000]), collapse("I2", [2000, 2000], witness="wit2")]
    missed = summarize(events, CFG)["M2_missed"]
    counts = {reason: n for reason, n in missed.items() if reason != "incidents"}
    assert set(counts) >= {"undetectable", "not_reported", "other_incident"}     # colunas fixas no runs.csv
    assert sum(counts.values()) == len(missed["incidents"]) == 2


def test_m9_dispatch_gap_starts_at_the_declaration():
    oracle = {"I1": {"first_responder_s": 100.0, "aed_s": 200.0, "ems_s": 400.0}}
    events = [collapse("I1", [1000, 1000], witness="wit1"),
              declared(60, "hub1-c1", sources=["wit1"]),
              ev(61, "case_located", agent="hub1", case="hub1-c1", location=[1000, 1010], by="wit1"),
              ev(300, "status", agent="hub1", case="hub1-c1", source="vol1", status="ON_SCENE")]
    m9 = summarize(events, CFG, oracle)["M9_gap_to_oracle_s"]
    assert m9["median"] == 200.0                                # desde o colapso: 300 - 0 - 100
    assert m9["dispatch_median"] == 140.0                       # desde a declaração: 300 - 60 - 100
