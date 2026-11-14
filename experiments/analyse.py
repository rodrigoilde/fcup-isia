"""Agrega o results/runs.csv em tabelas e figuras para o relatório de desempenho.

    python experiments/analyse.py                         # matriz final: results/runs.csv -> results/
    python experiments/analyse.py --runs runs/smoke/runs.csv --out runs/smoke

Escreve na pasta de saída:

- summary.csv e summary.md: média, intervalo de confiança a 95 % e n por cenário, variante e métrica;
- paired.csv e paired.md: diferença emparelhada por seed entre cada variante e "ours" (média, IC 95 %
  e em quantas seeds "ours" foi melhor), que tira a variação entre seeds da comparação;
- fig_<cenário>.png (médias) e fig_<cenário>_paired.png (diferenças emparelhadas).

Só entram os runs válidos, e todos têm de vir do mesmo commit do código.
"""

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# (coluna do runs.csv, nome curto, unidade, o que é melhor)
METRICS = [
    ("M1_verification_latency_s.median", "M1 verification latency", "s", "lower"),
    ("M2_verification.precision", "M2 precision", "%", "higher"),
    ("M2_verification.recall_P1_P2_detectable", "M2 recall (detectable)", "%", "higher"),
    ("M2_verification.recall_P1_P2_reported", "M2 recall (reported)", "%", "higher"),
    ("M2_verification.false_dispatches", "M2 false dispatches", "per run", "lower"),
    ("M3_time_to_cpr_s.median", "M3 time to CPR", "s", "lower"),
    ("M3_time_to_cpr_s.by_bystander_pct", "M3 CPR started by a bystander", "%", "higher"),
    ("M4_time_to_aed_s.median", "M4 time to AED", "s", "lower"),
    ("M5_time_to_ems_s.median", "M5 time to EMS", "s", "lower"),
    ("M6_survival_pct.mean", "M6 survival proxy", "%", "higher"),
    ("M7_coverage_before_ems_pct.volunteer", "M7 volunteer before EMS", "%", "higher"),
    ("M7_coverage_before_ems_pct.aed", "M7 AED before EMS", "%", "higher"),
    ("M8_messages.per_candidate", "M8 messages per candidate", "msgs", "lower"),
    ("M9_gap_to_oracle_s.median", "M9 gap to oracle B0", "s", "lower"),
    ("M10_volunteer_load.alerts_per_volunteer", "M10 alerts per volunteer", "alerts", "lower"),
    ("M10_volunteer_load.false_alarm_minutes", "M10 minutes on false alarms", "min", "lower"),
    ("M11_privacy_exposure.recipients_per_case", "M11 location recipients per case", "agents", "lower"),
    ("M12_robustness.recovery_s", "M12 recovery after hub crash", "s", "lower"),
    ("rules.violations", "Rule violations", "count", "lower"),
]
FIGURE_METRICS = ["M1_verification_latency_s.median", "M2_verification.recall_P1_P2_reported",
                  "M2_verification.false_dispatches", "M3_time_to_cpr_s.median",
                  "M7_coverage_before_ems_pct.volunteer", "M10_volunteer_load.alerts_per_volunteer"]

# Paleta categórica validada (modo claro); "ours" e "naive" ficam sempre com as cores 1 e 2.
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"
SCENARIO_NAMES = {"c1": "C1 base urban", "c2": "C2 noise and false alarms", "c3": "C3 surge with contention",
                  "c4": "C4 degraded periphery", "c5": "C5 adversarial sources"}
VARIANT_NAMES = {"ours": "Ours", "naive": "B1 naive broadcast", "alert_first": "AlertFirst",
                 "confirm_first": "ConfirmFirst", "no_reputation": "No reputation", "no_guidance": "No guidance",
                 "k1": "k = 1", "k3": "k = 3"}
# Valor t de Student para um IC a 95 %, por graus de liberdade (n - 1)
T_95 = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 7: 2.36, 8: 2.31, 9: 2.26, 10: 2.23,
        11: 2.20, 12: 2.18, 13: 2.16, 14: 2.14, 15: 2.13, 16: 2.12, 17: 2.11, 18: 2.10, 19: 2.09}


def ci95(values: pd.Series) -> float:
    """Meia largura do intervalo de confiança a 95 % da média (t de Student)."""
    values = values.dropna()
    if len(values) < 2:
        return float("nan")
    return T_95.get(len(values) - 1, 1.96) * values.std(ddof=1) / math.sqrt(len(values))


def variant_order(variants) -> list[str]:
    """Variantes com "ours" e "naive" primeiro e as outras por ordem alfabética."""
    head = [v for v in ("ours", "naive") if v in variants]
    return head + sorted(v for v in variants if v not in head)


