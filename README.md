# Decentralised Community Emergency Medical Response (CEMR)

ISIA 2026/27 · Assignment 1 · Topic O.

This is a SPADE multi-agent system that does three things without a central dispatcher:

- detects time-critical medical incidents, such as an out-of-hospital cardiac arrest;
- verifies each incident locally;
- dispatches the nearest capable volunteers, AEDs and ambulances, while guiding bystanders through CPR
  and keeping personal data on a need-to-know basis.

The city is split into cells, each served by the hub on its AED cabinet. Hubs verify alerts, coordinate
cases with a Contract Net, keep reputation, and take over each other's cases when one fails.

> **Status:** final week.
> - All 28 protocols (P22 is a read inside the hub), scenarios C1–C5, baselines B0/B1, the rule checker,
>   the experiment pipeline and the dashboard work.
> - Since the first experiment matrix: alerts merge by a 100 m area instead of by cell, duplicate cases
>   across cell borders are resolved by both hubs, scenario C5 (adversarial sources) and a variant
>   without bystander guidance were added, and the code was simplified and documented in Portuguese.
> - After the audit of 16 Nov:
>   - a witness's triage that contradicts its own report ("responds") is asked again before it lowers the
>     case to P3;
>   - half of the drifting sensors' false positives in C2 go unanswered;
>   - M9 is also measured from the declaration;
>   - M12 has message-loss variants;
>   - the analysis separates the effect of guidance from that of coordination.
> - An undecodable message is answered with FIPA `not-understood`.
> - The final matrix ran on the commit tagged `matrix-final`: 210 valid runs, all at code commit
>   `de13290`. The numbers in `results/` come from it. `results/evolution.md` compares it with the earlier
>   matrices (docs/03 §7.1), and `results/demo/` keeps one run for the dashboard replay.
> - Next: the performance report and the slides.

## Setup

