"""Unit tests of the pure decision logic: fusion and OS4, Contract Net, disclosure (OS5), AED custody (OS3),
reputation, survival proxy, geometry, network FIFO and trace reproducibility (RNF9)."""

import random

import pytest

from cemr.behaviours.aed_custody import AEDCustody
from cemr.behaviours.contract_net import Offer, assign, best_ambulance, offer_score
from cemr.behaviours.privacy import decide_disclosure
from cemr.behaviours.reputation import TrustTable
from cemr.behaviours.verification import (Belief, SourceView, case_priority, evidence_weight, os4_branch,
                                          should_declare)
from cemr.config import load_config
from cemr.protocol import messages
from cemr.protocol.ontology import AEDState, Priority, Protocol
from cemr.sim.clock import SimClock
from cemr.sim.geometry import CityGrid
from cemr.sim.incidents import generate_layout, generate_trace, trace_hash
from cemr.sim.network import NetworkModel
from cemr.sim.patient import PatientState, estimated_survival, larsen_survival

CFG = load_config("c1")
V = CFG["verification"]
LR = V["likelihood_ratio"]


def belief_after(*items):
    b = Belief(V["prior"])
    for kind, conf in items:
        b.add("s", kind, LR[kind], conf)
    return b.probability


# --- D5 fusion and OS4 -------------------------------------------------------------------------
def test_calibration_targets():
    assert belief_after(("sensor_alert", 0.8), ("wearer_no_response", 1)) >= V["tau_declare"]["P1"]
    assert belief_after(("sensor_alert", 0.68), ("wearer_no_response", 1)) >= V["tau_declare"]["P2"]
    assert belief_after(("sensor_alert", 0.9), ("wearer_ok", 1)) < V["discard_below"]
    assert belief_after(("witness_report", 0.8), ("triage_p1", 1)) >= V["tau_declare"]["P1"]
    assert belief_after(("sensor_alert", 0.9)) < V["tau_declare"]["P1"]          # a lone alert is not enough


def test_evidence_weight_is_bounded():
    assert evidence_weight(0.5, 0.5) == 1.0
    assert evidence_weight(1.0, 0.5) == 2.0
    assert evidence_weight(0.0, 0.5) == 0.0


def test_os4_branches():
    sensor = SourceView("dev1", "sensor", 0.5, positive=True, event_type="collapse_cardiac")
    assert os4_branch([sensor], 0.4) is None                                    # automatic alert alone
    sensor.wearer_no_response = True
    assert os4_branch([sensor], 0.4) == "automatic_alert_no_response"
    witness = SourceView("wit1", "witness", 0.5, positive=True, event_type="witness_collapse",
                         triage={"responsive": "no", "breathing_normally": "no"})
    assert os4_branch([witness], 0.4) == "reliable_human"
    witness.trust = 0.2                                                         # known unreliable
    assert os4_branch([witness], 0.4) is None
    assert os4_branch([sensor, witness], 0.4) == "independent_sources"
    sensor.cancelled = True
    assert os4_branch([sensor, witness], 0.4) is None


def test_os4_blocks_declaration_even_with_high_belief():
    assert not should_declare(0.99, Priority.P1, V["tau_declare"], None)
    assert should_declare(0.61, Priority.P1, V["tau_declare"], "reliable_human")
    assert not should_declare(0.61, Priority.P2, V["tau_declare"], "reliable_human")


def test_witness_cannot_downgrade_an_uncancelled_sensor():
    sensor = SourceView("dev1", "sensor", 0.5, positive=True, event_type="collapse_cardiac")
    witness = SourceView("wit1", "witness", 0.5, positive=True, event_type="witness_collapse",
                         triage={"responsive": "yes", "breathing_normally": "yes"})
    assert case_priority([witness]) == Priority.P3
    assert case_priority([sensor, witness]) == Priority.P1
    sensor.cancelled = True                                                     # wearer said "I'm fine"
    assert case_priority([sensor, witness]) == Priority.P3


def test_incoherent_triage_is_ignored():
    witness = SourceView("wit1", "witness", 0.5, positive=True, event_type="witness_collapse",
                         triage={"responsive": "yes", "breathing_normally": "no"})
    assert case_priority([witness]) == Priority.P1                              # back to the report's priority


