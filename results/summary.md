# Experiment results

65 valid runs. Values are means over seeds with 95 % confidence intervals.

## C1 base urban

| Metric | Ours | B1 naive broadcast |
|---|---|---|
| M1 verification latency (s, lower is better) | 34.5 ± 11.9 (n=5) | 26.1 ± 10.1 (n=5) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) |
| M2 recall (detectable) (%, higher is better) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M3 time to CPR (s, lower is better) | 62.4 ± 25.4 (n=5) | 257.9 ± 132.8 (n=4) |
| M4 time to AED (s, lower is better) | 335.4 ± 54.4 (n=3) | — |
| M5 time to EMS (s, lower is better) | 378.0 ± 45.5 (n=5) | 371.3 ± 45.8 (n=5) |
| M6 survival proxy (%, higher is better) | 43.6 ± 2.1 (n=5) | 33.6 ± 5.8 (n=5) |
| M7 volunteer before EMS (%, higher is better) | 90.0 ± 27.8 (n=5) | 50.0 ± 44.0 (n=5) |
| M7 AED before EMS (%, higher is better) | 25.0 ± 31.1 (n=5) | 0.0 ± 0.0 (n=5) |
| M8 messages per candidate (msgs, lower is better) | 161.0 ± 21.7 (n=5) | 123.8 ± 8.8 (n=5) |
| M9 gap to oracle B0 (s, lower is better) | 98.0 ± 60.5 (n=5) | 141.7 ± 128.9 (n=4) |
| M10 alerts per volunteer (alerts, lower is better) | 1.7 ± 1.3 (n=5) | 3.1 ± 2.0 (n=5) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M11 location recipients per case (agents, lower is better) | 4.8 ± 0.8 (n=5) | 4.7 ± 0.4 (n=5) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |

## C2 noise and false alarms

| Metric | Ours | B1 naive broadcast | AlertFirst | ConfirmFirst | No reputation |
|---|---|---|---|---|---|
| M1 verification latency (s, lower is better) | 38.9 ± 10.9 (n=5) | 30.6 ± 11.5 (n=5) | 35.2 ± 12.7 (n=5) | 44.6 ± 7.8 (n=5) | 39.5 ± 11.2 (n=5) |
| M2 precision (%, higher is better) | 68.3 ± 40.4 (n=5) | 56.7 ± 22.5 (n=5) | 68.3 ± 40.4 (n=5) | 68.3 ± 40.4 (n=5) | 69.8 ± 39.3 (n=5) |
| M2 recall (detectable) (%, higher is better) | 78.7 ± 38.2 (n=5) | 89.3 ± 19.1 (n=5) | 78.7 ± 38.2 (n=5) | 78.7 ± 38.2 (n=5) | 82.7 ± 36.0 (n=5) |
| M2 false dispatches (per run, lower is better) | 1.4 ± 1.9 (n=5) | 2.2 ± 2.0 (n=5) | 1.4 ± 1.9 (n=5) | 1.4 ± 1.9 (n=5) | 1.4 ± 1.9 (n=5) |
| M3 time to CPR (s, lower is better) | 76.3 ± 59.5 (n=5) | 271.5 ± 776.6 (n=2) | 89.4 ± 57.0 (n=5) | 97.1 ± 58.6 (n=5) | 76.5 ± 59.3 (n=5) |
| M5 time to EMS (s, lower is better) | 360.6 ± 33.6 (n=5) | 361.0 ± 33.0 (n=5) | 360.2 ± 33.9 (n=5) | 367.9 ± 33.1 (n=5) | 365.8 ± 41.3 (n=5) |
| M6 survival proxy (%, higher is better) | 42.6 ± 1.2 (n=3) | 33.7 ± 8.2 (n=3) | 42.6 ± 1.3 (n=3) | 42.6 ± 1.3 (n=3) | 42.5 ± 1.1 (n=3) |
| M7 volunteer before EMS (%, higher is better) | 60.0 ± 68.1 (n=5) | 40.0 ± 68.1 (n=5) | 60.0 ± 68.1 (n=5) | 60.0 ± 68.1 (n=5) | 60.0 ± 68.1 (n=5) |
| M7 AED before EMS (%, higher is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M8 messages per candidate (msgs, lower is better) | 118.3 ± 26.1 (n=5) | 111.9 ± 20.8 (n=5) | 90.1 ± 24.3 (n=5) | 133.6 ± 33.0 (n=5) | 120.5 ± 28.5 (n=5) |
| M9 gap to oracle B0 (s, lower is better) | 85.4 ± 82.8 (n=3) | 114.4 ± 340.0 (n=2) | 84.6 ± 79.7 (n=3) | 92.9 ± 50.7 (n=3) | 85.7 ± 80.8 (n=3) |
| M10 alerts per volunteer (alerts, lower is better) | 1.5 ± 1.5 (n=5) | 3.8 ± 1.9 (n=5) | 1.5 ± 1.5 (n=5) | 1.5 ± 1.5 (n=5) | 1.6 ± 1.8 (n=5) |
| M10 minutes on false alarms (min, lower is better) | 9.6 ± 13.9 (n=5) | 23.9 ± 34.7 (n=5) | 9.6 ± 13.9 (n=5) | 9.6 ± 13.9 (n=5) | 9.6 ± 13.9 (n=5) |
| M11 location recipients per case (agents, lower is better) | 4.7 ± 1.5 (n=5) | 4.9 ± 0.5 (n=5) | 4.7 ± 1.5 (n=5) | 4.7 ± 1.5 (n=5) | 4.7 ± 1.5 (n=5) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |

## C3 surge with contention

| Metric | Ours | B1 naive broadcast | k = 1 | k = 3 |
|---|---|---|---|---|
| M1 verification latency (s, lower is better) | 46.6 ± 9.0 (n=5) | 37.0 ± 9.8 (n=5) | 47.6 ± 10.1 (n=5) | 46.5 ± 8.4 (n=5) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) |
| M2 recall (detectable) (%, higher is better) | 64.0 ± 22.2 (n=5) | 64.0 ± 22.2 (n=5) | 64.0 ± 22.2 (n=5) | 64.0 ± 22.2 (n=5) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M3 time to CPR (s, lower is better) | 63.2 ± 13.7 (n=5) | 337.2 ± 90.3 (n=5) | 63.5 ± 14.2 (n=5) | 63.3 ± 14.0 (n=5) |
| M4 time to AED (s, lower is better) | 420.3 ± 106.4 (n=3) | 529.1 ± 303.6 (n=4) | 409.1 ± 45.0 (n=5) | 490.7 ± 171.3 (n=5) |
| M5 time to EMS (s, lower is better) | 509.1 ± 55.7 (n=5) | 498.3 ± 55.6 (n=5) | 509.1 ± 55.7 (n=5) | 509.2 ± 55.6 (n=5) |
| M6 survival proxy (%, higher is better) | 23.9 ± 15.6 (n=5) | 17.4 ± 13.3 (n=5) | 23.9 ± 16.8 (n=5) | 23.9 ± 14.6 (n=5) |
| M7 volunteer before EMS (%, higher is better) | 63.2 ± 24.3 (n=5) | 41.2 ± 31.3 (n=5) | 59.8 ± 20.4 (n=5) | 63.2 ± 24.3 (n=5) |
| M7 AED before EMS (%, higher is better) | 25.3 ± 31.8 (n=5) | 20.9 ± 19.8 (n=5) | 33.9 ± 20.6 (n=5) | 31.7 ± 35.0 (n=5) |
| M8 messages per candidate (msgs, lower is better) | 203.0 ± 31.7 (n=5) | 137.1 ± 21.2 (n=5) | 197.7 ± 31.2 (n=5) | 217.8 ± 36.9 (n=5) |
| M9 gap to oracle B0 (s, lower is better) | 153.2 ± 39.0 (n=5) | 185.1 ± 103.3 (n=5) | 197.6 ± 89.7 (n=5) | 140.7 ± 47.0 (n=5) |
| M10 alerts per volunteer (alerts, lower is better) | 3.9 ± 1.6 (n=5) | 5.2 ± 1.5 (n=5) | 3.8 ± 1.5 (n=5) | 4.1 ± 1.7 (n=5) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M11 location recipients per case (agents, lower is better) | 4.8 ± 0.5 (n=5) | 5.5 ± 0.6 (n=5) | 3.8 ± 0.3 (n=5) | 7.2 ± 1.5 (n=5) |
| Rule violations (count, lower is better) | 2.0 ± 5.6 (n=5) | 3.8 ± 10.6 (n=5) | 1.4 ± 3.9 (n=5) | 2.8 ± 7.8 (n=5) |

