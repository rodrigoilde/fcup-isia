"""Disposição do cenário e traço de incidentes, gerados à partida a partir da seed (RNF9).

A disposição coloca os armários de DAE, os dispositivos, os cidadãos, os voluntários e as bases
das ambulâncias. O traço lista todos os estímulos que o ambiente vai produzir: colapsos (verdade de
referência), eventos de sensor (verdadeiros e falsos positivos) e observações de testemunhas. Gerar
tudo antes do run mantém a verdade de referência igual para a mesma seed, seja qual for o
escalonamento dos agentes. Desenho em docs/03-detailed-design.md §6.
"""

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass, field

from .geometry import CityGrid, Pos


@dataclass
class VolunteerProfile:
    """Perfil de um voluntário.

    Attributes:
        pos (Pos): Posição inicial.
        mode (str): Modo de deslocação (foot, bike, car).
        qualification (str): Qualificação.
    """

    pos: Pos
    mode: str
    qualification: str


@dataclass
class Layout:
    """Disposição dos agentes e dos DAE de um run.

    Attributes:
        hub_positions (dict[int, Pos]): Posição de cada armário de DAE (= hub).
        devices (list[Pos]): Posição de cada dispositivo (do seu portador).
        bystanders (list[Pos]): Posição de cada cidadão.
        volunteers (list[VolunteerProfile]): Perfis dos voluntários.
        ems_bases (list[Pos]): Bases das ambulâncias.
        aed_faulty (dict[int, bool]): DAE em falta ou avariados (F8).
        aed_closed (dict[int, bool]): Armários fechados fora de horas (C4).
    """

    hub_positions: dict[int, Pos]
    devices: list[Pos]
    bystanders: list[Pos]
    volunteers: list[VolunteerProfile]
    ems_bases: list[Pos]
    aed_faulty: dict[int, bool]
    aed_closed: dict[int, bool] = field(default_factory=dict)

    def to_json(self) -> dict:
        """Versão em dicionário, com as chaves inteiras passadas a texto (para o trace.json)."""
        data = asdict(self)
        for key in ("hub_positions", "aed_faulty", "aed_closed"):
            data[key] = {str(k): v for k, v in getattr(self, key).items()}
        return data


def weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    """Escolhe uma chave com probabilidade proporcional ao seu peso."""
    keys = sorted(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def random_point(rng: random.Random, size: float) -> Pos:
    """Ponto uniforme dentro da cidade."""
    return (round(rng.uniform(0, size), 1), round(rng.uniform(0, size), 1))


def point_in_disk(rng: random.Random, centre, radius: float, grid: CityGrid) -> Pos:
    """Ponto uniforme num disco, trazido para dentro da cidade."""
    angle = rng.uniform(0, 2 * math.pi)
    r = radius * math.sqrt(rng.random())
    pos = grid.clamp((centre[0] + r * math.cos(angle), centre[1] + r * math.sin(angle)))
    return (round(pos[0], 1), round(pos[1], 1))


def place_aeds(rng: random.Random, count: int, size: float, min_distance: float) -> dict[int, Pos]:
    """Coloca os DAE por amostragem com rejeição e espaçamento mínimo, relaxado se não couberem."""
    spacing = min_distance
    while True:
        points: list[Pos] = []
        for _ in range(5000):
            if len(points) == count:
                break
            p = random_point(rng, size)
            if all(math.dist(p, q) >= spacing for q in points):
                points.append(p)
        if len(points) == count:
            return dict(enumerate(points))
        spacing *= 0.9


def generate_layout(cfg: dict, rng: random.Random) -> Layout:
    """Gera a disposição do cenário a partir da configuração."""
    size = cfg["city"]["size_m"]
    pop = cfg["population"]
    hubs = place_aeds(rng, pop["aeds"], size, pop["aed_min_distance_m"])
    devices = [random_point(rng, size) for _ in range(pop["devices"])]
    bystanders = [random_point(rng, size) for _ in range(pop["bystanders"])]
    vcfg = cfg["volunteers"]
    volunteers = []
    for _ in range(pop["volunteers"]):
        pos = random_point(rng, size)
        mode = weighted_choice(rng, vcfg["modes"])
        volunteers.append(VolunteerProfile(pos, mode, weighted_choice(rng, vcfg["qualification_mix"])))
    ems_bases = [tuple(b) for b in pop["ems_bases"]]
    aed_faulty = {h: rng.random() < cfg["aed"]["p_faulty"] for h in hubs}
    aed_closed = {h: rng.random() < cfg["aed"]["p_closed"] for h in hubs}
    return Layout(hubs, devices, bystanders, volunteers, ems_bases, aed_faulty, aed_closed)


# --- sinais dos sensores -----------------------------------------------------------------------
def true_sensor_features(cfg: dict, priority: str, rng: random.Random) -> dict:
    """Resumo dos sinais de um colapso real."""
    return {
        "fall": True,
        "immobile": priority in ("P1", "P2"),
        "cardiac": "absent" if priority == "P1" else "present",
        "quality": round(rng.uniform(*cfg["sensors"]["quality_true"]), 2),
    }


def false_positive_features(cfg: dict, rng: random.Random, drifting: bool = False) -> dict:
    """Resumo dos sinais de um falso positivo (F1) ou de um sensor com deriva (F3)."""
    scfg = cfg["sensors"]
    p_immobile = scfg["drift_p_immobile"] if drifting else scfg["p_immobile_on_fp"]
    p_flag = scfg["drift_p_cardiac_flag"] if drifting else scfg["p_cardiac_flag_on_fp"]
    return {
        "fall": True,
        "immobile": rng.random() < p_immobile,
        "cardiac": "anomalous" if rng.random() < p_flag else "present",
        "quality": round(rng.uniform(*scfg["quality_false"]), 2),
    }


def wearer_response_delay(cfg: dict, able: bool, rng: random.Random) -> float | None:
    """Segundos até o portador responder "Está bem?", ou None se nunca responde."""
    if not able or rng.random() >= cfg["wearer"]["p_respond_if_able"]:
        return None
    return round(rng.uniform(*cfg["wearer"]["response_delay_s"]), 1)


def poisson_times(rng: random.Random, rate_per_s: float, horizon: float) -> list[float]:
    """Instantes de um processo de Poisson com a taxa dada, até `horizon`."""
    times = []
    if rate_per_s <= 0:
        return times
    t = rng.expovariate(rate_per_s)
    while t < horizon:
        times.append(round(t, 1))
        t += rng.expovariate(rate_per_s)
    return times


# --- especificação dos incidentes ----------------------------------------------------------------
def scripted_specs(cfg: dict, layout: Layout, grid: CityGrid, rng: random.Random) -> list[dict]:
    """Incidentes com guião (C1 e C4), a horas fixas, por cima do processo de Poisson."""
    specs = []
    for i, spec in enumerate(cfg["scripted"]["incidents"], start=1):
        pos = None
        device = None
        if "cell" in spec:                        # numa célula dada, por exemplo a de um hub que vai falhar
            in_cell = [d for d, p in enumerate(layout.devices) if grid.cell_of(p) == spec["cell"]]
            if spec.get("wearer") and in_cell:
                device = rng.choice(in_cell)      # alguém com um dispositivo que vive lá
            else:
                pos = rng.choice(grid.cell_nodes[spec["cell"]])
        specs.append({"id": spec.get("id", f"S{i}"), "t": float(spec["t_s"]), "priority": spec["priority"],
                      "shockable": bool(spec.get("shockable", False)),
                      "wearer": bool(spec.get("wearer", False)) and pos is None, "device": device,
                      "witness": bool(spec.get("witness", False)), "pos": pos,
                      "witness_reports": spec.get("witness_reports")})
    return specs


def poisson_specs(cfg: dict, rng: random.Random, duration_s: float) -> list[dict]:
    """Incidentes de fundo, com chegadas de Poisson e a mistura de prioridades do cenário."""
    icfg = cfg["incidents"]
    specs = []
    times = poisson_times(rng, icfg["rate_per_hour"] / 3600.0, duration_s)
    for n, t in enumerate(times, start=1):
        priority = weighted_choice(rng, icfg["priority_mix"])
        shockable = priority == "P1" and rng.random() < icfg["p1_shockable"]
        wearer = rng.random() < icfg["p_wearer"]
        witness = rng.random() < icfg["p_witness"]
        specs.append({"id": f"I{n:03d}", "t": t, "priority": priority, "shockable": shockable,
                      "wearer": wearer, "witness": witness})
    return specs


def surge_specs(cfg: dict, grid: CityGrid, rng: random.Random) -> list[dict]:
    """Pico de incidentes à volta de um recinto (C3)."""
    icfg = cfg["incidents"]
    surge = icfg["surge"]
    specs = []
    for n in range(surge.get("count", 0)):
        priority = weighted_choice(rng, surge.get("priority_mix", icfg["priority_mix"]))
        t = round(surge["t_s"] + rng.uniform(0, surge["duration_s"]), 1)
        shockable = priority == "P1" and rng.random() < icfg["p1_shockable"]
        witness = rng.random() < surge.get("p_witness", icfg["p_witness"])
        pos = point_in_disk(rng, surge["centre"], surge["radius_m"], grid)
        specs.append({"id": f"U{n + 1:02d}", "t": t, "priority": priority, "shockable": shockable,
                      "wearer": False, "witness": witness, "pos": pos})
    return specs


# --- colocação dos incidentes e estímulos ----------------------------------------------------------
def pick_device(spec: dict, free_devices: list[int], rng: random.Random) -> int | None:
    """Dispositivo do doente: o do guião, ou um livre ao acaso se o doente usa um."""
    if spec.get("device") is not None and spec["device"] in free_devices:
        free_devices.remove(spec["device"])
        return spec["device"]
    if spec["wearer"] and free_devices:
        return free_devices.pop(rng.randrange(len(free_devices)))
    return None


def pick_witness(spec: dict, busy_until: list[float], witness_busy_s: float, rng: random.Random) -> int | None:
    """Cidadão que vê o colapso, entre os que não estão ocupados com outro incidente."""
    if not spec["witness"]:
        return None
    free = [b for b, until in enumerate(busy_until) if until <= spec["t"]]
    if not free:
        return None
    witness = rng.choice(free)
    busy_until[witness] = spec["t"] + witness_busy_s
    return witness


def witness_position(cfg: dict, pos: Pos, grid: CityGrid, rng: random.Random) -> list[float]:
    """A testemunha fica a alguns metros do doente."""
    angle = rng.uniform(0, 2 * math.pi)
    dist = rng.uniform(*cfg["incidents"]["witness_distance_m"])
    clamped = grid.clamp((pos[0] + dist * math.cos(angle), pos[1] + dist * math.sin(angle)))
    return [round(clamped[0], 1), round(clamped[1], 1)]


def incident_stimuli(cfg: dict, spec: dict, incident: dict, rng: random.Random) -> list[dict]:
    """Estímulos de um incidente: o colapso, a observação da testemunha e a deteção pelo sensor."""
    stimuli = [{"t": spec["t"], "kind": "collapse", "incident": spec["id"]}]
    if incident["witness"] is not None:
        stimuli.append({"t": spec["t"], "kind": "witness_observe", "bystander": incident["witness"],
                        "incident": spec["id"], "will_report": spec.get("witness_reports")})
    if incident["device"] is not None and rng.random() < cfg["sensors"]["tpr"]:
        t = round(spec["t"] + rng.uniform(*cfg["sensors"]["detection_delay_s"]), 1)
        features = true_sensor_features(cfg, spec["priority"], rng)
        response = wearer_response_delay(cfg, spec["priority"] == "P3", rng)
        stimuli.append({"t": t, "kind": "sensor_event", "device": incident["device"], "incident": spec["id"],
                        "features": features, "wearer_response_s": response})
    return stimuli


def place_incidents(cfg: dict, specs: list[dict], layout: Layout, grid: CityGrid,
                    rng: random.Random) -> tuple[list[dict], list[dict]]:
    """Dá posição, dispositivo e testemunha a cada incidente e gera os seus estímulos."""
    free_devices = list(range(len(layout.devices)))
    busy_until = [0.0] * len(layout.bystanders)
    incidents = []
    stimuli = []
    for spec in specs:
        device = pick_device(spec, free_devices, rng)
        if device is not None:
            pos = layout.devices[device]
        else:
            pos = spec.get("pos") or random_point(rng, grid.size_m)
        witness = pick_witness(spec, busy_until, cfg["incidents"]["witness_busy_s"], rng)
        witness_pos = None
        if witness is not None:
            witness_pos = witness_position(cfg, pos, grid, rng)
        incident = {"id": spec["id"], "t": spec["t"], "pos": list(pos), "cell": grid.cell_of(pos),
                    "priority": spec["priority"], "shockable": spec["shockable"],
                    "device": device, "witness": witness, "witness_pos": witness_pos}
        incidents.append(incident)
        stimuli += incident_stimuli(cfg, spec, incident, rng)
    return incidents, stimuli


def false_sensor_events(cfg: dict, layout: Layout, rng: random.Random, duration_s: float) -> list[dict]:
    """Falsos positivos dos sensores (F1), mais frequentes nos dispositivos com deriva (F3)."""
    scfg = cfg["sensors"]
    n_drift = scfg["drifting_devices"]
    drifting = set(rng.sample(range(len(layout.devices)), n_drift)) if n_drift else set()
    stimuli = []
    for device in range(len(layout.devices)):
        drift = device in drifting
        rate = scfg["drift_fp_per_hour"] if drift else scfg["fp_per_device_hour"]
        for t in poisson_times(rng, rate / 3600.0, duration_s):
            stimuli.append({"t": t, "kind": "sensor_event", "device": device, "incident": None, "drift": drift,
                            "features": false_positive_features(cfg, rng, drift),
                            "wearer_response_s": wearer_response_delay(cfg, True, rng)})
    return stimuli


def busy_witnessing(incidents: list[dict], bystander: int, t: float, witness_busy_s: float) -> bool:
    """Se o cidadão está a testemunhar um incidente real no instante t."""
    for inc in incidents:
        if inc["witness"] == bystander and inc["t"] <= t <= inc["t"] + witness_busy_s:
            return True
    return False


def false_witness_reports(cfg: dict, layout: Layout, grid: CityGrid, rng: random.Random,
                          duration_s: float, incidents: list[dict]) -> list[dict]:
    """Cidadãos que interpretam mal uma cena (F4): alguém a dormir parece inconsciente."""
    wcfg = cfg["witness"]
    rate = wcfg["false_report_per_hour"] / 3600.0
    stimuli = []
    for bystander in range(len(layout.bystanders)):
        for t in poisson_times(rng, rate, duration_s):
            if busy_witnessing(incidents, bystander, t, cfg["incidents"]["witness_busy_s"]):
                continue
            pos = point_in_disk(rng, layout.bystanders[bystander], wcfg["false_report_radius_m"], grid)
            stimuli.append({"t": t, "kind": "false_witness", "bystander": bystander, "pos": list(pos)})
    return stimuli


def stimulus_order(stimulus: dict) -> tuple:
    """Ordem dos estímulos: por tempo, tipo e agente."""
    who = stimulus.get("device", stimulus.get("bystander", ""))
    return (stimulus["t"], stimulus["kind"], str(who))


def generate_trace(cfg: dict, layout: Layout, grid: CityGrid, rng: random.Random, duration_s: float) -> dict:
    """Gera o traço completo de um run.

    Returns:
        dict: {"incidents": [...], "stimuli": [...]}, com os estímulos ordenados no tempo.
    """
    specs = scripted_specs(cfg, layout, grid, rng)
    specs += poisson_specs(cfg, rng, duration_s)
    specs += surge_specs(cfg, grid, rng)
    specs.sort(key=lambda s: (s["t"], s["id"]))
    incidents, stimuli = place_incidents(cfg, specs, layout, grid, rng)
    stimuli += false_sensor_events(cfg, layout, rng, duration_s)
    stimuli += false_witness_reports(cfg, layout, grid, rng, duration_s, incidents)
    stimuli.sort(key=stimulus_order)
    return {"incidents": incidents, "stimuli": stimuli}


def trace_hash(trace: dict) -> str:
    """Resumo do traço; a mesma seed tem de dar o mesmo resumo (RNF9)."""
    return hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest()[:16]
