"""Ambiente (análise §4): rede de ruas, registo de DAE, doentes, posições e perceções.

O World é infraestrutura da simulação, não um papel Gaia. Os agentes só o usam pelos métodos
abaixo, que seguem a matriz ambiente-papéis da análise §5.4:

- os recursos públicos (roadNetwork, aedRegistry) podem ser lidos por todos;
- a entrada de um DAE no registo só é alterada pelo seu hub (AEDCustodian);
- sensorStream e wearerResponse só chegam a um dispositivo pela sua fila de perceções;
- patientCondition só é observada e alterada no local do doente;
- groundTruth vai para o registo de eventos e nunca é mostrada aos agentes.
"""

import asyncio
import random

from ..metrics.eventlog import EventLog
from .clock import SimClock
from .directory import Directory
from .geometry import CityGrid, Pos, manhattan
from .layout import Layout
from .patient import PatientState


def pos_key(pos) -> tuple[float, float]:
    """Chave de dicionário para uma posição, arredondada ao decímetro."""
    return (round(float(pos[0]), 1), round(float(pos[1]), 1))


def flip(value: bool, rng: random.Random, error: float) -> bool:
    """Erro de observação: troca o valor com probabilidade `error`."""
    if rng.random() < error:
        return not value
    return value


class World:
    """Estado do ambiente da simulação.

    Attributes:
        grid (CityGrid): Cidade e células.
        layout (Layout): Disposição inicial.
        aed_registry (dict[int, dict]): Registo público dos DAE: id -> {pos, state}.
        patients (dict[str, PatientState]): Doentes por incidente.
    """

    def __init__(self, cfg: dict, grid: CityGrid, layout: Layout, clock: SimClock, log: EventLog):
        self.cfg = cfg
        self.grid = grid
        self.layout = layout
        self.clock = clock
        self.log = log
        self.aed_registry: dict[int, dict] = {}
        for hub, pos in layout.hub_positions.items():
            self.aed_registry[hub] = {"pos": pos, "state": "AVAILABLE"}
        self.patients: dict[str, PatientState] = {}
        self.patient_by_pos: dict[tuple[float, float], str] = {}
        self.positions: dict[str, Pos] = {}
        self.moves: dict[str, tuple[Pos, Pos, float, float]] = {}
        self.queues: dict[str, asyncio.Queue] = {}
        self.wearer_responses: dict[str, float | None] = {}
        self.phantoms: dict[tuple[float, float], dict] = {}     # cenas mal interpretadas (falsos relatos)

    # --- agentes e deslocações -----------------------------------------------------------------
    def register(self, name: str, pos: Pos, kind: str) -> None:
        """Coloca um agente no mapa."""
        self.positions[name] = tuple(pos)
        self.queues.setdefault(name, asyncio.Queue())
        self.log.write("agent", agent=name, agent_kind=kind, pos=[round(c, 1) for c in pos])

    def position(self, name: str) -> Pos:
        """Posição atual de um agente, interpolada se estiver a deslocar-se."""
        move = self.moves.get(name)
        if move is None:
            return self.positions[name]
        start, end, t0, t1 = move
        now = self.clock.now()
        if now >= t1:
            self.positions[name] = end
            del self.moves[name]
            return end
        if now <= t0:                       # ainda a preparar-se (por exemplo a ativação da ambulância)
            return start
        f = (now - t0) / (t1 - t0)
        return (start[0] + f * (end[0] - start[0]), start[1] + f * (end[1] - start[1]))

    def cell_of_agent(self, name: str) -> int:
        """Célula onde o agente está agora."""
        return self.grid.cell_of(self.position(name))

    def start_move(self, name: str, dest: Pos, mode: dict, delay_s: float = 0.0) -> float:
        """Começa uma deslocação até `dest` e devolve o instante simulado de chegada."""
        start = self.position(name)
        t0 = self.clock.now() + delay_s
        t1 = t0 + self.grid.travel_time(start, dest, mode)
        self.moves[name] = (start, tuple(dest), t0, t1)
        self.log.write("move", agent=name, src=list(start), dst=list(dest), t_start=round(t0, 2),
                       t_arrive=round(t1, 2))
        return t1

    def teleport(self, name: str, pos: Pos) -> None:
        """Põe um agente numa posição, sem deslocação."""
        self.moves.pop(name, None)
        self.positions[name] = tuple(pos)
        now = round(self.clock.now(), 2)
        self.log.write("move", agent=name, src=list(pos), dst=list(pos), t_start=now, t_arrive=now)

    # --- perceções (ambiente -> agente) ----------------------------------------------------------
    def perceptions(self, name: str) -> asyncio.Queue:
        """Fila de perceções de um agente (eventos de sensor, cenas observadas)."""
        return self.queues.setdefault(name, asyncio.Queue())

    def wearer_response(self, device: str) -> float | None:
        """wearerResponse[d]: segundos até o portador responder ao aviso atual (None = silêncio)."""
        return self.wearer_responses.pop(device, None)

    # --- registo de DAE (público; cada entrada só muda pelo seu hub) ------------------------------
    def set_aed_state(self, aed_id: int, state: str, by_hub: int) -> None:
        """Atualiza o estado de um DAE no registo público.

        Raises:
            PermissionError: Se quem muda não é o hub dono do DAE.
        """
        if by_hub != aed_id:
            raise PermissionError(f"hub{by_hub} cannot change the registry entry of AED {aed_id}")
        if self.aed_registry[aed_id]["state"] != state:
            self.aed_registry[aed_id]["state"] = state
            self.log.write("aed_state", aed=aed_id, state=state)

    def aeds_near(self, pos: Pos, count: int) -> list[int]:
        """Os `count` DAE disponíveis mais próximos de `pos`."""
        available = [a for a, entry in self.aed_registry.items() if entry["state"] == "AVAILABLE"]
        available.sort(key=lambda a: (manhattan(self.aed_registry[a]["pos"], pos), a))
        return available[:count]

    # --- doentes (observáveis e alteráveis só no local) -----------------------------------------
    def patient_at(self, pos) -> PatientState | None:
        """O doente em `pos` ou a menos de `city.scene_radius_m` (a testemunha está ao lado do doente)."""
        incident = self.patient_by_pos.get(pos_key(pos))
        if incident:
            return self.patients[incident]
        radius = self.cfg["city"]["scene_radius_m"]
        best = None
        best_dist = 0.0
        for patient in self.patients.values():
            dist = manhattan(patient.pos, pos)
            if dist <= radius and (best is None or dist < best_dist):
                best = patient
                best_dist = dist
        return best

    def observe_patient(self, pos, rng: random.Random, error: float) -> dict | None:
        """O que um cidadão vê no local, com erro de observação; None se não há ninguém."""
        patient = self.patient_at(pos)
        if patient is not None:
            return {"responsive": flip(patient.responsive, rng, error),
                    "breathing_normally": flip(patient.breathing_normally, rng, error)}
        phantom = self.phantoms.get(pos_key(pos))    # alguém a dormir ou embriagado parece inconsciente
        if phantom is None:
            return None
        return {key: flip(value, rng, error) for key, value in phantom.items()}

    def act_start_cpr(self, pos, actor: str) -> bool:
        """Começa a RCP; devolve True se o doente precisa dela."""
        patient = self.patient_at(pos)
        if patient is None or not patient.needs_cpr:
            return False
        if patient.cpr_start_t is None:
            patient.cpr_start_t = self.clock.now()
            self.log.write("cpr_started", incident=patient.incident_id, by=actor)
        return True

    def act_attach_aed(self, pos, actor: str) -> dict:
        """Coloca o DAE e dá um choque se o ritmo for desfibrilhável."""
        patient = self.patient_at(pos)
        if patient is None:
            return {"attached": False, "shock": False}
        if patient.aed_attached_t is None:
            patient.aed_attached_t = self.clock.now()
            self.log.write("aed_attached", incident=patient.incident_id, by=actor)
        shock = patient.needs_cpr and patient.shockable
        if shock:
            patient.shocks += 1
            if patient.first_shock_t is None:
                patient.first_shock_t = self.clock.now()
            self.log.write("shock", incident=patient.incident_id, by=actor, n=patient.shocks)
        return {"attached": True, "shock": shock}

    def act_ems_arrive(self, pos, unit: str) -> bool:
        """Chegada da ambulância; devolve True se encontrou um doente."""
        patient = self.patient_at(pos)
        if patient is None:
            self.log.write("ems_arrived", incident=None, by=unit, pos=list(pos))
            return False
        if patient.ems_arrival_t is None:
            patient.ems_arrival_t = self.clock.now()
        self.log.write("ems_arrived", incident=patient.incident_id, by=unit, pos=list(pos))
        return True

    # --- motor do ambiente ------------------------------------------------------------------------
    async def run(self, trace: dict) -> None:
        """Entrega os estímulos do traço às horas marcadas."""
        incidents = {inc["id"]: inc for inc in trace["incidents"]}
        for stimulus in trace["stimuli"]:
            await self.clock.sleep_until(stimulus["t"])
            kind = stimulus["kind"]
            if kind == "collapse":
                self.collapse(incidents[stimulus["incident"]])
            elif kind == "witness_observe":
                self.witness_observes(stimulus, incidents[stimulus["incident"]])
            elif kind == "false_witness":
                self.false_witness(stimulus)
            elif kind == "sensor_event":
                self.sensor_event(stimulus)

    def collapse(self, inc: dict) -> None:
        """Um doente cai: entra no mapa e na verdade de referência."""
        patient = PatientState(inc["id"], inc["priority"], inc["shockable"], self.clock.now(), tuple(inc["pos"]))
        self.patients[inc["id"]] = patient
        self.patient_by_pos[pos_key(inc["pos"])] = inc["id"]
        device = None if inc["device"] is None else Directory.device(inc["device"])
        witness = None if inc["witness"] is None else Directory.bystander(inc["witness"])
        self.log.write("gt_collapse", incident=inc["id"], pos=inc["pos"], cell=inc["cell"],
                       priority=inc["priority"], shockable=inc["shockable"], device=device, witness=witness)

    def witness_observes(self, stimulus: dict, inc: dict) -> None:
        """Um cidadão vê o colapso e fica junto ao doente."""
        name = Directory.bystander(stimulus["bystander"])
        self.teleport(name, tuple(inc["witness_pos"] or inc["pos"]))
        self.perceptions(name).put_nowait({"type": "observe_collapse", "pos": inc["pos"], "t": self.clock.now(),
                                           "will_report": stimulus.get("will_report")})

    def false_witness(self, stimulus: dict) -> None:
        """Um cidadão interpreta mal uma cena (F4): não responde mas respira."""
        name = Directory.bystander(stimulus["bystander"])
        self.teleport(name, tuple(stimulus["pos"]))
        self.phantoms[pos_key(stimulus["pos"])] = {"responsive": False, "breathing_normally": True}
        self.log.write("gt_false_witness", witness=name, pos=stimulus["pos"])
        self.perceptions(name).put_nowait({"type": "observe_collapse", "pos": stimulus["pos"], "t": self.clock.now(),
                                           "will_report": stimulus.get("will_report")})

    def sensor_event(self, stimulus: dict) -> None:
        """Um dispositivo deteta um evento, verdadeiro ou falso positivo."""
        name = Directory.device(stimulus["device"])
        self.wearer_responses[name] = stimulus["wearer_response_s"]
        if stimulus["incident"] is None:
            self.log.write("gt_false_alarm", device=name, drift=stimulus.get("drift", False))
        self.perceptions(name).put_nowait({"type": "sensor_event", "features": stimulus["features"],
                                           "t": self.clock.now()})
