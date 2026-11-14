"""Estado DISPATCH do caso (papel IncidentCoordinator): localização, ambulância e primeira adjudicação.

O coordenador pede a localização ao titular (P24), chama as ambulâncias (P10) e os voluntários da
célula e do anel 1 (P08, em `case_awards`), alarga ao anel 2 se ninguém se propõe (D3) e adjudica
a ambulância e as tarefas. As funções da ambulância e do P15 também são usadas no TRACK.
Desenho em docs/03-detailed-design.md §2.4 e §4.2.
"""

from typing import TYPE_CHECKING

from ..behaviours.contract_net import best_ambulance
from ..protocol.messages_assistance import HelpEnRoute
from ..protocol.messages_detection import Declaration
from ..protocol.messages_dispatch import AmbulanceAward, AmbulanceCall, AmbulanceRejection, Proposal
from ..protocol.messages_hubs import DisclosureRequest
from ..protocol.ontology import CaseState, DisclosureField, Outcome, Priority, TaskType
from .case_awards import award, award_in_arrival_order, call_responders, reject_losers
from .case_record import CLOSE, TRACK
from .conversation import Incoming, Step

if TYPE_CHECKING:
    from .case_fsm import CaseFSM


# --- P24: localização -------------------------------------------------------------------------------
async def request_location(fsm: "CaseFSM") -> None:
    """Pede a localização exata ao guardião do titular (P24)."""
    case = fsm.case
    if case.subject is None:
        fsm.log("no_subject")
        return
    case.location_requests += 1
    case.location_requested_at = fsm.now()
    await fsm.send(case.subject, DisclosureRequest(case.case_id, DisclosureField.PRECISE_LOCATION, "dispatch",
                                                   str(case.priority), recipients=["awarded responders", "EMS unit"]))


async def on_disclosure(fsm: "CaseFSM", inc: Incoming) -> None:
    """P24: o guardião divulgou o dado; quem divulga recebe depois o fecho do caso (OS11)."""
    fsm.case.disclosers.add(inc.sender)
    if inc.payload.field_name == DisclosureField.PRECISE_LOCATION:
        fsm.case.location = list(inc.payload.value)
        fsm.log("case_located", location=fsm.case.location, by=inc.sender)


async def on_disclosure_refusal(fsm: "CaseFSM", inc: Incoming) -> None:
    """P24: o guardião recusou."""
    fsm.case.location_refused = True
    fsm.log("disclosure_refused", field=inc.payload.field_name, reason=inc.payload.reason)


# --- P10: ambulância ----------------------------------------------------------------------------------
async def call_ambulance(fsm: "CaseFSM") -> float:
    """Envia o cfp do P10 a todas as ambulâncias; devolve o prazo das propostas."""
    case = fsm.case
    reply_by = fsm.now() + fsm.dcfg["ambulance_deadline_s"]
    case.ems_proposals.clear()
    case.ems_refusals.clear()
    case.ems_invited = set(fsm.hub.ctx.directory.ems_names)
    for unit in sorted(case.ems_invited):
        await fsm.send(unit, AmbulanceCall(case.case_id, str(case.priority), case.cell, reply_by))
    fsm.log("ambulance_requested", units=len(case.ems_invited))
    return reply_by


async def award_ambulance(fsm: "CaseFSM") -> None:
    """Adjudica a ambulância com menor ETA; sem propostas ou sem localização, tenta mais tarde (F10)."""
    case = fsm.case
    ranked = best_ambulance(case.ems_proposals)
    if not ranked or case.location is None:
        base = fsm.dcfg["ambulance_retry_s"]
        if case.ems_retry_delay:
            case.ems_retry_delay = min(4 * base, 2 * case.ems_retry_delay)        # backoff exponencial
        else:
            case.ems_retry_delay = base
        fsm.log("no_ambulance", proposals=len(ranked), located=case.location is not None,
                retry_in=case.ems_retry_delay)
        case.ems_retry_at = fsm.now() + case.ems_retry_delay
        return
    case.ems = ranked[0]
    case.ems_retry_at = None
    await fsm.send(case.ems, AmbulanceAward(case.case_id, str(case.priority), case.location))
    for unit in ranked[1:]:
        await fsm.send(unit, AmbulanceRejection(case.case_id))
    fsm.log("ems_award", unit=case.ems, eta=round(case.ems_proposals[case.ems], 1))
    await fsm.replicate()


async def on_ambulance_proposal(fsm: "CaseFSM", inc: Incoming) -> None:
    """P10 (propose)."""
    fsm.case.ems_proposals[inc.sender] = inc.payload.eta_s


