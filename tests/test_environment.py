"""Testes do ambiente e da infraestrutura: cidade, traço (RNF9), C5, rede, sobrevivência e mensagens."""

import json
import random
from dataclasses import MISSING, fields

import pytest
import spade
from spade.message import Message

import cemr
from cemr.agents.base import envelope, not_understood_reply
from cemr.config import load_config
from cemr.protocol import messages
from cemr.protocol.messages_dispatch import CallForProposals
from cemr.protocol.messages_response import ReleaseAck
from cemr.protocol.ontology import Protocol
from cemr.sim.clock import SimClock
from cemr.sim.geometry import CityGrid
from cemr.sim.incidents import generate_trace, trace_hash
from cemr.sim.layout import generate_layout
from cemr.sim.network import NetworkModel
from cemr.sim.patient import PatientState, estimated_survival, larsen_survival

CFG = load_config("c1")


def make_trace(scenario: str, seed: int = 1, overrides: dict | None = None) -> dict:
    cfg = load_config(scenario, overrides)
    layout = generate_layout(cfg, random.Random(f"{seed}/layout"))
    grid = CityGrid(cfg["city"]["size_m"], cfg["city"]["grid_spacing_m"], layout.hub_positions)
    return generate_trace(cfg, layout, grid, random.Random(f"{seed}/trace"), cfg["run"]["duration_s"])


def test_package_imports_with_the_pinned_spade():
    assert cemr.__version__
    assert spade.__version__ == "4.1.4"


# --- cidade e traço ------------------------------------------------------------------------------------
def test_cells_partition_the_grid_and_neighbours_are_symmetric():
    layout = generate_layout(CFG, random.Random("1/layout"))
    grid = CityGrid(3000, 100, layout.hub_positions)
    assert sum(len(n) for n in grid.cell_nodes.values()) == 31 * 31
    for cell, neighbours in grid.neighbours.items():
        assert cell not in neighbours
        assert all(cell in grid.neighbours[n] for n in neighbours)
        assert grid.cell_of(grid.hub_positions[cell]) == cell
    assert len(grid.ring(0, 2)) >= len(grid.ring(0, 1)) > 1


def test_trace_is_reproducible():
    assert trace_hash(make_trace("c1", 1)) == trace_hash(make_trace("c1", 1))
    assert trace_hash(make_trace("c1", 1)) != trace_hash(make_trace("c1", 2))


def test_c5_pranksters_are_two_citizens_who_always_report():
    pranks = [s for s in make_trace("c5")["stimuli"] if s.get("prankster")]
    assert len({s["bystander"] for s in pranks}) == 2
    assert len(pranks) > 2                                     # reincidentes: mais do que um relato cada
    assert all(s["will_report"] for s in pranks)


def test_only_drifting_devices_have_unanswered_false_positives():
    stimuli = make_trace("c2", overrides={"sensors": {"drift_p_no_response": 1.0}})["stimuli"]
    false_positives = [s for s in stimuli if s["kind"] == "sensor_event" and s["incident"] is None]
    assert all(s["wearer_response_s"] is None for s in false_positives if s["drift"])
    assert any(s["wearer_response_s"] is not None for s in false_positives if not s["drift"])


def test_scenarios_without_pranksters_have_none():
    assert not [s for s in make_trace("c1")["stimuli"] if s.get("prankster")]


# --- rede ----------------------------------------------------------------------------------------------
class OneCellWorld:
    def cell_of_agent(self, name: str) -> int:
        return 0


def test_network_keeps_fifo_per_link():
    net = NetworkModel(CFG, random.Random(5), SimClock(10), OneCellWorld())     # relógio parado: now = 0
    delays = [net.decide("a", "b").delay_s for _ in range(200)]
    assert all(later > earlier for earlier, later in zip(delays, delays[1:]))
    assert net.decide("b", "a").delay_s < max(delays)                           # as outras ligações são independentes
    assert net.decide("a", "a").delay_s == 0


# --- aproximação de sobrevivência (M6) ------------------------------------------------------------------
def test_larsen():
    assert larsen_survival(0, 0, 0) == 67
    assert larsen_survival(2, 5, 10) == pytest.approx(67 - 4.6 - 5.5 - 21)
    assert larsen_survival(30, 30, 30) == 0


def test_survival_falls_back_to_the_ems_when_nobody_helped():
    p = PatientState("I1", "P1", True, collapse_t=0, pos=(0, 0), ems_arrival_t=600)
    assert estimated_survival(p, 60) == pytest.approx(67 - 23 - 12.1 - 21)     # RCP aos 10 min, choque aos 11


def test_bystander_cpr_and_aed_raise_survival():
    p = PatientState("I1", "P1", True, collapse_t=0, pos=(0, 0), ems_arrival_t=600, cpr_start_t=120,
                     first_shock_t=240)
    assert estimated_survival(p, 60) == pytest.approx(67 - 4.6 - 4.4 - 21)


def test_survival_is_only_defined_for_shockable_p1():
    assert estimated_survival(PatientState("I2", "P2", False, 0, (0, 0)), 60) is None


# --- mensagens -----------------------------------------------------------------------------------------
def test_every_protocol_but_p22_has_messages_and_they_roundtrip():
    classes = messages.payload_classes()
    assert {cls.PROTOCOL for cls in classes} == set(Protocol)
    samples = {int: 1, float: 1.5, str: "x", bool: True, list: [1, 2], dict: {"a": 1}}
    for cls in classes:
        kwargs = {}
        for f in fields(cls):
            if f.default is MISSING and f.default_factory is MISSING:
                kwargs[f.name] = samples.get(f.type, "x")
        obj = cls(**kwargs)
        assert messages.decode(messages.encode(obj)) == obj
        assert cls.PERFORMATIVES, cls.__name__


def test_call_for_proposals_carries_fipa_reply_by():
    cfp = CallForProposals("hub1-c1", {"GO_TO_PATIENT": 2}, 1, "P1", "BLS", 112.5)
    metadata = envelope(cfp, "cfp", 7)
    assert metadata["reply-by"] == "112.5"
    assert metadata["protocol"] == "P08-CallForResponders" and metadata["ontology"] == "cemr-v1"


def test_messages_without_a_deadline_have_no_reply_by():
    assert "reply-by" not in envelope(ReleaseAck("hub1-c1"), "inform", 8)


def invalid_message() -> Message:
    return Message(to="hub1@localhost", sender="vol3@localhost", thread="hub1-c1", body="{not json",
                   metadata=envelope(ReleaseAck("hub1-c1"), "inform", 4))


def test_not_understood_goes_back_to_the_sender_in_the_same_conversation():
    reply = not_understood_reply(invalid_message(), "JSONDecodeError")
    assert str(reply.to) == "vol3@localhost"
    assert reply.thread == "hub1-c1"
    assert reply.get_metadata("performative") == "not-understood"
    assert reply.get_metadata("protocol") == ReleaseAck.PROTOCOL.value


def test_not_understood_says_why():
    reply = not_understood_reply(invalid_message(), "JSONDecodeError")
    assert json.loads(reply.body) == {"reason": "JSONDecodeError"}