def test_triage_replaces_the_witness_own_provisional_priority():
    witness = SourceView("wit1", "witness", 0.5, positive=True, event_type="witness_collapse")
    assert case_priority([witness]) == Priority.P1                              # report alone: worst plausible
    witness.triage = {"responsive": "no", "breathing_normally": "yes"}
    assert case_priority([witness]) == Priority.P2
    sensor = SourceView("dev1", "sensor", 0.5, positive=True, event_type="collapse_cardiac")
    assert case_priority([sensor, witness]) == Priority.P1                      # most severe source wins


# --- D4 Contract Net ---------------------------------------------------------------------------
def score(o):
    return offer_score(o, "BLS", 0.5, 0.5, 1.0)


def test_assign_respects_slots_one_task_per_bidder_and_n_max():
    offers = [Offer("a", "GO_TO_PATIENT", 60, "BLS"), Offer("a", "FETCH_AED", 90, "BLS", aed_id=1),
              Offer("b", "GO_TO_PATIENT", 80, "BLS"), Offer("c", "GO_TO_PATIENT", 70, "BLS"),
              Offer("c", "FETCH_AED", 100, "BLS", aed_id=2)]
    awarded = assign(offers, {"GO_TO_PATIENT": 2, "FETCH_AED": 1}, 4, score)
    assert [(o.bidder, o.task) for o in awarded] == [("a", "GO_TO_PATIENT"), ("c", "GO_TO_PATIENT")]
    assert len(assign(offers, {"GO_TO_PATIENT": 2, "FETCH_AED": 1}, 1, score)) == 1


def test_score_penalises_low_qualification_and_low_trust():
    base = Offer("x", "GO_TO_PATIENT", 100, "BLS")
    assert score(Offer("x", "GO_TO_PATIENT", 100, "NONE")) == pytest.approx(150)
    assert score(Offer("x", "GO_TO_PATIENT", 100, "BLS", trust=0.25)) == pytest.approx(200)
    assert score(base) == pytest.approx(100)


def test_best_ambulance_orders_by_eta():
    assert best_ambulance({"ems1": 300, "ems0": 120, "ems2": 120}) == ["ems0", "ems2", "ems1"]


# --- D7 / OS5 disclosure -----------------------------------------------------------------------
@pytest.mark.parametrize("field,requester,priority,granted", [
    ("precise_location", "hub", "P1", True),
    ("precise_location", "ems", "P2", True),
    ("precise_location", "hub", "P3", False),          # no vital interests, no consent
    ("precise_location", "volunteer", "P1", False),     # volunteers get it only through the award
    ("clinical", "hub", "P1", False),
    ("clinical", "ems", "P1", True),
    ("identity", "bystander", "P1", False),
])
def test_disclosure_policy(field, requester, priority, granted):
    assert decide_disclosure(field, requester, priority).granted is granted


def test_no_disclosure_after_case_closed():
    assert not decide_disclosure("precise_location", "hub", "P1", case_active=False).granted


# --- OS3 AED custody ---------------------------------------------------------------------------
def test_aed_single_reservation_and_token_check():
    aed = AEDCustody(3, faulty=False, rng=random.Random(1))
    ok, ref = aed.reserve("c1", "tok", 900, now=0)
    assert ok and aed.state == AEDState.RESERVED
    assert aed.reserve("c2", "tok2", 900, now=1) == (False, "reserved")          # OS3
    assert aed.retrieve(ref, "wrong", now=2) == (False, "invalid_reservation")
    ok, code = aed.retrieve(ref, "tok", now=3)
    assert ok and len(code) == 6 and aed.state == AEDState.IN_USE
    assert aed.retrieve(ref, "tok", now=4)[0] is False                            # single use
    assert aed.release(ref) == AEDState.UNAVAILABLE
    assert aed.restock() == AEDState.AVAILABLE


