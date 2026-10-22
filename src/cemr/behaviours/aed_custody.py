"""State machine of one AED cabinet, kept by its hub in the AEDCustodian role (R7).

AVAILABLE -> RESERVED (P11) -> IN_USE (P12) -> UNAVAILABLE (after the case, until restocked) -> AVAILABLE
A reservation that expires or is cancelled returns the AED to AVAILABLE.
OS3: at most one active reservation per AED. The unlock code is single use and only valid with
the reservation reference and the award token of the case.
"""

import random
from dataclasses import dataclass

from ..protocol.ontology import AEDState


@dataclass
class Reservation:
    ref: str
    case_id: str
    token: str
    expires_at: float
    retrieved: bool = False


class AEDCustody:
    def __init__(self, aed_id: int, faulty: bool, rng: random.Random, closed: bool = False):
        self.aed_id = aed_id
        self.faulty = faulty
        self.closed = closed                 # cabinet locked outside its opening hours (C4)
        self.rng = rng
        self.state = AEDState.UNAVAILABLE if closed else AEDState.AVAILABLE
        self.reservation: Reservation | None = None
        self._counter = 0

    def expire(self, now: float) -> bool:
        r = self.reservation
        if r is not None and not r.retrieved and now >= r.expires_at:
            self.reservation = None
            self.state = AEDState.AVAILABLE
            return True
        return False

    def reserve(self, case_id: str, token: str, valid_for: float, now: float) -> tuple[bool, str]:
        """Returns (True, reservation_ref) or (False, reason)."""
        self.expire(now)
        if self.state == AEDState.RESERVED:
            return False, "reserved"
        if self.state == AEDState.IN_USE:
            return False, "in_use"
        if self.state == AEDState.UNAVAILABLE:
            return False, "unavailable"
        self._counter += 1
        ref = f"aed{self.aed_id}-r{self._counter}"
        self.reservation = Reservation(ref, case_id, token, now + valid_for)
        self.state = AEDState.RESERVED
        return True, ref

    def cancel(self, ref: str) -> bool:
        r = self.reservation
        if r is None or r.ref != ref or r.retrieved:
            return False
        self.reservation = None
        self.state = AEDState.AVAILABLE
        return True

    def retrieve(self, ref: str, token: str, now: float) -> tuple[bool, str]:
        """Returns (True, access_code) or (False, reason)."""
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
        """Case closed: a used AED goes out of service until restocked; an unused one is freed."""
        r = self.reservation
        if r is None or r.ref != ref:
            return self.state
        self.reservation = None
        self.state = AEDState.UNAVAILABLE if r.retrieved else AEDState.AVAILABLE
        return self.state

    def restock(self) -> AEDState:
        if self.state == AEDState.UNAVAILABLE and not self.faulty and not self.closed:
            self.state = AEDState.AVAILABLE
        return self.state
