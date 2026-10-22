# Decentralised Community Emergency Medical Response (CEMR)

ISIA 2026/27 · Assignment 1 · Topic O.

This is a SPADE multi-agent system that does three things without a central dispatcher:

- detects time-critical medical incidents, such as an out-of-hospital cardiac arrest;
- verifies each incident locally;
- dispatches the nearest capable volunteers, AEDs and ambulances, while guiding bystanders through CPR
  and keeping personal data on a need-to-know basis.

The city is split into cells, each served by the hub on its AED cabinet. Hubs verify alerts, coordinate
cases with a Contract Net, keep reputation, and take over each other's cases when one fails.

> **Status:** sprint 2.
> - All 28 protocols, scenarios C1–C4, baselines B0/B1, the rule checker, the experiment pipeline and
>   the dashboard work.
> - Next: run the full experiment matrix and write the report; see [PLAN.md](PLAN.md).

## Setup

SPADE 4.1.4 needs **Python 3.10–3.14**. The macOS system Python (3.9) will not work.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
pytest -m "not slow"   # unit tests (< 1 s)
pytest                 # plus two end-to-end SPADE runs (~1.5 min)
```

`greenlet` is listed explicitly because the embedded XMPP server (pyjabber → SQLAlchemy asyncio) needs
it and `pip install spade` does not pull it in.

## Running a simulation

```bash
python -m cemr.run --scenario c1 --seed 1                                  # 60 simulated min, ~6 real min
python -m cemr.run --scenario c4 --seed 1 --duration 1500 --factor 30      # quick: hub crash + takeover
python -m cemr.run --scenario c2 --set sensors.policy=alert_first          # a variant
python -m cemr.run --scenario c1 --set policy.allocation=naive             # baseline B1
```

| Option | Meaning |
|---|---|
| `--scenario` | `c1`–`c4` or a file in `scenarios/`; overrides `scenarios/defaults.toml` |
| `--seed` | Seed of the layout and incident trace |
| `--duration`, `--factor` | Simulated seconds; clock acceleration (default 10×) |
| `--set key=value` | Override any parameter, e.g. `--set dispatch.redundancy.P1.GO_TO_PATIENT=3` |
| `--viz PORT` | Serve the live dashboard (use a slow clock, e.g. `--factor 5`) |
| `--external` | Use a running `spade run --host localhost --memory` instead of the embedded server |

| Scenario | What changes | Question |
|---|---|---|
| C1 base urban | Average density, reliable sensors, good network | Does the flow work? How often is a volunteer there before EMS? |
| C2 noise | Sensor false positives ×5, drifting sensors, misread scenes | Do corroboration and reputation keep precision? AlertFirst or ConfirmFirst? |
| C3 surge | 8 incidents in 10 min within 400 m | Do exclusivity and priority avoid conflicts? How much redundancy pays off? |
| C4 periphery | Half the volunteers, locked AEDs, distant ambulances, coverage gaps, a hub crash | Do guidance and re-allocation hold? What does recovering a coordinator cost? |

Each run writes `runs/<scenario>-s<seed>-<time>/`:

| File | Contents |
|---|---|
| `events.jsonl` | Every message, decision and ground-truth event; the audit log |
| `trace.json` | Layout and pre-generated incidents |
| `config.json` | Merged parameters |
| `summary.json` | Metrics M1–M13, the oracle B0, rule violations and a **validity** verdict |

**Validity.** A run is invalid (exit code 3) if the simulated clock did not advance as intended, e.g.
because the laptop slept: closing the lid suspends the process. For long runs, plug in the charger and
use `caffeinate -i`.

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
- the life-cycle rules OL1–OL9.

## Experiments

```bash
caffeinate -i python experiments/run_matrix.py --matrix main --seeds 1-5 --workers 4    # ~1h40
python experiments/analyse.py
```

`run_matrix.py` runs 13 configurations × seeds in parallel against one shared XMPP server, skipping
runs that are already valid. The configurations are:

- C1–C4, each with the system as designed and with baseline B1;
- C2 with AlertFirst, ConfirmFirst and without reputation;
- C3 with redundancy k = 1 and k = 3.

`analyse.py` writes these files to `results/`:

| File | Contents |
|---|---|
| `summary.csv`, `summary.md` | Means with 95 % CI per configuration and metric |
| `fig_c1.png` … `fig_c4.png` | One figure per scenario |

## Dashboard

```bash
python -m cemr.viz.server runs/<run>          # replay a finished run at http://127.0.0.1:8080/
python -m cemr.run --scenario c1 --factor 5 --viz 8080                     # watch a run live
```

The page shows:

- the cells and the AED state of each hub;
- people moving (by shape: volunteer, witness, device, ambulance);
- incidents;
- message arcs coloured by sub-organisation;
- live metrics, the case list and an event feed.

Open `?t=1200&speed=60` to start a replay at a given time.

## XMPP server

- **Single run:** the embedded server (`spade.run(..., embedded_xmpp_server=True)`) is used. Nothing
  else is needed.
- **Parallel runs:** one shared server, `spade run --host localhost --memory`. `--host localhost` is
  required: with the default domain, messages to `agent@localhost` are silently dropped.
- **Security:** the server also listens on the LAN address and agents auto-register with trivial
  passwords, so use it only on trusted networks. The dashboard listens on 127.0.0.1 only.

See [spikes/README.md](spikes/README.md) for the measurements behind these choices.

## Repository layout

| Path | Contents |
|---|---|
| `docs/` | Assignment brief, Gaia analysis, architectural design, detailed design, protocols and message schemas |
| `src/cemr/sim/` | Environment: clock, city grid, world, patients, incident trace, network model |
| `src/cemr/protocol/` | Ontology, payloads of P01–P28, schema-doc generator |
| `src/cemr/agents/` | Hub (with the case FSM), volunteer, EMS, citizen device, bystander |
| `src/cemr/behaviours/` | Pure decision logic: fusion, Contract Net, privacy, reputation, AED custody, guidance |
| `src/cemr/baselines/` | Oracle B0 (B1 is a policy of the hubs) |
| `src/cemr/metrics/` | Event log, metrics M1–M13, rule checker |
| `src/cemr/viz/` | Dashboard server and page |
| `scenarios/` | `defaults.toml` (every parameter, documented) and C1–C4 |
| `experiments/` | Matrix runner and analysis |
| `tests/` | Unit and end-to-end tests |
| `spikes/` | Sprint 0 scale spike |

## Documentation

1. [Gaia analysis](docs/01-gaia-analysis.pdf), in Portuguese: requirements, sub-organisations,
   environment, roles, protocols, organisational rules, metrics, scenarios.
2. [Architectural design](docs/02-architectural-design.md): organisational structure (cell hubs),
   decisions D1–D8, completed role and interaction models, rule enforcement.
3. [Detailed design](docs/03-detailed-design.md): agent and services models, SPADE mapping, decision
   logic, behaviour models, failure handling, verification.
4. [Protocols and message schemas](docs/04-protocols-and-messages.md): envelope, threads, sequence
   diagrams, and schema tables generated from `src/cemr/protocol/messages.py`.
