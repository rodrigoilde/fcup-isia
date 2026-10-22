"""Patient model (resource patientCondition, assumption A4) and the survival proxy of metric M6.

Larsen et al. (1993), for witnessed VF arrest: survival(%) = 67 - 2.3*t_CPR - 1.1*t_defib - 2.1*t_ALS,
with intervals in minutes from collapse. It is used only to compare strategies (analysis §8.1), never
as a clinical prediction.
"""

from dataclasses import dataclass

from .geometry import Pos

# Without a bystander AED, the first shock comes from the EMS crew about a minute after arrival.
EMS_SHOCK_DELAY_S = 60.0


@dataclass
class PatientState:
    incident_id: str
    priority: str          # P1 | P2 | P3 (operational triage, analysis §2.2)
    shockable: bool
    collapse_t: float
    pos: Pos
    cpr_start_t: float | None = None
    aed_attached_t: float | None = None
    first_shock_t: float | None = None
    shocks: int = 0
    ems_arrival_t: float | None = None

    @property
    def responsive(self) -> bool:
        return self.priority == "P3"

    @property
    def breathing_normally(self) -> bool:
        return self.priority != "P1"

    @property
    def needs_cpr(self) -> bool:
        return self.priority == "P1"


def larsen_survival(t_cpr_min: float, t_defib_min: float, t_als_min: float) -> float:
    return max(0.0, 67.0 - 2.3 * t_cpr_min - 1.1 * t_defib_min - 2.1 * t_als_min)


def estimated_survival(patient: PatientState, horizon_t: float | None = None) -> float | None:
    """M6 for one patient: only defined for shockable P1 cases.

    If EMS never arrived within the run, `horizon_t` stands in for its arrival, which gives a
    conservative estimate. CPR and defibrillation fall back to the EMS crew when no one else did them.
    """
    if patient.priority != "P1" or not patient.shockable:
        return None
    ems = patient.ems_arrival_t if patient.ems_arrival_t is not None else horizon_t
    if ems is None:
        return None
    cpr = min(t for t in (patient.cpr_start_t, ems) if t is not None)
    defib = min(t for t in (patient.first_shock_t, ems + EMS_SHOCK_DELAY_S) if t is not None)
    minutes = lambda t: max(0.0, t - patient.collapse_t) / 60.0  # noqa: E731
    return larsen_survival(minutes(cpr), minutes(defib), minutes(ems))