SPADE 4.1.4 needs **Python 3.10–3.14**. The macOS system Python (3.9) will not work.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
pytest -m "not slow"   # unit tests (~2 s)
pytest                 # plus two end-to-end SPADE runs (~2 min)
ruff check src experiments tests   # PEP 8 and unused imports (settings in pyproject.toml)
```

On Windows: `py -3.13 -m venv .venv`, then `.venv\Scripts\activate` (tested with Python 3.13).

`greenlet` is listed explicitly because the embedded XMPP server (pyjabber → SQLAlchemy asyncio) needs
it and `pip install spade` does not pull it in.

## Running a simulation

```bash
python -m cemr.run --scenario c1 --seed 1                                  # 60 simulated min, ~6 real min
python -m cemr.run --scenario c4 --seed 1 --duration 1500 --factor 30      # quick: hub crash + takeover
python -m cemr.run --scenario c2 --set sensors.policy=alert_first          # a variant
python -m cemr.run --scenario c1 --set policy.allocation=naive             # baseline B1
python -m cemr.run --scenario c5 --set policy.reputation=false             # C5 without reputation
```

| Option | Meaning |
|---|---|
| `--scenario` | `c1`–`c5` or a file in `scenarios/`; overrides `scenarios/defaults.toml` |
| `--seed` | Seed of the layout and incident trace |
| `--duration`, `--factor` | Simulated seconds; clock acceleration (default 10×) |
| `--set key=value` | Override any parameter, e.g. `--set dispatch.redundancy.P1.GO_TO_PATIENT=3` |
| `--viz PORT` | Serve the live dashboard (use a slow clock, e.g. `--factor 5`) |
| `--xmpp-port PORT` | Start a private in-process XMPP server on `PORT` (and `PORT+1`); used for parallel runs |

| Scenario | What changes | Question |
|---|---|---|
| C1 base urban | Average density, reliable sensors, good network | Does the flow work? How often is a volunteer there before EMS? |
| C2 noise | Sensor false positives ×5, drifting sensors, misread scenes | Do corroboration and reputation keep precision? AlertFirst or ConfirmFirst? |
| C3 surge | 8 incidents in 10 min within 400 m | Are different patients kept apart? Do exclusivity and priority avoid conflicts? How much redundancy pays off? |
| C4 periphery | Half the volunteers, locked AEDs, distant ambulances, coverage gaps, a hub crash | Do guidance and re-allocation hold? What does recovering a coordinator cost? |
| C5 adversarial | The C1 city with two citizens who keep reporting collapses that did not happen | Does reputation stop repeated false reports, and at what cost? |

Each run writes `runs/<scenario>-s<seed>-<time>/`:

| File | Contents |
|---|---|
| `events.jsonl` | Every message, decision and ground-truth event; the audit log |
| `trace.json` | Layout and pre-generated incidents |
| `config.json` | Merged parameters and the git commit of the code |
| `summary.json` | Metrics M1–M13, the reason each missed P1/P2 was missed (`M2_missed`), the oracle B0, rule violations, the code commit and a **validity** verdict |

**Validity.** A run is invalid (exit code 3) if the simulated clock did not advance as intended, e.g.
because the laptop slept: closing the lid suspends the process. For long runs, plug in the charger and
keep the lid open. On macOS use `caffeinate -i`; on Windows `run_matrix.py` keeps the machine awake itself.

## Checking the organisational rules

```bash
python -m cemr.metrics.check runs/<run> -v
```

This re-derives the rules of the Gaia analysis from the audit log:

- one owner per case;
- one commitment per responder;
- one reservation per AED;
- the declaration rule;
- need-to-know disclosure;
- ambulance cancellation;
- alert fatigue;
- data retention;
- guidance from the protocol only;
- the life-cycle rules OL1–OL9;
- DUP, added in the design: no incident handled by two declared cases.

## Experiments

```bash
python experiments/run_matrix.py --matrix smoke --seeds 1-2 --duration 1200   # ~15 min: 7 configurations
python experiments/run_matrix.py --matrix main --seeds 1-10 --workers 4       # ~6–7 h (macOS: prefix caffeinate -i)
powershell -ExecutionPolicy Bypass -File experiments\run_overnight.ps1        # Windows: main matrix, retries, analysis
python experiments/analyse.py
```

`run_matrix.py` runs configurations × seeds in parallel, each run with its own XMPP server. It skips
runs that are already valid **for the current commit** and refuses to start with uncommitted changes in
`src/`, `scenarios/` or `experiments/`, so the final results come from one version of the code. Each
matrix has its own folder, `runs/<matrix>/<scenario>-<variant>-s<seed>/`. The main matrix has 21
configurations:

- C1: the system as designed, baseline B1, without bystander guidance, and 10 % and 20 % message loss (M12);
- C2: as designed, B1, AlertFirst, ConfirmFirst and without reputation;
- C3: as designed, B1, without guidance, and redundancy k = 1 and k = 3;
- C4: as designed, B1 and without guidance;
- C5: as designed, B1 and without reputation.

`analyse.py` reads `results/runs.csv` (one row per job of the main matrix) and writes to `results/`:

| File | Contents |
|---|---|
| `summary.csv`, `summary.md` | Means with 95 % CI per configuration and metric, with the code commit |
| `paired.csv`, `paired.md` | Each variant minus "ours", paired by seed: mean, 95 % CI and in how many seeds ours was better. In C1, C3 and C4 also "B1 − No guidance": both lack guidance, so it isolates verification, Contract Net and reputation |
| `misses.md` | Missed P1/P2 incidents per configuration, summed over seeds, by reason (not reported, discarded as P3, fused with another patient, …); see detailed design §7 |
| `fig_c1.png` … `fig_c5.png` | Means per scenario |
| `fig_c1_paired.png` … | Paired differences per scenario |

## Dashboard

```bash
python -m cemr.viz.server runs/main/<run>     # replay a finished run at http://127.0.0.1:8080/
python -m cemr.run --scenario c1 --factor 5 --viz 8080                     # watch a run live
```

The page shows:

- the cells and the AED state of each hub;
- people moving (by shape: volunteer, witness, device, ambulance);
- incidents;
- message arcs coloured by sub-organisation;
- live metrics, the case list and an event feed.

Open `?t=1200&speed=60` to start a replay at a given time.

One run is kept in git for the demo, so it can be shown without XMPP or running a simulation: scenario
C4, seed 7, from the final matrix. Hub 2 crashes at 1200 s and its successor takes over its two open cases
in 19.6 s.

```bash
python -m cemr.viz.server results/demo/c4-ours-s7   # then open http://127.0.0.1:8080/?t=1150&speed=10
```

## XMPP server

- **Single run:** the embedded server (`spade.run(..., embedded_xmpp_server=True)`) is used. Nothing
  else is needed.
- **Parallel runs:** each run starts a private in-process server on its own port (`--xmpp-port`), so
  runs share nothing. A shared `spade run` server is not used: on Windows it never completes a
  registration (pyjabber hashes passwords in a process pool whose *spawned* workers re-run `spade run`'s
  entry point and crash), and even a fixed shared server logs 4 × 100 agents in very slowly.
- **Security:** the server also listens on the LAN address and agents auto-register with trivial
  passwords, so use it only on trusted networks. The dashboard listens on 127.0.0.1 only.

See [spikes/README.md](spikes/README.md) for the measurements behind these choices.

## Repository layout

| Path | Contents |
|---|---|
| `docs/` | Assignment brief, Gaia analysis, architectural design, detailed design, protocols and message schemas |
| `src/cemr/sim/` | Environment: clock, city grid, layout, world, patients, incident trace, network model |
| `src/cemr/protocol/` | Ontology, messages of P01–P28 (one module per sub-organisation) and their JSON encoding |
| `src/cemr/agents/` | Base agent and conversations; hub (with the case FSM in `case_*.py` and failover); volunteer; EMS; citizen device; bystander |
| `src/cemr/behaviours/` | Pure decision logic: fusion and merging, Contract Net, privacy, reputation, AED custody, guidance |
| `src/cemr/baselines/` | Oracle B0 (B1 is a policy of the hubs) |
| `src/cemr/metrics/` | Event log, metrics M1–M13, rule checker (safety and liveness rules) |
| `src/cemr/viz/` | Dashboard server and page |
| `scenarios/` | `defaults.toml` (every parameter, documented) and C1–C5 |
| `experiments/` | Matrix runner, overnight script and analysis |
| `tests/` | Unit tests by topic and end-to-end tests |
| `spikes/` | Sprint 0 scale spike |

## Documentation

1. [Gaia analysis](docs/01-gaia-analysis.pdf), in Portuguese: requirements, sub-organisations,
   environment, roles, protocols, organisational rules, metrics, scenarios.
2. [Architectural design](docs/02-architectural-design.md): organisational structure (cell hubs),
   decisions D1–D8, completed role and interaction models, rule enforcement.
3. [Detailed design](docs/03-detailed-design.md): agent and services models, SPADE mapping, decision
   logic, behaviour models, failure handling, verification, and how the design relates to the course
   concepts (agent architectures, auctions, social choice).
4. [Protocols and message schemas](docs/04-protocols-and-messages.md): envelope, threads, sequence
   diagrams, and the schema of every message in `src/cemr/protocol/messages_*.py`.
5. API documentation from the docstrings (in Portuguese): `pdoc src/cemr -o docs/api`, then open
   `docs/api/index.html`.
