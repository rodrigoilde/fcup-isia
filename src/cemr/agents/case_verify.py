"""Estado VERIFY do caso (papel IncidentVerifier) e o descarte de candidatos (estado DISCARD).

Junta a evidência dos alertas (P01/P02), da corroboração (P03) e da triagem (P04), liga a
orientação da testemunha logo na triagem (P05, OL3) e declara o incidente quando a crença chega a
tau(p) e um ramo de OS4 se verifica. Desenho em docs/03-detailed-design.md §2.4 e §4.1.
"""

from dataclasses import asdict
from typing import TYPE_CHECKING

from ..behaviours.verification import (KEY_QUESTIONS, case_priority, close_areas, os4_branch, should_declare,
                                       triage_incoherent)
from ..protocol.messages_detection import (AlertAck, AlertReport, CancelAck, CorroborationQuery, GuidanceActivation,
                                           TriageQuestion)
from ..protocol.messages_hubs import OutcomeLabels
from ..protocol.messages_response import CaseClosure
from ..protocol.ontology import (Answer, CancelReason, CaseState, EventType, Outcome, PromptStatus, SourceKind,
                                 TriageQuestionId, Verdict)
from ..sim.directory import Directory
from .case_record import DISCARD, DISPATCH
from .case_track import retract
from .conversation import Incoming, Step

if TYPE_CHECKING:
    from .case_fsm import CaseFSM

TRIAGE_QUESTIONS = (TriageQuestionId.SCENE_SAFE, TriageQuestionId.RESPONSIVE,
                    TriageQuestionId.BREATHING_NORMALLY, TriageQuestionId.CALLED_112)
MIN_WAIT_S = 0.2           # espera mínima entre duas voltas do ciclo de verificação


# --- P01 / P02: alertas -------------------------------------------------------------------------
async def on_alert_report(fsm: "CaseFSM", inc: Incoming) -> None:
    """P01, diretamente da fonte ou reencaminhado por outro hub depois de uma fusão (P26)."""
    await on_alert(fsm, inc.payload.origin or inc.sender, inc.payload)


async def on_alert(fsm: "CaseFSM", origin: str, report: AlertReport) -> None:
    """Junta um alerta ao candidato: recibo, evidência e, para uma testemunha, a triagem."""
    case = fsm.case
    src = fsm.source(origin)
    case.alert_reports[report.alert_id] = (origin, asdict(report))
    if report.alert_id not in case.alerts:
        case.alerts[report.alert_id] = origin
        fsm.hub.claim(report.alert_id, fsm)
        await fsm.hub.send_to(origin, AlertAck(report.alert_id, case.case_id), thread=report.alert_id)
        src.positive = True
        src.event_type = report.event_type
        kind = "witness_report" if src.kind == SourceKind.WITNESS else "sensor_alert"
        fsm.add_evidence(src, kind, report.confidence)
        # Titular dos dados (P24): o dispositivo do próprio doente, se alertou, senão a primeira testemunha.
        if case.subject is None or (src.kind == SourceKind.SENSOR and Directory.kind_of(case.subject) != "device"):
            case.subject = origin
        if src.kind == SourceKind.WITNESS and not fsm.naive:
            await ask_triage(fsm, origin)
    if report.prompt_status == PromptStatus.NO_RESPONSE and not src.wearer_no_response:
        src.wearer_no_response = True
        fsm.add_evidence(src, "wearer_no_response")


async def on_alert_cancel(fsm: "CaseFSM", inc: Incoming) -> None:
    """P02: o portador disse "estou bem" ou a testemunha retirou o relato; pode levar à retração (P07)."""
    cancel = inc.payload
    origin = cancel.origin or inc.sender
    case = fsm.case
    src = case.sources.get(origin)
    await fsm.hub.send_to(origin, CancelAck(cancel.alert_id, str(case.state)), thread=cancel.alert_id)
    if src is None or src.cancelled:
        return
    src.cancelled = True
    fsm.add_evidence(src, "wearer_ok" if cancel.reason == CancelReason.WEARER_OK else "witness_retracts")
    if fsm.declared and case.outcome is None and case.belief.probability < fsm.vcfg["retract_below"]:
        await retract(fsm, f"{cancel.reason} from {origin}", human_confirmed=True)


async def on_candidate_merge(fsm: "CaseFSM", inc: Incoming) -> None:
    """P26: outro hub largou o seu duplicado e manda-nos os alertas dele."""
    merge = inc.payload
    for item in merge.alerts:
        await on_alert(fsm, item["origin"], AlertReport(**item["report"]))
    fsm.log("candidate_absorbed", dropped=merge.candidate_id, by=inc.sender, alerts=len(merge.alerts))


async def on_candidate_notice(fsm: "CaseFSM", inc: Incoming) -> None:
    """P26: o hub decidiu que este candidato é um duplicado de outro aberto antes."""
    fsm.case.merged_into = (inc.sender, inc.payload.candidate_id)


