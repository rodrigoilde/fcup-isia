"""Protocolo de orientação (guidanceProtocol) e escolha do passo seguinte (_SelectNextStep, papel R9).

Sequência simplificada de suporte básico de vida para leigos: segurança do local, verificar se
responde, ligar 112, verificar a respiração e depois compressões até alguém assumir. Se a pessoa
não responde mas respira (P2): posição lateral de segurança e vigiar a respiração.
OS12: a app só dá passos desta tabela, nunca um diagnóstico nem uma instrução improvisada.
Desenho em docs/03-detailed-design.md §4.6.
"""

from dataclasses import dataclass, field

VERSION = "bls-lay-v1"


@dataclass(frozen=True)
class Step:
    """Um passo do protocolo.

    Attributes:
        id (str): Identificador do passo.
        text (str): Instrução mostrada ao ajudante.
        expected_s (float): Duração esperada do passo, em segundos.
        cadence_per_min (int | None): Ritmo do metrónomo nas compressões.
    """

    id: str
    text: str
    expected_s: float
    cadence_per_min: int | None = None


STEPS = {
    "SCENE_SAFETY": Step("SCENE_SAFETY", "Make sure the place is safe for you before you approach.", 10),
    "CHECK_RESPONSE": Step("CHECK_RESPONSE", "Tap the shoulders and ask loudly: are you all right?", 10),
    "CALL_112": Step("CALL_112", "Call 112 now and put the phone on speaker.", 30),
    "CHECK_BREATHING": Step("CHECK_BREATHING", "Tilt the head back and look for normal breathing for 10 seconds.",
                            15),
    "COMPRESSIONS": Step("COMPRESSIONS", "Push hard and fast in the centre of the chest, to the beat. Do not stop.",
                         120, 110),
    "RECOVERY_POSITION": Step("RECOVERY_POSITION", "Turn the person on their side and keep checking the breathing.",
                              30),
    "KEEP_WATCHING": Step("KEEP_WATCHING", "Stay with the person and tell me if the breathing stops.", 60),
}

# Resultados que o ajudante pode reportar (P17)
DONE = "DONE"
CANNOT = "CANNOT"
NO_RESPONSE = "NO_RESPONSE"
WOKE_UP = "WOKE_UP"
BREATHING = "BREATHING"
NOT_BREATHING = "NOT_BREATHING"
TIRED = "TIRED"


@dataclass
class GuideState:
    """O que a app sabe sobre o doente e sobre os passos já feitos.

    Attributes:
        responsive (str | None): "yes", "no" ou None (ainda não se sabe).
        breathing (str | None): "yes", "no" ou None.
        called_112 (str | None): "yes", "no" ou None.
        done (set): Passos já concluídos.
        compressing (bool): Se o ajudante está a fazer compressões.
        woke_up (bool): Se a pessoa acordou.
    """

    responsive: str | None = None
    breathing: str | None = None
    called_112: str | None = None
    done: set = field(default_factory=set)
    compressing: bool = False
    woke_up: bool = False

    @classmethod
    def from_triage(cls, triage: dict) -> "GuideState":
        """Começa a partir das respostas já dadas na triagem P04, para não as repetir (P05)."""
        state = cls(triage.get("responsive"), triage.get("breathing_normally"), triage.get("called_112"))
        if triage.get("scene_safe") == "yes":
            state.done.add("SCENE_SAFETY")
        return state

    def apply(self, step: str, result: str) -> None:
        """Atualiza o estado com o resultado de um passo (P17)."""
        self.done.add(step)
        if result == WOKE_UP:
            self.woke_up = True
            self.responsive = "yes"
            self.compressing = False
        elif step == "CHECK_RESPONSE" and result in (NO_RESPONSE, DONE):
            self.responsive = "no"
        elif step == "CHECK_BREATHING":
            self.breathing = "yes" if result == BREATHING else "no"
        elif step == "CALL_112" and result == DONE:
            self.called_112 = "yes"
        elif step == "COMPRESSIONS" and result in (DONE, TIRED):
            self.compressing = True
        elif result == NOT_BREATHING:          # a respiração parou enquanto se vigiava
            self.breathing = "no"
            self.compressing = False


def next_step(state: GuideState) -> Step:
    """Escolhe o passo seguinte do protocolo (_SelectNextStep)."""
    if "SCENE_SAFETY" not in state.done:
        return STEPS["SCENE_SAFETY"]
    if state.woke_up or state.responsive == "yes":
        return STEPS["KEEP_WATCHING"]
    if state.responsive is None:
        return STEPS["CHECK_RESPONSE"]
    if state.called_112 != "yes" and "CALL_112" not in state.done:
        return STEPS["CALL_112"]              # logo que se sabe que não responde
    if state.breathing is None:
        return STEPS["CHECK_BREATHING"]
    if state.breathing == "no":
        return STEPS["COMPRESSIONS"]          # repetido até alguém assumir
    if "RECOVERY_POSITION" not in state.done:
        return STEPS["RECOVERY_POSITION"]
    return STEPS["KEEP_WATCHING"]
