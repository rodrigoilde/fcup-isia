# Experiment results

65 valid runs. Values are means over seeds with 95 % confidence intervals.

## C1 base urban

| Metric | Ours | B1 naive broadcast |
|---|---|---|
| M1 verification latency (s, lower is better) | 34.4 ± 12.0 (n=5) | 25.8 ± 10.2 (n=5) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) |
| M2 recall (detectable) (%, higher is better) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M3 time to CPR (s, lower is better) | 55.6 ± 24.7 (n=5) | 244.7 ± 129.7 (n=4) |
| M4 time to AED (s, lower is better) | 335.6 ± 53.2 (n=3) | 343.7 ± 137.3 (n=2) |
| M5 time to EMS (s, lower is better) | 378.4 ± 45.3 (n=5) | 371.2 ± 45.2 (n=5) |
| M6 survival proxy (%, higher is better) | 44.2 ± 2.5 (n=5) | 34.1 ± 6.5 (n=5) |
| M7 volunteer before EMS (%, higher is better) | 90.0 ± 27.8 (n=5) | 45.0 ± 46.1 (n=5) |
| M7 AED before EMS (%, higher is better) | 25.0 ± 31.1 (n=5) | 20.0 ± 34.0 (n=5) |
| M8 messages per candidate (msgs, lower is better) | 161.1 ± 21.7 (n=5) | 125.6 ± 11.7 (n=5) |
| M9 gap to oracle B0 (s, lower is better) | 98.5 ± 61.1 (n=5) | 156.8 ± 151.2 (n=4) |
| M10 alerts per volunteer (alerts, lower is better) | 1.7 ± 1.3 (n=5) | 3.1 ± 2.0 (n=5) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M11 location recipients per case (agents, lower is better) | 4.8 ± 0.8 (n=5) | 5.0 ± 1.1 (n=5) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |

## C2 noise and false alarms

| Metric | Ours | B1 naive broadcast | AlertFirst | ConfirmFirst | No reputation |
|---|---|---|---|---|---|
| M1 verification latency (s, lower is better) | 39.0 ± 10.6 (n=5) | 30.5 ± 11.5 (n=5) | 35.5 ± 12.4 (n=5) | 44.6 ± 7.6 (n=5) | 39.3 ± 11.4 (n=5) |
| M2 precision (%, higher is better) | 68.3 ± 40.4 (n=5) | 56.7 ± 22.5 (n=5) | 68.3 ± 40.4 (n=5) | 68.3 ± 40.4 (n=5) | 69.8 ± 39.3 (n=5) |
| M2 recall (detectable) (%, higher is better) | 78.7 ± 38.2 (n=5) | 89.3 ± 19.1 (n=5) | 78.7 ± 38.2 (n=5) | 78.7 ± 38.2 (n=5) | 82.7 ± 36.0 (n=5) |
| M2 false dispatches (per run, lower is better) | 1.4 ± 1.9 (n=5) | 2.2 ± 2.0 (n=5) | 1.4 ± 1.9 (n=5) | 1.4 ± 1.9 (n=5) | 1.4 ± 1.9 (n=5) |
| M3 time to CPR (s, lower is better) | 89.8 ± 57.4 (n=5) | 304.9 ± 406.1 (n=2) | 89.6 ± 57.2 (n=5) | 96.7 ± 57.8 (n=5) | 89.5 ± 57.5 (n=5) |
| M4 time to AED (s, lower is better) | — | 336.9 (n=1) | — | — | — |
| M5 time to EMS (s, lower is better) | 360.6 ± 33.2 (n=5) | 361.3 ± 33.1 (n=5) | 360.8 ± 33.4 (n=5) | 367.4 ± 33.2 (n=5) | 365.3 ± 41.0 (n=5) |
| M6 survival proxy (%, higher is better) | 42.6 ± 1.3 (n=3) | 33.7 ± 3.4 (n=3) | 42.6 ± 1.1 (n=3) | 42.6 ± 1.2 (n=3) | 42.6 ± 1.3 (n=3) |
| M7 volunteer before EMS (%, higher is better) | 60.0 ± 68.1 (n=5) | 26.7 ± 54.0 (n=5) | 60.0 ± 68.1 (n=5) | 60.0 ± 68.1 (n=5) | 60.0 ± 68.1 (n=5) |
| M7 AED before EMS (%, higher is better) | 0.0 ± 0.0 (n=5) | 20.0 ± 55.6 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M8 messages per candidate (msgs, lower is better) | 118.2 ± 25.9 (n=5) | 112.7 ± 20.4 (n=5) | 90.1 ± 24.4 (n=5) | 133.6 ± 33.0 (n=5) | 120.4 ± 28.5 (n=5) |
| M9 gap to oracle B0 (s, lower is better) | 85.0 ± 78.5 (n=3) | 194.6 ± 252.9 (n=2) | 85.3 ± 80.3 (n=3) | 91.8 ± 51.1 (n=3) | 84.9 ± 80.2 (n=3) |
| M10 alerts per volunteer (alerts, lower is better) | 1.5 ± 1.5 (n=5) | 3.8 ± 1.9 (n=5) | 1.5 ± 1.5 (n=5) | 1.5 ± 1.5 (n=5) | 1.6 ± 1.8 (n=5) |
| M10 minutes on false alarms (min, lower is better) | 9.6 ± 13.9 (n=5) | 23.9 ± 34.7 (n=5) | 9.6 ± 13.9 (n=5) | 9.6 ± 13.9 (n=5) | 9.6 ± 13.9 (n=5) |
| M11 location recipients per case (agents, lower is better) | 4.7 ± 1.5 (n=5) | 4.9 ± 0.5 (n=5) | 4.7 ± 1.5 (n=5) | 4.7 ± 1.5 (n=5) | 4.7 ± 1.5 (n=5) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |

