"""Ciclo de vida de um candidato ou caso no seu hub: papéis IncidentVerifier e IncidentCoordinator.

Estados da FSMBehaviour e a liveness que implementam (análise §5.2, R3 e R4):

    VERIFY   = RaiseCandidateAlert . _MergeCandidates . CandidateOpen . _OpenWindow .
               (Gather || [ActivateGuidance]) . _FuseEvidence . _ClassifyPriority . _LogDecision .
               (DeclareIncident | _DiscardCandidate . [CloseCase])
    DISPATCH = DeclareIncident . _AssessNeeds . RequestDisclosure .
               ([RequestAmbulance] || Recruit+ || [_SelectAED . ReserveAED]) . HelpEnRouteNotice
    TRACK    = (StatusUpdate . _MonitorProgress . [Recruit | ReleaseResponder])+ . [RetractIncident]
    CLOSE    = CloseCase . OutcomeFeedback
    DISCARD  = _DiscardCandidate . [CloseCase] . [OutcomeFeedback]

O código de cada estado está em `case_verify` (VERIFY, DISCARD), `case_dispatch` (DISPATCH) e
`case_track` (TRACK) e `case_close` (CLOSE); o Contract Net com os voluntários está em `case_awards` e os dados do
caso em `case_record`. Este módulo junta-os numa
FSM e encaminha as mensagens do caso para o handler de cada tipo.

Todas as mensagens do caso levam thread = id do caso, menos os alertas, que mantêm o id do alerta
como thread; o hub associa essas threads ao caso quando funde o alerta. Um caso declarado é
replicado no sucessor do hub a cada mudança relevante (P27, D8); um sucessor que o assume
reconstrói-o a partir da réplica e começa em TRACK.

Política "naive" (linha de base B1): sem verificação (declara ao primeiro alerta), chama todos os
voluntários até ao anel 2, adjudica por ordem de chegada e não usa reputação.
"""

from ..behaviours.verification import SourceView, evidence_weight
from ..protocol.messages_detection import (AlertCancel, AlertReport, CorroborationRefusal, CorroborationReply,
                                           GuidanceAck, TriageAnswer)
from ..protocol.messages_dispatch import (AmbulanceConfirmation, AmbulanceFailure, AmbulanceProposal, AmbulanceRefusal,
                                          AwardConfirmation, AwardFailure, Proposal, ProposalRefusal)
from ..protocol.messages_hubs import CandidateMerge, CandidateNotice, Disclosure, DisclosureRefusal
from ..protocol.messages_response import AEDReservation, AEDReservationRefusal, ReleaseAck, StatusReport
from ..protocol.ontology import CaseState
from . import case_awards, case_close, case_dispatch, case_track, case_verify
from .case_record import CLOSE, DISCARD, DISPATCH, TRACK, TRANSITIONS, VERIFY, CaseRecord, snapshot, source_kind
from .conversation import Conversation, Incoming


async def ignore(fsm: "CaseFSM", inc: Incoming) -> None:
    """Mensagem esperada que não muda nada no caso."""


# Tipo de mensagem -> handler (fsm, mensagem)
HANDLERS = {
    AlertReport: case_verify.on_alert_report,
    AlertCancel: case_verify.on_alert_cancel,
    CandidateMerge: case_verify.on_candidate_merge,
    CandidateNotice: case_verify.on_candidate_notice,
    CorroborationReply: case_verify.on_corroboration,
    CorroborationRefusal: case_verify.on_corroboration_refusal,
    TriageAnswer: case_verify.on_triage_answer,
    GuidanceAck: case_verify.on_guidance_ack,
    Disclosure: case_dispatch.on_disclosure,
    DisclosureRefusal: case_dispatch.on_disclosure_refusal,
    Proposal: case_awards.on_proposal,
    ProposalRefusal: case_awards.on_proposal_refusal,
    AwardConfirmation: case_awards.on_award_confirmation,
    AwardFailure: case_awards.on_award_failure,
    AmbulanceProposal: case_dispatch.on_ambulance_proposal,
    AmbulanceRefusal: case_dispatch.on_ambulance_refusal,
    AmbulanceConfirmation: ignore,
    AmbulanceFailure: case_dispatch.on_ambulance_failure,
    AEDReservation: case_awards.on_aed_reservation,
    AEDReservationRefusal: case_awards.on_aed_reservation_refusal,
    StatusReport: case_track.on_status_report,
    ReleaseAck: case_track.on_release_ack,
}


