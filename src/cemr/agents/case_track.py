"""Estado TRACK do caso (papel IncidentCoordinator): acompanhamento e novo recrutamento.

O coordenador acompanha os estados dos intervenientes (P13), volta a recrutar quando uma
adjudicação falha ou se atrasa (OL6), dispensa os excedentes (OL8) e os voluntários quando a
ambulância assume (OL7), e repete os pedidos perdidos (F5). Desenho em docs/03-detailed-design.md §2.4.
"""

from typing import TYPE_CHECKING

from ..protocol.messages_detection import Retraction
from ..protocol.messages_hubs import Takeover
from ..protocol.messages_response import OnSceneRoster, Release
from ..protocol.ontology import ON_SCENE_STATUSES, Outcome, Priority, ResponderStatus, TaskType
from .case_awards import award, award_open_slots, call_responders, cancel_reservation, offers, reject_losers, uncovered
from .case_dispatch import award_ambulance, call_ambulance, request_location, send_help_notice
from .case_record import CLOSE, AwardInfo
from .conversation import Incoming, Step

if TYPE_CHECKING:
    from .case_fsm import CaseFSM

FAILURE_STATUSES = {ResponderStatus.AED_MISSING, ResponderStatus.WITHDRAWN, ResponderStatus.UNSAFE_SCENE}
IDLE_WAKE_S = 30           # o TRACK revê o caso pelo menos de 30 em 30 s
MIN_WAIT_S = 0.5           # espera mínima entre duas voltas do ciclo


# --- P13: estados dos intervenientes ------------------------------------------------------------------
async def on_status_report(fsm: "CaseFSM", inc: Incoming) -> None:
    """P13: estado de um voluntário adjudicado, de um guia ou da ambulância do caso."""
    case = fsm.case
    report = inc.payload
    case.status[inc.sender] = report.status
    fsm.log("status", source=inc.sender, status=report.status, eta=report.eta_s)
    info = case.awards.get(inc.sender)
    if info is not None:
        await on_responder_status(fsm, inc.sender, report, info)
    elif inc.sender in case.guides and report.status == ResponderStatus.WITNESS_SILENT:
        reinforce_after_silence(fsm)
    elif inc.sender == case.ems:
        await on_ems_status(fsm, inc.sender, report)


async def on_responder_status(fsm: "CaseFSM", sender: str, report, info: AwardInfo) -> None:
    """Estado de um voluntário adjudicado (_MonitorProgress)."""
    case = fsm.case
    if report.status == ResponderStatus.EN_ROUTE and report.eta_s is not None and info.active:
        # O ETA do próprio voluntário para o troço atual afina a estimativa feita na adjudicação.
        info.arrive_by = fsm.now() + report.eta_s + fsm.dcfg["eta_slack_s"]
        info.late = False
    if report.status in ON_SCENE_STATUSES and info.on_scene_t is None:
        info.on_scene_t = fsm.now()
    if report.status == ResponderStatus.AED_DELIVERED:
        info.aed_delivered = True
    if report.status in ON_SCENE_STATUSES:
        await release_surplus(fsm)                                        # OL8
    if report.status in FAILURE_STATUSES and info.active:                 # OL6
        info.status = "failed"
        if report.status == ResponderStatus.AED_MISSING and info.aed_id is not None:
            case.failed_aeds.add(info.aed_id)
            case.reservation = None
        fsm.log("award_failed", responder=sender, task=info.task, reason=report.status)
        case.recruit_exhausted = False         # OL6: podem ter ficado voluntários livres desde a última chamada
        case.unaudited_failures.append(sender)
        await fsm.replicate()


def reinforce_after_silence(fsm: "CaseFSM") -> None:
    """F11: o ajudante guiado calou-se num P1 sem ninguém no local; pede-se mais um voluntário."""
    case = fsm.case
    if case.priority == Priority.P1 and not case.silent_reinforced and not anyone_on_scene(fsm):
        case.silent_reinforced = True
        case.needs[TaskType.GO_TO_PATIENT] = case.needs.get(TaskType.GO_TO_PATIENT, 0) + 1


async def on_ems_status(fsm: "CaseFSM", sender: str, report) -> None:
    """Estado da ambulância do caso: chegada, passagem (OL7), confirmação clínica e transporte."""
    case = fsm.case
    if report.status == ResponderStatus.ON_SCENE:
        on_scene = [v for v, a in case.awards.items() if a.on_scene_t is not None and a.active]
        await fsm.send(sender, OnSceneRoster(case.case_id, on_scene or sorted(case.guides)))
    elif report.status == ResponderStatus.EMS_TOOK_OVER:
        case.ems_took_over = True
        await release_all(fsm, "ems_took_over")                         # OL7
    elif report.status == ResponderStatus.CLINICAL_CONFIRMATION:
        case.clinical = dict(report.detail)
        if not case.clinical.get("real_incident", True):
            await release_all(fsm, "false_alarm")
            case.outcome = Outcome.FALSE_ALARM
    elif report.status == ResponderStatus.TRANSPORTING:
        case.outcome = Outcome.TRANSPORTED


