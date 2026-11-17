"""Corre a matriz de experiências: cenários x variantes x seeds, em paralelo, cada run com o seu servidor XMPP.

    python experiments/run_matrix.py --matrix main --seeds 1-10 --workers 4            # Windows/Linux
    caffeinate -i python experiments/run_matrix.py --matrix main --seeds 1-10 --workers 4   # macOS

Cada run arranca um servidor pyjabber próprio na porta do seu job (`cemr.run --xmpp-port`): no
Windows um servidor partilhado (`spade run`) é muito lento a fazer o login de 4 x 100 agentes, e
servidores próprios mantêm os runs independentes. No Windows o script impede a suspensão da máquina.

Cada run vai para runs/<matriz>/<cenário>-<variante>-s<seed>/. O runs.csv tem uma linha por job da
matriz pedida (com --only também), lida do summary.json no disco: as métricas, a validade, as
violações de regras e o commit do código (o último que mexeu em src/, scenarios/
ou experiments/). A matriz main escreve-o em results/ e as outras (smoke) em
runs/<matriz>/. Voltar a correr o script salta os runs válidos do mesmo commit, por isso uma matriz
interrompida pode ser retomada. Os resultados finais têm de vir todos do mesmo commit, por isso o
script recusa arrancar com alterações por commitar (salvo --allow-dirty).
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
RESULTS = ROOT / "results"
NAIVE = {"policy.allocation": '"naive"'}
NO_GUIDANCE = {"policy.guidance": "false"}
NO_REPUTATION = {"policy.reputation": "false"}

# (cenário, variante, alterações). "ours" é o sistema como foi desenhado; "naive" é a linha de base B1.
MATRICES = {
    "main": [
        ("c1", "ours", {}), ("c1", "naive", NAIVE), ("c1", "no_guidance", NO_GUIDANCE),
        # M12 como na análise: degradação de M3-M5 com mensagens perdidas (o C1 tem 0 % de perdas)
        ("c1", "loss10", {"network.loss": "0.1"}), ("c1", "loss20", {"network.loss": "0.2"}),
        ("c2", "ours", {}), ("c2", "naive", NAIVE),
        ("c2", "alert_first", {"sensors.policy": '"alert_first"'}),
        ("c2", "confirm_first", {"sensors.policy": '"confirm_first"'}),
        ("c2", "no_reputation", NO_REPUTATION),
        ("c3", "ours", {}), ("c3", "naive", NAIVE), ("c3", "no_guidance", NO_GUIDANCE),
        ("c3", "k1", {"dispatch.redundancy.P1.GO_TO_PATIENT": "1"}),
        ("c3", "k3", {"dispatch.redundancy.P1.GO_TO_PATIENT": "3"}),
        ("c4", "ours", {}), ("c4", "naive", NAIVE), ("c4", "no_guidance", NO_GUIDANCE),
        ("c5", "ours", {}), ("c5", "naive", NAIVE), ("c5", "no_reputation", NO_REPUTATION),
    ],
    "smoke": [
        ("c1", "ours", {}), ("c1", "no_guidance", NO_GUIDANCE), ("c2", "ours", {}), ("c3", "ours", {}),
        ("c4", "ours", {}), ("c5", "ours", {}), ("c5", "no_reputation", NO_REPUTATION),
    ],
}


def git(*args: str) -> str:
    """Corre um comando git na raiz do repositório e devolve a saída."""
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def flatten(data: dict, prefix: str = "") -> dict:
    """Achata um dicionário aninhado em colunas "a.b.c" (as listas ficam de fora)."""
    out = {}
    for key, value in data.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, name + "."))
        elif not isinstance(value, list):
            out[name] = value
    return out


def run_dir(matrix: str, scenario: str, variant: str, seed: int) -> Path:
    """Pasta de um run da matriz."""
    return ROOT / "runs" / matrix / f"{scenario}-{variant}-s{seed}"


def read_summary(matrix: str, scenario: str, variant: str, seed: int) -> dict | None:
    """O summary.json de um run, ou None se o run ainda não existe."""
    path = run_dir(matrix, scenario, variant, seed) / "summary.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def is_done(summary: dict | None, commit: str) -> bool:
    """Um run está feito se é válido e foi corrido com o commit atual."""
    return summary is not None and summary.get("valid") and summary.get("code", {}).get("commit") == commit


def run_one(scenario: str, variant: str, overrides: dict, seed: int, args, port: int) -> int:
    """Corre um run da matriz num processo próprio; devolve o código de saída."""
    out = run_dir(args.matrix, scenario, variant, seed)
    cmd = [sys.executable, "-m", "cemr.run", "--scenario", scenario, "--seed", str(seed), "--xmpp-port", str(port),
           "--quiet", "--out", str(out)]
    if args.duration:
        cmd += ["--duration", str(args.duration)]
    if args.factor:
        cmd += ["--factor", str(args.factor)]
    for key, value in overrides.items():
        cmd += ["--set", f"{key}={value}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if proc.returncode != 0:
        out.mkdir(parents=True, exist_ok=True)
        (out / "stderr.txt").write_text(proc.stderr, encoding="utf-8")
    return proc.returncode


def table_row(matrix: str, scenario: str, variant: str, seed: int) -> dict:
    """Linha do runs.csv de um job, a partir do que está no disco."""
    row = {"scenario": scenario, "variant": variant, "seed": seed}
    summary = read_summary(matrix, scenario, variant, seed)
    if summary is None:
        row["status"] = "missing"
        return row
    row["status"] = "ok" if summary.get("valid") else "invalid"
    row.update(flatten(summary))
    return row


def write_rows(rows: list[dict], path: Path) -> Path:
    """Escreve o runs.csv, com as colunas de todas as linhas."""
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = []
    for row in rows:
        columns += [c for c in row if c not in columns]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def keep_awake() -> None:
    """Windows: impede a máquina de suspender enquanto o processo corre (o `caffeinate -i` do macOS).

    Fechar a tampa ainda pode suspender um portátil, conforme as definições de energia; esses runs
    ficam inválidos e são repetidos na invocação seguinte.
    """
    if sys.platform == "win32":
        import ctypes
        es_continuous, es_system_required = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(es_continuous | es_system_required)


def parse_seeds(text: str) -> list[int]:
    """Lê "1-10" ou "1,3,5"."""
    if "-" in text:
        lo, hi = text.split("-")
        return list(range(int(lo), int(hi) + 1))
    return [int(s) for s in text.split(",")]


def parse_args() -> argparse.Namespace:
    """Opções da linha de comandos."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matrix", default="main", choices=sorted(MATRICES))
    parser.add_argument("--seeds", default="1-10")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--duration", type=float, help="override the simulated duration")
    parser.add_argument("--factor", type=float, help="override the clock factor")
    parser.add_argument("--only", help="comma-separated scenarios to run, e.g. c1,c3 (runs.csv keeps all rows)")
    parser.add_argument("--force", action="store_true", help="redo runs that already have a valid summary")
    parser.add_argument("--allow-dirty", action="store_true", help="run with uncommitted changes in src/scenarios")
    parser.add_argument("--base-port", type=int, default=15222,
                        help="first private XMPP port; job i uses base + 2i and base + 2i + 1")
    return parser.parse_args()


