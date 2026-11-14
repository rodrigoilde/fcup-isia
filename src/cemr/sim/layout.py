"""Disposição do cenário, gerada à partida a partir da seed (RNF9): armários de DAE, dispositivos,
cidadãos, voluntários e bases das ambulâncias. Desenho em docs/03-detailed-design.md §6.
"""

import math
import random
from dataclasses import asdict, dataclass, field

from .geometry import Pos


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
