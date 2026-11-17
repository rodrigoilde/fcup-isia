"""Contract Net do coordenador com os voluntários (decisão D4): chamada (P08), reserva do DAE (P11)
e adjudicação (P09).

Usado no DISPATCH, para a primeira adjudicação, e no TRACK, para o novo recrutamento quando uma
adjudicação falha ou se atrasa (OL6). A tarefa FETCH_AED é preenchida primeiro, pela melhor proposta
cujo DAE se consegue reservar; as GO_TO_PATIENT depois, de forma gulosa. Desenho em
docs/03-detailed-design.md §4.2.
"""

from typing import TYPE_CHECKING

from ..behaviours.contract_net import Offer, assign, offer_score
from ..behaviours.tracking import AwardInfo, uncovered_tasks
from ..protocol.messages_dispatch import Award, AwardRejection, CallForProposals
from ..protocol.messages_response import AEDReservationCancel, AEDReservationRequest
from ..protocol.ontology import Qualification, TaskType
from ..sim.directory import Directory
from .conversation import Incoming

if TYPE_CHECKING:
    from .case_fsm import CaseFSM


# --- P08: chamada aos voluntários -----------------------------------------------------------------------
def candidate_aeds(fsm: "CaseFSM") -> list[dict]:
    """DAE disponíveis mais próximos do centro da célula, sem os que já falharam neste caso."""
    case = fsm.case
    world = fsm.hub.world
    count = fsm.dcfg["candidate_aeds"]
    nearest = world.aeds_near(world.grid.centroid(case.cell), count + len(case.failed_aeds))
    usable = [a for a in nearest if a not in case.failed_aeds][:count]
    return [{"aed_id": a, "pos": list(world.aed_registry[a]["pos"])} for a in usable]


async def call_responders(fsm: "CaseFSM", ring: int, tasks: dict) -> float | None:
    """P08 aos voluntários registados até `ring` que ainda não foram chamados.

    Returns:
        float | None: O prazo das propostas, ou None se já não há ninguém para chamar.
    """
    case = fsm.case
    task_counts = {str(t): n for t, n in tasks.items()}
    targets = [v for v in fsm.hub.registered("volunteer", ring) if v not in case.invited]
    if not targets:
        fsm.log("responders_called", ring=ring, invited=0, tasks=task_counts)
        return None
    reply_by = fsm.now() + fsm.dcfg["proposal_deadline_s"]
    aeds = candidate_aeds(fsm) if TaskType.FETCH_AED in tasks else []
    cfp = CallForProposals(case.case_id, task_counts, case.cell, str(case.priority), Qualification.BLS, reply_by, aeds)
    for volunteer in targets:
        await fsm.send(volunteer, cfp)
    case.invited.update(targets)
    fsm.log("responders_called", ring=ring, invited=len(targets), tasks=task_counts)
    return reply_by


async def on_proposal(fsm: "CaseFSM", inc: Incoming) -> None:
    """P08 (propose)."""
    fsm.case.proposals[inc.sender] = inc.payload
    fsm.case.refusals.discard(inc.sender)


async def on_proposal_refusal(fsm: "CaseFSM", inc: Incoming) -> None:
    """P08 (refuse)."""
    fsm.case.refusals.add(inc.sender)


# --- P11: reserva do DAE -----------------------------------------------------------------------------------
async def reserve_aed(fsm: "CaseFSM", aed_id: int) -> bool:
    """Reserva um DAE (P11) e espera pela resposta do seu guardião; devolve True se ficou reservado."""
    case = fsm.case
    token = f"{case.case_id}-aed{aed_id}"     # na simulação o token só tem de coincidir; não gasta aleatório
    case.reservation = {"aed_id": aed_id, "ref": None, "token": token}
    case.reservation_pending = True
    await fsm.send(Directory.hub(aed_id), AEDReservationRequest(
        case.case_id, aed_id, fsm.hub.cfg["aed"]["reservation_valid_s"], str(case.priority), token))
    until = fsm.now() + fsm.dcfg["reservation_timeout_s"]
    while case.reservation_pending and fsm.now() < until:
        inc = await fsm.next_incoming(until)
        if inc is not None:
            await fsm.handle(inc)
    if case.reservation_pending:              # sem resposta (o guardião falhou?): desiste deste DAE
        case.reservation_pending = False
        case.reservation = None
        case.failed_aeds.add(aed_id)
    return case.reservation is not None and case.reservation.get("ref") is not None


async def on_aed_reservation(fsm: "CaseFSM", inc: Incoming) -> None:
    """P11 (agree): guarda a referência da reserva."""
    case = fsm.case
    if case.reservation is not None:
        case.reservation = {"aed_id": inc.payload.aed_id, "ref": inc.payload.reservation_ref,
                            "token": case.reservation["token"]}
    case.reservation_pending = False


async def on_aed_reservation_refusal(fsm: "CaseFSM", inc: Incoming) -> None:
    """P11 (refuse)."""
    fsm.log("aed_reservation_refused", aed=inc.payload.aed_id, reason=inc.payload.reason)
    fsm.case.reservation = None
    fsm.case.reservation_pending = False


async def cancel_reservation(fsm: "CaseFSM") -> None:
    """Cancela a reserva de DAE do caso, se houver uma confirmada."""
    res = fsm.case.reservation
    if res and res.get("ref"):
        await fsm.send(Directory.hub(res["aed_id"]), AEDReservationCancel(fsm.case.case_id, res["aed_id"], res["ref"]))


