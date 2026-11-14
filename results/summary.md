# Experiment results

190 valid runs at commit `67a012b025537940270e195071482f39dcd74b44`. Values are means over seeds with 95 % confidence intervals.

## C1 base urban

| Metric | Ours | B1 naive broadcast | No guidance |
|---|---|---|---|
| M1 verification latency (s, lower is better) | 33.6 ± 10.6 (n=10) | 26.5 ± 9.0 (n=10) | 33.7 ± 10.6 (n=10) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) |
| M2 recall (detectable) (%, higher is better) | 92.5 ± 12.1 (n=10) | 92.5 ± 12.1 (n=10) | 92.5 ± 12.1 (n=10) |
| M2 recall (reported) (%, higher is better) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M3 time to CPR (s, lower is better) | 55.5 ± 13.4 (n=10) | 296.3 ± 55.5 (n=7) | 230.2 ± 51.7 (n=10) |
| M3 CPR started by a bystander (%, higher is better) | 90.0 ± 15.1 (n=10) | 0.0 ± 0.0 (n=7) | 0.0 ± 0.0 (n=10) |
| M4 time to AED (s, lower is better) | 328.6 ± 49.8 (n=5) | — | 328.6 ± 49.4 (n=5) |
| M5 time to EMS (s, lower is better) | 385.6 ± 26.9 (n=10) | 378.6 ± 25.8 (n=10) | 385.6 ± 27.1 (n=10) |
| M6 survival proxy (%, higher is better) | 41.5 ± 4.6 (n=10) | 31.0 ± 3.9 (n=10) | 34.7 ± 4.5 (n=10) |
| M7 volunteer before EMS (%, higher is better) | 81.7 ± 17.3 (n=10) | 50.8 ± 32.3 (n=10) | 81.7 ± 17.3 (n=10) |
| M7 AED before EMS (%, higher is better) | 25.8 ± 23.9 (n=10) | 0.0 ± 0.0 (n=10) | 25.8 ± 23.9 (n=10) |
| M8 messages per candidate (msgs, lower is better) | 165.7 ± 10.2 (n=10) | 126.0 ± 4.2 (n=10) | 160.8 ± 9.7 (n=10) |
| M9 gap to oracle B0 (s, lower is better) | 119.2 ± 44.0 (n=10) | 182.3 ± 51.6 (n=7) | 119.3 ± 43.8 (n=10) |
| M10 alerts per volunteer (alerts, lower is better) | 1.3 ± 0.6 (n=10) | 2.4 ± 1.0 (n=10) | 1.3 ± 0.6 (n=10) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M11 location recipients per case (agents, lower is better) | 5.3 ± 1.0 (n=10) | 5.0 ± 0.2 (n=10) | 5.3 ± 1.0 (n=10) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |

## C2 noise and false alarms

