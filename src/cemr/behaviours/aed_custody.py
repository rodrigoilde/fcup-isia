"""Máquina de estados de um armário de DAE, mantida pelo seu hub no papel AEDCustodian (R7).

    AVAILABLE -> RESERVED (P11) -> IN_USE (P12) -> UNAVAILABLE (depois do caso, até ser reposto) -> AVAILABLE

Uma reserva que expira ou é cancelada devolve o DAE a AVAILABLE. OS3: cada DAE tem no máximo uma
reserva ativa. O código de abertura é de uso único e só vale com a referência da reserva e o token
da adjudicação do caso. Desenho em docs/03-detailed-design.md §4.4.
"""

import random
from dataclasses import dataclass

from ..protocol.ontology import AEDState


@dataclass
class Reservation:
    """Reserva de um DAE para um caso.

    Attributes:
        ref (str): Referência que o estafeta apresenta no armário.
        case_id (str): Caso que fez a reserva.
        token (str): Token da adjudicação, conferido na recolha.
        expires_at (float): Instante simulado em que a reserva expira.
        retrieved (bool): Se o DAE já foi levantado.
    """

    ref: str
    case_id: str
    token: str
    expires_at: float
    retrieved: bool = False


class AEDCustody:
    """Estado de um armário de DAE e das suas reservas.

    Attributes:
        aed_id (int): Identificador do DAE (igual ao do hub).
        faulty (bool): Se o DAE falta ou está avariado (F8); só se descobre na recolha.
        closed (bool): Se o armário está fechado fora de horas (C4).
        state (AEDState): Estado atual.
        reservation (Reservation | None): Reserva ativa, se houver.
    """

    def __init__(self, aed_id: int, faulty: bool, rng: random.Random, closed: bool = False):
        self.aed_id = aed_id
        self.faulty = faulty
        self.closed = closed
        self.rng = rng
        self.state = AEDState.UNAVAILABLE if closed else AEDState.AVAILABLE
        self.reservation: Reservation | None = None
        self.counter = 0

    def expire(self, now: float) -> None:
        """Liberta o DAE se a reserva expirou sem o DAE ter sido levantado."""
        r = self.reservation
        if r is not None and not r.retrieved and now >= r.expires_at:
            self.reservation = None
            self.state = AEDState.AVAILABLE

    def reserve(self, case_id: str, token: str, valid_for: float, now: float) -> tuple[bool, str]:
        """Reserva o DAE para um caso (P11).

        Returns:
            tuple[bool, str]: (True, referência da reserva) ou (False, motivo da recusa).
        """
        self.expire(now)
        if self.state == AEDState.RESERVED:
            return False, "reserved"
        if self.state == AEDState.IN_USE:
            return False, "in_use"
        if self.state == AEDState.UNAVAILABLE:
            return False, "unavailable"
        self.counter += 1
        ref = f"aed{self.aed_id}-r{self.counter}"
        self.reservation = Reservation(ref, case_id, token, now + valid_for)
        self.state = AEDState.RESERVED
        return True, ref

    def cancel(self, ref: str) -> bool:
        """Cancela uma reserva ainda não levantada; devolve True se a cancelou."""
        r = self.reservation
        if r is None or r.ref != ref or r.retrieved:
            return False
        self.reservation = None
        self.state = AEDState.AVAILABLE
        return True

    def retrieve(self, ref: str, token: str, now: float) -> tuple[bool, str]:
        """Abre o armário para o estafeta adjudicado (P12).

        Returns:
            tuple[bool, str]: (True, código de abertura) ou (False, motivo da falha).
        """
        self.expire(now)
        r = self.reservation
        if r is None or r.ref != ref or r.token != token or r.retrieved:
            return False, "invalid_reservation"
        if self.faulty:
            self.reservation = None
            self.state = AEDState.UNAVAILABLE
            return False, "missing_or_faulty"
        r.retrieved = True
        self.state = AEDState.IN_USE
        return True, f"{self.rng.randrange(10**6):06d}"

    def release(self, ref: str) -> AEDState:
        """Fecho do caso (P20): um DAE usado fica fora de serviço até ser reposto; um não usado fica livre."""
        r = self.reservation
        if r is None or r.ref != ref:
            return self.state
        self.reservation = None
        if r.retrieved:
            self.state = AEDState.UNAVAILABLE
        else:
            self.state = AEDState.AVAILABLE
        return self.state

    def restock(self) -> AEDState:
        """Reposição do DAE depois de usado (se não estiver avariado nem o armário fechado)."""
        if self.state == AEDState.UNAVAILABLE and not self.faulty and not self.closed:
            self.state = AEDState.AVAILABLE
        return self.state
