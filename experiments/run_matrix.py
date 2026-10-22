"""Run the experiment matrix: scenarios x variants x seeds, in parallel, against one shared XMPP server.

    caffeinate -i python experiments/run_matrix.py --matrix main --seeds 1-5 --workers 4

Each run goes to runs/matrix/<scenario>-<variant>-s<seed>/; results/runs.csv gets one row per run with
the flattened summary (metrics, validity, rule violations). Re-running skips runs that already have a
valid summary, so an interrupted matrix can be resumed. Plug the laptop in: a run during which the
machine sleeps is marked invalid and redone on the next invocation.
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "matrix"
RESULTS = ROOT / "results"
NAIVE = {"policy.allocation": "naive"}

# (scenario, variant, overrides). "ours" is the system as designed; "naive" is baseline B1.
MATRICES = {
    "main": [
        ("c1", "ours", {}), ("c1", "naive", NAIVE),
        ("c2", "ours", {}), ("c2", "naive", NAIVE),
        ("c2", "alert_first", {"sensors.policy": '"alert_first"'}),
        ("c2", "confirm_first", {"sensors.policy": '"confirm_first"'}),
        ("c2", "no_reputation", {"policy.reputation": "false"}),
        ("c3", "ours", {}), ("c3", "naive", NAIVE),
        ("c3", "k1", {"dispatch.redundancy.P1.GO_TO_PATIENT": "1"}),
        ("c3", "k3", {"dispatch.redundancy.P1.GO_TO_PATIENT": "3"}),
        ("c4", "ours", {}), ("c4", "naive", NAIVE),
    ],
    "smoke": [("c1", "ours", {}), ("c2", "ours", {}), ("c3", "ours", {}), ("c4", "ours", {})],
}


def flatten(data: dict, prefix: str = "") -> dict:
    out = {}
    for key, value in data.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, name + "."))
        elif not isinstance(value, list):
            out[name] = value
    return out


def run_one(scenario: str, variant: str, overrides: dict, seed: int, args) -> dict:
    out = RUNS / f"{scenario}-{variant}-s{seed}"
    summary_file = out / "summary.json"
    if summary_file.exists() and not args.force:
        previous = json.loads(summary_file.read_text())
        if previous.get("valid"):
            return {"scenario": scenario, "variant": variant, "seed": seed, "exit": 0, "skipped": True,
                    **flatten(previous)}
    cmd = [sys.executable, "-m", "cemr.run", "--scenario", scenario, "--seed", str(seed), "--external", "--quiet",
           "--out", str(out), "--prefix", f"{scenario}{variant}s{seed}".replace("_", "")]
    if args.duration:
        cmd += ["--duration", str(args.duration)]
    if args.factor:
        cmd += ["--factor", str(args.factor)]
    for key, value in overrides.items():
        cmd += ["--set", f"{key}={value}"]
    started = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    row = {"scenario": scenario, "variant": variant, "seed": seed, "exit": proc.returncode,
           "real_s": round(time.monotonic() - started, 1)}
    if summary_file.exists():
        row.update(flatten(json.loads(summary_file.read_text())))
    else:
        row["valid"] = False
        (out / "stderr.txt").parent.mkdir(parents=True, exist_ok=True)
        (out / "stderr.txt").write_text(proc.stderr)
    return row


def write_rows(rows: list[dict]) -> Path:
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / "runs.csv"
    columns = []
    for row in rows:
        columns += [c for c in row if c not in columns]
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (r["scenario"], r["variant"], r["seed"])):
            writer.writerow(row)
    return path


def parse_seeds(text: str) -> list[int]:
    if "-" in text:
        lo, hi = text.split("-")
        return list(range(int(lo), int(hi) + 1))
    return [int(s) for s in text.split(",")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matrix", default="main", choices=sorted(MATRICES))
    parser.add_argument("--seeds", default="1-5")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--duration", type=float, help="override the simulated duration")
    parser.add_argument("--factor", type=float, help="override the clock factor")
    parser.add_argument("--only", help="comma-separated scenarios to run, e.g. c1,c3")
    parser.add_argument("--force", action="store_true", help="redo runs that already have a valid summary")
    args = parser.parse_args()

    jobs = [(sc, var, ov, seed) for sc, var, ov in MATRICES[args.matrix] for seed in parse_seeds(args.seeds)
            if not args.only or sc in args.only.split(",")]
    server = subprocess.Popen([str(Path(sys.executable).with_name("spade")), "run", "--host", "localhost",
                               "--memory"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=ROOT)
    time.sleep(4)
    rows = []
    print(f"{len(jobs)} runs, {args.workers} in parallel")
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_one, sc, var, ov, seed, args): (sc, var, seed) for sc, var, ov, seed in jobs}
            for n, future in enumerate(as_completed(futures), start=1):
                row = future.result()
                rows.append(row)
                write_rows(rows)
                status = "skipped" if row.get("skipped") else ("ok" if row.get("valid") and row["exit"] == 0
                                                              else f"PROBLEM exit={row['exit']}")
                print(f"[{n}/{len(jobs)}] {row['scenario']}-{row['variant']}-s{row['seed']}: {status}"
                      f" rules={row.get('rules.violations')} errors={row.get('errors')}", flush=True)
    finally:
        server.terminate()
    path = write_rows(rows)
    bad = [r for r in rows if not r.get("valid") or r["exit"] not in (0,)]
    print(f"results: {path} ({len(rows)} runs, {len(bad)} invalid or failed)")
    return 1 if bad else 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    sys.exit(main())
