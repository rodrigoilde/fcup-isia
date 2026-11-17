"""Modelo de reputação Beta do papel ReputationManager (decisão D6, recurso trustTable).

    confiança = (a + d * a_rec + 1) / (a + b + d * (a_rec + b_rec) + 2)

a e b contam os resultados rotulados pelo próprio hub (P21). a_rec e b_rec são a soma dos
últimos resumos recebidos de cada hub vizinho (P23), descontados por um d fixo (0,5 em
`scenarios/defaults.toml`): os hubs são infraestrutura instalada e confiam uns nos outros ao nível
do prior, por isso não se mantém uma confiança própria em cada par.
É a média da distribuição Beta com as recomendações descontadas (Jøsang e Ismail, 2002).
As contagens decaem para o prior (_DecayTrust). Um pseudónimo novo começa em 0,5, por isso mudar
de pseudónimo não dá vantagem (OS13). Desenho em docs/03-detailed-design.md §4.5.
"""

MIN_COUNT = 1e-3   # contagens abaixo disto são esquecidas, para a tabela não crescer sem fim


class TrustTable:
    """Tabela de confiança de um hub, por pseudónimo.

    Attributes:
        enabled (bool): Se a reputação está ligada; desligada, todos têm confiança 0,5.
        peer_discount (float): Desconto d aplicado às contagens dos hubs vizinhos.
    """

    def __init__(self, enabled: bool = True, peer_discount: float = 0.5):
        self.enabled = enabled
        self.peer_discount = peer_discount
        self.alpha: dict[str, float] = {}
        self.beta: dict[str, float] = {}
        self.peers: dict[str, dict[str, tuple[float, float]]] = {}   # hub -> pseudónimo -> (a, b)

    def recommended(self, pseudonym: str) -> tuple[float, float]:
        """Soma as contagens dos vizinhos sobre um pseudónimo, já descontadas por d."""
        a = 0.0
        b = 0.0
        for entries in self.peers.values():
            peer_a, peer_b = entries.get(pseudonym, (0.0, 0.0))
            a += peer_a
            b += peer_b
        return self.peer_discount * a, self.peer_discount * b

    def trust(self, pseudonym: str) -> float:
        """Calcula a confiança numa fonte com o modelo de reputação Beta.

        Args:
            pseudonym (str): Pseudónimo da fonte.

        Returns:
            float: Confiança entre 0 e 1 (0,5 quando ainda não há observações).
        """
        if not self.enabled:
            return 0.5
        rec_a, rec_b = self.recommended(pseudonym)
        a = self.alpha.get(pseudonym, 0.0) + rec_a
        b = self.beta.get(pseudonym, 0.0) + rec_b
        return (a + 1.0) / (a + b + 2.0)

    def update(self, pseudonym: str, success: bool, weight: float = 1.0) -> float:
        """Junta um rótulo de resultado (P21) e devolve a nova confiança."""
        table = self.alpha if success else self.beta
        table[pseudonym] = table.get(pseudonym, 0.0) + weight
        return self.trust(pseudonym)

    def decay(self, factor: float) -> None:
        """Multiplica todas as contagens próprias por `factor`, aproximando-as do prior."""
        for table in (self.alpha, self.beta):
            for name in list(table):
                table[name] *= factor
                if table[name] < MIN_COUNT:
                    del table[name]

    def summary(self) -> list[dict]:
        """Resumo para o gossip P23: só as contagens próprias.

        As recomendações recebidas nunca são reenviadas, para não ecoarem entre hubs.
        """
        names = sorted(set(self.alpha) | set(self.beta))
        return [{"pseudonym": n, "alpha": round(self.alpha.get(n, 0.0), 4), "beta": round(self.beta.get(n, 0.0), 4)}
                for n in names]

    def merge(self, peer: str, entries: list[dict]) -> None:
        """Substitui o resumo anterior de um hub vizinho (o mais recente já inclui o histórico)."""
        self.peers[peer] = {}
        for entry in entries:
            self.peers[peer][entry["pseudonym"]] = (float(entry["alpha"]), float(entry["beta"]))
