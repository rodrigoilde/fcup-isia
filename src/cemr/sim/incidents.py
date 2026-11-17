"""Traço de incidentes, gerado à partida a partir da seed (RNF9).

O traço lista todos os estímulos que o ambiente vai produzir: colapsos (verdade de referência),
eventos de sensor (verdadeiros e falsos positivos) e observações de testemunhas. Gerar tudo antes
do run mantém a verdade de referência igual para a mesma seed, seja qual for o escalonamento dos
agentes. A disposição do cenário está em `layout`. Desenho em docs/03-detailed-design.md §6.
"""

import hashlib
import json
import math
import random

from .geometry import CityGrid, Pos
from .layout import Layout, random_point, weighted_choice


def point_in_disk(rng: random.Random, centre, radius: float, grid: CityGrid) -> Pos:
    """Ponto uniforme num disco, trazido para dentro da cidade."""
    angle = rng.uniform(0, 2 * math.pi)
    r = radius * math.sqrt(rng.random())
    pos = grid.clamp((centre[0] + r * math.cos(angle), centre[1] + r * math.sin(angle)))
    return (round(pos[0], 1), round(pos[1], 1))


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
            able = True
            if drift:            # só se sorteia com deriva, para o traço dos cenários sem deriva não mudar
                able = rng.random() >= scfg["drift_p_no_response"]
            stimuli.append({"t": t, "kind": "sensor_event", "device": device, "incident": None, "drift": drift,
                            "features": false_positive_features(cfg, rng, drift),
                            "wearer_response_s": wearer_response_delay(cfg, able, rng)})
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


def prankster_reports(cfg: dict, layout: Layout, grid: CityGrid, rng: random.Random,
                      duration_s: float, incidents: list[dict]) -> list[dict]:
    """C5: cidadãos reincidentes que reportam colapsos que não aconteceram (fontes não cooperativas).

    Ao contrário dos falsos relatos do F4, que vêm de pessoas diferentes, estes repetem-se, por isso a
    reputação pode aprender a desconfiar deles. Reportam sempre, e a cena parece um P2 (não responde
    mas respira), que sem reputação passa a verificação pelo ramo "humano fiável" da OS4.
    """
    wcfg = cfg["witness"]
    if wcfg["pranksters"] == 0:
        return []
    chosen = sorted(rng.sample(range(len(layout.bystanders)), wcfg["pranksters"]))
    rate = wcfg["prankster_rate_per_hour"] / 3600.0
    stimuli = []
    for bystander in chosen:
        for t in poisson_times(rng, rate, duration_s):
            if busy_witnessing(incidents, bystander, t, cfg["incidents"]["witness_busy_s"]):
                continue
            pos = point_in_disk(rng, layout.bystanders[bystander], wcfg["false_report_radius_m"], grid)
            stimuli.append({"t": t, "kind": "false_witness", "bystander": bystander, "pos": list(pos),
                            "will_report": True, "prankster": True})
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
    stimuli += prankster_reports(cfg, layout, grid, rng, duration_s, incidents)
    stimuli.sort(key=stimulus_order)
    return {"incidents": incidents, "stimuli": stimuli}


def trace_hash(trace: dict) -> str:
    """Resumo do traço; a mesma seed tem de dar o mesmo resumo (RNF9)."""
    return hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest()[:16]