def aggregate(runs: pd.DataFrame) -> pd.DataFrame:
    """Média, IC 95 % e n de cada métrica, por cenário e variante."""
    rows = []
    for (scenario, variant), group in runs.groupby(["scenario", "variant"]):
        for column, label, unit, better in METRICS:
            if column not in group:
                continue
            values = pd.to_numeric(group[column], errors="coerce")
            rows.append({"scenario": scenario, "variant": variant, "metric": label, "unit": unit, "better": better,
                         "mean": values.mean(), "ci95": ci95(values), "n": int(values.notna().sum())})
    return pd.DataFrame(rows)


def paired_row(scenario: str, variant: str, metric: tuple, ours: pd.DataFrame, other: pd.DataFrame) -> dict:
    """Diferença emparelhada (variante - ours) de uma métrica, nas seeds em que as duas têm valor."""
    column, label, unit, better = metric
    a = pd.to_numeric(ours.set_index("seed")[column], errors="coerce")
    b = pd.to_numeric(other.set_index("seed")[column], errors="coerce")
    diff = (b - a).dropna()
    if better == "lower":
        ours_better = int((diff > 0).sum())
    else:
        ours_better = int((diff < 0).sum())
    return {"scenario": scenario, "variant": variant, "metric": label, "unit": unit, "better": better,
            "mean_diff": diff.mean(), "ci95": ci95(diff), "n": len(diff), "ours_better": ours_better}


def paired(runs: pd.DataFrame) -> pd.DataFrame:
    """Comparações emparelhadas por seed de cada variante com "ours", no mesmo cenário."""
    rows = []
    for scenario in sorted(runs["scenario"].unique()):
        part = runs[runs["scenario"] == scenario]
        ours = part[part["variant"] == "ours"]
        for variant in variant_order(part["variant"].unique()):
            if variant == "ours" or ours.empty:
                continue
            other = part[part["variant"] == variant]
            for metric in METRICS:
                if metric[0] in part:
                    rows.append(paired_row(scenario, variant, metric, ours, other))
    return pd.DataFrame(rows)


def format_cell(mean: float, ci: float, n: int, signed: bool = False) -> str:
    """Texto "média ± IC (n=...)" de uma célula das tabelas."""
    if math.isnan(mean):
        return "—"
    text = f"{mean:+.1f}" if signed else f"{mean:.1f}"
    if not math.isnan(ci):
        text += f" ± {ci:.1f}"
    return text + f" (n={n})"


def write_summary_md(summary: pd.DataFrame, n_runs: int, commit: str, out: Path) -> None:
    """summary.md: uma tabela por cenário, com uma coluna por variante."""
    lines = ["# Experiment results", "",
             f"{n_runs} valid runs at commit `{commit}`. Values are means over seeds with 95 % confidence "
             "intervals.", ""]
    for scenario in sorted(summary["scenario"].unique()):
        part = summary[summary["scenario"] == scenario]
        variants = variant_order(part["variant"].unique())
        lines += [f"## {SCENARIO_NAMES.get(scenario, scenario)}", "",
                  "| Metric | " + " | ".join(VARIANT_NAMES.get(v, v) for v in variants) + " |",
                  "|---|" + "---|" * len(variants)]
        for _, label, unit, better in METRICS:
            cells = []
            for v in variants:
                row = part[(part["variant"] == v) & (part["metric"] == label)]
                if row.empty:
                    cells.append("—")
                else:
                    cells.append(format_cell(row["mean"].iloc[0], row["ci95"].iloc[0], row["n"].iloc[0]))
            if any(c != "—" for c in cells):
                lines.append(f"| {label} ({unit}, {better} is better) | " + " | ".join(cells) + " |")
        lines.append("")
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_paired_md(table: pd.DataFrame, commit: str, out: Path) -> None:
    """paired.md: diferenças emparelhadas por seed, uma tabela por cenário."""
    lines = ["# Paired comparisons", "",
             f"Commit `{commit}`. Each cell is the mean over seeds of (variant − ours) with a 95 % confidence "
             "interval, and in how many seeds ours was better. An interval that excludes 0 is a difference "
             "beyond the seed-to-seed variation.", ""]
    for scenario in sorted(table["scenario"].unique()):
        part = table[table["scenario"] == scenario]
        variants = variant_order(part["variant"].unique())
        lines += [f"## {SCENARIO_NAMES.get(scenario, scenario)}", "",
                  "| Metric | " + " | ".join(f"{VARIANT_NAMES.get(v, v)} − Ours" for v in variants) + " |",
                  "|---|" + "---|" * len(variants)]
        for _, label, unit, better in METRICS:
            cells = []
            for v in variants:
                row = part[(part["variant"] == v) & (part["metric"] == label)]
                if row.empty or row["n"].iloc[0] == 0:
                    cells.append("—")
                    continue
                r = row.iloc[0]
                cells.append(format_cell(r["mean_diff"], r["ci95"], r["n"], signed=True)
                             + f"; ours better {r['ours_better']}/{r['n']}")
            if any(c != "—" for c in cells):
                lines.append(f"| {label} ({unit}, {better} is better) | " + " | ".join(cells) + " |")
        lines.append("")
    (out / "paired.md").write_text("\n".join(lines), encoding="utf-8")


