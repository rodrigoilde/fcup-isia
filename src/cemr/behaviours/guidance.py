"""guidanceProtocol (static, versioned) and the guide's step selection (_SelectNextStep, role R9).

A simplified lay-rescuer BLS sequence: scene safety, check response, call 112, check breathing, then
compressions until help takes over. Unconscious but breathing (P2): recovery position and keep
watching the breathing. OS12: the guide can only issue steps from STEPS, never a diagnosis or an
improvised instruction.
"""

from dataclasses import dataclass, field

VERSION = "bls-lay-v1"


@dataclass(frozen=True)
class Step:
    id: str
    text: str
    expected_s: float
    cadence_per_min: int | None = None


STEPS = {s.id: s for s in (
    Step("SCENE_SAFETY", "Make sure the place is safe for you before you approach.", 10),
    Step("CHECK_RESPONSE", "Tap the shoulders and ask loudly: are you all right?", 10),
    Step("CALL_112", "Call 112 now and put the phone on speaker.", 30),
    Step("CHECK_BREATHING", "Tilt the head back and look for normal breathing for 10 seconds.", 15),
    Step("COMPRESSIONS", "Push hard and fast in the centre of the chest, to the beat. Do not stop.", 120, 110),
    Step("RECOVERY_POSITION", "Turn the person on their side and keep checking the breathing.", 30),
    Step("KEEP_WATCHING", "Stay with the person and tell me if the breathing stops.", 60),
)}

# Feedback results the helper can report (P17)
DONE, CANNOT, NO_RESPONSE, WOKE_UP, BREATHING, NOT_BREATHING, TIRED = (
    "DONE", "CANNOT", "NO_RESPONSE", "WOKE_UP", "BREATHING", "NOT_BREATHING", "TIRED")


@dataclass
class GuideState:
    responsive: str | None = None          # "yes" | "no" | None (unknown)
    breathing: str | None = None
    called_112: str | None = None
    done: set = field(default_factory=set)
    compressing: bool = False
    woke_up: bool = False

    @classmethod
    def from_triage(cls, triage: dict) -> "GuideState":
        """Start from the answers already given in P04, so they are not asked again (P05)."""
        state = cls(triage.get("responsive"), triage.get("breathing_normally"), triage.get("called_112"))
        if triage.get("scene_safe") == "yes":
            state.done.add("SCENE_SAFETY")
        return state

    def apply(self, step: str, result: str) -> None:
        self.done.add(step)
        if result == WOKE_UP:
            self.woke_up, self.responsive, self.compressing = True, "yes", False
        elif step == "CHECK_RESPONSE" and result in (NO_RESPONSE, DONE):
            self.responsive = "no"
        elif step == "CHECK_BREATHING":
            self.breathing = "yes" if result == BREATHING else "no"
        elif step == "CALL_112" and result == DONE:
            self.called_112 = "yes"
        elif step == "COMPRESSIONS" and result in (DONE, TIRED):
            self.compressing = True
        elif result == NOT_BREATHING:                # breathing stopped while being watched
            self.breathing, self.compressing = "no", False


def next_step(state: GuideState) -> Step:
    if "SCENE_SAFETY" not in state.done:
        return STEPS["SCENE_SAFETY"]               # always first
    if state.woke_up or state.responsive == "yes":
        return STEPS["KEEP_WATCHING"]
    if state.responsive is None:
        return STEPS["CHECK_RESPONSE"]
    if state.called_112 != "yes" and "CALL_112" not in state.done:
        return STEPS["CALL_112"]                   # as soon as there is no response
    if state.breathing is None:
        return STEPS["CHECK_BREATHING"]
    if state.breathing == "no":
        return STEPS["COMPRESSIONS"]               # repeated until someone takes over
    if "RECOVERY_POSITION" not in state.done:
        return STEPS["RECOVERY_POSITION"]
    return STEPS["KEEP_WATCHING"]