def anyone_on_scene(fsm: "CaseFSM") -> bool:
    """Se algum voluntário adjudicado já está no local."""
    return any(a.on_scene_t is not None and a.active for a in fsm.case.awards.values())


# --- OL6: acompanhamento e novo recrutamento ---------------------------------------------------------
def flag_late(fsm: "CaseFSM") -> list[str]:
    """Marca as adjudicações que passaram de ETA + δ sem chegar; devolve os voluntários marcados agora."""
    newly_late = []
    now = fsm.now()
    for name, info in fsm.case.awards.items():
        if info.active and info.on_scene_t is None and not info.late and now > info.arrive_by:
            info.late = True
            newly_late.append(name)
            fsm.log("award_at_risk", responder=name, task=info.task)
    return newly_late


def skip_reason(fsm: "CaseFSM", missing: dict) -> str:
    """Motivo registado quando uma falha ou atraso não leva a novo recrutamento (rasto para o OL6)."""
    if not missing:
        return "covered"
    if fsm.case.call_deadline is not None:
        return "call_in_progress"
    if fsm.case.location is None:
        return "no_location"
    return "pool_exhausted"


async def check_progress(fsm: "CaseFSM") -> None:
    """_MonitorProgress: marca os atrasos e volta a recrutar as tarefas por cobrir (OL6)."""
    case = fsm.case
    if case.outcome is not None or case.ems_took_over or case.retracted:
        return
    newly_late = flag_late(fsm)
    missing = uncovered(fsm)
    if missing and case.call_deadline is None and case.location is not None and not case.recruit_exhausted:
        if offers(fsm, set(case.awards)):                  # primeiro as propostas que já temos
            await award_open_slots(fsm)
            missing = uncovered(fsm)
        if missing:                                        # depois uma chamada até ao anel 2
            case.call_deadline = await call_responders(fsm, 2, missing)
            case.recruit_exhausted = case.call_deadline is None
            fsm.log("recruit", tasks={str(t): n for t, n in missing.items()}, exhausted=case.recruit_exhausted)
            case.unaudited_failures = []
            return
    unaudited = newly_late + case.unaudited_failures
    case.unaudited_failures = []
    if unaudited:
        fsm.log("recruit_skipped", responders=unaudited, reason=skip_reason(fsm, missing))


async def ensure_location(fsm: "CaseFSM") -> None:
    """F5: continua a pedir a localização enquanto não a tem (por exemplo se a resposta se perdeu num takeover)."""
    case = fsm.case
    if case.location is not None or case.location_refused or not case.subject:
        return
    if case.location_requests > fsm.vcfg["max_retries"]:
        return
    if fsm.now() - case.location_requested_at >= fsm.vcfg["retry_after_s"]:
        await request_location(fsm)


# --- P14: dispensa -------------------------------------------------------------------------------------
async def send_release(fsm: "CaseFSM", name: str, reason: str, retries: int = 0) -> None:
    """P14: dispensa um interveniente e espera pelo ReleaseAck (F5)."""
    await fsm.send(name, Release(fsm.case.case_id, reason))
    fsm.case.pending_release[name] = (fsm.now(), reason, retries)
    fsm.log("release", responder=name, reason=reason, retry=retries)


async def on_release_ack(fsm: "CaseFSM", inc: Incoming) -> None:
    """P14 (inform): a dispensa chegou."""
    fsm.case.pending_release.pop(inc.sender, None)


async def retry_releases(fsm: "CaseFSM") -> None:
    """F5: reenvia uma dispensa que não teve ReleaseAck."""
    now = fsm.now()
    for name, (t, reason, retries) in list(fsm.case.pending_release.items()):
        if now - t < fsm.vcfg["retry_after_s"]:
            continue
        if retries >= fsm.vcfg["max_retries"]:
            del fsm.case.pending_release[name]
        else:
            await send_release(fsm, name, reason, retries + 1)


async def release_surplus(fsm: "CaseFSM") -> None:
    """OL8: com N_need socorristas no local, dispensa os que ainda vêm a caminho (menos um DAE por entregar)."""
    case = fsm.case
    n_need = fsm.dcfg["n_need"].get(str(case.priority), 1)
    if sum(1 for a in case.awards.values() if a.on_scene_t is not None and a.active) < n_need:
        return
    aed_done = any(a.aed_delivered for a in case.awards.values())
    for name, info in case.awards.items():
        if info.active and info.on_scene_t is None and (info.task != TaskType.FETCH_AED or aed_done):
            info.status = "released"
            await send_release(fsm, name, "enough_on_scene")
    case.call_deadline = None


