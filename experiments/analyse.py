"""Aggregate results/runs.csv into tables and figures for the performance report.

    python experiments/analyse.py

Writes results/summary.csv (mean, 95 % CI and n per scenario x variant x metric), results/summary.md
(the same as markdown tables, which also serve as the table view of every figure) and
results/fig_<scenario>.png (small multiples: one panel per metric, one bar per variant).
Only valid runs (summary "valid") enter the statistics.
"""

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

# (column in runs.csv, short label, unit, better)
METRICS = [
    ("M1_verification_latency_s.median", "M1 verification latency", "s", "lower"),
    ("M2_verification.precision", "M2 precision", "%", "higher"),
    ("M2_verification.recall_P1_P2_detectable", "M2 recall (detectable)", "%", "higher"),
    ("M2_verification.false_dispatches", "M2 false dispatches", "per run", "lower"),
    ("M3_time_to_cpr_s.median", "M3 time to CPR", "s", "lower"),
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
FIGURE_METRICS = ["M1_verification_latency_s.median", "M2_verification.precision", "M3_time_to_cpr_s.median",
                  "M7_coverage_before_ems_pct.volunteer", "M10_volunteer_load.alerts_per_volunteer",
                  "M8_messages.per_candidate"]

# Validated categorical palette (dataviz reference, light mode); "ours" and "naive" keep slots 1 and 2 everywhere.
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"
SCENARIO_NAMES = {"c1": "C1 base urban", "c2": "C2 noise and false alarms", "c3": "C3 surge with contention",
                  "c4": "C4 degraded periphery"}
VARIANT_NAMES = {"ours": "Ours", "naive": "B1 naive broadcast", "alert_first": "AlertFirst",
                 "confirm_first": "ConfirmFirst", "no_reputation": "No reputation", "k1": "k = 1", "k3": "k = 3"}


def ci95(series: pd.Series) -> float:
    values = series.dropna()
    if len(values) < 2:
        return float("nan")
    t = {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 6: 2.57, 7: 2.45, 8: 2.36, 9: 2.31, 10: 2.26}.get(len(values), 1.96)
    return t * values.std(ddof=1) / math.sqrt(len(values))


def variant_order(variants) -> list[str]:
    head = [v for v in ("ours", "naive") if v in variants]
    return head + sorted(v for v in variants if v not in head)


def aggregate(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (scenario, variant), group in runs.groupby(["scenario", "variant"]):
        for column, label, unit, better in METRICS:
            if column not in group:
                continue
            values = pd.to_numeric(group[column], errors="coerce")
            rows.append({"scenario": scenario, "variant": variant, "metric": label, "unit": unit, "better": better,
                         "mean": values.mean(), "ci95": ci95(values), "n": int(values.notna().sum())})
    return pd.DataFrame(rows)


def write_markdown(summary: pd.DataFrame, runs: pd.DataFrame) -> None:
    lines = ["# Experiment results", "",
             f"{len(runs)} valid runs. Values are means over seeds with 95 % confidence intervals.", ""]
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
                if row.empty or math.isnan(row["mean"].iloc[0]):
                    cells.append("—")
                    continue
                mean, ci, n = row["mean"].iloc[0], row["ci95"].iloc[0], row["n"].iloc[0]
                cells.append(f"{mean:.1f}" + (f" ± {ci:.1f}" if not math.isnan(ci) else "") + f" (n={n})")
            if any(c != "—" for c in cells):
                lines.append(f"| {label} ({unit}, {better} is better) | " + " | ".join(cells) + " |")
        lines.append("")
    (RESULTS / "summary.md").write_text("\n".join(lines))


def plot_scenario(scenario: str, summary: pd.DataFrame) -> Path:
    part = summary[summary["scenario"] == scenario]
    variants = variant_order(part["variant"].unique())
    colours = {v: SLOTS[i] for i, v in enumerate(variants)}
    labels = [label for column, label, _, _ in METRICS if column in FIGURE_METRICS]
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.2), facecolor=SURFACE)
    for ax, label in zip(axes.flat, labels):
        rows = [part[(part["variant"] == v) & (part["metric"] == label)] for v in variants]
        means = [r["mean"].iloc[0] if not r.empty else float("nan") for r in rows]
        cis = [r["ci95"].iloc[0] if not r.empty else float("nan") for r in rows]
        unit = next(u for _, lab, u, _ in METRICS if lab == label)
        x = range(len(variants))
        ax.bar(x, means, width=0.78, color=[colours[v] for v in variants], edgecolor=SURFACE, linewidth=2,
               yerr=[c if not math.isnan(c) else 0 for c in cis], error_kw={"ecolor": INK, "elinewidth": 1,
                                                                            "capsize": 3})
        for xi, m, c in zip(x, means, cis):
            if not math.isnan(m):                                     # label above the error bar
                top = m + (c if not math.isnan(c) else 0)
                ax.annotate(f"{m:.0f}" if abs(m) >= 10 else f"{m:.1f}", (xi, top), xytext=(0, 3),
                            textcoords="offset points", ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_xlim(-0.6, max(len(variants), 4) - 0.4)              # thin bars whatever the variant count
        ax.set_title(f"{label} ({unit})", fontsize=9.5, color=INK, loc="left")
        ax.set_xticks([])
        ax.set_facecolor(SURFACE)
        ax.grid(axis="y", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color("#c3c2b7")
        ax.tick_params(axis="y", colors=MUTED, labelsize=8, length=0)
    for ax in list(axes.flat)[len(labels):]:
        ax.set_visible(False)
    if len(variants) > 1:                                             # a single series needs no legend
        handles = [plt.Rectangle((0, 0), 1, 1, color=colours[v]) for v in variants]
        fig.legend(handles, [VARIANT_NAMES.get(v, v) for v in variants], loc="lower center", ncol=len(variants),
                   frameon=False, fontsize=9, labelcolor=INK)
    fig.suptitle(f"{SCENARIO_NAMES.get(scenario, scenario)} — mean over seeds, 95 % CI", fontsize=11, color=INK,
                 x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.06, 1, 0.97))
    path = RESULTS / f"fig_{scenario}.png"
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)
    return path


def main() -> int:
    runs = pd.read_csv(RESULTS / "runs.csv")
    valid = runs[(runs["valid"] == True) & (runs["exit"].isin([0, 2]))]  # noqa: E712
    summary = aggregate(valid)
    summary.to_csv(RESULTS / "summary.csv", index=False)
    write_markdown(summary, valid)
    for scenario in sorted(summary["scenario"].unique()):
        print(plot_scenario(scenario, summary))
    print(f"{len(valid)}/{len(runs)} runs valid -> results/summary.csv, results/summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