def test_aed_reservation_expires_and_faulty_aed_fails():
    aed = AEDCustody(1, faulty=False, rng=random.Random(1))
    aed.reserve("c1", "t", 60, now=0)
    assert aed.reserve("c2", "t", 60, now=61)[0]                                  # expired -> free again
    broken = AEDCustody(2, faulty=True, rng=random.Random(1))
    _, ref = broken.reserve("c1", "t", 60, now=0)
    assert broken.retrieve(ref, "t", now=1) == (False, "missing_or_faulty")
    assert broken.state == AEDState.UNAVAILABLE


# --- D6 reputation -----------------------------------------------------------------------------
def test_beta_reputation():
    table = TrustTable()
    assert table.trust("new") == 0.5                                              # OS13: prior
    table.update("good", True)
    table.update("bad", False)
    assert table.trust("good") > 0.5 > table.trust("bad")
    assert 0.0 <= table.trust("bad") <= 1.0
    assert TrustTable(enabled=False).trust("good") == 0.5


# --- M6 survival proxy -------------------------------------------------------------------------
def test_larsen():
    assert larsen_survival(0, 0, 0) == 67
    assert larsen_survival(2, 5, 10) == pytest.approx(67 - 4.6 - 5.5 - 21)
    assert larsen_survival(30, 30, 30) == 0


def test_survival_uses_ems_when_nobody_helped():
    p = PatientState("I1", "P1", True, collapse_t=0, pos=(0, 0), ems_arrival_t=600)
    # CPR at 10 min, shock at 11 min, ALS at 10 min
    assert estimated_survival(p) == pytest.approx(67 - 23 - 12.1 - 21)
    p.cpr_start_t, p.first_shock_t = 120, 240
    assert estimated_survival(p) == pytest.approx(67 - 4.6 - 4.4 - 21)
    assert estimated_survival(PatientState("I2", "P2", False, 0, (0, 0))) is None


# --- environment ---------------------------------------------------------------------------------
def test_cells_partition_and_neighbours():
    layout = generate_layout(CFG, random.Random("1/layout"))
    grid = CityGrid(3000, 100, layout.hub_positions)
    assert sum(len(n) for n in grid.cell_nodes.values()) == 31 * 31
    for cell, neighbours in grid.neighbours.items():
        assert cell not in neighbours
        assert all(cell in grid.neighbours[n] for n in neighbours)
        assert grid.cell_of(grid.hub_positions[cell]) == cell
    assert len(grid.ring(0, 2)) >= len(grid.ring(0, 1)) > 1


def test_trace_is_reproducible():
    def make(seed):
        layout = generate_layout(CFG, random.Random(f"{seed}/layout"))
        grid = CityGrid(3000, 100, layout.hub_positions)
        return trace_hash(generate_trace(CFG, layout, grid, random.Random(f"{seed}/trace"), 3600))
    assert make(1) == make(1)
    assert make(1) != make(2)


def test_network_keeps_fifo_per_link():
    class FakeWorld:
        def cell_of_agent(self, name):
            return 0
    net = NetworkModel(CFG, random.Random(5), SimClock(10), FakeWorld())     # clock not started: now = 0
    delays = [net.decide("a", "b").delay_s for _ in range(200)]
    assert all(later > earlier for earlier, later in zip(delays, delays[1:]))
    assert net.decide("b", "a").delay_s < max(delays)                         # other links are independent
    assert net.decide("a", "a").delay_s == 0


# --- message schemas -----------------------------------------------------------------------------
def test_every_protocol_has_payloads_and_they_roundtrip():
    payloads = messages.all_payloads()
    assert {p.PROTOCOL for p in payloads} == set(Protocol)
    for cls in payloads:
        kwargs = {}
        for name, typ, _ in messages.field_docs(cls):
            default = cls.__dataclass_fields__[name].default
            if default is not messages.MISSING:
                continue
            factory = cls.__dataclass_fields__[name].default_factory
            if factory is not messages.MISSING:
                continue
            kwargs[name] = {"int": 1, "float": 1.5, "str": "x", "bool": True, "list": [1, 2], "dict": {"a": 1}}.get(
                typ, "x")
        obj = cls(**kwargs)
        assert messages.decode(messages.encode(obj)) == obj
        assert cls.PERFORMATIVES, cls.__name__