def style_axis(ax, title: str) -> None:
    """Aspeto comum dos painéis das figuras."""
    ax.set_title(title, fontsize=9.5, color=INK, loc="left")
    ax.set_xticks([])
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.tick_params(axis="y", colors=MUTED, labelsize=8, length=0)


def plot_bars(table: pd.DataFrame, value: str, variants: list[str], title: str, path: Path) -> None:
    """Pequenos múltiplos: um painel por métrica, uma barra por variante, com o IC 95 %."""
    colours = {v: SLOTS[i % len(SLOTS)] for i, v in enumerate(variant_order(set(variants) | {"ours"}))}
    labels = [label for column, label, _, _ in METRICS if column in FIGURE_METRICS]
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.2), facecolor=SURFACE)
    for ax, label in zip(axes.flat, labels):
        rows = [table[(table["variant"] == v) & (table["metric"] == label)] for v in variants]
        means = [r[value].iloc[0] if not r.empty else float("nan") for r in rows]
        cis = [r["ci95"].iloc[0] if not r.empty else float("nan") for r in rows]
        errors = [0 if math.isnan(c) else c for c in cis]
        x = range(len(variants))
        ax.bar(x, means, width=0.78, color=[colours[v] for v in variants], edgecolor=SURFACE, linewidth=2,
               yerr=errors, error_kw={"ecolor": INK, "elinewidth": 1, "capsize": 3})
        ax.axhline(0, color="#c3c2b7", linewidth=0.8)
        for xi, m, e in zip(x, means, errors):
            if not math.isnan(m):                                # rótulo por cima da barra de erro
                top = m + e if m >= 0 else m - e
                text = f"{m:.0f}" if abs(m) >= 10 else f"{m:.1f}"
                ax.annotate(text, (xi, top), xytext=(0, 3 if m >= 0 else -10), textcoords="offset points",
                            ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_xlim(-0.6, max(len(variants), 4) - 0.4)          # barras finas seja qual for o número de variantes
        unit = next(u for _, lab, u, _ in METRICS if lab == label)
        style_axis(ax, f"{label} ({unit})")
    for ax in list(axes.flat)[len(labels):]:
        ax.set_visible(False)
    if len(variants) > 1 or value == "mean_diff":               # nas diferenças diz sempre qual é a variante
        handles = [plt.Rectangle((0, 0), 1, 1, color=colours[v]) for v in variants]
        fig.legend(handles, [VARIANT_NAMES.get(v, v) for v in variants], loc="lower center", ncol=len(variants),
                   frameon=False, fontsize=9, labelcolor=INK)
    fig.suptitle(title, fontsize=11, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.06, 1, 0.97))
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def main() -> int:
    """Lê o runs.csv e escreve as tabelas e as figuras."""
    parser = argparse.ArgumentParser(description="Aggregate a runs.csv into tables and figures.")
    parser.add_argument("--runs", type=Path, default=RESULTS / "runs.csv")
    parser.add_argument("--out", type=Path, default=RESULTS)
    args = parser.parse_args()
    out = args.out
    runs = pd.read_csv(args.runs)
    valid = runs[runs["status"] == "ok"]
    commits = valid["code.commit"].dropna().unique()
    if len(commits) != 1:
        raise SystemExit(f"runs.csv must come from exactly one commit, found {list(commits)}")
    commit = commits[0]
    summary = aggregate(valid)
    summary.to_csv(out / "summary.csv", index=False)
    write_summary_md(summary, len(valid), commit, out)
    table = paired(valid)
    table.to_csv(out / "paired.csv", index=False)
    write_paired_md(table, commit, out)
    for scenario in sorted(summary["scenario"].unique()):
        name = SCENARIO_NAMES.get(scenario, scenario)
        part = summary[summary["scenario"] == scenario]
        plot_bars(part, "mean", variant_order(part["variant"].unique()), f"{name} — mean over seeds, 95 % CI",
                  out / f"fig_{scenario}.png")
        diffs = table[table["scenario"] == scenario]
        if not diffs.empty:
            plot_bars(diffs, "mean_diff", variant_order(diffs["variant"].unique()),
                      f"{name} — paired difference (variant − ours), 95 % CI", out / f"fig_{scenario}_paired.png")
    print(f"{len(valid)}/{len(runs)} runs valid at {commit[:10]} -> {out}: summary.*, paired.*, figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
