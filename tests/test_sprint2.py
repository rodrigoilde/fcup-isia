"""Unit tests for sprint 2 logic: guidance step selection (OS12), reputation with gossip and decay (D6),
and the rule checker itself (it must catch violations, not only pass clean runs)."""

from cemr.behaviours import guidance as gp
from cemr.behaviours.reputation import TrustTable
from cemr.config import load_config
from cemr.metrics.check import check

CFG = load_config("c1")


# --- guidanceProtocol -------------------------------------------------------------------------
def test_guidance_starts_with_scene_safety_then_follows_bls():
    state = gp.GuideState()
    assert gp.next_step(state).id == "SCENE_SAFETY"
    state.apply("SCENE_SAFETY", gp.DONE)
    assert gp.next_step(state).id == "CHECK_RESPONSE"
    state.apply("CHECK_RESPONSE", gp.NO_RESPONSE)
    assert gp.next_step(state).id == "CALL_112"
    state.apply("CALL_112", gp.DONE)
    assert gp.next_step(state).id == "CHECK_BREATHING"
    state.apply("CHECK_BREATHING", gp.NOT_BREATHING)
    assert gp.next_step(state).id == "COMPRESSIONS"
    state.apply("COMPRESSIONS", gp.TIRED)
    assert gp.next_step(state).id == "COMPRESSIONS"           # keep going until someone takes over


def test_guidance_reuses_triage_answers():
    state = gp.GuideState.from_triage({"scene_safe": "yes", "responsive": "no", "breathing_normally": "yes",
                                       "called_112": "yes"})
    assert gp.next_step(state).id == "RECOVERY_POSITION"      # P2: no questions repeated
    state.apply("RECOVERY_POSITION", gp.DONE)
    assert gp.next_step(state).id == "KEEP_WATCHING"
    state.apply("KEEP_WATCHING", gp.NOT_BREATHING)            # breathing stopped
    assert gp.next_step(state).id == "COMPRESSIONS"


def test_guidance_only_uses_protocol_steps():
    state = gp.GuideState()
    for result in (gp.DONE, gp.NO_RESPONSE, gp.DONE, gp.NOT_BREATHING, gp.DONE, gp.WOKE_UP, gp.DONE):
        step = gp.next_step(state)
        assert step.id in gp.STEPS                             # OS12
        state.apply(step.id, result)


# --- reputation ---------------------------------------------------------------------------------
def test_peer_recommendations_are_discounted_and_not_reshared():
    a, b = TrustTable(peer_discount=0.5), TrustTable(peer_discount=0.5)
    for _ in range(4):
        b.update("vol1", False)
    a.merge("hub2", b.summary())
    assert a.trust("vol1") == (0 + 1) / (0 + 2 + 2)            # 4 failures count as 2
    assert a.summary() == []                                   # only own counts are gossiped
    a.merge("hub2", [])                                        # a newer summary replaces the old one
    assert a.trust("vol1") == 0.5


def test_decay_moves_back_towards_the_prior():
    t = TrustTable()
    for _ in range(5):
        t.update("dev1", False)
    low = t.trust("dev1")
    for _ in range(50):
        t.decay(0.9)
    assert low < t.trust("dev1") <= 0.5


# --- the rule checker catches violations ----------------------------------------------------------
def ev(t, kind, **kw):
    return {"t": t, "kind": kind, **kw}


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
              ev(1, "case_declared", agent="hub1", case="c1", priority="P1", p=0.8, rule="reliable_human"),
              ev(1.5, "ambulance_requested", agent="hub1", case="c1"),
              ev(2, "award", agent="hub1", case="c1", responder="vol1", task="GO_TO_PATIENT", qualification="BLS"),
              ev(2, "msg", src="hub1", dst="vol1", msg_type="Award", thread="c1", dropped=None, protocol="P09"),
              ev(9, "case_closed", agent="hub1", case="c1", outcome="TRANSPORTED"),
              ev(9, "local_msg", agent="hub1", msg_type="OutcomeLabels", thread="c1", body="{}")]
    assert not any(check(events, CFG).values())
