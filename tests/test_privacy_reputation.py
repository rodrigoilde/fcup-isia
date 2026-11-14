"""Testes da política de divulgação (D7, OS5) e da reputação Beta (D6)."""

import pytest

from cemr.behaviours.privacy import decide_disclosure
from cemr.behaviours.reputation import TrustTable


# --- divulgação --------------------------------------------------------------------------------------
@pytest.mark.parametrize("field,requester,priority,granted", [
    ("precise_location", "hub", "P1", True),
    ("precise_location", "ems", "P2", True),
    ("precise_location", "hub", "P3", False),           # sem interesses vitais nem consentimento
    ("precise_location", "volunteer", "P1", False),     # os voluntários só a recebem na adjudicação
    ("clinical", "hub", "P1", False),
    ("clinical", "ems", "P1", True),
    ("identity", "bystander", "P1", False),
])
def test_disclosure_policy(field, requester, priority, granted):
    assert decide_disclosure(field, requester, priority).granted is granted


def test_no_disclosure_after_case_closed():
    assert not decide_disclosure("precise_location", "hub", "P1", case_active=False).granted


# --- reputação ---------------------------------------------------------------------------------------
def test_new_pseudonym_starts_at_the_prior():
    assert TrustTable().trust("new") == 0.5                                     # OS13


def test_outcomes_move_trust_up_and_down():
    table = TrustTable()
    table.update("good", True)
    table.update("bad", False)
    assert table.trust("good") > 0.5 > table.trust("bad") >= 0.0


def test_reputation_off_gives_everyone_the_prior():
    table = TrustTable(enabled=False)
    table.update("bad", False)
    assert table.trust("bad") == 0.5


def test_peer_recommendations_are_discounted_and_not_reshared():
    a, b = TrustTable(peer_discount=0.5), TrustTable(peer_discount=0.5)
    for _ in range(4):
        b.update("vol1", False)
    a.merge("hub2", b.summary())
    assert a.trust("vol1") == (0 + 1) / (0 + 2 + 2)             # 4 falhas contam como 2
    assert a.summary() == []                                     # só as contagens próprias vão no gossip


def test_newer_summary_replaces_the_old_one():
    a, b = TrustTable(), TrustTable()
    b.update("vol1", False)
    a.merge("hub2", b.summary())
    a.merge("hub2", [])
    assert a.trust("vol1") == 0.5


def test_decay_moves_back_towards_the_prior():
    table = TrustTable()
    for _ in range(5):
        table.update("dev1", False)
    low = table.trust("dev1")
    for _ in range(50):
        table.decay(0.9)
    assert low < table.trust("dev1") <= 0.5
