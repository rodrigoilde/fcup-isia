"""Run one simulation.

    python -m cemr.run --scenario c1 --seed 1 [--duration 900] [--factor 10] [--external]

Writes runs/<scenario>-s<seed>-<timestamp>/ with events.jsonl (event and audit log), trace.json
(ground truth), config.json and summary.json (metrics and a validity verdict).
Exit codes: 0 ok, 1 crash, 2 agent errors logged, 3 invalid run (clock did not advance as intended,
e.g. the laptop slept). For long experiments run on AC power under `caffeinate -i`.
--external connects to a server started with `spade run --host localhost --memory`; this is how
parallel runs share one server (each run gets its own JID prefix).
"""

import argparse
import asyncio
import json
import logging
import os
import random
import sys
import time
from pathlib import Path

import spade

from .agents.aed_hub import AEDHubAgent
from .agents.bystander import BystanderAgent
from .agents.citizen_device import CitizenDeviceAgent
from .agents.ems import EMSAgent
from .agents.volunteer import VolunteerAgent
from .config import REPO_ROOT, load_config
from .baselines.oracle_b0 import oracle_times
from .metrics.check import check, summary_line
from .metrics.compute import summarize
from .metrics.eventlog import EventLog
from .sim.clock import SimClock
from .sim.context import SimContext, start_agents
from .sim.directory import Directory
from .sim.geometry import CityGrid
from .sim.incidents import generate_layout, generate_trace, trace_hash
from .sim.network import NetworkModel
from .sim.world import World


def build(cfg: dict, out_dir: Path, prefix: str):
    run = cfg["run"]
    seed = run["seed"]
    clock = SimClock(run["clock_factor"])
    log = EventLog(clock, out_dir / "events.jsonl")
    layout = generate_layout(cfg, random.Random(f"{seed}/layout"))
    grid = CityGrid(cfg["city"]["size_m"], cfg["city"]["grid_spacing_m"], layout.hub_positions)
    trace = generate_trace(cfg, layout, grid, random.Random(f"{seed}/trace"), run["duration_s"])
    world = World(cfg, grid, layout, clock, log)
    net = NetworkModel(cfg, random.Random(f"{seed}/network"), clock, world)
    directory = Directory(prefix, hubs=layout.hub_positions, ems_units=len(layout.ems_bases))
    ctx = SimContext(cfg, clock, world, net, log, directory, seed)
    agents = [AEDHubAgent(h, ctx) for h in sorted(layout.hub_positions)]          # hubs first: others register
    agents += [EMSAgent(i, ctx, base) for i, base in enumerate(layout.ems_bases)]
    agents += [VolunteerAgent(i, ctx, p) for i, p in enumerate(layout.volunteers)]
    agents += [CitizenDeviceAgent(i, ctx, pos) for i, pos in enumerate(layout.devices)]
    agents += [BystanderAgent(i, ctx, pos) for i, pos in enumerate(layout.bystanders)]
    return ctx, layout, grid, trace, agents


async def simulate(cfg: dict, out_dir: Path, prefix: str, quiet: bool = False, viz_port: int | None = None) -> dict:
    ctx, layout, grid, trace, agents = build(cfg, out_dir, prefix)
    run = cfg["run"]
    viz = None
    if viz_port:                                   # live dashboard: subscribe before any agent logs anything
        from .viz.server import VizServer
        viz = VizServer(viz_port, "live", title=f"{run['name']} · seed {run['seed']}")
        await viz.start()
        ctx.log.subscribe(viz.publish)
    (out_dir / "config.json").write_text(json.dumps(cfg, indent=2))
    (out_dir / "trace.json").write_text(json.dumps({"layout": layout.to_json(), **trace}, indent=1))
    t0 = time.monotonic()
    failures = await start_agents(agents, run["start_batch"], run["start_retries"])
    if failures:
        raise RuntimeError(f"{len(failures)} agents failed to start, e.g. {failures[0]}")
    ctx.clock.start()
    ctx.log.write("run_start", scenario=run["name"], seed=run["seed"], factor=run["clock_factor"],
                  duration=run["duration_s"], trace_hash=trace_hash(trace), agents=len(agents),
                  cells={str(c): {"hub": list(grid.hub_positions[c]), "neighbours": sorted(grid.neighbours[c])}
                         for c in grid.cells},
                  start_real_s=round(time.monotonic() - t0, 2))
    if not quiet:
        print(f"{len(agents)} agents started in {time.monotonic() - t0:.1f}s; running {run['duration_s']} s "
              f"simulated at {run['clock_factor']}x (~{run['duration_s'] / run['clock_factor']:.0f} s real)")
    world_task = asyncio.create_task(ctx.world.run(trace))
    fault_tasks = [asyncio.create_task(crash_hub(ctx, agents, f["hub"], f["at_s"]))
                   for f in cfg["faults"]["hub_crashes"]]
    stall = {"max": 0.0}

    async def watchdog(period: float = 0.5):
        while True:
            t = time.monotonic()
            await asyncio.sleep(period)
            stall["max"] = max(stall["max"], time.monotonic() - t - period)

    watchdog_task = asyncio.create_task(watchdog())
    wall0, mono0 = time.time(), time.monotonic()
    try:
        await ctx.clock.sleep(run["duration_s"])
    finally:
        world_task.cancel()
        watchdog_task.cancel()
        for task in fault_tasks:
            task.cancel()
        ctx.log.write("run_end")
        await asyncio.gather(*(a.stop() for a in agents), return_exceptions=True)
        ctx.log.close()
    summary = summarize(ctx.log.records, run["duration_s"], oracle_times(trace, layout, cfg), cfg["city"]["size_m"])
    summary["trace_hash"] = trace_hash(trace)
    summary["rules"] = summary_line(check(ctx.log.records, cfg))
    summary.update(validity(run, ctx.clock.now(), time.time() - wall0, time.monotonic() - mono0, stall["max"]))
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    if viz is not None:
        await viz.stop()
    return summary


