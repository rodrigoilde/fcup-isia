"""Beta reputation (Jøsang & Ismail, 2002), decision D6 (resource trustTable[i]).

    trust = (α + d·α_rec + 1) / (α + β + d·(α_rec + β_rec) + 2)

α, β count this hub's own labelled outcomes (P21); α_rec, β_rec are the latest summaries received
from each neighbouring hub (P23), summed and discounted by d, the trust in those peers. Everything
decays towards the prior (_DecayTrust). An unknown pseudonym starts at 0.5, so switching pseudonym
gives no advantage (OS13), and a peer's recommendation can never outweigh d times its own counts.
"""


class TrustTable:
    def __init__(self, enabled: bool = True, peer_discount: float = 0.5):
        self.enabled = enabled
        self.peer_discount = peer_discount
        self._alpha: dict[str, float] = {}
        self._beta: dict[str, float] = {}
        self._peers: dict[str, dict[str, tuple[float, float]]] = {}     # peer -> pseudonym -> (α, β)

    def _recommended(self, pseudonym: str) -> tuple[float, float]:
        a = sum(entries.get(pseudonym, (0.0, 0.0))[0] for entries in self._peers.values())
        b = sum(entries.get(pseudonym, (0.0, 0.0))[1] for entries in self._peers.values())
        return self.peer_discount * a, self.peer_discount * b

    def trust(self, pseudonym: str) -> float:
        if not self.enabled:
            return 0.5
        ra, rb = self._recommended(pseudonym)
        a = self._alpha.get(pseudonym, 0.0) + ra
        b = self._beta.get(pseudonym, 0.0) + rb
        return (a + 1.0) / (a + b + 2.0)

    def observations(self, pseudonym: str) -> float:
        ra, rb = self._recommended(pseudonym)
        return self._alpha.get(pseudonym, 0.0) + self._beta.get(pseudonym, 0.0) + ra + rb

    def update(self, pseudonym: str, success: bool, weight: float = 1.0) -> float:
        table = self._alpha if success else self._beta
        table[pseudonym] = table.get(pseudonym, 0.0) + weight
        return self.trust(pseudonym)

    def decay(self, factor: float) -> None:
        for table in (self._alpha, self._beta):
            for key in list(table):
                table[key] *= factor
                if table[key] < 1e-3:
                    del table[key]

    def summary(self) -> list[dict]:
        """Own counts only (never re-share recommendations, so they do not echo between hubs)."""
        names = sorted(set(self._alpha) | set(self._beta))
        return [{"pseudonym": n, "alpha": round(self._alpha.get(n, 0.0), 4),
                 "beta": round(self._beta.get(n, 0.0), 4)} for n in names]

    def merge(self, peer: str, entries: list[dict]) -> None:
        """Replace the previous summary from `peer` (the latest one already includes its history)."""
        self._peers[peer] = {e["pseudonym"]: (float(e["alpha"]), float(e["beta"])) for e in entries}
