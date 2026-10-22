"""Environment (analysis §4): road network, AED registry, patients, positions and perceptions.

The World is simulation infrastructure, not a Gaia role. Agents use it only through the methods
below, which follow the environment–role matrix of analysis §5.4:
- public resources (roadNetwork, aedRegistry) can be read by anyone;
- an AED's registry entry is changed only by its own hub (AEDCustodian);
- sensorStream and wearerResponse reach a device only through its perception queue;
- patientCondition is observed and changed only at the patient's location;
- groundTruth goes to the event log and is never exposed to agents.
"""

import asyncio
import random

from ..metrics.eventlog import EventLog
from .clock import SimClock
from .directory import Directory
from .geometry import CityGrid, Pos
from .incidents import Layout
from .patient import PatientState


def _key(pos) -> tuple[float, float]:
    return (round(float(pos[0]), 1), round(float(pos[1]), 1))


class World:
    def __init__(self, cfg: dict, grid: CityGrid, layout: Layout, clock: SimClock, log: EventLog):
        self.cfg = cfg
        self.grid = grid
        self.layout = layout
        self.clock = clock
        self.log = log
        self.aed_registry: dict[int, dict] = {
            h: {"pos": pos, "state": "AVAILABLE"} for h, pos in layout.hub_positions.items()
        }
        self.patients: dict[str, PatientState] = {}
        self._patient_at: dict[tuple[float, float], str] = {}
        self._positions: dict[str, Pos] = {}
        self._kinds: dict[str, str] = {}
        self._moves: dict[str, tuple[Pos, Pos, float, float]] = {}
        self._perceptions: dict[str, asyncio.Queue] = {}
        self._wearer_response: dict[str, float | None] = {}
        self._phantoms: dict[tuple[float, float], dict] = {}       # misread scenes (false witness reports)

    # --- agents and movement ---------------------------------------------------------------
    def register(self, name: str, pos: Pos, kind: str) -> None:
        self._positions[name] = tuple(pos)
        self._kinds[name] = kind
        self._perceptions.setdefault(name, asyncio.Queue())
        self.log.write("agent", agent=name, agent_kind=kind, pos=[round(c, 1) for c in pos])

    def position(self, name: str) -> Pos:
        move = self._moves.get(name)
        if move is None:
            return self._positions[name]
        start, end, t0, t1 = move
        now = self.clock.now()
        if now >= t1:
            self._positions[name] = end
            del self._moves[name]
            return end
        if now <= t0:                       # still preparing (e.g. ambulance dispatch delay)
            return start
        f = (now - t0) / (t1 - t0) if t1 > t0 else 1.0
        return (start[0] + f * (end[0] - start[0]), start[1] + f * (end[1] - start[1]))

    def cell_of_agent(self, name: str) -> int:
        return self.grid.cell_of(self.position(name))

    def start_move(self, name: str, dest: Pos, mode: dict, delay_s: float = 0.0) -> float:
        """Begin travelling to `dest`; returns the simulated arrival time."""
        start = self.position(name)
        t0 = self.clock.now() + delay_s
        t1 = t0 + self.grid.travel_time(start, dest, mode)
        self._moves[name] = (start, tuple(dest), t0, t1)
        self.log.write("move", agent=name, src=list(start), dst=list(dest), t_start=round(t0, 2),
                       t_arrive=round(t1, 2))
        return t1

    def teleport(self, name: str, pos: Pos) -> None:
        self._moves.pop(name, None)
        self._positions[name] = tuple(pos)
        self.log.write("move", agent=name, src=list(pos), dst=list(pos), t_start=round(self.clock.now(), 2),
                       t_arrive=round(self.clock.now(), 2))

    # --- perceptions (environment -> agent) ---------------------------------------------------
    def perceptions(self, name: str) -> asyncio.Queue:
        return self._perceptions.setdefault(name, asyncio.Queue())

    def wearer_response(self, device: str) -> float | None:
        """wearerResponse[d]: seconds until the wearer answers the current prompt (None = silence)."""
        return self._wearer_response.pop(device, None)

    # --- AED registry (public; each entry changed only by its own hub) -----------------------
    def aed_state(self, aed_id: int) -> str:
        return self.aed_registry[aed_id]["state"]

    def set_aed_state(self, aed_id: int, state: str, by_hub: int) -> None:
        if by_hub != aed_id:
            raise PermissionError(f"hub{by_hub} cannot change the registry entry of AED {aed_id}")
        if self.aed_registry[aed_id]["state"] != state:
            self.aed_registry[aed_id]["state"] = state
            self.log.write("aed_state", aed=aed_id, state=state)

    def aeds_near(self, pos: Pos, count: int, states=("AVAILABLE",)) -> list[int]:
        candidates = [a for a, e in self.aed_registry.items() if e["state"] in states]
        return sorted(candidates, key=lambda a: (abs(self.aed_registry[a]["pos"][0] - pos[0])
                                                 + abs(self.aed_registry[a]["pos"][1] - pos[1]), a))[:count]

    # --- patients (observable and changeable only on scene) ----------------------------------
    def patient_at(self, pos, radius: float = 30.0) -> PatientState | None:
        """The patient at (or within `radius` metres of) pos: a witness's location is next to the patient."""
        incident = self._patient_at.get(_key(pos))
        if incident:
            return self.patients[incident]
        near = [(abs(p.pos[0] - pos[0]) + abs(p.pos[1] - pos[1]), p) for p in self.patients.values()]
        near = [(d, p) for d, p in near if d <= radius]
        return min(near, key=lambda dp: dp[0])[1] if near else None

    def observe_patient(self, pos, rng: random.Random, error: float) -> dict | None:
        flip = lambda value: (not value) if rng.random() < error else value  # noqa: E731
        patient = self.patient_at(pos)
        if patient is None:
            phantom = self._phantoms.get(_key(pos))              # someone asleep, drunk... looks unconscious
            return None if phantom is None else {k: flip(v) for k, v in phantom.items()}
        return {"responsive": flip(patient.responsive), "breathing_normally": flip(patient.breathing_normally)}

    def act_start_cpr(self, pos, actor: str) -> bool:
        patient = self.patient_at(pos)
        if patient is None or not patient.needs_cpr:
            return False
        if patient.cpr_start_t is None:
            patient.cpr_start_t = self.clock.now()
            self.log.write("cpr_started", incident=patient.incident_id, by=actor)
        return True

    def act_attach_aed(self, pos, actor: str) -> dict:
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
        patient = self.patient_at(pos)
        if patient is None:
            self.log.write("ems_arrived", incident=None, by=unit, pos=list(pos))
            return False
        if patient.ems_arrival_t is None:
            patient.ems_arrival_t = self.clock.now()
        self.log.write("ems_arrived", incident=patient.incident_id, by=unit, pos=list(pos))
        return True

    # --- environment driver -------------------------------------------------------------------
    async def run(self, trace: dict) -> None:
        incidents = {inc["id"]: inc for inc in trace["incidents"]}
        for stimulus in trace["stimuli"]:
            await self.clock.sleep_until(stimulus["t"])
            kind = stimulus["kind"]
            if kind == "collapse":
                self._collapse(incidents[stimulus["incident"]])
            elif kind == "witness_observe":
                inc = incidents[stimulus["incident"]]
                name = Directory.bystander(stimulus["bystander"])
                self.teleport(name, tuple(inc["witness_pos"] or inc["pos"]))
                self.perceptions(name).put_nowait({"type": "observe_collapse", "pos": inc["pos"],
                                                   "t": self.clock.now(), "will_report": stimulus.get("will_report")})
            elif kind == "false_witness":
                name = Directory.bystander(stimulus["bystander"])
                self.teleport(name, tuple(stimulus["pos"]))
                self._phantoms[_key(stimulus["pos"])] = {"responsive": False, "breathing_normally": True}
                self.log.write("gt_false_witness", witness=name, pos=stimulus["pos"])
                self.perceptions(name).put_nowait({"type": "observe_collapse", "pos": stimulus["pos"],
                                                   "t": self.clock.now()})
            elif kind == "sensor_event":
                name = Directory.device(stimulus["device"])
                self._wearer_response[name] = stimulus["wearer_response_s"]
                if stimulus["incident"] is None:
                    self.log.write("gt_false_alarm", device=name, drift=stimulus.get("drift", False))
                self.perceptions(name).put_nowait({"type": "sensor_event", "features": stimulus["features"],
                                                   "t": self.clock.now()})

    def _collapse(self, inc: dict) -> None:
        patient = PatientState(inc["id"], inc["priority"], inc["shockable"], self.clock.now(), tuple(inc["pos"]))
        self.patients[inc["id"]] = patient
        self._patient_at[_key(inc["pos"])] = inc["id"]
        self.log.write("gt_collapse", incident=inc["id"], pos=inc["pos"], cell=inc["cell"],
                       priority=inc["priority"], shockable=inc["shockable"],
                       device=None if inc["device"] is None else Directory.device(inc["device"]),
                       witness=None if inc["witness"] is None else Directory.bystander(inc["witness"]))