async def release_all(fsm: "CaseFSM", reason: str) -> None:
    """Dispensa todos os voluntários ativos e cancela a reserva de um DAE que não chegou a ser usado."""
    case = fsm.case
    if case.released:
        return
    case.released = True
    case.call_deadline = None
    for volunteer, info in case.awards.items():
        if info.active:
            info.status = "released"
            await send_release(fsm, volunteer, reason)
    aed_used = any(a.aed_delivered or case.status.get(v) == ResponderStatus.AED_OK for v, a in case.awards.items())
    if case.reservation and case.reservation.get("ref") and not aed_used:
        await cancel_reservation(fsm)
        case.reservation = None
    await fsm.replicate()


async def retract(fsm: "CaseFSM", reason: str, human_confirmed: bool) -> None:
    """P07: desfaz a declaração. A ambulância só é dispensada num falso alarme confirmado por um humano (OS6)."""
    case = fsm.case
    if case.retracted:
        return
    case.retracted = True
    case.human_false_alarm = human_confirmed
    p = round(case.belief.probability, 4)
    fsm.hub.log_local(Retraction(case.case_id, reason, p), "IncidentCoordinator", case.case_id)
    fsm.log("case_retracted", reason=reason, human_confirmed=human_confirmed, p=p)
    await release_all(fsm, "false_alarm")
    if human_confirmed:
        if case.ems:
            await send_release(fsm, case.ems, "false_alarm")
        case.outcome = Outcome.FALSE_ALARM


# --- estados ---------------------------------------------------------------------------------------------
class Track(Step):
    """Acompanha o caso até haver um resultado ou até ao timeout do caso."""

    async def step(self) -> None:
        fsm, case = self.fsm, self.fsm.case
        if case.taken_over_from is not None:
            await self.announce_takeover()
        timeout = case.t_open + fsm.dcfg["case_timeout_s"]
        self.ems_call_until: float | None = None               # prazo de um novo pedido de ambulância
        while case.outcome is None:
            now = fsm.now()
            if now >= timeout:
                case.outcome = Outcome.TIMEOUT
                break
            await self.follow_ambulance(now)
            await self.follow_recruitment(now)
            await ensure_location(fsm)
            await check_progress(fsm)
            await retry_releases(fsm)
            inc = await fsm.next_incoming(self.next_wake(now, timeout))
            if inc is not None:
                await fsm.handle(inc)
        self.set_next_state(CLOSE)

    async def follow_ambulance(self, now: float) -> None:
        """F10: sem ambulância, volta a pedir quando chega a hora e adjudica quando há respostas."""
        fsm, case = self.fsm, self.fsm.case
        retry_due = case.ems_retry_at is not None and now >= case.ems_retry_at
        if case.ems is None and retry_due and self.ems_call_until is None and not case.retracted:
            self.ems_call_until = await call_ambulance(fsm)
            case.ems_retry_at = None
        if self.ems_call_until is None:
            return
        all_answered = case.ems_invited <= (set(case.ems_proposals) | case.ems_refusals)
        if now >= self.ems_call_until or all_answered:
            self.ems_call_until = None
            await award_ambulance(fsm)
            await send_help_notice(fsm)

    async def follow_recruitment(self, now: float) -> None:
        """OL6: no fim de uma chamada de novo recrutamento, adjudica com as propostas recebidas."""
        fsm, case = self.fsm, self.fsm.case
        if case.call_deadline is None or now < case.call_deadline:
            return
        case.call_deadline = None
        await award(fsm)
        await reject_losers(fsm)
        await send_help_notice(fsm)
        await fsm.replicate()

    def next_wake(self, now: float, timeout: float) -> float:
        """Próximo instante em que há algo a rever: um prazo, uma chegada prevista ou a revisão periódica."""
        case = self.fsm.case
        times = [timeout, now + IDLE_WAKE_S]
        for t in (self.ems_call_until, case.ems_retry_at, case.call_deadline):
            if t is not None:
                times.append(t)
        for info in case.awards.values():
            if info.active and info.on_scene_t is None and not info.late:
                times.append(info.arrive_by)
        return max(min(times), now + MIN_WAIT_S)

    async def announce_takeover(self) -> None:
        """P28: diz a todos os participantes quem coordena agora o caso e volta a pedir a localização (D7)."""
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        participants = {v for v, a in case.awards.items() if a.active} | set(case.guides)
        if case.ems:
            participants.add(case.ems)
        for name in sorted(participants):
            await fsm.send(name, Takeover(case.case_id, hub.label))
        fsm.log("case_taken_over", previous=case.taken_over_from, participants=len(participants))
        await request_location(fsm)
