"""Corre uma simulação.

    python -m cemr.run --scenario c1 --seed 1 [--duration 900] [--factor 10] [--xmpp-port 15222]

Escreve runs/<cenário>-s<seed>-<data>/ com events.jsonl (registo de eventos e de auditoria),
trace.json (verdade de referência), config.json e summary.json (métricas e validade do run).
Códigos de saída: 0 tudo bem, 1 falha, 2 erros registados pelos agentes, 3 run inválido (o relógio
não avançou como devia, por exemplo porque o portátil suspendeu). Experiências longas: ligado à
corrente e sem fechar a tampa.
"""

import argparse
import asyncio
import json
import logging
import random
import subprocess
import sys
import time
import tomllib
import traceback
from pathlib import Path

import spade

from .agents.aed_hub import AEDHubAgent
from .agents.bystander import BystanderAgent
from .agents.citizen_device import CitizenDeviceAgent
from .agents.ems import EMSAgent
from .agents.volunteer import VolunteerAgent
from .baselines.oracle_b0 import oracle_times
from .config import REPO_ROOT, load_config
from .metrics.check import check, summary_line
from .metrics.compute import summarize
from .metrics.eventlog import EventLog
from .sim.clock import SimClock
from .sim.context import SimContext, start_agents
from .sim.directory import Directory
from .sim.geometry import CityGrid
from .sim.incidents import generate_trace, trace_hash
from .sim.layout import generate_layout
from .sim.network import NetworkModel
from .sim.world import World


def build(cfg: dict, out_dir: Path, xmpp_port: int):
    """Cria o ambiente, o traço e os agentes de um run a partir da configuração e da seed."""
    run = cfg["run"]
    seed = run["seed"]
    clock = SimClock(run["clock_factor"])
    log = EventLog(clock, out_dir / "events.jsonl")
    layout = generate_layout(cfg, random.Random(f"{seed}/layout"))
    grid = CityGrid(cfg["city"]["size_m"], cfg["city"]["grid_spacing_m"], layout.hub_positions)
    trace = generate_trace(cfg, layout, grid, random.Random(f"{seed}/trace"), run["duration_s"])
    world = World(cfg, grid, layout, clock, log)
    net = NetworkModel(cfg, random.Random(f"{seed}/network"), clock, world)
    directory = Directory(hubs=layout.hub_positions, ems_units=len(layout.ems_bases))
    ctx = SimContext(cfg, clock, world, net, log, directory, seed, xmpp_port=xmpp_port)
    agents = [AEDHubAgent(h, ctx) for h in sorted(layout.hub_positions)]          # hubs primeiro: os outros registam-se
    agents += [EMSAgent(i, ctx, base) for i, base in enumerate(layout.ems_bases)]
    agents += [VolunteerAgent(i, ctx, p) for i, p in enumerate(layout.volunteers)]
    agents += [CitizenDeviceAgent(i, ctx, pos) for i, pos in enumerate(layout.devices)]
    agents += [BystanderAgent(i, ctx, pos) for i, pos in enumerate(layout.bystanders)]
    return ctx, layout, trace, agents


def code_version() -> dict:
    """Commit git do código e se havia alterações por commitar em src/, scenarios/ ou experiments/."""
    def git(*args: str) -> str:
        result = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
        return result.stdout.strip()

    return {"commit": git("rev-parse", "HEAD"),
            "dirty": bool(git("status", "--porcelain", "--", "src", "scenarios", "experiments"))}