def main() -> int:
    """Corre os jobs que faltam e escreve o runs.csv da matriz inteira."""
    args = parse_args()
    if git("status", "--porcelain", "--", "src", "scenarios", "experiments") and not args.allow_dirty:
        print("uncommitted changes in src/, scenarios/ or experiments/: commit first (or --allow-dirty)")
        return 2
    # O último commit que mexeu no código (o mesmo que o run.py grava): commits só de documentação
    # feitos com a matriz a correr não obrigam a repetir os runs.
    commit = git("log", "-1", "--format=%H", "--", "src", "scenarios", "experiments")
    seeds = parse_seeds(args.seeds)
    all_jobs = [(sc, var, ov, seed) for sc, var, ov in MATRICES[args.matrix] for seed in seeds]
    wanted = [job for job in all_jobs if not args.only or job[0] in args.only.split(",")]
    todo = [job for job in wanted
            if args.force or not is_done(read_summary(args.matrix, job[0], job[1], job[3]), commit)]
    keep_awake()
    print(f"{len(todo)} of {len(wanted)} runs to do at commit {commit[:10]}, {args.workers} in parallel")
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        # Cada job tem o seu par de portas, para nenhum run usar uma porta que outro acabou de largar.
        futures = {pool.submit(run_one, sc, var, ov, seed, args, args.base_port + 2 * i): (sc, var, seed)
                   for i, (sc, var, ov, seed) in enumerate(todo)}
        for n, future in enumerate(as_completed(futures), start=1):
            sc, var, seed = futures[future]
            row = table_row(args.matrix, sc, var, seed)
            print(f"[{n}/{len(todo)}] {sc}-{var}-s{seed}: exit={future.result()} {row['status']}"
                  f" rules={row.get('rules.violations')} errors={row.get('errors')}"
                  f" ({(time.monotonic() - started) / 60:.0f} min)", flush=True)
    rows = [table_row(args.matrix, sc, var, seed) for sc, var, _, seed in all_jobs]
    if args.matrix == "main":
        path = write_rows(rows, RESULTS / "runs.csv")
    else:
        path = write_rows(rows, ROOT / "runs" / args.matrix / "runs.csv")
    bad = [r for r in rows if r["status"] != "ok"]
    print(f"results: {path} ({len(rows)} rows, {len(bad)} invalid or missing)")
    return 1 if bad else 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    sys.exit(main())