| Metric | Ours | B1 naive broadcast | AlertFirst | ConfirmFirst | No reputation |
|---|---|---|---|---|---|
| M1 verification latency (s, lower is better) | 36.4 ± 9.8 (n=8) | 28.1 ± 7.9 (n=8) | 33.6 ± 9.7 (n=8) | 43.7 ± 5.3 (n=8) | 35.9 ± 9.5 (n=8) |
| M2 precision (%, higher is better) | 60.2 ± 27.2 (n=9) | 38.7 ± 19.1 (n=10) | 60.2 ± 27.2 (n=9) | 60.2 ± 27.2 (n=9) | 61.0 ± 27.0 (n=9) |
| M2 recall (detectable) (%, higher is better) | 73.3 ± 28.2 (n=9) | 83.0 ± 25.7 (n=9) | 73.3 ± 28.2 (n=9) | 73.3 ± 28.2 (n=9) | 75.6 ± 28.0 (n=9) |
| M2 recall (reported) (%, higher is better) | 90.6 ± 15.5 (n=8) | 100.0 ± 0.0 (n=8) | 90.6 ± 15.5 (n=8) | 90.6 ± 15.5 (n=8) | 93.8 ± 14.7 (n=8) |
| M2 false dispatches (per run, lower is better) | 1.2 ± 0.9 (n=10) | 2.8 ± 1.0 (n=10) | 1.2 ± 0.9 (n=10) | 1.2 ± 0.9 (n=10) | 1.2 ± 0.9 (n=10) |
| M3 time to CPR (s, lower is better) | 67.1 ± 32.5 (n=8) | 262.9 ± 22.3 (n=3) | 76.1 ± 34.0 (n=8) | 84.2 ± 33.3 (n=8) | 76.2 ± 34.1 (n=8) |
| M3 CPR started by a bystander (%, higher is better) | 87.5 ± 29.5 (n=8) | 0.0 ± 0.0 (n=3) | 75.0 ± 38.6 (n=8) | 75.0 ± 38.6 (n=8) | 75.0 ± 38.6 (n=8) |
| M4 time to AED (s, lower is better) | 256.0 ± 596.1 (n=2) | — | 256.1 ± 593.6 (n=2) | 271.5 ± 783.6 (n=2) | 256.1 ± 604.4 (n=2) |
| M5 time to EMS (s, lower is better) | 370.9 ± 23.1 (n=8) | 370.1 ± 23.2 (n=8) | 371.0 ± 23.2 (n=8) | 379.1 ± 24.4 (n=8) | 374.0 ± 25.1 (n=8) |
| M6 survival proxy (%, higher is better) | 31.3 ± 19.8 (n=7) | 27.5 ± 11.5 (n=7) | 31.2 ± 19.8 (n=7) | 30.9 ± 19.5 (n=7) | 31.2 ± 19.8 (n=7) |
| M7 volunteer before EMS (%, higher is better) | 61.1 ± 37.4 (n=9) | 20.4 ± 27.1 (n=9) | 61.1 ± 37.4 (n=9) | 61.1 ± 37.4 (n=9) | 61.1 ± 37.4 (n=9) |
| M7 AED before EMS (%, higher is better) | 16.7 ± 27.2 (n=9) | 0.0 ± 0.0 (n=9) | 16.7 ± 27.2 (n=9) | 16.7 ± 27.2 (n=9) | 16.7 ± 27.2 (n=9) |
| M8 messages per candidate (msgs, lower is better) | 107.1 ± 18.9 (n=10) | 112.7 ± 8.0 (n=10) | 84.3 ± 13.0 (n=10) | 136.9 ± 15.5 (n=9) | 108.4 ± 20.1 (n=10) |
| M9 gap to oracle B0 (s, lower is better) | 88.8 ± 44.1 (n=6) | 148.5 ± 156.1 (n=3) | 88.9 ± 44.1 (n=6) | 97.6 ± 32.6 (n=6) | 89.2 ± 43.8 (n=6) |
| M10 alerts per volunteer (alerts, lower is better) | 1.2 ± 0.7 (n=10) | 3.8 ± 0.9 (n=10) | 1.2 ± 0.7 (n=10) | 1.2 ± 0.7 (n=10) | 1.2 ± 0.8 (n=10) |
| M10 minutes on false alarms (min, lower is better) | 7.9 ± 6.3 (n=10) | 17.5 ± 15.1 (n=10) | 7.9 ± 6.3 (n=10) | 7.9 ± 6.3 (n=10) | 7.9 ± 6.3 (n=10) |
| M11 location recipients per case (agents, lower is better) | 4.7 ± 0.7 (n=9) | 4.9 ± 0.2 (n=10) | 4.7 ± 0.7 (n=9) | 4.7 ± 0.7 (n=9) | 4.8 ± 0.7 (n=9) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=10) | 0.1 ± 0.2 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |

## C3 surge with contention