# --- P09: adjudicação -------------------------------------------------------------------------------------
def scorer(fsm: "CaseFSM"):
    """Função que pontua as propostas deste caso (menor é melhor, ver `contract_net.offer_score`)."""
    dcfg = fsm.dcfg
    trust_prior = fsm.vcfg["trust_prior"]

    def score(offer: Offer) -> float:
        return offer_score(offer, Qualification.BLS, dcfg["quality_penalty"], trust_prior, dcfg["trust_exponent"])

    return score


def offers(fsm: "CaseFSM", exclude: set) -> list[Offer]:
    """Todas as ofertas recebidas, menos as de `exclude` e as de DAE que já falharam."""
    case = fsm.case
    result = []
    for bidder, proposal in case.proposals.items():
        if bidder in exclude:
            continue
        trust = fsm.hub.trust.trust(bidder)
        for o in proposal.offers:
            if o["task"] == TaskType.FETCH_AED and o.get("aed_id") in case.failed_aeds:
                continue
            result.append(Offer(bidder, o["task"], float(o["eta_s"]), proposal.qualification, trust, o.get("aed_id")))
    return result


def uncovered(fsm: "CaseFSM") -> dict:
    """Tarefas ainda em falta neste caso (OL6, ver `tracking.uncovered_tasks`)."""
    return uncovered_tasks(fsm.case.needs, fsm.case.awards)


async def send_award(fsm: "CaseFSM", offer: Offer) -> None:
    """P09 (accept-proposal): a única mensagem que dá ao voluntário a localização exata (OS5)."""
    case = fsm.case
    arrive_by = fsm.now() + offer.eta_s + fsm.dcfg["eta_slack_s"]
    res = case.reservation if offer.task == TaskType.FETCH_AED else None
    aed_id = res["aed_id"] if res else None
    guide = sorted(case.guides)[0] if case.guides else None
    award = Award(case.case_id, offer.task, case.location, arrive_by, aed_id, res["ref"] if res else None,
                  res["token"] if res else None, guide=guide)
    await fsm.send(offer.bidder, award)
    case.awards[offer.bidder] = AwardInfo(offer.task, offer.eta_s, aed_id, arrive_by=arrive_by)
    fsm.log("award", responder=offer.bidder, task=offer.task, eta=round(offer.eta_s, 1), aed=aed_id,
            qualification=case.proposals[offer.bidder].qualification)


async def award_aed_slot(fsm: "CaseFSM", taken: set) -> None:
    """Adjudica a tarefa FETCH_AED à melhor proposta cujo DAE se consegue reservar."""
    case = fsm.case
    fetch = [o for o in offers(fsm, taken) if o.task == TaskType.FETCH_AED and o.aed_id is not None]
    for offer in sorted(fetch, key=scorer(fsm)):
        res = case.reservation
        if res and res.get("ref") and res["aed_id"] == offer.aed_id:
            reserved = True                                  # reaproveita a reserva do caso
        else:
            await cancel_reservation(fsm)                    # não deixa presa a reserva de outro DAE
            reserved = await reserve_aed(fsm, offer.aed_id)
        if reserved:
            await send_award(fsm, offer)
            taken.add(offer.bidder)
            return


async def award_open_slots(fsm: "CaseFSM") -> None:
    """Contract Net (D4): adjudica as tarefas em falta com as propostas recebidas até agora."""
    case = fsm.case
    missing = uncovered(fsm)
    if not missing or case.location is None:
        return
    taken = set(case.awards)
    if missing.get(TaskType.FETCH_AED):
        await award_aed_slot(fsm, taken)
    remaining = {t: n for t, n in missing.items() if t != TaskType.FETCH_AED}
    n_left = fsm.dcfg["n_max"] - sum(1 for a in case.awards.values() if a.active)
    for offer in assign(offers(fsm, taken), remaining, n_left, scorer(fsm)):
        await send_award(fsm, offer)


async def award_in_arrival_order(fsm: "CaseFSM") -> None:
    """Linha de base B1: os primeiros voluntários a aceitar ficam com as tarefas em falta."""
    case = fsm.case
    if case.location is None:
        return
    for bidder, proposal in list(case.proposals.items()):
        if bidder in case.awards:
            continue
        missing = uncovered(fsm)
        if not missing:
            return
        for o in proposal.offers:
            if not missing.get(o["task"]):
                continue
            if o["task"] == TaskType.FETCH_AED and not await reserve_aed(fsm, o["aed_id"]):
                continue
            await send_award(fsm, Offer(bidder, o["task"], float(o["eta_s"]), proposal.qualification, 0.5,
                                        o.get("aed_id")))
            break


async def award(fsm: "CaseFSM") -> None:
    """Adjudica as tarefas em falta com a política do hub (Contract Net ou B1)."""
    if fsm.naive:
        await award_in_arrival_order(fsm)
    else:
        await award_open_slots(fsm)


async def reject_losers(fsm: "CaseFSM") -> None:
    """P09 (reject-proposal) a quem se propôs e não ganhou."""
    for bidder in fsm.case.proposals:
        if bidder not in fsm.case.awards:
            await fsm.send(bidder, AwardRejection(fsm.case.case_id))


async def on_award_confirmation(fsm: "CaseFSM", inc: Incoming) -> None:
    """P09 (inform): o voluntário comprometeu-se."""
    info = fsm.case.awards.get(inc.sender)
    if info is not None and info.status == "awarded":
        info.status = "committed"


async def on_award_failure(fsm: "CaseFSM", inc: Incoming) -> None:
    """P09 (failure): o voluntário ficou ocupado depois de propor; a tarefa passa à proposta seguinte."""
    info = fsm.case.awards.get(inc.sender)
    if info is None or not info.active:
        return
    info.status = "failed"
    fsm.log("award_failed", responder=inc.sender, task=info.task, reason="busy")
    fsm.case.recruit_exhausted = False
    fsm.case.unaudited_failures.append(inc.sender)
    await award(fsm)