# --- P03: corroboração ----------------------------------------------------------------------------
async def query_neighbourhood(fsm: "CaseFSM") -> None:
    """Pede evidência independente aos sensores e testemunhas registados na célula e no anel 1."""
    case = fsm.case
    hub = fsm.hub
    reply_by = fsm.now() + fsm.vcfg["corroboration_deadline_s"]
    query = CorroborationQuery(case.case_id, case.cell, case.t_open - fsm.vcfg["merge_window_s"], reply_by, reply_by)
    targets = [n for n in hub.registered("sensor", 1) + hub.registered("witness", 1) if n not in case.sources]
    for name in targets:
        await fsm.send(name, query)
    fsm.log("corroboration_requested", targets=len(targets))


async def on_corroboration(fsm: "CaseFSM", inc: Incoming) -> None:
    """P03: uma confirmação conta como fonte independente; uma testemunha que confirma recebe a triagem.

    Uma confirmação de outra área é de outro doente da mesma célula e é ignorada.
    """
    reply = inc.payload
    if reply.verdict == Verdict.NO_DATA:
        return
    if reply.verdict == Verdict.CONFIRM and not close_areas(fsm.case.area, reply.area, fsm.vcfg["merge_radius_m"]):
        fsm.log("corroboration_elsewhere", source=inc.sender)
        return
    src = fsm.source(inc.sender)
    if reply.verdict == Verdict.CONFIRM:
        if not src.positive:
            src.positive = True
            fsm.add_evidence(src, "corroboration_confirm", reply.confidence)
        if src.kind == SourceKind.WITNESS:
            await ask_triage(fsm, inc.sender)
    elif reply.verdict == Verdict.DENY:
        fsm.add_evidence(src, "corroboration_deny", reply.confidence)


async def on_corroboration_refusal(fsm: "CaseFSM", inc: Incoming) -> None:
    """P03: a fonte recusou partilhar (fica só registado)."""
    fsm.log("corroboration_refused", source=inc.sender, reason=inc.payload.reason)


# --- P04 / P05: triagem e orientação -------------------------------------------------------------
async def ask_triage(fsm: "CaseFSM", witness: str) -> None:
    """Faz as perguntas da triagem a uma testemunha, uma só vez."""
    if witness in fsm.case.triaged:
        return
    fsm.case.triaged.add(witness)
    await send_triage(fsm, witness, TRIAGE_QUESTIONS)


async def send_triage(fsm: "CaseFSM", witness: str, questions) -> None:
    """Envia perguntas da triagem e marca quando repeti-las se não houver resposta (F5)."""
    reply_by = fsm.now() + fsm.vcfg["triage_deadline_s"]
    for question in questions:
        await fsm.send(witness, TriageQuestion(fsm.case.case_id, str(question), reply_by))
    fsm.case.triage_retry_at[witness] = reply_by


async def retry_triage(fsm: "CaseFSM") -> None:
    """F5: repete as perguntas sem resposta depois do prazo (as respostas são idempotentes)."""
    case = fsm.case
    now = fsm.now()
    for witness, at in list(case.triage_retry_at.items()):
        if now < at:
            continue
        src = case.sources.get(witness)
        missing = [q for q in TRIAGE_QUESTIONS if src is None or q not in src.triage]
        tries = case.triage_retries.get(witness, 0)
        if not missing or tries >= fsm.vcfg["max_retries"]:
            del case.triage_retry_at[witness]
            continue
        case.triage_retries[witness] = tries + 1
        fsm.log("triage_retry", witness=witness, questions=[str(q) for q in missing])
        await send_triage(fsm, witness, missing)


async def on_triage_answer(fsm: "CaseFSM", inc: Incoming) -> None:
    """P04: com as duas perguntas-chave respondidas, a triagem conta como evidência e liga a orientação."""
    answer = inc.payload
    src = fsm.source(inc.sender)
    src.triage[answer.question] = answer.answer
    fsm.log("triage_answer", source=inc.sender, question=answer.question, answer=answer.answer)
    if not src.triage_complete or src.triage_scored:
        return
    src.triage_scored = True
    if triage_incoherent(src.triage):
        await recheck_triage(fsm, src)
        return
    if src.triage[TriageQuestionId.RESPONSIVE] == Answer.NO:
        breathing = src.triage[TriageQuestionId.BREATHING_NORMALLY]
        fsm.add_evidence(src, "triage_p1" if breathing == Answer.NO else "triage_p2")
        await activate_guidance(fsm, inc.sender, src.triage)


async def recheck_triage(fsm: "CaseFSM", src) -> None:
    """F4: triagem incoerente. Os erros de observação são independentes, por isso repetem-se uma vez
    as duas perguntas-chave; uma segunda resposta incoerente é ignorada."""
    case = fsm.case
    if src.name in case.triage_rechecked:
        fsm.log("triage_incoherent", source=src.name, action="ignored")
        return
    case.triage_rechecked.add(src.name)
    for question in KEY_QUESTIONS:
        src.triage.pop(question, None)
    src.triage_scored = False
    case.triage_retries.pop(src.name, None)
    await send_triage(fsm, src.name, KEY_QUESTIONS)
    fsm.log("triage_incoherent", source=src.name, action="re-ask")