## C3 surge with contention

| Metric | Ours | B1 naive broadcast | k = 1 | k = 3 |
|---|---|---|---|---|
| M1 verification latency (s, lower is better) | 46.8 ± 8.6 (n=5) | 37.1 ± 10.1 (n=5) | 46.5 ± 8.4 (n=5) | 47.6 ± 6.0 (n=5) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) |
| M2 recall (detectable) (%, higher is better) | 64.0 ± 22.2 (n=5) | 64.0 ± 22.2 (n=5) | 64.0 ± 22.2 (n=5) | 64.0 ± 22.2 (n=5) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M3 time to CPR (s, lower is better) | 63.4 ± 14.1 (n=5) | 405.6 ± 80.4 (n=5) | 63.6 ± 14.4 (n=5) | 63.2 ± 14.1 (n=5) |
| M4 time to AED (s, lower is better) | 415.6 ± 57.8 (n=4) | 464.6 ± 204.0 (n=2) | 409.5 ± 45.1 (n=5) | 513.3 ± 235.9 (n=4) |
| M5 time to EMS (s, lower is better) | 509.3 ± 55.3 (n=5) | 498.2 ± 55.7 (n=5) | 509.3 ± 55.8 (n=5) | 509.1 ± 55.5 (n=5) |
| M6 survival proxy (%, higher is better) | 23.9 ± 15.7 (n=5) | 16.8 ± 11.9 (n=5) | 23.8 ± 16.8 (n=5) | 23.9 ± 14.6 (n=5) |
| M7 volunteer before EMS (%, higher is better) | 63.2 ± 24.3 (n=5) | 44.6 ± 34.3 (n=5) | 59.8 ± 20.4 (n=5) | 63.2 ± 24.3 (n=5) |
| M7 AED before EMS (%, higher is better) | 28.2 ± 28.2 (n=5) | 10.7 ± 19.1 (n=5) | 33.9 ± 20.6 (n=5) | 28.9 ± 38.5 (n=5) |
| M8 messages per candidate (msgs, lower is better) | 204.1 ± 29.8 (n=5) | 135.0 ± 24.0 (n=5) | 197.9 ± 30.4 (n=5) | 218.3 ± 36.4 (n=5) |
| M9 gap to oracle B0 (s, lower is better) | 153.4 ± 40.2 (n=5) | 245.0 ± 93.0 (n=5) | 197.8 ± 89.5 (n=5) | 140.4 ± 47.7 (n=5) |
| M10 alerts per volunteer (alerts, lower is better) | 3.8 ± 1.4 (n=5) | 5.1 ± 1.3 (n=5) | 3.7 ± 1.4 (n=5) | 4.1 ± 1.4 (n=5) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M11 location recipients per case (agents, lower is better) | 5.0 ± 1.0 (n=5) | 5.3 ± 0.4 (n=5) | 3.9 ± 0.4 (n=5) | 7.0 ± 1.6 (n=5) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |

## C4 degraded periphery

| Metric | Ours | B1 naive broadcast |
|---|---|---|
| M1 verification latency (s, lower is better) | 40.7 ± 30.5 (n=5) | 31.3 ± 20.1 (n=5) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=5) | 100.0 ± 0.0 (n=5) |
| M2 recall (detectable) (%, higher is better) | 95.0 ± 13.9 (n=5) | 95.0 ± 13.9 (n=5) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M3 time to CPR (s, lower is better) | 59.3 ± 27.4 (n=5) | 473.5 ± 179.2 (n=5) |
| M4 time to AED (s, lower is better) | 542.7 ± 119.2 (n=3) | 798.8 ± 868.7 (n=3) |
| M5 time to EMS (s, lower is better) | 725.7 ± 155.9 (n=5) | 808.7 ± 280.8 (n=5) |
| M6 survival proxy (%, higher is better) | 23.3 ± 14.7 (n=5) | 12.2 ± 11.7 (n=5) |
| M7 volunteer before EMS (%, higher is better) | 73.3 ± 31.4 (n=5) | 58.3 ± 46.3 (n=5) |
| M7 AED before EMS (%, higher is better) | 35.0 ± 52.0 (n=5) | 11.7 ± 20.2 (n=5) |
| M8 messages per candidate (msgs, lower is better) | 132.5 ± 28.5 (n=5) | 88.5 ± 17.0 (n=5) |
| M9 gap to oracle B0 (s, lower is better) | 221.0 ± 169.8 (n=5) | 382.8 ± 180.3 (n=4) |
| M10 alerts per volunteer (alerts, lower is better) | 2.1 ± 1.9 (n=5) | 2.8 ± 1.4 (n=5) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
| M11 location recipients per case (agents, lower is better) | 5.9 ± 1.6 (n=5) | 5.7 ± 1.1 (n=5) |
| M12 recovery after hub crash (s, lower is better) | 18.8 ± 3.1 (n=5) | 19.9 ± 1.5 (n=5) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=5) | 0.0 ± 0.0 (n=5) |
