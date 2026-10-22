# Sprint 0 — scale spike

`scale_spike.py` checks whether SPADE 4.1.4 with its pyjabber XMPP server can carry the agent population
of the base scenario (~100 agents, analysis §8.3), and how far the simulated clock can be accelerated.
Ten hub agents run CFP → propose rounds with their clients, the same shape as P08 `CallForResponders`.
The spike records round-trip time (RTT) and event-loop lag.

Environment: MacBook (Apple Silicon), Python 3.11.17, spade 4.1.4, pyjabber 0.4.5. Run on 2026-10-22.

## Results

| Run | Agents | Path | Load (msg/s) | Start failures | Lost | RTT p50 / p99 (ms) | Loop lag p99 (ms) |
|---|---|---|---|---|---|---|---|
| single, realistic | 100 | in-process | 178 | 0 | 0 | 7.2 / 11.8 | 1.1 |
| single, stress | 100 | in-process | 852 | 0 | 0 | 7.5 / 11.4 | 3.1 |
| single, stress | 200 | in-process | 1719 | 0 | 0 | 12.6 / 64.7 | 7.5 |
| two processes, realistic | 100 | XMPP | 176 | 0 | 0 | 19.4 / 54.8 | 2.2 |
| two processes, stress | 100 | XMPP | 849 | 0 | 0 | 8.9 / 22.6 | 1.3 |
| 4 parallel runs, all at once | 4 × 100 | in-process, shared server | 4 × ~178 | **40–55 per run** | — | — | — |
| 4 parallel runs, batched start | 4 × 100 | in-process, shared server | 4 × ~178 | 0 | 0 | 7–8 / 10–59 | 1.1 |

Raw summaries are written to `spikes/out/*.json`, which is not versioned.

## Findings and decisions

1. **SPADE copes with the planned scale.** 100 agents start in about 1.5 s, and 200 agents also work.
   Across all runs no message was lost.
2. **Agents in the same process do not use XMPP.** SPADE's `Container` hands a message directly to the
   receiver when both agents are registered in the same process (`spade/container.py`, `Container.send`).
   XMPP is only used for login, and for messages between processes.
   → All network effects (latency, loss, cells without coverage; assumption A3) must come from our own
   `NetworkModel`, applied in a single `send_with_faults()` in the base agent class. The docs must state
   that, inside one simulation process, XMPP carries no messages.
3. **`spade run` must be started with `--host localhost`.** Its default domain is `0.0.0.0`. With that
   domain, pyjabber treats `agent@localhost` as a *remote* domain and opens a server-to-server
   connection to itself, where the message is silently dropped. The embedded server
   (`spade.run(..., embedded_xmpp_server=True)`) already uses `localhost`.
4. **pyjabber drops connections during login bursts.** With 400 simultaneous logins, 40–55 agents per
   process fail with `DisconnectedException`.
   → Start agents in **batches of 10, retrying with exponential backoff**. `Agent.start()` is safe to
   retry, because it builds a new `XMPPClient` each time and `setup()` runs only after a successful
   login. This took start failures to zero. This helper moves into `cemr` in sprint 1.
5. **Clock acceleration factor: 10×.** A real delay *L* appears as *L × factor* simulated seconds.
   - At 10×, the worst p99 one-way delay observed (~30 ms, four parallel runs) distorts time by about
     0.3 simulated seconds. The shortest protocol deadline is 10 s (P08 proposals; analysis §8.3).
   - At 20×, a single run is still acceptable (11.8 ms RTT p99 → ~0.12 s), but parallel runs reach
     ~0.6 s. One factor is used everywhere so results stay comparable.
   - At 10×, 60 simulated minutes take 6 real minutes. Four parallel runs complete about 70 runs in under
     2 hours.
6. **Parallel experiments** use a single external server, started with
   `spade run --host localhost --memory`. Each run gets its own JID prefix, and each process holds one
   complete simulation.
7. **Dependency fix.** pyjabber's SQLAlchemy asyncio layer needs `greenlet`, which `pip install spade`
   did not pull in. It is now listed in `pyproject.toml` and `requirements.txt`.
8. **Security note.** Even with `--host localhost`, pyjabber also listens on the machine's LAN address
   (ports 5222/5269). Agents auto-register with trivial passwords, so run the server only on trusted
   networks.

## Reproduce

```bash
source .venv/bin/activate
python spikes/scale_spike.py --hubs 10 --clients 90 --interval 1.0 --rounds 20       # single process

spade run --host localhost --memory &                                                 # shared server
python spikes/scale_spike.py --part clients --external --idle-stop 10 &
python spikes/scale_spike.py --part hubs --external --interval 1.0 --rounds 20       # through XMPP

for i in 1 2 3 4; do                                                                  # parallel runs
  python spikes/scale_spike.py --external --prefix par$i --interval 1.0 --rounds 20 \
    --batch 10 --retries 4 --out spikes/out/parallel_$i.json &
done
```
