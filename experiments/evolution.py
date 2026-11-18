"""Tabela de evolução do desenho: o efeito de cada alteração nas métricas, com as mesmas seeds.

    python experiments/evolution.py        # escreve results/evolution.md

Cada linha compara dois `results/runs.csv` guardados no git, o de antes e o de depois da alteração, só
para a variante "ours" e só nas seeds que os dois têm. A diferença é emparelhada por seed, como em
`paired.md`. Entre dois commits pode ter havido mais do que uma alteração, por isso cada linha diz de
que commit vêm os dados. Texto e ressalvas em docs/03-detailed-design.md §7.1.
"""

import io
import subprocess

import pandas as pd

from analyse import RESULTS, ROOT, ci95, format_cell

# (alteração, cenário, coluna do runs.csv, nome da métrica, ref git dos dados antes, ref git dos dados depois)
CHANGES = [
    ("Alerts merged by a 100 m area instead of by cell", "c3",
     "M2_verification.recall_P1_P2_detectable", "M2 recall, detectable (%)", "6df23fb", "b473e26"),
    ("Triage that contradicts the report is asked again", "c3",
     "M2_verification.recall_P1_P2_detectable", "M2 recall, detectable (%)", "b473e26", "fb57b6b"),
    ("Triage that contradicts the report is asked again", "c3",
     "M2_verification.recall_P1_P2_reported", "M2 recall, reported (%)", "b473e26", "fb57b6b"),
    ("A source counts once per candidate", "c5",
     "M2_verification.false_dispatches", "M2 false dispatches (per run)", "b473e26", "fb57b6b"),
    ("A source counts once per candidate", "c5",
     "M2_verification.precision", "M2 precision (%)", "b473e26", "fb57b6b"),
]


def runs_at(ref: str) -> pd.DataFrame:
    """Os runs válidos de "ours" no `results/runs.csv` guardado num commit."""
    text = subprocess.run(["git", "show", f"{ref}:results/runs.csv"], cwd=ROOT, capture_output=True,
                          text=True, check=True, encoding="utf-8").stdout
    runs = pd.read_csv(io.StringIO(text))
    if "status" in runs:
        runs = runs[runs["status"] == "ok"]
    else:                                     # os runs.csv mais antigos só tinham a coluna "valid"
        runs = runs[runs["valid"].astype(bool)]
    return runs[runs["variant"] == "ours"]


def code_commit(runs: pd.DataFrame, ref: str) -> str:
    """Commit do código que produziu os runs (os runs.csv antigos não o guardam: fica a ref dos dados)."""
    if "code.commit" in runs and runs["code.commit"].notna().any():
        return str(runs["code.commit"].dropna().iloc[0])[:7]
    return ref


def change_row(change: tuple) -> str:
    """Uma linha da tabela: médias antes e depois e diferença emparelhada, nas seeds comuns."""
    name, scenario, column, label, before_ref, after_ref = change
    before, after = runs_at(before_ref), runs_at(after_ref)
    a = before[before["scenario"] == scenario].set_index("seed")[column]
    b = after[after["scenario"] == scenario].set_index("seed")[column]
    seeds = sorted(set(a.dropna().index) & set(b.dropna().index))
    a, b = a.loc[seeds], b.loc[seeds]
    diff = b - a
    cells = [name, f"{scenario.upper()}, {label}",
             f"{format_cell(a.mean(), ci95(a), len(a))} at `{code_commit(before, before_ref)}`",
             f"{format_cell(b.mean(), ci95(b), len(b))} at `{code_commit(after, after_ref)}`",
             format_cell(diff.mean(), ci95(diff), len(diff), signed=True),
             f"{min(seeds)}–{max(seeds)}"]
    return "| " + " | ".join(cells) + " |"


def main() -> None:
    """Escreve results/evolution.md."""
    lines = ["# Design evolution", "",
             "Variant \"ours\", valid runs only, paired by seed over the seeds both runs.csv have. Values are "
             "means with 95 % confidence intervals. The commit is the code that produced the runs; more than "
             "one change may lie between two commits (see docs/03-detailed-design.md §7.1).", "",
             "| Change | Scenario, metric | Before | After | After − before | Seeds |",
             "|---|---|---|---|---|---|"]
    lines += [change_row(change) for change in CHANGES]
    (RESULTS / "evolution.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
