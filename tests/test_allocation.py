"""Testes da alocação: Contract Net (D4) e custódia do DAE (OS3)."""

import random

import pytest

from cemr.behaviours.aed_custody import AEDCustody
from cemr.behaviours.contract_net import Offer, assign, best_ambulance, offer_score
from cemr.protocol.ontology import AEDState


def score(offer: Offer) -> float:
    return offer_score(offer, "BLS", 0.5, 0.5, 1.0)


# --- Contract Net ------------------------------------------------------------------------------------
def test_assign_respects_slots_and_one_task_per_bidder():
    offers = [Offer("a", "GO_TO_PATIENT", 60, "BLS"), Offer("a", "FETCH_AED", 90, "BLS", aed_id=1),
              Offer("b", "GO_TO_PATIENT", 80, "BLS"), Offer("c", "GO_TO_PATIENT", 70, "BLS"),
              Offer("c", "FETCH_AED", 100, "BLS", aed_id=2)]
    awarded = assign(offers, {"GO_TO_PATIENT": 2, "FETCH_AED": 1}, 4, score)
    assert [(o.bidder, o.task) for o in awarded] == [("a", "GO_TO_PATIENT"), ("c", "GO_TO_PATIENT")]


def test_assign_never_awards_more_than_n_max():
    offers = [Offer("a", "GO_TO_PATIENT", 60, "BLS"), Offer("b", "GO_TO_PATIENT", 80, "BLS")]
    assert len(assign(offers, {"GO_TO_PATIENT": 2}, 1, score)) == 1


def test_score_penalises_low_qualification_and_low_trust():
    assert score(Offer("x", "GO_TO_PATIENT", 100, "BLS")) == pytest.approx(100)
    assert score(Offer("x", "GO_TO_PATIENT", 100, "NONE")) == pytest.approx(150)
    assert score(Offer("x", "GO_TO_PATIENT", 100, "BLS", trust=0.25)) == pytest.approx(200)


def test_best_ambulance_orders_by_eta():
    assert best_ambulance({"ems1": 300, "ems0": 120, "ems2": 120}) == ["ems0", "ems2", "ems1"]


# --- custódia do DAE ---------------------------------------------------------------------------------
def test_aed_has_one_reservation_at_a_time():
    aed = AEDCustody(3, faulty=False, rng=random.Random(1))
    ok, _ = aed.reserve("c1", "tok", 900, now=0)
    assert ok and aed.state == AEDState.RESERVED
    assert aed.reserve("c2", "tok2", 900, now=1) == (False, "reserved")          # OS3


def test_aed_unlock_needs_the_award_token_and_is_single_use():
    aed = AEDCustody(3, faulty=False, rng=random.Random(1))
    _, ref = aed.reserve("c1", "tok", 900, now=0)
    assert aed.retrieve(ref, "wrong", now=2) == (False, "invalid_reservation")
    ok, code = aed.retrieve(ref, "tok", now=3)
    assert ok and len(code) == 6 and aed.state == AEDState.IN_USE
    assert aed.retrieve(ref, "tok", now=4)[0] is False


def test_used_aed_is_out_of_service_until_restocked():
    aed = AEDCustody(3, faulty=False, rng=random.Random(1))
    _, ref = aed.reserve("c1", "tok", 900, now=0)
    aed.retrieve(ref, "tok", now=1)
    assert aed.release(ref) == AEDState.UNAVAILABLE
    assert aed.restock() == AEDState.AVAILABLE


def test_aed_reservation_expires():
    aed = AEDCustody(1, faulty=False, rng=random.Random(1))
    aed.reserve("c1", "t", 60, now=0)
    assert aed.reserve("c2", "t", 60, now=61)[0]


def test_faulty_aed_fails_at_retrieval():
    broken = AEDCustody(2, faulty=True, rng=random.Random(1))
    _, ref = broken.reserve("c1", "t", 60, now=0)
    assert broken.retrieve(ref, "t", now=1) == (False, "missing_or_faulty")
    assert broken.state == AEDState.UNAVAILABLE