async def on_ambulance_refusal(fsm: "CaseFSM", inc: Incoming) -> None:
    """P10 (refuse)."""
    fsm.case.ems_refusals.add(inc.sender)


async def on_ambulance_failure(fsm: "CaseFSM", inc: Incoming) -> None:
    """P10 (failure): a ambulância adjudicada ficou ocupada; volta-se a pedir uma."""
    case = fsm.case
    if inc.sender == case.ems:
        fsm.log("ambulance_failed", unit=inc.sender, reason=inc.payload.reason)
        case.ems = None
        case.ems_retry_at = fsm.now()


# --- P15: ajuda a caminho ---------------------------------------------------------------------------------
async def send_help_notice(fsm: "CaseFSM") -> None:
    """P15: diz aos guias no local que ajuda vem a caminho (só ETA, nunca identidades)."""
    case = fsm.case
    if not case.guides:
        return
    now = fsm.now()
    slack = fsm.dcfg["eta_slack_s"]
    go = [a.arrive_by - slack - now for a in case.awards.values() if a.active and a.task == TaskType.GO_TO_PATIENT]
    aed = [a.arrive_by - slack - now for a in case.awards.values() if a.active and a.task == TaskType.FETCH_AED]
    eta_go = round(min(go), 1) if go else None
    eta_aed = round(min(aed), 1) if aed else None
    eta_ems = case.ems_proposals.get(case.ems) if case.ems else None
    for guide in sorted(case.guides):
        await fsm.send(guide, HelpEnRoute(case.case_id, eta_go, eta_aed, eta_ems))


# --- estado ------------------------------------------------------------------------------------------------
class Dispatch(Step):
    """Despacho inicial do caso declarado."""

    async def step(self) -> None:
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        case.state = CaseState.DISPATCHING
        hub.log_local(Declaration(case.case_id, str(case.priority), round(case.belief.probability, 4), case.cell,
                                  case.os4_rule or "", sorted(case.sources)), "IncidentCoordinator", case.case_id)
        if case.priority == Priority.P3:              # só contacto e orientação (análise §2.2)
            case.outcome = Outcome.RESOLVED_ON_SCENE
            self.set_next_state(CLOSE)
            return
        case.needs = dict(fsm.dcfg["redundancy"][str(case.priority)])
        await fsm.replicate()
        await request_location(fsm)
        ems_deadline = await call_ambulance(fsm)
        ring = 2 if fsm.naive else 1
        deadline = await call_responders(fsm, ring, case.needs)
        await self.collect(max(deadline or 0.0, ems_deadline))
        if not case.proposals and not fsm.naive and case.outcome is None:
            wider = await call_responders(fsm, 2, case.needs)                 # alarga ao anel 2 (D3)
            if wider is not None:
                await self.collect(wider)
        await self.wait_for_location()
        if case.outcome is not None:                  # retirado durante o despacho
            self.set_next_state(CLOSE)
            return
        await self.award_everything()
        self.set_next_state(TRACK)

    async def collect(self, deadline: float) -> None:
        """Recebe propostas até ao prazo, ou até todos os convidados terem respondido."""
        fsm, case = self.fsm, self.fsm.case
        while fsm.now() < deadline and case.outcome is None:
            answered = case.invited <= (set(case.proposals) | case.refusals)
            ems_answered = case.ems_invited <= (set(case.ems_proposals) | case.ems_refusals)
            if answered and ems_answered and case.location is not None:
                return
            inc = await fsm.next_incoming(deadline)
            if inc is None:
                continue
            await fsm.handle(inc)
            if fsm.naive and isinstance(inc.payload, Proposal):
                await award_in_arrival_order(fsm)                          # B1: primeiro a chegar, primeiro servido

    async def wait_for_location(self) -> None:
        """F5: sem localização, volta a pedi-la uma vez e espera um pouco por ela."""
        fsm, case = self.fsm, self.fsm.case
        if case.location is not None or case.location_refused:
            return
        await request_location(fsm)
        until = fsm.now() + fsm.dcfg["location_wait_s"]
        while case.location is None and fsm.now() < until:
            inc = await fsm.next_incoming(until)
            if inc is not None:
                await fsm.handle(inc)

    async def award_everything(self) -> None:
        """Adjudica a ambulância e as tarefas, rejeita as outras propostas e avisa os guias (P15)."""
        fsm, case = self.fsm, self.fsm.case
        await award_ambulance(fsm)
        await award(fsm)
        await reject_losers(fsm)
        if case.location is None:
            fsm.log("no_location_for_awards")
        await send_help_notice(fsm)
        case.state = CaseState.TRACKING
        await fsm.replicate()

