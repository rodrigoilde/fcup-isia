"""Modelo da cidade (recurso roadNetwork): grelha quadrada, deslocações Manhattan e células de Voronoi.

Cada célula pertence a um armário de DAE, o hub dessa célula (decisão D1). A partição só depende de
dados públicos (a grelha e as posições dos DAE), por isso qualquer agente a pode calcular.
"""

import math
from collections import deque

Pos = tuple[float, float]


def manhattan(a: Pos, b: Pos) -> float:
    """Distância Manhattan entre dois pontos, em metros."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class CityGrid:
    """Grelha da cidade dividida em células, uma por hub.

    Attributes:
        size_m (float): Lado da cidade, em metros.
        spacing_m (float): Distância entre cruzamentos da grelha.
        hub_positions (dict[int, Pos]): Posição do armário de cada hub.
        cell_nodes (dict[int, list[Pos]]): Cruzamentos de cada célula.
        neighbours (dict[int, set[int]]): Células vizinhas de cada célula.
    """

    def __init__(self, size_m: float, spacing_m: float, hub_positions: dict[int, Pos]):
        if not hub_positions:
            raise ValueError("at least one hub is needed")
        self.size_m = size_m
        self.spacing_m = spacing_m
        self.hub_positions = dict(hub_positions)
        n = int(round(size_m / spacing_m)) + 1
        node_cell: dict[tuple[int, int], int] = {}
        self.cell_nodes: dict[int, list[Pos]] = {h: [] for h in self.hub_positions}
        for i in range(n):
            for j in range(n):
                pos = (i * spacing_m, j * spacing_m)
                cell = self.cell_of(pos)
                node_cell[(i, j)] = cell
                self.cell_nodes[cell].append(pos)
        self.neighbours = self.find_neighbours(node_cell)
        self.centroids = {cell: self.mean_position(nodes) for cell, nodes in self.cell_nodes.items() if nodes}

    def find_neighbours(self, node_cell: dict[tuple[int, int], int]) -> dict[int, set[int]]:
        """Duas células são vizinhas se têm cruzamentos adjacentes na grelha."""
        neighbours: dict[int, set[int]] = {h: set() for h in self.hub_positions}
        for (i, j), cell in node_cell.items():
            for other in (node_cell.get((i + 1, j)), node_cell.get((i, j + 1))):
                if other is not None and other != cell:
                    neighbours[cell].add(other)
                    neighbours[other].add(cell)
        return neighbours

    @staticmethod
    def mean_position(nodes: list[Pos]) -> Pos:
        """Ponto médio de uma lista de posições."""
        return (sum(p[0] for p in nodes) / len(nodes), sum(p[1] for p in nodes) / len(nodes))

    @property
    def cells(self) -> list[int]:
        """Ids das células, por ordem."""
        return sorted(self.hub_positions)

    def cell_of(self, pos: Pos) -> int:
        """Célula de uma posição: o hub mais próximo (euclidiano); em empate, o de menor id."""
        return min(self.hub_positions, key=lambda h: (math.dist(pos, self.hub_positions[h]), h))

    def centroid(self, cell: int) -> Pos:
        """Centro da célula; os voluntários estimam o ETA até aqui antes de saberem a localização exata."""
        return self.centroids.get(cell, self.hub_positions[cell])

    def ring(self, cell: int, radius: int) -> dict[int, int]:
        """Células a até `radius` saltos de `cell`, com a sua distância em saltos (pesquisa em largura)."""
        dist = {cell: 0}
        queue = deque([cell])
        while queue:
            current = queue.popleft()
            if dist[current] == radius:
                continue
            for nxt in sorted(self.neighbours[current]):
                if nxt not in dist:
                    dist[nxt] = dist[current] + 1
                    queue.append(nxt)
        return dist

    def clamp(self, pos: Pos) -> Pos:
        """Traz uma posição para dentro dos limites da cidade."""
        return (min(max(pos[0], 0.0), self.size_m), min(max(pos[1], 0.0), self.size_m))

    @staticmethod
    def travel_time(a: Pos, b: Pos, mode: dict) -> float:
        """Segundos para ir de a a b num modo de deslocação {"speed": m/s, "overhead_s": s}."""
        distance = manhattan(a, b)
        if distance == 0:
            return 0.0
        return mode.get("overhead_s", 0.0) + distance / mode["speed"]
