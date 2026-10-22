"""Ranking and award logic of the Contract Net (decision D4, protocols P08–P10).

score = ETA * (1 + quality_penalty if below the needed qualification) / (trust / trust_prior) ** beta
Lower is better. Low reputation therefore means a later expected arrival, not exclusion.
"""

from dataclasses import dataclass

from ..protocol.ontology import Qualification, TaskType


@dataclass(frozen=True)
class Offer:
    bidder: str
    task: str
    eta_s: float
    qualification: str
    trust: float = 0.5
    aed_id: int | None = None


def offer_score(offer: Offer, min_qualification: str, quality_penalty: float,
                trust_prior: float, trust_exponent: float) -> float:
    score = offer.eta_s
    if (offer.task == TaskType.GO_TO_PATIENT
            and Qualification(offer.qualification).rank < Qualification(min_qualification).rank):
        score *= 1.0 + quality_penalty
    trust_factor = max(1e-3, offer.trust / trust_prior) ** trust_exponent
    return score / trust_factor


def assign(offers: list[Offer], slots: dict[str, int], n_max: int, score) -> list[Offer]:
    """Greedy award: best score first, one task per bidder, per-task slots, at most n_max in total."""
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
    """Units ordered by ETA (name breaks ties)."""
    return [unit for unit, _ in sorted(proposals.items(), key=lambda kv: (kv[1], kv[0]))]
