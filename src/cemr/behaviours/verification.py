"""Fusão de evidência e regra de declaração do papel IncidentVerifier (decisão D5, regra OS4).

O hub guarda o log-odds de "este candidato é um incidente real". Cada evidência soma

    peso(confiança na fonte) * confiança local * ln(LR)

em que LR é a razão de verosimilhança do tipo de evidência (`scenarios/defaults.toml`). É a
atualização bayesiana em log-odds, com as evidências tratadas como independentes dado o estado
do doente, como num modelo naive Bayes (Russell e Norvig, 2022, cap. 12).

Desenho em docs/03-detailed-design.md §4.1.
"""

import math
from dataclasses import dataclass, field

from ..protocol.ontology import Answer, EventType, Priority, SourceKind, TriageQuestionId

KEY_QUESTIONS = (TriageQuestionId.RESPONSIVE, TriageQuestionId.BREATHING_NORMALLY)


def logit(p: float) -> float:
    """Converte uma probabilidade em log-odds."""
    return math.log(p / (1.0 - p))


def evidence_weight(trust: float, trust_prior: float) -> float:
    """Calcula o peso de uma evidência a partir da confiança na fonte.

    Uma fonte com a confiança do prior conta pelo valor nominal, uma fonte de confiança total
    conta a dobrar e uma fonte desacreditada quase não conta.

    Args:
        trust (float): Confiança na fonte, entre 0 e 1.
        trust_prior (float): Confiança de uma fonte desconhecida.

    Returns:
        float: trust / trust_prior, limitado ao intervalo [0, 2].
    """
    return max(0.0, min(2.0, trust / trust_prior))


class Belief:
    """Crença do verificador de que o candidato é um incidente real.

    Attributes:
        log_odds (float): Log-odds atual da crença.
    """

    def __init__(self, prior: float):
        self.log_odds = logit(prior)

    @property
    def probability(self) -> float:
        """Probabilidade correspondente ao log-odds atual."""
        return 1.0 / (1.0 + math.exp(-self.log_odds))

    def add(self, lr: float, confidence: float = 1.0, weight: float = 1.0) -> float:
        """Soma uma evidência ao log-odds.

        Args:
            lr (float): Razão de verosimilhança do tipo de evidência.
            confidence (float): Confiança local da fonte; é cortada ao intervalo [0, 1].
            weight (float): Peso dado pela confiança na fonte (ver `evidence_weight`).

        Returns:
            float: Variação do log-odds.
        """
        confidence = max(0.0, min(1.0, confidence))
        delta = weight * confidence * math.log(lr)
        self.log_odds += delta
        return delta


@dataclass
class SourceView:
    """O que o verificador sabe sobre uma fonte de um candidato.

    Attributes:
        name (str): Pseudónimo da fonte.
        kind (str): "sensor" ou "witness".
        trust (float): Confiança na fonte no momento em que apareceu no candidato.
        positive (bool): Se a fonte já deu evidência a favor.
        cancelled (bool): Se o portador disse "estou bem" ou a testemunha retirou o relato.
        wearer_no_response (bool): Se o portador do dispositivo não respondeu ao aviso.
        event_type (str | None): Tipo de evento do alerta da fonte.
        triage (dict): Respostas da triagem P04, pergunta -> resposta.
        triage_scored (bool): Se a triagem completa já foi contada como evidência.
    """

    name: str
    kind: str
    trust: float
    positive: bool = False
    cancelled: bool = False
    wearer_no_response: bool = False
    event_type: str | None = None
    triage: dict = field(default_factory=dict)
    triage_scored: bool = False

    @property
    def triage_complete(self) -> bool:
        """Se as duas perguntas-chave (responde? respira normalmente?) têm resposta sim ou não."""
        return all(self.triage.get(q) in (Answer.YES, Answer.NO) for q in KEY_QUESTIONS)


def triage_incoherent(triage: dict) -> bool:
    """Indica se a triagem é incoerente (modo de falha F4).

    Uma pessoa que responde mas não respira normalmente é impossível: pelo menos uma das respostas
    está errada.
    """
    responsive = triage.get(TriageQuestionId.RESPONSIVE)
    breathing = triage.get(TriageQuestionId.BREATHING_NORMALLY)
    return responsive == Answer.YES and breathing == Answer.NO


def triage_priority(triage: dict) -> Priority | None:
    """Converte uma triagem coerente na prioridade operacional.

    Returns:
        Priority | None: P1 (não responde, não respira), P2 (não responde, respira),
        P3 (responde), ou None se a triagem estiver incompleta ou for incoerente.
    """
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
    """Prioridade que uma fonte suporta.

    A triagem coerente de uma testemunha substitui a prioridade provisória do seu próprio relato.
    Nos outros casos vale a prioridade provisória do tipo de evento do alerta.
    """
    if source.cancelled:
        return None
    if source.kind == SourceKind.WITNESS and source.triage_complete:
        priority = triage_priority(source.triage)
        if priority is not None:
            return priority
    if source.event_type:
        return EventType(source.event_type).provisional_priority
    return None


def case_priority(sources: list[SourceView]) -> Priority:
    """Agrega as prioridades das fontes ativas com a regra "a mais grave ganha" (segurança, RNF5).

    A triagem de uma testemunha pode baixar o seu próprio relato, mas não o de outra fonte: um
    dispositivo que reporta colapso cardíaco sem resposta do portador mantém o caso em P1, mesmo
    que a testemunha diga que a pessoa responde.

    Args:
        sources (list[SourceView]): Fontes do candidato.

    Returns:
        Priority: A prioridade mais grave suportada, ou P3 se nenhuma fonte suporta nenhuma.
    """
    priorities = [source_priority(s) for s in sources]
    priorities = [p for p in priorities if p is not None]
    if not priorities:
        return Priority.P3
    return min(priorities, key=lambda p: p.rank)


def os4_branch(sources: list[SourceView], human_min_trust: float) -> str | None:
    """Indica que ramo da regra OS4 está satisfeito.

    OS4: só se declara um incidente com pelo menos duas fontes independentes, ou com um humano
    fiável, ou com um alerta automático cujo portador não respondeu ao aviso.

    Args:
        sources (list[SourceView]): Fontes do candidato.
        human_min_trust (float): Confiança mínima para uma testemunha contar como humano fiável.

    Returns:
        str | None: "independent_sources", "reliable_human", "automatic_alert_no_response",
        ou None se nenhum ramo se verifica.
    """
    active = [s for s in sources if s.positive and not s.cancelled]
    if len({s.name for s in active}) >= 2:
        return "independent_sources"
    for s in active:
        if s.kind == SourceKind.WITNESS and s.trust >= human_min_trust and s.triage_complete:
            return "reliable_human"
    for s in active:
        if s.kind == SourceKind.SENSOR and s.wearer_no_response:
            return "automatic_alert_no_response"
    return None


def should_declare(probability: float, priority: Priority, tau: dict, branch: str | None) -> bool:
    """Decide a declaração: a crença tem de chegar a tau(prioridade) e um ramo de OS4 tem de valer."""
    return branch is not None and probability >= tau[str(priority)]
