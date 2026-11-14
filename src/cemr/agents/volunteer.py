"""VolunteerAgent: papéis VolunteerResponder (R5) e AEDRunner (R6), conforme a tarefa adjudicada.

O voluntário avalia cada call for proposals no seu telemóvel (_EvaluateAlertLocally): a posição
nunca sai do telemóvel, só o ETA (D3). Depois de uma adjudicação corre a FSM `Mission`
(em `volunteer_mission`).

OS2: no máximo um compromisso ativo. OS8: as chamadas acima de A_max alertas por hora ou de K_max
adjudicações recentes são recusadas pela app sem incomodar o voluntário ("alert_shown" conta as
que chegam à pessoa). Modelo de comportamento (A6): com probabilidade p_no_show um voluntário
adjudicado desiste a caminho (WITHDRAWN) ou nunca aparece sem dizer nada; a viagem real demora
0 a 30 % mais do que a estimativa. Isto dá trabalho ao OL6 (novo recrutamento) e ao OL8 (dispensa
dos excedentes). Desenho em docs/03-detailed-design.md §2.5.
"""

from collections import deque

from ..protocol.messages_assistance import ActionSummary
from ..protocol.messages_dispatch import (Award, AwardConfirmation, AwardFailure, AwardRejection, CallForProposals,
                                          Proposal, ProposalRefusal)
from ..protocol.messages_hubs import RegistrationAck, Takeover
from ..protocol.messages_response import CaseClosure, Release
from ..protocol.ontology import Qualification, RegistrationRole, TaskType
from ..sim.directory import Directory
from ..sim.layout import VolunteerProfile
from .base import CEMRAgent
from .conversation import Incoming
from .volunteer_mission import HOUR_S, Mission


class VolunteerAgent(CEMRAgent):
    """Voluntário: agente baseado em utilidade (Russell e Norvig, 2022).

    A app escolhe o DAE e calcula o ETA que minimizam o tempo de chegada; a decisão de aceitar é um
    modelo humano estocástico (`volunteers.p_accept`).

    Attributes:
        mode (str): Modo de deslocação.
        qualification (str): Qualificação.
        commitment (str | None): Caso com que está comprometido (OS2).
    """

    KIND = "volunteer"

    def __init__(self, idx: int, ctx, profile: VolunteerProfile):
        super().__init__(Directory.volunteer(idx), ctx, profile.pos)
        self.mode = profile.mode
        self.qualification = profile.qualification

    async def on_setup(self) -> None:
        self.commitment: str | None = None
        self.alert_times: deque[float] = deque()
        self.award_times: deque[float] = deque()
        await self.register_with_hubs(RegistrationRole.VOLUNTEER, self.qualification)

    @property
    def travel_mode(self) -> dict:
        """Velocidade e tempo de preparação do modo de deslocação."""
        return self.cfg["travel"][self.mode]

    async def on_message(self, inc: Incoming) -> None:
        p = inc.payload
        if isinstance(p, CallForProposals):
            self.spawn(lambda: self.evaluate_call(inc), "evaluate_call")
        elif isinstance(p, Award):
            await self.on_award(inc, p)
        elif isinstance(p, (AwardRejection, RegistrationAck, CaseClosure, Release, Takeover, ActionSummary)):
            pass
        else:
            await super().on_message(inc)

    def over_load_cap(self) -> bool:
        """OS8: se o voluntário já viu A_max alertas na última hora ou teve K_max adjudicações recentes."""
        vcfg = self.cfg["volunteers"]
        now = self.now()
        while self.alert_times and now - self.alert_times[0] > HOUR_S:
            self.alert_times.popleft()
        while self.award_times and now - self.award_times[0] > vcfg["award_window_s"]:
            self.award_times.popleft()
        too_many_alerts = len(self.alert_times) >= vcfg["max_alerts_per_hour"]
        too_many_awards = len(self.award_times) >= vcfg["max_consecutive_awards"]
        return too_many_alerts or too_many_awards

    async def evaluate_call(self, inc: Incoming) -> None:
        """_EvaluateAlertLocally (P08): decide e calcula os ETA no telemóvel; só o ETA é enviado."""
        cfp: CallForProposals = inc.payload
        vcfg = self.cfg["volunteers"]
        await self.sleep(self.uniform(vcfg["eval_delay_s"]))
        # O limite de carga (OS8) vem primeiro: os alertas de um voluntário ocupado também chegam à pessoa.
        if self.over_load_cap():
            await self.reply(inc, ProposalRefusal(cfp.case_id, "load_cap"))
            return
        self.alert_times.append(self.now())
        self.log("alert_shown", case=cfp.case_id)
        reason = None
        if self.commitment:
            reason = "busy"
        elif self.rng.random() >= vcfg["p_accept"]:
            reason = "declined"
        offers = [] if reason else self.compute_offers(cfp)
        if reason is None and not offers:
            reason = "unqualified"
        if reason:
            await self.reply(inc, ProposalRefusal(cfp.case_id, reason))
        else:
            await self.reply(inc, Proposal(cfp.case_id, offers, self.qualification))

    def compute_offers(self, cfp: CallForProposals) -> list[dict]:
        """ETA de cada tarefa que o voluntário pode fazer, até ao centro da célula do caso."""
        grid = self.world.grid
        here = self.pos()
        target = grid.centroid(cfp.cell)
        mode = self.travel_mode
        offers = []
        qualified = Qualification(self.qualification).rank >= Qualification(cfp.min_qualification).rank
        if TaskType.GO_TO_PATIENT in cfp.tasks and qualified:
            eta = grid.travel_time(here, target, mode)
            offers.append({"task": TaskType.GO_TO_PATIENT.value, "eta_s": round(eta, 1)})
        if TaskType.FETCH_AED in cfp.tasks and cfp.candidate_aeds:
            best_eta = None
            best_aed = None
            for aed in cfp.candidate_aeds:
                aed_pos = tuple(aed["pos"])
                travel = grid.travel_time(here, aed_pos, mode) + grid.travel_time(aed_pos, target, mode)
                if best_eta is None or travel < best_eta:
                    best_eta = travel
                    best_aed = aed["aed_id"]
            eta = best_eta + self.cfg["volunteers"]["aed_retrieval_s"]
            offers.append({"task": TaskType.FETCH_AED.value, "eta_s": round(eta, 1), "aed_id": best_aed})
        return offers

    async def on_award(self, inc: Incoming, award: Award) -> None:
        """P09: aceita a adjudicação se estiver livre (OS2) e começa a missão."""
        if self.commitment is not None:
            await self.reply(inc, AwardFailure(award.case_id, "busy"))
            return
        self.commitment = award.case_id
        self.award_times.append(self.now())
        await self.reply(inc, AwardConfirmation(award.case_id, award.task))
        vcfg = self.cfg["volunteers"]
        no_show = None
        if self.rng.random() < vcfg["p_no_show"]:
            no_show = "withdraw" if self.rng.random() < vcfg["p_withdraw_if_no_show"] else "silent"
        slowdown = self.uniform(vcfg["speed_variability"])
        self.log("committed", case=award.case_id, task=award.task, no_show=no_show)
        self.open_conversation(Mission(self, award, inc.sender, inc.thread, no_show, slowdown))

    async def mission_finished(self, mission: Mission) -> None:
        """Fim da missão: fica onde está, livre, e volta a registar-se nos hubs da nova célula."""
        self.commitment = None
        self.world.teleport(self.label, self.pos())
        self.log("mission_end", case=mission.award.case_id)
        await self.register_with_hubs(RegistrationRole.VOLUNTEER, self.qualification)
