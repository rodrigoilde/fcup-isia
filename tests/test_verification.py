"""Testes da verificação (D5, OS4): fusão de evidência, prioridade, fusão de alertas e deduplicação P26."""

from cemr.behaviours.privacy import coarse_area
from cemr.behaviours.verification import (Belief, Candidate, SourceView, case_priority, close_areas, evidence_weight,
                                          notice_decision, os4_branch, same_incident, should_declare)
from cemr.config import load_config
from cemr.protocol.ontology import Priority

CFG = load_config("c1")
V = CFG["verification"]
LR = V["likelihood_ratio"]
WINDOW = V["merge_window_s"]
RADIUS = V["merge_radius_m"]
SPACING = CFG["city"]["grid_spacing_m"]


def belief_after(*items) -> float:
    belief = Belief(V["prior"])
    for kind, confidence in items:
        belief.add(LR[kind], confidence)
    return belief.probability


# --- fusão de evidência e OS4 ------------------------------------------------------------------------
def test_calibration_targets():
    # A tabela de calibração de docs/03 §4.1.
    assert belief_after(("sensor_alert", 0.8), ("wearer_no_response", 1)) >= V["tau_declare"]["P1"]
    assert belief_after(("sensor_alert", 0.68), ("wearer_no_response", 1)) >= V["tau_declare"]["P2"]
    assert belief_after(("sensor_alert", 0.9), ("wearer_ok", 1)) < V["discard_below"]
    assert belief_after(("witness_report", 0.8), ("triage_p1", 1)) >= V["tau_declare"]["P1"]


def test_a_lone_sensor_alert_is_not_enough():
    assert belief_after(("sensor_alert", 0.9)) < V["tau_declare"]["P1"]


def test_evidence_weight_is_bounded():
    assert evidence_weight(0.5, 0.5) == 1.0
    assert evidence_weight(1.0, 0.5) == 2.0
    assert evidence_weight(0.0, 0.5) == 0.0


def test_os4_branches():
    sensor = SourceView("dev1", "sensor", 0.5, positive=True, event_type="collapse_cardiac")
    assert os4_branch([sensor], 0.4) is None                                    # alerta automático sozinho
    sensor.wearer_no_response = True
    assert os4_branch([sensor], 0.4) == "automatic_alert_no_response"
    witness = SourceView("wit1", "witness", 0.5, positive=True, event_type="witness_collapse",
                         triage={"responsive": "no", "breathing_normally": "no"})
    assert os4_branch([witness], 0.4) == "reliable_human"
    assert os4_branch([sensor, witness], 0.4) == "independent_sources"


def test_a_distrusted_witness_is_not_a_reliable_human():
    witness = SourceView("wit1", "witness", 0.2, positive=True, event_type="witness_collapse",
                         triage={"responsive": "no", "breathing_normally": "no"})
    assert os4_branch([witness], 0.4) is None


def test_a_cancelled_source_does_not_count_for_os4():
    sensor = SourceView("dev1", "sensor", 0.5, positive=True, event_type="collapse_cardiac", cancelled=True)
    witness = SourceView("wit1", "witness", 0.2, positive=True, event_type="witness_collapse")
    assert os4_branch([sensor, witness], 0.4) is None


def test_os4_blocks_declaration_even_with_high_belief():
    assert not should_declare(0.99, Priority.P1, V["tau_declare"], None)
    assert should_declare(0.61, Priority.P1, V["tau_declare"], "reliable_human")
    assert not should_declare(0.61, Priority.P2, V["tau_declare"], "reliable_human")


# --- prioridade ("a mais grave ganha") -----------------------------------------------------------------
def test_witness_cannot_downgrade_an_uncancelled_sensor():
    sensor = SourceView("dev1", "sensor", 0.5, positive=True, event_type="collapse_cardiac")
    witness = SourceView("wit1", "witness", 0.5, positive=True, event_type="witness_collapse",
                         triage={"responsive": "yes", "breathing_normally": "yes"})
    assert case_priority([witness]) == Priority.P3
    assert case_priority([sensor, witness]) == Priority.P1
    sensor.cancelled = True                                                     # o portador disse "estou bem"
    assert case_priority([sensor, witness]) == Priority.P3


def test_incoherent_triage_is_ignored():
    witness = SourceView("wit1", "witness", 0.5, positive=True, event_type="witness_collapse",
                         triage={"responsive": "yes", "breathing_normally": "no"})
    assert case_priority([witness]) == Priority.P1                              # volta à prioridade do relato


def test_triage_replaces_the_witness_own_provisional_priority():
    witness = SourceView("wit1", "witness", 0.5, positive=True, event_type="witness_collapse")
    assert case_priority([witness]) == Priority.P1                              # relato sozinho: pior plausível
    witness.triage = {"responsive": "no", "breathing_normally": "yes"}
    assert case_priority([witness]) == Priority.P2


# --- fusão de alertas por área (T1.1) ------------------------------------------------------------------
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


# --- deduplicação P26 simétrica (T1.2) -----------------------------------------------------------------
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