async def activate_guidance(fsm: "CaseFSM", witness: str, triage: dict) -> None:
    """P05: a orientação começa com a triagem, antes da declaração (OL3), e só para quem respondeu (OL5).

    A variante `policy.guidance = false` desliga só a orientação (a triagem continua, porque faz
    parte da verificação), para separar o seu efeito do da alocação.
    """
    case = fsm.case
    if not fsm.hub.cfg["policy"]["guidance"]:
        return
    if witness in case.guides_asked or case.outcome is not None:
        return
    case.guides_asked.add(witness)
    priority = case_priority(list(case.sources.values()))
    await fsm.send(witness, GuidanceActivation(case.case_id, str(priority), dict(triage)))


async def on_guidance_ack(fsm: "CaseFSM", inc: Incoming) -> None:
    """P05: a app da testemunha aceitou orientar o caso."""
    if inc.payload.accepted:
        fsm.case.guides.add(inc.sender)
        fsm.log("guidance_active", guide=inc.sender)


# --- estados ---------------------------------------------------------------------------------------
class Verify(Step):
    """Recolhe evidência até poder declarar, até a crença cair ou até acabar a janela W_max."""

    async def step(self) -> None:
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        provisional = EventType(case.first_event_type).provisional_priority
        deadline = case.t_open + fsm.vcfg["w_max_s"][str(provisional)]
        queried = False
        while True:
            wake = min([deadline] + list(case.triage_retry_at.values()))
            inc = await fsm.next_incoming(max(wake, hub.now() + MIN_WAIT_S))
            if inc is not None:
                await fsm.handle(inc)
            if case.sources and not fsm.announced:
                fsm.announced = True
                await hub.announce_candidate(fsm)                              # P26
            if case.merged_into is not None:
                await self.drop_duplicate()
                return
            if fsm.naive and case.sources:                                     # B1: declara ao primeiro alerta
                self.declare(case_priority(list(case.sources.values())), "naive")
                return
            if not queried and case.sources:
                queried = True
                await query_neighbourhood(fsm)
            await retry_triage(fsm)
            if self.decide(deadline):
                return

    def decide(self, deadline: float) -> bool:
        """Declara ou descarta, se já for possível; devolve True quando decidiu."""
        fsm, case = self.fsm, self.fsm.case
        sources = list(case.sources.values())
        priority = case_priority(sources)
        rule = os4_branch(sources, fsm.vcfg["human_reliable_min_trust"])
        p = case.belief.probability
        if should_declare(p, priority, fsm.vcfg["tau_declare"], rule):
            self.declare(priority, rule)
            return True
        too_low = p < fsm.vcfg["discard_below"]
        if too_low or fsm.now() >= deadline:
            fsm.log("candidate_discarded", p=round(p, 4), priority=str(priority),
                    reason="belief_too_low" if too_low else "window_expired")
            self.set_next_state(DISCARD)
            return True
        return False

    def declare(self, priority, rule: str) -> None:
        """Declara o incidente e passa ao despacho (P06 a seguir, em DISPATCH)."""
        fsm, case = self.fsm, self.fsm.case
        case.priority = priority
        case.os4_rule = rule
        case.state = CaseState.DECLARED
        active = sorted(s.name for s in case.sources.values() if s.positive and not s.cancelled)
        fsm.log("case_declared", priority=str(priority), p=round(case.belief.probability, 4), rule=rule,
                cell=case.cell, sources=active, latency=round(fsm.now() - case.t_open, 2))
        self.set_next_state(DISPATCH)

    async def drop_duplicate(self) -> None:
        """P26: outro hub tem o mesmo incidente desde antes; passa-lhe os alertas e descarta este."""
        fsm, case = self.fsm, self.fsm.case
        await fsm.hub.drop_duplicate(fsm)
        fsm.log("candidate_discarded", p=round(case.belief.probability, 4), priority=str(case.priority),
                reason="merged", keeper=case.merged_into[1])
        self.set_next_state(DISCARD)


class Discard(Step):
    """Descarta o candidato: fecha a orientação que estava ativa e rotula os alertas cancelados."""

    async def step(self) -> None:
        fsm, hub, case = self.fsm, self.agent, self.fsm.case
        case.state = CaseState.DISCARDED
        for guide in sorted(case.guides | case.disclosers):       # orientação ativa, e OS11
            await fsm.send(guide, CaseClosure(case.case_id, Outcome.FALSE_ALARM, fsm.now()))
        # Uma fonte que alertou e depois foi cancelada por um humano ("estou bem", relato retirado)
        # deu um falso alerta: rótulo negativo fraco para a reputação.
        labels = [{"pseudonym": s.name, "kind": "source", "success": False, "weight": 0.5}
                  for s in case.sources.values() if s.positive and s.cancelled]
        if labels and case.merged_into is None:
            hub.log_local(OutcomeLabels(case.case_id, labels), "ReputationManager", case.case_id)
            hub.apply_outcome(case.case_id, labels)
