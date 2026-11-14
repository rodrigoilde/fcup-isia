"""Ordenação das propostas e adjudicação do Contract Net (decisão D4, protocolos P08-P10).

Segue o Contract Net (Smith, 1980; especificação FIPA SC00029H): o hub anuncia as tarefas (cfp),
os voluntários propõem um ETA (propose) e o hub adjudica as melhores propostas (accept-proposal).
A pontuação de uma proposta é

    score = ETA * (1 + penalização se abaixo da qualificação pedida) / (confiança / confiança_prior) ** beta

e quanto menor, melhor. Uma reputação baixa traduz-se numa chegada esperada mais tarde, não numa
exclusão. Desenho em docs/03-detailed-design.md §4.2.
"""

from dataclasses import dataclass

from ..protocol.ontology import Qualification, TaskType


@dataclass(frozen=True)
class Offer:
    """Uma proposta de um voluntário para uma tarefa.

    Attributes:
        bidder (str): Pseudónimo do voluntário.
        task (str): GO_TO_PATIENT ou FETCH_AED.
        eta_s (float): ETA estimado pela app do voluntário, em segundos.
        qualification (str): Qualificação do voluntário.
        trust (float): Confiança do hub no voluntário.
        aed_id (int | None): DAE a ir buscar, numa proposta FETCH_AED.
    """

    bidder: str
    task: str
    eta_s: float
    qualification: str
    trust: float = 0.5
    aed_id: int | None = None


def offer_score(offer: Offer, min_qualification: str, quality_penalty: float,
                trust_prior: float, trust_exponent: float) -> float:
    """Pontua uma proposta (menor é melhor).

    Args:
        offer (Offer): Proposta a pontuar.
        min_qualification (str): Qualificação pedida para GO_TO_PATIENT.
        quality_penalty (float): Fração somada ao ETA quando o voluntário está abaixo dela.
        trust_prior (float): Confiança de um voluntário desconhecido.
        trust_exponent (float): Expoente beta do fator de confiança.

    Returns:
        float: ETA corrigido pela qualificação e pela confiança.
    """
    score = offer.eta_s
    below = Qualification(offer.qualification).rank < Qualification(min_qualification).rank
    if offer.task == TaskType.GO_TO_PATIENT and below:
        score *= 1.0 + quality_penalty
    trust_factor = max(1e-3, offer.trust / trust_prior) ** trust_exponent
    return score / trust_factor


def assign(offers: list[Offer], slots: dict[str, int], n_max: int, score) -> list[Offer]:
    """Adjudica as tarefas de forma gulosa, das melhores propostas para as piores.

    Cada voluntário fica com uma tarefa no máximo e o total não passa de N_max. A alocação ótima
    seria um problema combinatório; a métrica M9 (distância ao oráculo B0) mede o custo desta escolha.

    Args:
        offers (list[Offer]): Propostas recebidas.
        slots (dict[str, int]): Número de voluntários pedidos por tarefa.
        n_max (int): Máximo de adjudicações.
        score: Função que pontua uma proposta.

    Returns:
        list[Offer]: Propostas adjudicadas, pela ordem de pontuação.
    """
    remaining = {task: count for task, count in slots.items() if count > 0}
    taken: set[str] = set()
    awarded: list[Offer] = []
    for offer in sorted(offers, key=lambda o: (score(o), o.bidder, o.task)):
        if len(awarded) >= n_max:
            break
        if offer.bidder in taken or remaining.get(offer.task, 0) <= 0:
            continue
        if offer.task == TaskType.FETCH_AED and offer.aed_id is None:
            continue
        awarded.append(offer)
        taken.add(offer.bidder)
        remaining[offer.task] -= 1
    return awarded


def best_ambulance(proposals: dict[str, float]) -> list[str]:
    """Ordena as ambulâncias por ETA; o nome desempata.

    Args:
        proposals (dict[str, float]): Unidade -> ETA proposto.

    Returns:
        list[str]: Unidades da melhor para a pior.
    """
    return sorted(proposals, key=lambda unit: (proposals[unit], unit))