## C4 degraded periphery

| Metric | Ours | B1 naive broadcast |
|---|---|---|
| M1 verification latency (s, lower is better) | 40.2 ± 18.4 (n=5) | 31.2 ± 20.2 (n=5) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) |
| M2 recall (detectable) (%, higher is better) | 95.0 ± 13.9 (n=5) | 95.0 ± 13.9 (n=5) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M3 time to CPR (s, lower is better) | 153.4 ± 165.8 (n=5) | 357.3 ± 76.0 (n=5) |
| M4 time to AED (s, lower is better) | 597.9 ± 247.3 (n=5) | 773.5 ± 561.0 (n=3) |
| M5 time to EMS (s, lower is better) | 1008.9 ± 546.5 (n=5) | 829.2 ± 182.1 (n=5) |
| M6 survival proxy (%, higher is better) | 21.8 ± 13.9 (n=5) | 8.6 ± 10.7 (n=5) |
| M7 volunteer before EMS (%, higher is better) | 85.0 ± 41.7 (n=5) | 81.7 ± 36.2 (n=5) |
| M7 AED before EMS (%, higher is better) | 68.3 ± 40.4 (n=5) | 6.7 ± 18.5 (n=5) |
| M8 messages per candidate (msgs, lower is better) | 138.8 ± 26.7 (n=5) | 91.1 ± 16.9 (n=5) |
| M9 gap to oracle B0 (s, lower is better) | 197.0 ± 146.4 (n=5) | 419.5 ± 339.7 (n=5) |
| M10 alerts per volunteer (alerts, lower is better) | 2.2 ± 1.4 (n=5) | 2.6 ± 1.2 (n=5) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M11 location recipients per case (agents, lower is better) | 5.8 ± 1.5 (n=5) | 5.8 ± 1.1 (n=5) |
| M12 recovery after hub crash (s, lower is better) | 20.9 ± 3.1 (n=5) | 21.9 ± 1.6 (n=5) |
| Rule violations (count, lower is better) | 0.2 ± 0.6 (n=5) | 0.0 ± 0.0 (n=5) |
