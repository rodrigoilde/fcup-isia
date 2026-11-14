"""Tudo o que um agente precisa da simulação, junto num só objeto, e o arranque dos agentes."""

import asyncio
import random
from dataclasses import dataclass

from ..metrics.eventlog import EventLog
from .clock import SimClock
from .directory import Directory
from .network import NetworkModel
from .world import World


@dataclass
class SimContext:
    """Contexto partilhado por todos os agentes de um run.

    Attributes:
        cfg (dict): Configuração do cenário.
        clock (SimClock): Relógio simulado.
        world (World): Ambiente.
        net (NetworkModel): Modelo de rede.
        log (EventLog): Registo de eventos e de auditoria.
        directory (Directory): Nomes dos agentes.
        seed (int): Seed do run.
        password (str): Palavra-passe XMPP de todos os agentes (servidor local).
        xmpp_port (int): Porta do servidor XMPP.
    """

    cfg: dict
    clock: SimClock
    world: World
    net: NetworkModel
    log: EventLog
    directory: Directory
    seed: int
    password: str = "cemr-sim"
    xmpp_port: int = 5222

    def rng_for(self, name: str) -> random.Random:
        """Gerador aleatório próprio de um agente: a mesma seed e o mesmo nome dão a mesma sequência."""
        return random.Random(f"{self.seed}/{name}")


async def start_with_retry(agent, retries: int) -> Exception | None:
    """Arranca um agente, repetindo se o login falhar.

    O pyjabber deixa cair ligações em rajadas de logins; `Agent.start()` pode ser repetido sem
    problemas (spikes/README.md).

    Returns:
        Exception | None: A última exceção, se todas as tentativas falharem.
    """
    for attempt in range(retries + 1):
        try:
            await agent.start(auto_register=True)
            return None
        except Exception as exc:  # noqa: BLE001 - o login pode falhar de várias formas; guarda-se a última
            if attempt == retries:
                return exc
            await asyncio.sleep(0.2 * 2 ** attempt)
    return None


async def start_agents(agents: list, batch: int, retries: int) -> list[tuple[str, Exception]]:
    """Arranca os agentes em lotes, pela ordem da lista (hubs primeiro, para os registos os encontrarem).

    Returns:
        list[tuple[str, Exception]]: Agentes que não arrancaram e o erro de cada um.
    """
    failures = []
    for i in range(0, len(agents), batch):
        group = agents[i:i + batch]
        results = await asyncio.gather(*(start_with_retry(a, retries) for a in group))
        for agent, error in zip(group, results):
            if error is not None:
                failures.append((str(agent.jid), error))
    return failures
