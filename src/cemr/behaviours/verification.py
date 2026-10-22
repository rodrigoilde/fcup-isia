"""Evidence fusion and the declaration rule (decision D5, organisational rule OS4).

The hub keeps the log-odds of "this candidate is a real incident". Each piece of evidence adds
    weight(trust) * confidence * ln(LR)
where LR is the likelihood ratio of the evidence type (scenarios/defaults.toml) and the weight
scales with the source's trust: a source at the prior trust counts at face value, a fully trusted
one counts double, a distrusted one counts little (min(2, trust / trust_prior)).
"""

import math
from dataclasses import dataclass, field

from ..protocol.ontology import Answer, EventType, Priority, SourceKind, TriageQuestionId


def logit(p: float) -> float:
    return math.log(p / (1.0 - p))


def evidence_weight(trust: float, trust_prior: float) -> float:
    return max(0.0, min(2.0, trust / trust_prior))


@dataclass
class EvidenceItem:
    source: str
    kind: str
    delta: float
    log_odds: float


class Belief:
    def __init__(self, prior: float):
        self.log_odds = logit(prior)
        self.history: list[EvidenceItem] = []

    @property
    def probability(self) -> float:
        return 1.0 / (1.0 + math.exp(-self.log_odds))

    def add(self, source: str, kind: str, lr: float, confidence: float = 1.0, weight: float = 1.0) -> float:
        delta = weight * max(0.0, min(1.0, confidence)) * math.log(lr)
        self.log_odds += delta
        self.history.append(EvidenceItem(source, kind, round(delta, 4), round(self.log_odds, 4)))
        return delta


@dataclass
class SourceView:
    """What the verifier knows about one source of a candidate."""
    name: str
    kind: str                            # sensor | witness
    trust: float
    positive: bool = False               # has given supporting evidence
    cancelled: bool = False              # wearer said "I'm fine" / witness retracted
    wearer_no_response: bool = False
    event_type: str | None = None
    triage: dict = field(default_factory=dict)   # question -> answer
    triage_scored: bool = False

    @property
    def triage_complete(self) -> bool:
        return all(self.triage.get(q) in (Answer.YES, Answer.NO)
                   for q in (TriageQuestionId.RESPONSIVE, TriageQuestionId.BREATHING_NORMALLY))


def triage_incoherent(triage: dict) -> bool:
    """A person who responds but does not breathe normally: at least one answer is wrong (F4)."""
    return (triage.get(TriageQuestionId.RESPONSIVE) == Answer.YES
            and triage.get(TriageQuestionId.BREATHING_NORMALLY) == Answer.NO)


def triage_priority(triage: dict) -> Priority | None:
    if triage_incoherent(triage):
        return None
    responsive = triage.get(TriageQuestionId.RESPONSIVE)
    breathing = triage.get(TriageQuestionId.BREATHING_NORMALLY)
    if responsive == Answer.YES:
        return Priority.P3
    if responsive == Answer.NO and breathing == Answer.NO:
        return Priority.P1
    if responsive == Answer.NO and breathing == Answer.YES:
        return Priority.P2
    return None


def source_priority(source: SourceView) -> Priority | None:
    """A witness's coherent triage replaces its own provisional priority; otherwise the alert's event type."""
    if source.cancelled:
        return None
    if source.kind == SourceKind.WITNESS and source.triage_complete:
        p = triage_priority(source.triage)
        if p is not None:
            return p
    return EventType(source.event_type).provisional_priority if source.event_type else None


def case_priority(sources: list[SourceView]) -> Priority:
    """The most severe priority any active source supports (safety first, RNF5).

    A witness's triage can lower its own report but not another source: a device reporting a cardiac
    collapse whose wearer has not answered keeps the case at P1 even if a witness says "responsive".
    """
    priorities = [p for p in (source_priority(s) for s in sources) if p is not None]
    return min(priorities, key=lambda p: p.rank) if priorities else Priority.P3


def os4_branch(sources: list[SourceView], human_min_trust: float) -> str | None:
    """Which branch of OS4 is satisfied, if any.

    OS4: declare only if (independent sources >= 2) or (a reliable human) or
    (an automatic alert whose wearer did not answer the prompt).
    """
    active = [s for s in sources if s.positive and not s.cancelled]
    if len({s.name for s in active}) >= 2:
        return "independent_sources"
    if any(s.kind == SourceKind.WITNESS and s.trust >= human_min_trust and s.triage_complete for s in active):
        return "reliable_human"
    if any(s.kind == SourceKind.SENSOR and s.wearer_no_response for s in active):
        return "automatic_alert_no_response"
    return None


def should_declare(probability: float, priority: Priority, tau: dict, branch: str | None) -> bool:
    return branch is not None and probability >= tau[str(priority)]