def write_inputs(cfg: dict, out_dir: Path, layout, trace: dict) -> None:
    """Guarda a configuração e o traço do run."""
    (out_dir / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    trace_file = {"layout": layout.to_json(), **trace}
    (out_dir / "trace.json").write_text(json.dumps(trace_file, indent=1), encoding="utf-8")


async def crash_hub(ctx: SimContext, agents: list, hub_id: int, at_s: float) -> None:
    """Injeção de falhas: o hub para (F6); a partir daí as suas mensagens perdem-se."""
    await ctx.clock.sleep_until(at_s)
    name = Directory.hub(hub_id)
    ctx.net.down.add(name)
    ctx.log.write("fault_hub_crash", agent=name, hub=hub_id)
    agent = next(a for a in agents if a.label == name)
    await agent.stop()


async def watchdog(stall: dict, period: float = 0.5) -> None:
    """Mede a maior paragem do event loop (um loop parado atrasa todos os temporizadores)."""
    while True:
        t = time.monotonic()
        await asyncio.sleep(period)
        stall["max"] = max(stall["max"], time.monotonic() - t - period)


def validity(run: dict, reached: float, wall_s: float, mono_s: float, max_stall_s: float) -> dict:
    """Um run só é válido se o tempo simulado avançou mesmo como devia.

    Suspender o portátil (fechar a tampa) suspende o processo: o relógio simulado para, mas os
    temporizadores e o relógio de parede não, e o run acaba antes do tempo. Um event loop parado
    atrasa todos os temporizadores em paragem x fator segundos simulados.
    """
    problems = []
    if reached < run["duration_s"] - 1.0:
        problems.append(f"simulated clock reached only {reached:.0f} of {run['duration_s']:.0f} s")
    if wall_s - mono_s > run["max_suspend_s"]:
        problems.append(f"system suspended for ~{wall_s - mono_s:.0f} s (sleep or lid closed)")
    stall_sim = max_stall_s * run["clock_factor"]
    if stall_sim > run["max_stall_sim_s"]:
        problems.append(f"event loop stalled {max_stall_s:.2f} s real = {stall_sim:.1f} s simulated")
    return {"valid": not problems, "validity_problems": problems, "real_seconds": round(wall_s, 1),
            "max_loop_stall_s": round(max_stall_s, 3)}


async def run_clock(ctx: SimContext, cfg: dict, agents: list, trace: dict) -> dict:
    """Corre o ambiente durante o tempo simulado do run e devolve as medidas de validade."""
    run = cfg["run"]
    world_task = asyncio.create_task(ctx.world.run(trace))
    fault_tasks = []
    for fault in cfg["faults"]["hub_crashes"]:
        fault_tasks.append(asyncio.create_task(crash_hub(ctx, agents, fault["hub"], fault["at_s"])))
    stall = {"max": 0.0}
    watchdog_task = asyncio.create_task(watchdog(stall))
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
    return validity(run, ctx.clock.now(), time.time() - wall0, time.monotonic() - mono0, stall["max"])


async def simulate(cfg: dict, out_dir: Path, quiet: bool = False, viz_port: int | None = None,
                   xmpp_port: int = 5222) -> dict:
    """Corre um run completo e devolve o summary.json."""
    ctx, layout, trace, agents = build(cfg, out_dir, xmpp_port)
    run = cfg["run"]
    viz = None
    if viz_port:                                   # dashboard ao vivo: subscreve antes de qualquer agente registar
        from .viz.server import VizServer
        viz = VizServer(viz_port, "live", title=f"{run['name']} · seed {run['seed']}")
        await viz.start()
        ctx.log.subscribe(viz.publish)
    write_inputs(cfg, out_dir, layout, trace)
    t0 = time.monotonic()
    failures = await start_agents(agents, run["start_batch"], run["start_retries"])
    if failures:
        raise RuntimeError(f"{len(failures)} agents failed to start, e.g. {failures[0]}")
    ctx.clock.start()
    cells = {str(c): {"hub": list(ctx.world.grid.hub_positions[c]), "neighbours": sorted(ctx.world.grid.neighbours[c])}
             for c in ctx.world.grid.cells}
    ctx.log.write("run_start", scenario=run["name"], seed=run["seed"], factor=run["clock_factor"],
                  duration=run["duration_s"], trace_hash=trace_hash(trace), agents=len(agents), cells=cells,
                  start_real_s=round(time.monotonic() - t0, 2))
    if not quiet:
        print(f"{len(agents)} agents started in {time.monotonic() - t0:.1f}s; running {run['duration_s']} s "
              f"simulated at {run['clock_factor']}x (~{run['duration_s'] / run['clock_factor']:.0f} s real)")
    valid = await run_clock(ctx, cfg, agents, trace)
    summary = summarize(ctx.log.records, cfg, oracle_times(trace, layout, cfg))
    summary["trace_hash"] = trace_hash(trace)
    summary["rules"] = summary_line(check(ctx.log.records, cfg))
    summary["code"] = cfg["code"]
    summary.update(valid)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if viz is not None:
        await viz.stop()
    return summary


async def start_private_server(port: int):
    """Servidor pyjabber dentro do processo na porta `port` (s2s em port + 1), para runs em paralelo.

    Cada run da matriz tem o seu servidor, porque no Windows um servidor partilhado (`spade run`)
    demora muito a fazer o login de 4 x 100 agentes. O plugin de upload HTTP fica de fora: a sua
    página de administração usa sempre a porta 9090, que os servidores em paralelo disputariam.
    """
    import loguru
    from pyjabber.server import Server
    from pyjabber.server_parameters import Parameters

    loguru.logger.remove()                                            # silencioso, como o servidor embutido
    plugins = [p for p in Parameters().plugins if p != "urn:xmpp:http:upload:0"]
    server = Server(Parameters(host="localhost", client_port=port, server_port=port + 1,
                               database_in_memory=True, plugins=plugins))
    task = asyncio.create_task(server.start())
    await asyncio.wait_for(server.ready.wait(), 30)
    return task


def parse_args(argv=None) -> argparse.Namespace:
    """Opções da linha de comandos."""
    parser = argparse.ArgumentParser(description="Run one CEMR simulation.")
    parser.add_argument("--scenario", default="c1", help="scenario id or file (default: c1)")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--duration", type=float, help="simulated seconds")
    parser.add_argument("--factor", type=float, help="clock acceleration")
    parser.add_argument("--out", type=Path, help="output directory")
    parser.add_argument("--xmpp-port", type=int, metavar="PORT",
                        help="run a private XMPP server on PORT (and PORT+1) for this run; for parallel runs")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                        help="override a parameter, e.g. --set sensors.policy=alert_first (repeatable)")
    parser.add_argument("--viz", type=int, metavar="PORT", help="serve the live dashboard on this port")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def parse_overrides(items: list[str]) -> dict:
    """Converte 'a.b.c=valor' em {'a': {'b': {'c': valor}}}; o valor é lido como TOML, ou fica texto."""
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