| Metric | Ours | B1 naive broadcast | k = 1 | k = 3 | No guidance |
|---|---|---|---|---|---|
| M1 verification latency (s, lower is better) | 49.2 ± 3.6 (n=10) | 39.1 ± 4.7 (n=10) | 49.3 ± 3.4 (n=10) | 50.3 ± 2.5 (n=10) | 49.0 ± 3.4 (n=10) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) |
| M2 recall (detectable) (%, higher is better) | 75.8 ± 8.2 (n=10) | 81.5 ± 9.6 (n=10) | 76.8 ± 8.8 (n=10) | 78.1 ± 10.0 (n=10) | 78.0 ± 7.5 (n=10) |
| M2 recall (reported) (%, higher is better) | 90.9 ± 5.8 (n=10) | 95.9 ± 4.9 (n=10) | 91.9 ± 5.2 (n=10) | 93.2 ± 5.3 (n=10) | 92.2 ± 5.0 (n=10) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M3 time to CPR (s, lower is better) | 73.8 ± 25.2 (n=10) | 312.9 ± 53.6 (n=10) | 73.2 ± 25.6 (n=10) | 81.3 ± 29.6 (n=10) | 342.9 ± 36.6 (n=10) |
| M3 CPR started by a bystander (%, higher is better) | 85.4 ± 9.9 (n=10) | 0.0 ± 0.0 (n=10) | 85.4 ± 9.9 (n=10) | 88.1 ± 10.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M4 time to AED (s, lower is better) | 515.9 ± 70.6 (n=9) | 760.3 ± 363.6 (n=6) | 515.3 ± 100.2 (n=9) | 528.5 ± 83.0 (n=9) | 546.9 ± 119.2 (n=9) |
| M5 time to EMS (s, lower is better) | 521.5 ± 19.4 (n=10) | 535.7 ± 54.4 (n=10) | 521.6 ± 19.9 (n=10) | 547.6 ± 56.6 (n=10) | 521.0 ± 20.0 (n=10) |
| M6 survival proxy (%, higher is better) | 22.9 ± 11.7 (n=8) | 13.7 ± 6.9 (n=8) | 22.9 ± 11.8 (n=8) | 23.7 ± 10.7 (n=8) | 15.8 ± 8.5 (n=8) |
| M7 volunteer before EMS (%, higher is better) | 73.6 ± 16.4 (n=10) | 48.5 ± 18.9 (n=10) | 73.4 ± 13.6 (n=10) | 77.9 ± 15.8 (n=10) | 68.9 ± 15.7 (n=10) |
| M7 AED before EMS (%, higher is better) | 40.9 ± 18.0 (n=10) | 18.7 ± 12.8 (n=10) | 41.1 ± 17.5 (n=10) | 37.6 ± 19.8 (n=10) | 40.9 ± 18.0 (n=10) |
| M8 messages per candidate (msgs, lower is better) | 210.6 ± 14.0 (n=10) | 145.3 ± 10.2 (n=10) | 206.9 ± 15.9 (n=10) | 226.1 ± 20.5 (n=10) | 202.7 ± 14.0 (n=10) |
| M9 gap to oracle B0 (s, lower is better) | 214.4 ± 48.6 (n=10) | 196.8 ± 66.6 (n=10) | 221.1 ± 49.2 (n=10) | 194.3 ± 33.2 (n=10) | 214.2 ± 48.7 (n=10) |
| M10 alerts per volunteer (alerts, lower is better) | 4.4 ± 0.5 (n=10) | 5.8 ± 0.3 (n=10) | 4.3 ± 0.5 (n=10) | 4.7 ± 0.5 (n=10) | 4.4 ± 0.5 (n=10) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M11 location recipients per case (agents, lower is better) | 5.0 ± 0.7 (n=10) | 5.0 ± 0.3 (n=10) | 3.8 ± 0.4 (n=10) | 6.6 ± 1.3 (n=10) | 4.9 ± 0.8 (n=10) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |

## C4 degraded periphery

| Metric | Ours | B1 naive broadcast | No guidance |
|---|---|---|---|
| M1 verification latency (s, lower is better) | 38.7 ± 11.1 (n=10) | 27.6 ± 10.3 (n=10) | 38.2 ± 15.0 (n=10) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) |
| M2 recall (detectable) (%, higher is better) | 95.5 ± 6.8 (n=10) | 95.5 ± 6.8 (n=10) | 95.5 ± 6.8 (n=10) |
| M2 recall (reported) (%, higher is better) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M3 time to CPR (s, lower is better) | 201.2 ± 120.1 (n=10) | 476.8 ± 127.4 (n=10) | 397.7 ± 54.9 (n=10) |
| M3 CPR started by a bystander (%, higher is better) | 56.7 ± 27.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M4 time to AED (s, lower is better) | 611.4 ± 141.9 (n=8) | 960.2 ± 385.1 (n=5) | 520.7 ± 83.0 (n=8) |
| M5 time to EMS (s, lower is better) | 837.5 ± 157.8 (n=10) | 790.3 ± 93.4 (n=10) | 789.8 ± 104.5 (n=10) |
| M6 survival proxy (%, higher is better) | 16.8 ± 6.1 (n=10) | 7.7 ± 5.8 (n=10) | 9.9 ± 4.5 (n=10) |
| M7 volunteer before EMS (%, higher is better) | 78.5 ± 23.9 (n=10) | 72.2 ± 23.1 (n=10) | 88.0 ± 12.4 (n=10) |
| M7 AED before EMS (%, higher is better) | 54.3 ± 29.6 (n=10) | 22.0 ± 23.0 (n=10) | 52.7 ± 28.2 (n=10) |
| M8 messages per candidate (msgs, lower is better) | 143.8 ± 19.3 (n=10) | 93.6 ± 12.8 (n=10) | 138.4 ± 15.4 (n=10) |
| M9 gap to oracle B0 (s, lower is better) | 342.3 ± 162.5 (n=10) | 334.1 ± 165.2 (n=9) | 225.6 ± 72.3 (n=10) |
| M10 alerts per volunteer (alerts, lower is better) | 2.4 ± 0.7 (n=10) | 2.9 ± 1.0 (n=10) | 2.4 ± 0.7 (n=10) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M11 location recipients per case (agents, lower is better) | 6.5 ± 1.0 (n=10) | 5.9 ± 0.8 (n=10) | 6.2 ± 0.7 (n=10) |
| M12 recovery after hub crash (s, lower is better) | 22.1 ± 1.8 (n=10) | 21.8 ± 1.4 (n=10) | 22.5 ± 1.4 (n=10) |
| Rule violations (count, lower is better) | 0.2 ± 0.3 (n=10) | 0.1 ± 0.2 (n=10) | 0.1 ± 0.2 (n=10) |

