# Design evolution

Variant "ours", valid runs only, paired by seed over the seeds both runs.csv have. Values are means with 95 % confidence intervals. The commit is the code that produced the runs; more than one change may lie between two commits (see docs/03-detailed-design.md §7.1).

| Change | Scenario, metric | Before | After | After − before | Seeds |
|---|---|---|---|---|---|
| Alerts merged by a 100 m area instead of by cell | C3, M2 recall, detectable (%) | 64.0 ± 22.2 (n=5) at `6df23fb` | 77.5 ± 13.7 (n=5) at `67a012b` | +13.5 ± 13.3 (n=5) | 1–5 |
| Triage that contradicts the report is asked again | C3, M2 recall, detectable (%) | 75.8 ± 8.2 (n=10) at `67a012b` | 80.3 ± 10.8 (n=10) at `de13290` | +4.5 ± 4.2 (n=10) | 1–10 |
| Triage that contradicts the report is asked again | C3, M2 recall, reported (%) | 90.9 ± 5.8 (n=10) at `67a012b` | 95.7 ± 5.2 (n=10) at `de13290` | +4.8 ± 4.4 (n=10) | 1–10 |
| A source counts once per candidate | C5, M2 false dispatches (per run) | 3.0 ± 0.7 (n=10) at `67a012b` | 3.0 ± 0.7 (n=10) at `de13290` | +0.0 ± 0.0 (n=10) | 1–10 |
| A source counts once per candidate | C5, M2 precision (%) | 26.6 ± 14.0 (n=10) at `67a012b` | 28.3 ± 15.0 (n=10) at `de13290` | +1.7 ± 3.8 (n=10) | 1–10 |
