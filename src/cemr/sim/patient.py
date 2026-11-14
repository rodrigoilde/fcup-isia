"""Modelo do doente (recurso patientCondition, pressuposto A4) e aproximação de sobrevivência da métrica M6.

Larsen et al. (1993), para paragem testemunhada em fibrilhação ventricular:

    sobrevivência (%) = 67 - 2,3 * t_RCP - 1,1 * t_desfibrilhação - 2,1 * t_SAV

com os intervalos em minutos desde o colapso. Só serve para comparar estratégias (análise §8.1),
nunca como previsão clínica.
"""

from dataclasses import dataclass

from .geometry import Pos


@dataclass
class PatientState:
    """Estado de um doente, alterado pelos agentes que estão no local.

    Attributes:
        incident_id (str): Incidente da verdade de referência.
        priority (str): P1, P2 ou P3 (triagem operacional, análise §2.2).
        shockable (bool): Se o ritmo é desfibrilhável.
        collapse_t (float): Instante do colapso.
        pos (Pos): Posição do doente.
        cpr_start_t (float | None): Início da RCP.
        aed_attached_t (float | None): Quando o DAE foi colocado.
        first_shock_t (float | None): Primeiro choque.
        shocks (int): Número de choques.
        ems_arrival_t (float | None): Chegada da ambulância.
    """

    incident_id: str
    priority: str
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
        """Só um P3 responde."""
        return self.priority == "P3"

    @property
    def breathing_normally(self) -> bool:
        """Só um P1 não respira normalmente."""
        return self.priority != "P1"

    @property
    def needs_cpr(self) -> bool:
        """Um P1 precisa de RCP."""
        return self.priority == "P1"


def larsen_survival(t_cpr_min: float, t_defib_min: float, t_als_min: float) -> float:
    """Sobrevivência estimada (%) com a fórmula de Larsen et al. (1993), nunca abaixo de 0."""
    return max(0.0, 67.0 - 2.3 * t_cpr_min - 1.1 * t_defib_min - 2.1 * t_als_min)


def estimated_survival(patient: PatientState, ems_shock_delay_s: float,
                       horizon_t: float | None = None) -> float | None:
    """Métrica M6 para um doente; só é definida para P1 com ritmo desfibrilhável.

    Se a ambulância não chegou dentro do run, `horizon_t` faz de instante de chegada, o que dá uma
    estimativa conservadora. Quando ninguém fez RCP ou desfibrilhou antes, conta a equipa da EMS.

    Args:
        patient (PatientState): Doente.
        ems_shock_delay_s (float): Atraso do primeiro choque da equipa da EMS depois de chegar.
        horizon_t (float | None): Instante usado se a ambulância não chegou.

    Returns:
        float | None: Sobrevivência estimada em %, ou None se não se aplica.
    """
    if patient.priority != "P1" or not patient.shockable:
        return None
    ems = patient.ems_arrival_t if patient.ems_arrival_t is not None else horizon_t
    if ems is None:
        return None
    cpr = ems if patient.cpr_start_t is None else min(patient.cpr_start_t, ems)
    defib = ems + ems_shock_delay_s
    if patient.first_shock_t is not None:
        defib = min(patient.first_shock_t, defib)

    def minutes(t: float) -> float:
        return max(0.0, t - patient.collapse_t) / 60.0

    return larsen_survival(minutes(cpr), minutes(defib), minutes(ems))
