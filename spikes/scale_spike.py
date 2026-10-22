"""Sprint 0 scale spike: can SPADE 4.1.4 + pyjabber carry ~100 agents, and how fast can the sim clock run?

Each hub runs CFP -> propose rounds with its clients (shape of P08 CallForResponders) and records
round-trip times. A side task measures event-loop lag, which bounds the clock acceleration factor:
a real delay L shows up as L * factor simulated seconds.

Single process (in-process container delivery, embedded XMPP server):
    python spikes/scale_spike.py --hubs 10 --clients 90

Two processes (messages go through XMPP), with an external server started by `spade run`:
    python spikes/scale_spike.py --part clients --external &
    python spikes/scale_spike.py --part hubs --external
"""

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

DOMAIN = "localhost"
PREFIX = "spike"  # overridden by --prefix so parallel runs can share one server
PADDING = "x" * 300  # roughly the size of a real JSON payload
SIM_LATENCY_BUDGET_S = 0.25  # max simulated seconds of distortion we accept from real delays


def hub_jid(h):
    return f"{PREFIX}_hub{h}@{DOMAIN}"


def client_jid(c):
    return f"{PREFIX}_client{c}@{DOMAIN}"


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(q / 100 * (len(ordered) - 1))))
    return ordered[idx]


class HubAgent(Agent):
    def __init__(self, jid, password, clients, rounds, interval, warmup):
        super().__init__(jid, password)
        self.clients = clients
        self.rounds = rounds
        self.interval = interval
        self.warmup = warmup
        self.rtts = []
        self.sent = 0
        self.received = 0

    class Rounds(CyclicBehaviour):
        async def on_start(self):
            self.round = 0
            await asyncio.sleep(self.agent.warmup)

        async def run(self):
            agent = self.agent
            if self.round >= agent.rounds:
                self.kill()
                return
            sent_at = {}
            for c in agent.clients:
                msg = Message(to=client_jid(c))
                msg.set_metadata("performative", "cfp")
                msg.set_metadata("protocol", "P08-CallForResponders")
                msg.thread = f"{agent.jid.user}-r{self.round}"
                msg.body = json.dumps({"round": self.round, "client": c, "pad": PADDING})
                sent_at[c] = time.perf_counter()
                await self.send(msg)
                agent.sent += 1
            deadline = time.perf_counter() + 5.0
            while sent_at and time.perf_counter() < deadline:
                reply = await self.receive(timeout=max(0.0, deadline - time.perf_counter()))
                if reply is None:
                    break
                body = json.loads(reply.body)
                if body["round"] != self.round:
                    continue  # late reply from an earlier round
                t0 = sent_at.pop(body["client"], None)
                if t0 is not None:
                    agent.rtts.append(time.perf_counter() - t0)
                    agent.received += 1
            self.round += 1
            await asyncio.sleep(agent.interval)

    async def setup(self):
        template = Template()
        template.set_metadata("performative", "propose")
        self.rounds_behaviour = self.Rounds()
        self.add_behaviour(self.rounds_behaviour, template)


class ClientAgent(Agent):
    def __init__(self, jid, password, idle_stop):
        super().__init__(jid, password)
        self.idle_stop = idle_stop

    class Answer(CyclicBehaviour):
        async def on_start(self):
            self.seen_any = False

        async def run(self):
            msg = await self.receive(timeout=self.agent.idle_stop)
            if msg is None:
                if self.seen_any:
                    self.kill()
                return
            self.seen_any = True
            reply = msg.make_reply()
            reply.set_metadata("performative", "propose")
            reply.body = msg.body
            await self.send(reply)

    async def setup(self):
        template = Template()
        template.set_metadata("performative", "cfp")
        self.answer_behaviour = self.Answer()
        self.add_behaviour(self.answer_behaviour, template)


async def monitor_loop_lag(samples, stop, period=0.01):
    while not stop.is_set():
        t0 = time.perf_counter()
        await asyncio.sleep(period)
        samples.append(time.perf_counter() - t0 - period)


async def start_with_retry(agent, retries):
    """pyjabber drops connections during login bursts (DisconnectedException); start() is safe to retry."""
    for attempt in range(retries + 1):
        try:
            await agent.start(auto_register=True)
            return None
        except Exception as exc:  # noqa: BLE001 - report whatever the last failure was
            if attempt == retries:
                return exc
            await asyncio.sleep(0.2 * 2 ** attempt)


