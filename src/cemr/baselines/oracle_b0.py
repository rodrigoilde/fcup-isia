"""Baseline B0: a centralised oracle with complete information and no latency (analysis §8.2).

For every incident it knows the exact place and time of the collapse, and every volunteer's position
and travel mode. It dispatches instantly, picking the best volunteer, AED and ambulance. It ignores
that volunteers may decline or be busy, so it is the best case for allocation (metric M9): the gap
between our system and B0 is the cost of verification, privacy (ETAs to the cell centre) and autonomy.
"""

from ..sim.geometry import CityGrid
from ..sim.incidents import Layout


def oracle_times(trace: dict, layout: Layout, cfg: dict) -> dict[str, dict]:
    travel = cfg["travel"]
    retrieval = cfg["volunteers"]["aed_retrieval_s"]
    aeds = [pos for h, pos in layout.hub_positions.items()
            if not layout.aed_faulty.get(h) and not layout.aed_closed.get(h)]
    out = {}
    for inc in trace["incidents"]:
        pos = tuple(inc["pos"])
        first = min((CityGrid.travel_time(v.pos, pos, travel[v.mode]) for v in layout.volunteers), default=None)
        aed = min((CityGrid.travel_time(v.pos, a, travel[v.mode]) + retrieval + CityGrid.travel_time(a, pos, travel[v.mode])
                   for v in layout.volunteers for a in aeds), default=None)
        ems = min((cfg["ems"]["dispatch_delay_s"] + CityGrid.travel_time(tuple(b), pos, travel["ambulance"])
                   for b in layout.ems_bases), default=None)
        out[inc["id"]] = {"first_responder_s": first, "aed_s": aed, "ems_s": ems}
    return out
