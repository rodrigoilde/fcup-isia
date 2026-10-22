"""City model (resource roadNetwork): a square grid, Manhattan travel and a Voronoi partition into cells.

Each cell belongs to one AED cabinet, the hub of that cell (decision D1). The partition only depends
on public data (grid and AED positions), so every agent can compute it locally.
"""

import math
from collections import deque

Pos = tuple[float, float]


def manhattan(a: Pos, b: Pos) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class CityGrid:
    def __init__(self, size_m: float, spacing_m: float, hub_positions: dict[int, Pos]):
        if not hub_positions:
            raise ValueError("at least one hub is needed")
        self.size_m = size_m
        self.spacing_m = spacing_m
        self.hub_positions = dict(hub_positions)
        n = int(round(size_m / spacing_m)) + 1
        self._n = n
        self._node_cell: dict[tuple[int, int], int] = {}
        self.cell_nodes: dict[int, list[Pos]] = {h: [] for h in self.hub_positions}
        for i in range(n):
            for j in range(n):
                pos = (i * spacing_m, j * spacing_m)
                cell = self.cell_of(pos)
                self._node_cell[(i, j)] = cell
                self.cell_nodes[cell].append(pos)
        self.neighbours: dict[int, set[int]] = {h: set() for h in self.hub_positions}
        for (i, j), cell in self._node_cell.items():
            for di, dj in ((1, 0), (0, 1)):
                other = self._node_cell.get((i + di, j + dj))
                if other is not None and other != cell:
                    self.neighbours[cell].add(other)
                    self.neighbours[other].add(cell)
        self._centroids = {
            cell: (sum(p[0] for p in nodes) / len(nodes), sum(p[1] for p in nodes) / len(nodes))
            for cell, nodes in self.cell_nodes.items() if nodes
        }

    @property
    def cells(self) -> list[int]:
        return sorted(self.hub_positions)

    def cell_of(self, pos: Pos) -> int:
        """Nearest hub (Euclidean); ties go to the lowest hub id."""
        return min(self.hub_positions, key=lambda h: (math.dist(pos, self.hub_positions[h]), h))

    def centroid(self, cell: int) -> Pos:
        return self._centroids.get(cell, self.hub_positions[cell])

    def ring(self, cell: int, radius: int) -> dict[int, int]:
        """Cells within `radius` hops of `cell`, mapped to their hop distance (BFS on neighbours)."""
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

    def area_km2(self, cell: int) -> float:
        return len(self.cell_nodes[cell]) * (self.spacing_m / 1000) ** 2

    def clamp(self, pos: Pos) -> Pos:
        return (min(max(pos[0], 0.0), self.size_m), min(max(pos[1], 0.0), self.size_m))

    @staticmethod
    def travel_time(a: Pos, b: Pos, mode: dict) -> float:
        """Seconds to go from a to b with a travel mode {"speed": m/s, "overhead_s": s}."""
        distance = manhattan(a, b)
        if distance == 0:
            return 0.0
        return mode.get("overhead_s", 0.0) + distance / mode["speed"]
