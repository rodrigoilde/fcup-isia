"""Linha de base B0: um oráculo centralizado, com informação completa e sem latência (análise §8.2).

Para cada incidente conhece o local e a hora exatos do colapso e a posição e o modo de deslocação
de todos os voluntários, e despacha logo o melhor voluntário, DAE e ambulância. Ignora que os
voluntários podem recusar ou estar ocupados, por isso é o melhor caso para a alocação (métrica M9):
a distância entre o nosso sistema e o B0 é o custo da verificação, da privacidade (ETA até ao centro
da célula) e da autonomia.
"""

from ..sim.geometry import CityGrid
from ..sim.layout import Layout


def oracle_times(trace: dict, layout: Layout, cfg: dict) -> dict[str, dict]:
    """Tempos do oráculo por incidente.

    Returns:
        dict[str, dict]: Incidente -> {first_responder_s, aed_s, ems_s}, em segundos desde o colapso.
    """
    travel = cfg["travel"]
    retrieval = cfg["volunteers"]["aed_retrieval_s"]
    aeds = [pos for h, pos in layout.hub_positions.items()
            if not layout.aed_faulty.get(h) and not layout.aed_closed.get(h)]
    out = {}
    for inc in trace["incidents"]:
        pos = tuple(inc["pos"])
        first = None
        aed = None
        for v in layout.volunteers:
            mode = travel[v.mode]
            to_patient = CityGrid.travel_time(v.pos, pos, mode)
            if first is None or to_patient < first:
                first = to_patient
            for a in aeds:
                via_aed = CityGrid.travel_time(v.pos, a, mode) + retrieval + CityGrid.travel_time(a, pos, mode)
                if aed is None or via_aed < aed:
                    aed = via_aed
        ems = None
        for base in layout.ems_bases:
            t = cfg["ems"]["dispatch_delay_s"] + CityGrid.travel_time(tuple(base), pos, travel["ambulance"])
            if ems is None or t < ems:
                ems = t
        out[inc["id"]] = {"first_responder_s": first, "aed_s": aed, "ems_s": ems}
    return out