## C5 adversarial sources

| Metric | Ours | B1 naive broadcast | No reputation |
|---|---|---|---|
| M1 verification latency (s, lower is better) | 38.7 ± 12.4 (n=8) | 30.3 ± 10.5 (n=8) | 39.6 ± 12.5 (n=8) |
| M2 precision (%, higher is better) | 26.6 ± 14.0 (n=10) | 15.3 ± 7.6 (n=10) | 16.1 ± 7.5 (n=10) |
| M2 recall (detectable) (%, higher is better) | 79.3 ± 28.5 (n=9) | 83.0 ± 25.7 (n=9) | 83.0 ± 25.7 (n=9) |
| M2 recall (reported) (%, higher is better) | 93.8 ± 14.7 (n=8) | 100.0 ± 0.0 (n=8) | 100.0 ± 0.0 (n=8) |
| M2 false dispatches (per run, lower is better) | 3.0 ± 0.7 (n=10) | 7.1 ± 1.1 (n=10) | 6.5 ± 1.2 (n=10) |
| M3 time to CPR (s, lower is better) | 62.6 ± 22.0 (n=8) | 297.4 ± 113.3 (n=4) | 73.7 ± 42.3 (n=7) |
| M3 CPR started by a bystander (%, higher is better) | 87.5 ± 29.5 (n=8) | 0.0 ± 0.0 (n=4) | 85.7 ± 35.0 (n=7) |
| M4 time to AED (s, lower is better) | 263.9 ± 519.8 (n=2) | 253.5 (n=1) | 280.7 ± 125.2 (n=3) |
| M5 time to EMS (s, lower is better) | 390.3 ± 38.1 (n=8) | 399.4 ± 31.6 (n=8) | 409.1 ± 30.4 (n=8) |
| M6 survival proxy (%, higher is better) | 36.7 ± 15.2 (n=7) | 27.4 ± 11.9 (n=7) | 36.7 ± 15.2 (n=7) |
| M7 volunteer before EMS (%, higher is better) | 55.6 ± 40.6 (n=9) | 44.4 ± 40.6 (n=9) | 66.7 ± 38.5 (n=9) |
| M7 AED before EMS (%, higher is better) | 16.7 ± 27.2 (n=9) | 11.1 ± 25.7 (n=9) | 27.8 ± 34.0 (n=9) |
| M8 messages per candidate (msgs, lower is better) | 109.5 ± 13.3 (n=10) | 109.9 ± 5.8 (n=10) | 137.4 ± 12.5 (n=10) |
| M9 gap to oracle B0 (s, lower is better) | 101.3 ± 86.0 (n=5) | 156.9 ± 132.4 (n=4) | 118.1 ± 61.7 (n=6) |
| M10 alerts per volunteer (alerts, lower is better) | 2.2 ± 0.7 (n=10) | 5.4 ± 0.5 (n=10) | 3.5 ± 0.9 (n=10) |
| M10 minutes on false alarms (min, lower is better) | 22.9 ± 8.3 (n=10) | 104.8 ± 12.5 (n=10) | 47.1 ± 14.9 (n=10) |
| M11 location recipients per case (agents, lower is better) | 3.8 ± 0.3 (n=10) | 4.7 ± 0.4 (n=10) | 3.6 ± 0.2 (n=10) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
