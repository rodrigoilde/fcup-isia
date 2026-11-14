"""Dados de um candidato ou caso no hub (recurso incidentCase[c], análise §4.1) e a sua réplica (P27).

Os estados da FSM do caso também estão aqui, porque os usam todos os módulos `case_*`.
Desenho em docs/03-detailed-design.md §2.4.
"""

from dataclasses import asdict, dataclass, field

from ..behaviours.verification import Belief, SourceView
from ..protocol.messages_hubs import CaseSnapshot
from ..protocol.ontology import CaseState, Priority, SourceKind
from ..sim.directory import Directory

VERIFY, DISPATCH, TRACK, CLOSE, DISCARD = "VERIFY", "DISPATCH", "TRACK", "CLOSE", "DISCARD"
TRANSITIONS = ((VERIFY, DISPATCH), (VERIFY, DISCARD), (DISPATCH, TRACK), (DISPATCH, CLOSE), (TRACK, CLOSE))


@dataclass
class AwardInfo:
    """Uma adjudicação a um voluntário.

    Attributes:
        task (str): GO_TO_PATIENT ou FETCH_AED.
        eta_s (float): ETA da proposta.
        aed_id (int | None): DAE a ir buscar.
        status (str): awarded, committed, failed ou released.
        arrive_by (float): ETA + δ; depois disto a adjudicação está em risco (OL6).
        on_scene_t (float | None): Quando chegou ao local.
        late (bool): Se passou de `arrive_by` sem chegar.
        aed_delivered (bool): Se entregou o DAE.
    """

    task: str
    eta_s: float
    aed_id: int | None = None
    status: str = "awarded"
    arrive_by: float = 0.0
    on_scene_t: float | None = None
    late: bool = False
    aed_delivered: bool = False

    @property
    def active(self) -> bool:
        """Se a adjudicação ainda conta (não falhou nem foi dispensada)."""
        return self.status in ("awarded", "committed")


@dataclass
class CaseRecord:
    """Estado de um candidato ou caso. Só um hub de cada vez é seu dono (OS1).

    Attributes:
        case_id (str): Id do caso.
        cell (int): Célula onde foi aberto.
        t_open (float): Quando foi aberto.
        belief (Belief): Crença fundida de ser um incidente real.
        first_event_type (str): Tipo de evento do primeiro alerta (define a janela W_max).
        state (str): Estado do caso (CaseState).
        priority (str): Prioridade atual.
        os4_rule (str | None): Ramo de OS4 que permitiu declarar.
        needs (dict): Tarefa -> voluntários pedidos.
        alerts (dict): Alerta -> fonte.
        alert_reports (dict): Alerta -> (fonte, último AlertReport em dict), para as fusões P26.
        sources (dict): Fonte -> SourceView.
        subject (str | None): Guardião a quem pedir a localização (P24).
        disclosers (set): Guardiões que divulgaram dados; recebem o fecho (OS11).
        location (list | None): Localização exata, depois do P24.
        awards (dict): Voluntário -> AwardInfo.
        ems (str | None): Ambulância adjudicada.
        reservation (dict | None): Reserva de DAE {aed_id, ref, token}.
        outcome (str | None): Resultado, quando o caso acaba.
        merged_into (tuple | None): (hub, caso) que ficou com este candidato depois do P26.
        taken_over_from (str | None): Hub de quem este caso foi herdado (P28).
    """

    case_id: str
    cell: int
    t_open: float
    belief: Belief
    first_event_type: str = ""
    state: str = CaseState.VERIFYING
    priority: str = Priority.P3
    os4_rule: str | None = None
    needs: dict = field(default_factory=dict)
    # verificação
    alerts: dict = field(default_factory=dict)
    alert_reports: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    triaged: set = field(default_factory=set)
    triage_retry_at: dict = field(default_factory=dict)       # testemunha -> quando repetir as perguntas (F5)
    triage_retries: dict = field(default_factory=dict)
    triage_rechecked: set = field(default_factory=set)        # testemunhas a quem se repetiu a triagem (F4)
    guides_asked: set = field(default_factory=set)
    guides: set = field(default_factory=set)                  # telemóveis de testemunhas com orientação ativa
    merged_into: tuple | None = None
    # privacidade
    subject: str | None = None
    disclosers: set = field(default_factory=set)
    location: list | None = None
    location_refused: bool = False
    location_requests: int = 0
    location_requested_at: float = 0.0
    # Contract Net com os voluntários
    invited: set = field(default_factory=set)
    proposals: dict = field(default_factory=dict)             # voluntário -> Proposal, por ordem de chegada
    refusals: set = field(default_factory=set)
    awards: dict = field(default_factory=dict)
    failed_aeds: set = field(default_factory=set)
    call_deadline: float | None = None                        # chamada de novo recrutamento em curso (OL6)
    recruit_exhausted: bool = False                           # ninguém para chamar (volta a False se algo falha)
    unaudited_failures: list = field(default_factory=list)    # falhas ainda sem resposta registada (OL6)
    reservation: dict | None = None
    reservation_pending: bool = False
    # ambulância
    ems_invited: set = field(default_factory=set)
    ems_proposals: dict = field(default_factory=dict)
    ems_refusals: set = field(default_factory=set)
    ems: str | None = None
    ems_retry_at: float | None = None
    ems_retry_delay: float = 0.0                              # backoff exponencial enquanto não há ambulância livre
    ems_took_over: bool = False
    # acompanhamento e fecho
    status: dict = field(default_factory=dict)                # interveniente -> último estado
    clinical: dict | None = None
    pending_release: dict = field(default_factory=dict)       # interveniente -> (enviado em, motivo, tentativas)
    released: bool = False
    retracted: bool = False
    human_false_alarm: bool = False
    silent_reinforced: bool = False
    outcome: str | None = None
    taken_over_from: str | None = None


