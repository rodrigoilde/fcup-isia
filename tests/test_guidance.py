"""Testes do protocolo de orientação da testemunha (OS12)."""

from cemr.behaviours import guidance as gp


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


def test_compressions_go_on_until_someone_takes_over():
    state = gp.GuideState(responsive="no", breathing="no", called_112="yes", done={"SCENE_SAFETY"})
    state.apply("COMPRESSIONS", gp.TIRED)
    assert gp.next_step(state).id == "COMPRESSIONS"


def test_guidance_reuses_triage_answers():
    state = gp.GuideState.from_triage({"scene_safe": "yes", "responsive": "no", "breathing_normally": "yes",
                                       "called_112": "yes"})
    assert gp.next_step(state).id == "RECOVERY_POSITION"         # P2: nenhuma pergunta repetida
    state.apply("RECOVERY_POSITION", gp.DONE)
    assert gp.next_step(state).id == "KEEP_WATCHING"


def test_breathing_that_stops_leads_back_to_compressions():
    state = gp.GuideState.from_triage({"scene_safe": "yes", "responsive": "no", "breathing_normally": "yes",
                                       "called_112": "yes"})
    state.apply("RECOVERY_POSITION", gp.DONE)
    state.apply("KEEP_WATCHING", gp.NOT_BREATHING)
    assert gp.next_step(state).id == "COMPRESSIONS"


def test_guidance_only_uses_protocol_steps():
    state = gp.GuideState()
    for result in (gp.DONE, gp.NO_RESPONSE, gp.DONE, gp.NOT_BREATHING, gp.DONE, gp.WOKE_UP, gp.DONE):
        step = gp.next_step(state)
        assert step.id in gp.STEPS                                 # OS12
        state.apply(step.id, result)