async def crash_hub(ctx: SimContext, agents: list, hub_id: int, at_s: float) -> None:
    """Fault injection: crash-stop a hub (F6). Its messages are dropped from then on."""
    await ctx.clock.sleep_until(at_s)
    name = Directory.hub(hub_id)
    ctx.net.down.add(name)
    ctx.log.write("fault_hub_crash", agent=name, hub=hub_id)
    agent = next(a for a in agents if a.label == name)
    await agent.stop()


def validity(run: dict, reached: float, wall_s: float, mono_s: float, max_stall_s: float) -> dict:
    """A run is valid only if simulated time really advanced as intended.

    Laptop sleep (e.g. closing the lid) suspends the process: the simulated clock stops while timers
    and the wall clock do not, and the run ends early. A stalled event loop shifts every timer by
    stall x factor simulated seconds.
    """
    problems = []
    if reached < run["duration_s"] - 1.0:
        problems.append(f"simulated clock reached only {reached:.0f} of {run['duration_s']:.0f} s")
    if wall_s - mono_s > 2.0:
        problems.append(f"system suspended for ~{wall_s - mono_s:.0f} s (sleep or lid closed)")
    if max_stall_s * run["clock_factor"] > 2.0:
        problems.append(f"event loop stalled {max_stall_s:.2f} s real = {max_stall_s * run['clock_factor']:.1f} s simulated")
    return {"valid": not problems, "validity_problems": problems, "real_seconds": round(wall_s, 1),
            "max_loop_stall_s": round(max_stall_s, 3)}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run one CEMR simulation.")
    parser.add_argument("--scenario", default="c1", help="scenario id or file (default: c1)")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--duration", type=float, help="simulated seconds")
    parser.add_argument("--factor", type=float, help="clock acceleration")
    parser.add_argument("--out", type=Path, help="output directory")
    parser.add_argument("--prefix", help="JID prefix (unique per parallel run)")
    parser.add_argument("--external", action="store_true", help="use a running `spade run --host localhost`")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                        help="override a parameter, e.g. --set sensors.policy=alert_first (repeatable)")
    parser.add_argument("--viz", type=int, metavar="PORT", help="serve the live dashboard on this port")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def parse_overrides(items: list[str]) -> dict:
    """'a.b.c=value' -> {'a': {'b': {'c': value}}}; the value is read as TOML, else kept as a string."""
    import tomllib
    result: dict = {}
    for item in items:
        key, _, raw = item.partition("=")
        try:
            value = tomllib.loads(f"v = {raw}")["v"]
        except tomllib.TOMLDecodeError:
            value = raw
        node = result
        *path, last = key.strip().split(".")
        for part in path:
            node = node.setdefault(part, {})
        node[last] = value
    return result


def main(argv=None) -> int:
    args = parse_args(argv)
    overrides = parse_overrides(args.set)
    overrides.setdefault("run", {}).update({k: v for k, v in (("seed", args.seed), ("duration_s", args.duration),
                                                              ("clock_factor", args.factor)) if v is not None})
    cfg = load_config(args.scenario, overrides)
    run = cfg["run"]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = args.out or REPO_ROOT / "runs" / f"{run['name']}-s{run['seed']}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix or f"{run['name'].split('_')[0]}s{run['seed']}p{os.getpid()}"
    logging.getLogger("spade").setLevel(logging.ERROR)
    logging.getLogger("slixmpp").setLevel(logging.ERROR)

    result: dict = {}

    async def runner():
        try:
            result["summary"] = await simulate(cfg, out_dir, prefix, args.quiet, args.viz)
        except Exception as exc:  # noqa: BLE001 - spade.run swallows exceptions, so report them here
            import traceback
            traceback.print_exc()
            result["error"] = exc

    spade.run(runner(), embedded_xmpp_server=not args.external)
    if "error" in result or "summary" not in result:
        return 1
    summary = result["summary"]
    if not args.quiet:
        print(json.dumps(summary, indent=2))
        print(f"output: {out_dir}")
    if not summary["valid"]:
        print("INVALID RUN: " + "; ".join(summary["validity_problems"]), file=sys.stderr)
        return 3
    return 0 if summary["errors"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