class CaseFSM(Conversation):
    """FSM de um caso, dentro do hub. O hub é um agente híbrido em camadas: os handlers de serviço
    são a camada reativa e esta FSM é a camada deliberativa de cada caso.

    Attributes:
        hub (AEDHubAgent): O hub dono do caso.
        case (CaseRecord): Os dados do caso.
        naive (bool): Se o hub segue a linha de base B1.
        announced (bool): Se o candidato já foi anunciado aos hubs vizinhos (P26).
    """

    def __init__(self, hub, case: CaseRecord, restored: bool = False):
        super().__init__({case.case_id} | set(case.alerts))
        self.hub = hub
        self.case = case
        self.naive = hub.cfg["policy"]["allocation"] == "naive"
        self.announced = False
        self.add_state(VERIFY, case_verify.Verify(self), initial=not restored)
        self.add_state(DISPATCH, case_dispatch.Dispatch(self))
        self.add_state(TRACK, case_track.Track(self), initial=restored)
        self.add_state(CLOSE, case_close.Close(self))
        self.add_state(DISCARD, case_verify.Discard(self))
        for src, dst in TRANSITIONS:
            self.add_transition(src, dst)

    # --- atalhos ------------------------------------------------------------------------------------
    @property
    def vcfg(self) -> dict:
        """Parâmetros da verificação."""
        return self.hub.cfg["verification"]

    @property
    def dcfg(self) -> dict:
        """Parâmetros do despacho."""
        return self.hub.cfg["dispatch"]

    @property
    def declared(self) -> bool:
        """Se o caso já foi declarado (e não descartado)."""
        return self.case.state not in (CaseState.VERIFYING, CaseState.DISCARDED)

    def now(self) -> float:
        """Instante simulado atual."""
        return self.hub.now()

    async def send(self, to: str, payload, performative=None) -> bool:
        """Envia uma mensagem na thread do caso."""
        return await self.hub.send_to(to, payload, thread=self.case.case_id, performative=performative)

    def log(self, kind: str, **fields) -> None:
        """Regista um evento do caso."""
        self.hub.log(kind, case=self.case.case_id, **fields)

    # --- evidência ----------------------------------------------------------------------------------
    def source(self, name: str) -> SourceView:
        """A vista do verificador sobre uma fonte, criada com a confiança atual se for nova."""
        src = self.case.sources.get(name)
        if src is None:
            src = SourceView(name, source_kind(name), self.hub.trust.trust(name))
            self.case.sources[name] = src
        return src

    def add_evidence(self, src: SourceView, kind: str, confidence: float = 1.0) -> None:
        """_FuseEvidence: soma uma evidência à crença, pesada pela confiança na fonte (D5)."""
        lr = self.vcfg["likelihood_ratio"][kind]
        weight = evidence_weight(src.trust, self.vcfg["trust_prior"])
        delta = self.case.belief.add(lr, confidence, weight)
        self.log("evidence", source=src.name, evidence=kind, confidence=round(confidence, 3),
                 weight=round(weight, 3), delta=round(delta, 3), p=round(self.case.belief.probability, 4))

    # --- mensagens e réplica ----------------------------------------------------------------------
    async def handle(self, inc: Incoming) -> None:
        """Encaminha uma mensagem do caso para o seu handler."""
        handler = HANDLERS.get(type(inc.payload))
        if handler is None:
            self.log("unexpected", msg_type=type(inc.payload).__name__, sender=inc.sender)
            return
        await handler(self, inc)

    async def replicate(self, closed: bool = False) -> None:
        """P27: envia a réplica ao sucessor, se o caso já foi declarado ou acabou de fechar."""
        if self.declared or closed:
            await self.hub.failover.replicate(snapshot(self.case, closed))

    async def finished(self) -> None:
        self.hub.case_finished(self)
