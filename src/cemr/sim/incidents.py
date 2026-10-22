"""Scenario layout and incident trace, generated up front from the seed (RNF9).

The layout places AED cabinets, citizen devices, bystanders, volunteers and EMS bases. The trace
lists every stimulus the environment will produce: collapses (ground truth), sensor events
(true and false positives) and witness observations. Generating everything before the run keeps the
ground truth identical for a given seed, whatever the scheduling of the agents.
"""

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass, field

from .geometry import CityGrid, Pos

PRIORITIES = ("P1", "P2", "P3")


@dataclass
class VolunteerProfile:
    pos: Pos
    mode: str
    qualification: str


@dataclass
class Layout:
    hub_positions: dict[int, Pos]
    devices: list[Pos]
    bystanders: list[Pos]
    volunteers: list[VolunteerProfile]
    ems_bases: list[Pos]
    aed_faulty: dict[int, bool]
    aed_closed: dict[int, bool] = field(default_factory=dict)    # locked at night (C4)

    def to_json(self) -> dict:
        data = asdict(self)
        for key in ("hub_positions", "aed_faulty", "aed_closed"):
            data[key] = {str(k): v for k, v in getattr(self, key).items()}
        return data


def _weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    keys = sorted(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def _random_point(rng: random.Random, size: float) -> Pos:
    return (round(rng.uniform(0, size), 1), round(rng.uniform(0, size), 1))


def _place_aeds(rng: random.Random, count: int, size: float, min_distance: float) -> dict[int, Pos]:
    """Rejection sampling with a minimum spacing, relaxed if the city is too crowded."""
    spacing = min_distance
    while True:
        points: list[Pos] = []
        for _ in range(5000):
            if len(points) == count:
                break
            p = _random_point(rng, size)
            if all(math.dist(p, q) >= spacing for q in points):
                points.append(p)
        if len(points) == count:
            return {i: p for i, p in enumerate(points)}
        spacing *= 0.9


def generate_layout(cfg: dict, rng: random.Random) -> Layout:
    size = cfg["city"]["size_m"]
    pop = cfg["population"]
    hubs = _place_aeds(rng, pop["aeds"], size, pop["aed_min_distance_m"])
    devices = [_random_point(rng, size) for _ in range(pop["devices"])]
    bystanders = [_random_point(rng, size) for _ in range(pop["bystanders"])]
    vcfg = cfg["volunteers"]
    volunteers = [
        VolunteerProfile(_random_point(rng, size), _weighted_choice(rng, vcfg["modes"]),
                         _weighted_choice(rng, vcfg["qualification_mix"]))
        for _ in range(pop["volunteers"])
    ]
    ems_bases = [tuple(b) for b in pop["ems_bases"]]
    aed_faulty = {h: rng.random() < cfg["aed"]["p_faulty"] for h in hubs}
    aed_closed = {h: rng.random() < cfg["aed"].get("p_closed", 0.0) for h in hubs}
    return Layout(hubs, devices, bystanders, volunteers, ems_bases, aed_faulty, aed_closed)


def true_sensor_features(priority: str, rng: random.Random) -> dict:
    return {
        "fall": True,
        "immobile": priority in ("P1", "P2"),
        "cardiac": "absent" if priority == "P1" else "present",
        "quality": round(rng.uniform(0.7, 1.0), 2),
    }


def false_positive_features(cfg: dict, rng: random.Random, drifting: bool = False) -> dict:
    p_flag = cfg["sensors"]["drift_p_cardiac_flag"] if drifting else cfg["sensors"]["p_cardiac_flag_on_fp"]
    return {
        "fall": True,
        "immobile": rng.random() < (0.8 if drifting else 0.5),
        "cardiac": "anomalous" if rng.random() < p_flag else "present",
        "quality": round(rng.uniform(0.5, 1.0), 2),
    }


def _point_in_disk(rng: random.Random, centre, radius: float, grid: CityGrid) -> Pos:
    angle, r = rng.uniform(0, 2 * math.pi), radius * math.sqrt(rng.random())
    return tuple(round(c, 1) for c in grid.clamp((centre[0] + r * math.cos(angle), centre[1] + r * math.sin(angle))))


def _wearer_response_delay(cfg: dict, able: bool, rng: random.Random) -> float | None:
    """Seconds until the wearer answers "Are you OK?", or None if they never answer."""
    if not able or rng.random() >= cfg["wearer"]["p_respond_if_able"]:
        return None
    return round(rng.uniform(*cfg["wearer"]["response_delay_s"]), 1)


def _poisson_times(rng: random.Random, rate_per_s: float, horizon: float) -> list[float]:
    times, t = [], 0.0
    if rate_per_s <= 0:
        return times
    while True:
        t += rng.expovariate(rate_per_s)
        if t >= horizon:
            return times
        times.append(round(t, 1))


def generate_trace(cfg: dict, layout: Layout, grid: CityGrid, rng: random.Random, duration_s: float) -> dict:
    icfg = cfg["incidents"]
    specs = []
    for i, spec in enumerate(cfg.get("scripted", {}).get("incidents", []), start=1):
        pos, device = None, None
        if "cell" in spec:                                    # in a given cell (e.g. of a hub about to fail)
            in_cell = [d for d, p in enumerate(layout.devices) if grid.cell_of(p) == spec["cell"]]
            if spec.get("wearer") and in_cell:
                device = rng.choice(in_cell)                  # someone with a wearable who lives there
            else:
                pos = rng.choice(grid.cell_nodes[spec["cell"]])
        specs.append({"id": spec.get("id", f"S{i}"), "t": float(spec["t_s"]), "priority": spec["priority"],
                      "shockable": bool(spec.get("shockable", False)),
                      "wearer": bool(spec.get("wearer", False)) and pos is None, "device": device,
                      "witness": bool(spec.get("witness", False)), "pos": pos,
                      "witness_reports": spec.get("witness_reports")})
    for n, t in enumerate(_poisson_times(rng, icfg["rate_per_hour"] / 3600.0, duration_s), start=1):
        priority = _weighted_choice(rng, icfg["priority_mix"])
        specs.append({"id": f"I{n:03d}", "t": t, "priority": priority,
                      "shockable": priority == "P1" and rng.random() < icfg["p1_shockable"],
                      "wearer": rng.random() < icfg["p_wearer"], "witness": rng.random() < icfg["p_witness"]})
    surge = icfg.get("surge", {})
    for n in range(surge.get("count", 0)):                    # event surge (C3): crowd around a venue
        priority = _weighted_choice(rng, surge.get("priority_mix", icfg["priority_mix"]))
        specs.append({"id": f"U{n + 1:02d}", "t": round(surge["t_s"] + rng.uniform(0, surge["duration_s"]), 1),
                      "priority": priority, "shockable": priority == "P1" and rng.random() < icfg["p1_shockable"],
                      "wearer": False, "witness": rng.random() < surge.get("p_witness", icfg["p_witness"]),
                      "pos": _point_in_disk(rng, surge["centre"], surge["radius_m"], grid)})
    specs.sort(key=lambda s: (s["t"], s["id"]))

    free_devices = list(range(len(layout.devices)))
    witness_busy_until = [0.0] * len(layout.bystanders)
    incidents, stimuli = [], []
    for spec in specs:
        device = None
        if spec.get("device") is not None and spec["device"] in free_devices:
            device = spec["device"]
            free_devices.remove(device)
        elif spec["wearer"] and free_devices:
            device = free_devices.pop(rng.randrange(len(free_devices)))
        pos = layout.devices[device] if device is not None else spec.get("pos") or _random_point(rng, grid.size_m)
        witness = None
        if spec["witness"]:
            free = [b for b, until in enumerate(witness_busy_until) if until <= spec["t"]]
            if free:
                witness = rng.choice(free)
                witness_busy_until[witness] = spec["t"] + icfg["witness_busy_s"]
        witness_pos = None
        if witness is not None:                    # the witness stands 5-15 m from the patient
            angle, dist = rng.uniform(0, 2 * math.pi), rng.uniform(5, 15)
            witness_pos = [round(c, 1) for c in grid.clamp((pos[0] + dist * math.cos(angle),
                                                            pos[1] + dist * math.sin(angle)))]
        incident = {"id": spec["id"], "t": spec["t"], "pos": list(pos), "cell": grid.cell_of(pos),
                    "priority": spec["priority"], "shockable": spec["shockable"],
                    "device": device, "witness": witness, "witness_pos": witness_pos}
        incidents.append(incident)
        stimuli.append({"t": spec["t"], "kind": "collapse", "incident": spec["id"]})
        if witness is not None:
            stimuli.append({"t": spec["t"], "kind": "witness_observe", "bystander": witness,
                            "incident": spec["id"], "will_report": spec.get("witness_reports")})
        if device is not None and rng.random() < cfg["sensors"]["tpr"]:
            stimuli.append({
                "t": round(spec["t"] + rng.uniform(*cfg["sensors"]["detection_delay_s"]), 1),
                "kind": "sensor_event", "device": device, "incident": spec["id"],
                "features": true_sensor_features(spec["priority"], rng),
                "wearer_response_s": _wearer_response_delay(cfg, spec["priority"] == "P3", rng),
            })

    scfg = cfg["sensors"]
    n_drift = scfg.get("drifting_devices", 0)
    drifting = set(rng.sample(range(len(layout.devices)), n_drift)) if n_drift else set()
    for device in range(len(layout.devices)):
        drift = device in drifting                            # F3: sensor drift, many false positives
        rate = (scfg["drift_fp_per_hour"] if drift else scfg["fp_per_device_hour"]) / 3600.0
        for t in _poisson_times(rng, rate, duration_s):
            stimuli.append({"t": t, "kind": "sensor_event", "device": device, "incident": None, "drift": drift,
                            "features": false_positive_features(cfg, rng, drift),
                            "wearer_response_s": _wearer_response_delay(cfg, True, rng)})

    false_rate = cfg["witness"].get("false_report_per_hour", 0.0) / 3600.0
    for bystander in range(len(layout.bystanders)):           # F4: a citizen misreads a scene
        for t in _poisson_times(rng, false_rate, duration_s):
            if all(not (inc["witness"] == bystander and inc["t"] <= t <= inc["t"] + icfg["witness_busy_s"])
                   for inc in incidents):
                stimuli.append({"t": t, "kind": "false_witness", "bystander": bystander,
                                "pos": list(_point_in_disk(rng, layout.bystanders[bystander], 200, grid))})

    stimuli.sort(key=lambda s: (s["t"], s["kind"], str(s.get("device", s.get("bystander", "")))))
    return {"incidents": incidents, "stimuli": stimuli}


def trace_hash(trace: dict) -> str:
    return hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest()[:16]