def run_config(args: argparse.Namespace) -> dict:
    """Configuração do run: defaults, cenário, --set e as opções --seed, --duration e --factor."""
    overrides = parse_overrides(args.set)
    run = overrides.setdefault("run", {})
    for key, value in (("seed", args.seed), ("duration_s", args.duration), ("clock_factor", args.factor)):
        if value is not None:
            run[key] = value
    cfg = load_config(args.scenario, overrides)
    cfg["code"] = code_version()
    return cfg


def main(argv=None) -> int:
    """Ponto de entrada: corre o run e devolve o código de saída."""
    args = parse_args(argv)
    cfg = run_config(args)
    run = cfg["run"]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = args.out or REPO_ROOT / "runs" / f"{run['name']}-s{run['seed']}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    logging.getLogger("spade").setLevel(logging.ERROR)
    logging.getLogger("slixmpp").setLevel(logging.ERROR)
    result: dict = {}

    async def runner():
        server = None
        try:
            if args.xmpp_port:
                server = await start_private_server(args.xmpp_port)
            result["summary"] = await simulate(cfg, out_dir, args.quiet, args.viz, args.xmpp_port or 5222)
        except Exception:  # noqa: BLE001 - o spade.run engole as exceções, por isso mostram-se aqui
            traceback.print_exc()
        finally:
            if server is not None:
                server.cancel()

    spade.run(runner(), embedded_xmpp_server=not args.xmpp_port)
    if "summary" not in result:
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