def source_kind(name: str) -> str:
    """Tipo de fonte pelo nome do agente: os dispositivos são sensores, os cidadãos testemunhas."""
    if Directory.kind_of(name) == "device":
        return SourceKind.SENSOR
    return SourceKind.WITNESS


def snapshot(case: CaseRecord, closed: bool = False) -> CaseSnapshot:
    """Réplica compacta do caso para o hub sucessor (P27), sem localização nem dados clínicos (D7)."""
    awards = {name: asdict(info) for name, info in case.awards.items()}
    positive = sorted(s.name for s in case.sources.values() if s.positive)
    reservation = None
    if case.reservation:
        reservation = {key: case.reservation[key] for key in ("aed_id", "ref", "token")}
    return CaseSnapshot(case.case_id, str(case.state), str(case.priority), case.cell, case.t_open, case.subject,
                        case.ems, awards, sorted(case.guides), positive, reservation, closed)


def record_from_snapshot(snap: CaseSnapshot, cfg: dict, trust, previous_owner: str, now: float) -> CaseRecord:
    """Reconstrói um caso a partir da última réplica, quando o sucessor o assume (P28).

    Args:
        snap (CaseSnapshot): Última réplica recebida.
        cfg (dict): Configuração do cenário.
        trust (TrustTable): Tabela de confiança do novo dono.
        previous_owner (str): Hub que falhou.
        now (float): Instante atual.

    Returns:
        CaseRecord: O caso, em acompanhamento (TRACKING).
    """
    record = CaseRecord(snap.case_id, snap.cell, snap.t_open, Belief(cfg["verification"]["prior"]),
                        state=CaseState.TRACKING, priority=snap.priority, subject=snap.subject, ems=snap.ems,
                        awards={name: AwardInfo(**info) for name, info in snap.awards.items()},
                        guides=set(snap.guides), reservation=snap.reservation,
                        needs=dict(cfg["dispatch"]["redundancy"][str(snap.priority)]),
                        taken_over_from=previous_owner)
    for name in snap.sources:
        record.sources[name] = SourceView(name, source_kind(name), trust.trust(name), positive=True)
    if not snap.ems:
        record.ems_retry_at = now
    return record