async def start_all(agents, batch, retries):
    t0 = time.perf_counter()
    failures = []
    for i in range(0, len(agents), batch):
        results = await asyncio.gather(*(start_with_retry(a, retries) for a in agents[i:i + batch]))
        failures += [repr(r) for r in results if r is not None]
    return time.perf_counter() - t0, failures


def recommend_factor(rtt_p99, lag_p99):
    worst = max(x for x in (rtt_p99 / 2 if rtt_p99 else 0, lag_p99 or 0, 1e-4))
    for f in (50, 40, 30, 20, 15, 10, 5, 2, 1):
        if worst * f <= SIM_LATENCY_BUDGET_S:
            return f
    return 1


async def main(args):
    hubs = list(range(args.hubs))
    clients_of = {h: [c for c in range(args.clients) if c % args.hubs == h] for h in hubs}
    run_hubs = args.part in ("all", "hubs")
    run_clients = args.part in ("all", "clients")

    agents = []
    if run_clients:
        agents += [ClientAgent(client_jid(c), "pw", idle_stop=args.idle_stop) for c in range(args.clients)]
    hub_agents = []
    if run_hubs:
        hub_agents = [HubAgent(hub_jid(h), "pw", clients_of[h], args.rounds, args.interval, args.warmup)
                      for h in hubs]
        agents += hub_agents

    start_s, failures = await start_all(agents, args.batch, args.retries)
    print(f"[{args.part}] started {len(agents) - len(failures)}/{len(agents)} agents in {start_s:.2f}s")

    # measured after startup: the burst of logins is a one-off, not steady-state simulation load
    lag, stop = [], asyncio.Event()
    lag_task = asyncio.create_task(monitor_loop_lag(lag, stop))

    if run_hubs:
        t0 = time.perf_counter()
        await asyncio.gather(*(h.rounds_behaviour.join() for h in hub_agents if h.is_alive()))
        elapsed = time.perf_counter() - t0 - args.warmup
    else:
        await asyncio.gather(*(a.answer_behaviour.join() for a in agents if a.is_alive()))
        elapsed = None

    stop.set()
    await lag_task
    await asyncio.gather(*(a.stop() for a in agents if a.is_alive()))

    if not run_hubs:
        return

    rtts = [r for h in hub_agents for r in h.rtts]
    sent = sum(h.sent for h in hub_agents)
    received = sum(h.received for h in hub_agents)
    ms = lambda v: None if v is None else round(v * 1000, 2)  # noqa: E731
    summary = {
        "mode": "single-process" if args.part == "all" else "two-process (XMPP)",
        "agents": args.hubs + args.clients,
        "start_seconds": round(start_s, 2),
        "start_failures": failures,
        "messages": {"cfp_sent": sent, "replies": received, "lost": sent - received,
                     "msgs_per_s": round(2 * received / elapsed, 1) if elapsed else None},
        "rtt_ms": {"p50": ms(percentile(rtts, 50)), "p95": ms(percentile(rtts, 95)),
                   "p99": ms(percentile(rtts, 99)), "max": ms(max(rtts) if rtts else None),
                   "mean": ms(statistics.fmean(rtts) if rtts else None)},
        "loop_lag_ms": {"p50": ms(percentile(lag, 50)), "p95": ms(percentile(lag, 95)),
                        "p99": ms(percentile(lag, 99)), "max": ms(max(lag) if lag else None)},
    }
    summary["recommended_factor"] = recommend_factor(percentile(rtts, 99), percentile(lag, 99))
    print(json.dumps(summary, indent=2))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hubs", type=int, default=10)
    parser.add_argument("--clients", type=int, default=90)
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--interval", type=float, default=0.2, help="real seconds between CFP rounds per hub")
    parser.add_argument("--warmup", type=float, default=2.0, help="real seconds before hubs start sending")
    parser.add_argument("--idle-stop", type=float, default=8.0, help="clients stop after this many idle seconds")
    parser.add_argument("--part", choices=("all", "hubs", "clients"), default="all")
    parser.add_argument("--external", action="store_true", help="use a server started with `spade run`")
    parser.add_argument("--batch", type=int, default=1000, help="agents started concurrently (1000 = all at once)")
    parser.add_argument("--retries", type=int, default=0, help="start retries per agent, with exponential backoff")
    parser.add_argument("--prefix", default=PREFIX, help="JID prefix (unique per parallel run)")
    parser.add_argument("--out", help="write the JSON summary here")
    args = parser.parse_args()
    PREFIX = args.prefix
    spade.run(main(args), embedded_xmpp_server=not args.external)
