# Experiment results

210 valid runs at commit `de13290a48e40ba4098fa5da95639c68366acece`. Values are means over seeds with 95 % confidence intervals.

## C1 base urban

| Metric | Ours | B1 naive broadcast | 10 % message loss | 20 % message loss | No guidance |
|---|---|---|---|---|---|
| M1 verification latency (s, lower is better) | 33.5 ± 10.7 (n=10) | 26.4 ± 8.6 (n=10) | 39.9 ± 13.7 (n=10) | 41.8 ± 8.0 (n=9) | 33.6 ± 10.5 (n=10) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) |
| M2 recall (detectable) (%, higher is better) | 92.5 ± 12.1 (n=10) | 92.5 ± 12.1 (n=10) | 92.5 ± 12.1 (n=10) | 76.7 ± 23.1 (n=10) | 92.5 ± 12.1 (n=10) |
| M2 recall (reported) (%, higher is better) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 84.2 ± 22.9 (n=10) | 100.0 ± 0.0 (n=10) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M2 false dispatches with a witness (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M2 false dispatches from sensors only (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M3 time to CPR (s, lower is better) | 52.2 ± 12.4 (n=10) | 306.5 ± 41.3 (n=7) | 175.4 ± 108.3 (n=10) | 176.7 ± 114.1 (n=9) | 229.8 ± 51.8 (n=10) |
| M3 CPR started by a bystander (%, higher is better) | 95.0 ± 11.3 (n=10) | 0.0 ± 0.0 (n=7) | 55.0 ± 31.3 (n=10) | 66.7 ± 33.3 (n=9) | 0.0 ± 0.0 (n=10) |
| M4 time to AED (s, lower is better) | 328.4 ± 49.4 (n=5) | 399.3 (n=1) | 392.7 ± 84.3 (n=7) | 703.5 ± 605.3 (n=4) | 328.2 ± 49.0 (n=5) |
| M5 time to EMS (s, lower is better) | 385.1 ± 27.3 (n=10) | 378.5 ± 25.8 (n=10) | 443.9 ± 39.5 (n=10) | 459.8 ± 60.5 (n=9) | 385.1 ± 27.0 (n=10) |
| M6 survival proxy (%, higher is better) | 41.8 ± 4.7 (n=10) | 31.3 ± 4.0 (n=10) | 28.5 ± 9.0 (n=10) | 20.0 ± 11.7 (n=10) | 34.7 ± 4.6 (n=10) |
| M7 volunteer before EMS (%, higher is better) | 81.7 ± 17.3 (n=10) | 55.8 ± 32.0 (n=10) | 76.7 ± 24.6 (n=10) | 46.7 ± 31.7 (n=10) | 81.7 ± 17.3 (n=10) |
| M7 AED before EMS (%, higher is better) | 25.8 ± 23.9 (n=10) | 2.5 ± 5.6 (n=10) | 38.3 ± 22.5 (n=10) | 15.8 ± 15.5 (n=10) | 25.8 ± 23.9 (n=10) |
| M8 messages per candidate (msgs, lower is better) | 165.8 ± 10.1 (n=10) | 127.1 ± 4.7 (n=10) | 118.9 ± 15.4 (n=10) | 110.2 ± 37.2 (n=10) | 160.8 ± 9.7 (n=10) |
| M8 all messages, heartbeats included (msgs per run, lower is better) | 16528.2 ± 240.8 (n=10) | 16462.1 ± 158.0 (n=10) | 16377.5 ± 209.0 (n=10) | 16124.1 ± 123.0 (n=10) | 16527.6 ± 236.4 (n=10) |
| M8 background messages (P23, P25, P27) (msgs per run, lower is better) | 16101.2 ± 73.7 (n=10) | 16138.2 ± 52.5 (n=10) | 15966.7 ± 59.6 (n=10) | 15778.8 ± 40.4 (n=10) | 16113.1 ± 80.7 (n=10) |
| M9 gap to oracle B0 from the collapse (s, lower is better) | 118.9 ± 44.1 (n=10) | 188.2 ± 47.3 (n=7) | 184.0 ± 46.1 (n=10) | 302.1 ± 145.8 (n=8) | 119.0 ± 43.8 (n=10) |
| M9 gap to oracle B0 from the declaration (s, lower is better) | 83.4 ± 37.3 (n=10) | 156.3 ± 40.1 (n=7) | 143.0 ± 35.3 (n=10) | 263.2 ± 140.3 (n=8) | 83.2 ± 37.2 (n=10) |
| M10 alerts per volunteer (alerts, lower is better) | 1.3 ± 0.6 (n=10) | 2.4 ± 1.0 (n=10) | 1.3 ± 0.7 (n=10) | 1.1 ± 0.4 (n=10) | 1.3 ± 0.6 (n=10) |
| M10 Jain index of tasks (0-1, higher is better) | 0.2 ± 0.1 (n=10) | 0.2 ± 0.1 (n=10) | 0.2 ± 0.1 (n=10) | 0.2 ± 0.1 (n=9) | 0.2 ± 0.1 (n=10) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M11 location recipients per case (agents, lower is better) | 5.3 ± 1.0 (n=10) | 5.1 ± 0.3 (n=10) | 5.2 ± 0.7 (n=10) | 4.2 ± 0.8 (n=9) | 5.3 ± 1.0 (n=10) |
| M13 time to CPR, central cells (s, lower is better) | 49.2 ± 15.3 (n=7) | 304.6 ± 76.8 (n=5) | 139.8 ± 140.5 (n=7) | 195.4 ± 171.6 (n=7) | 201.8 ± 66.3 (n=6) |
| M13 time to CPR, peripheral cells (s, lower is better) | 52.4 ± 15.6 (n=8) | 308.3 ± 44.4 (n=5) | 146.2 ± 125.0 (n=7) | 110.3 ± 87.2 (n=7) | 241.6 ± 74.5 (n=7) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.2 ± 0.3 (n=10) | 0.4 ± 0.5 (n=10) | 0.0 ± 0.0 (n=10) |
| P1 incidents, total over seeds (count) | 26.0 (n=10) | 26.0 (n=10) | 26.0 (n=10) | 26.0 (n=10) | 26.0 (n=10) |
| M6 patients, total over seeds (count) | 17.0 (n=10) | 17.0 (n=10) | 17.0 (n=10) | 17.0 (n=10) | 17.0 (n=10) |

## C2 noise and false alarms

| Metric | Ours | B1 naive broadcast | AlertFirst | ConfirmFirst | No reputation |
|---|---|---|---|---|---|
| M1 verification latency (s, lower is better) | 40.6 ± 13.8 (n=7) | 30.5 ± 10.7 (n=8) | 39.3 ± 13.6 (n=7) | 47.3 ± 10.7 (n=8) | 41.0 ± 13.8 (n=8) |
| M2 precision (%, higher is better) | 23.1 ± 13.8 (n=10) | 24.9 ± 10.6 (n=10) | 22.5 ± 14.9 (n=10) | 24.9 ± 13.4 (n=10) | 22.6 ± 12.1 (n=10) |
| M2 recall (detectable) (%, higher is better) | 75.6 ± 33.4 (n=9) | 83.0 ± 25.7 (n=9) | 75.6 ± 33.4 (n=9) | 79.3 ± 28.5 (n=9) | 79.3 ± 28.5 (n=9) |
| M2 recall (reported) (%, higher is better) | 87.5 ± 29.5 (n=8) | 100.0 ± 0.0 (n=8) | 87.5 ± 29.5 (n=8) | 93.8 ± 14.7 (n=8) | 93.8 ± 14.7 (n=8) |
| M2 false dispatches (per run, lower is better) | 4.7 ± 2.0 (n=10) | 9.4 ± 2.1 (n=10) | 4.6 ± 2.0 (n=10) | 4.9 ± 1.9 (n=10) | 5.8 ± 2.3 (n=10) |
| M2 false dispatches with a witness (per run, lower is better) | 1.8 ± 1.5 (n=10) | 2.0 ± 1.4 (n=10) | 1.8 ± 1.5 (n=10) | 1.8 ± 1.5 (n=10) | 1.8 ± 1.5 (n=10) |
| M2 false dispatches from sensors only (per run, lower is better) | 2.9 ± 0.9 (n=10) | 7.4 ± 1.7 (n=10) | 2.8 ± 1.1 (n=10) | 3.1 ± 1.0 (n=10) | 4.0 ± 1.4 (n=10) |
| M3 time to CPR (s, lower is better) | 65.8 ± 26.4 (n=7) | 270.8 ± 134.3 (n=3) | 66.0 ± 26.5 (n=7) | 71.2 ± 19.5 (n=7) | 64.0 ± 22.7 (n=7) |
| M3 CPR started by a bystander (%, higher is better) | 85.7 ± 35.0 (n=7) | 0.0 ± 0.0 (n=3) | 85.7 ± 35.0 (n=7) | 85.7 ± 35.0 (n=7) | 85.7 ± 35.0 (n=7) |
| M4 time to AED (s, lower is better) | 223.6 (n=1) | — | 225.1 (n=1) | 224.7 (n=1) | 224.6 (n=1) |
| M5 time to EMS (s, lower is better) | 386.1 ± 30.5 (n=7) | 371.8 ± 25.8 (n=8) | 385.9 ± 30.2 (n=7) | 394.0 ± 29.1 (n=8) | 387.9 ± 29.2 (n=8) |
| M6 survival proxy (%, higher is better) | 36.2 ± 14.9 (n=7) | 26.9 ± 11.5 (n=7) | 36.2 ± 14.9 (n=7) | 35.8 ± 14.8 (n=7) | 36.2 ± 14.9 (n=7) |
| M7 volunteer before EMS (%, higher is better) | 55.6 ± 40.6 (n=9) | 25.9 ± 33.4 (n=9) | 55.6 ± 40.6 (n=9) | 55.6 ± 40.6 (n=9) | 55.6 ± 40.6 (n=9) |
| M7 AED before EMS (%, higher is better) | 5.6 ± 12.8 (n=9) | 0.0 ± 0.0 (n=9) | 5.6 ± 12.8 (n=9) | 5.6 ± 12.8 (n=9) | 5.6 ± 12.8 (n=9) |
| M8 messages per candidate (msgs, lower is better) | 104.7 ± 7.0 (n=10) | 93.3 ± 7.5 (n=10) | 93.0 ± 5.9 (n=10) | 120.4 ± 9.8 (n=10) | 111.5 ± 5.9 (n=10) |
| M8 all messages, heartbeats included (msgs per run, lower is better) | 17503.1 ± 365.9 (n=10) | 17326.3 ± 211.5 (n=10) | 17711.8 ± 344.0 (n=10) | 17134.1 ± 296.9 (n=10) | 17366.7 ± 376.5 (n=10) |
| M8 background messages (P23, P25, P27) (msgs per run, lower is better) | 16186.5 ± 54.5 (n=10) | 16174.4 ± 67.1 (n=10) | 16161.2 ± 46.9 (n=10) | 15997.7 ± 38.2 (n=10) | 15955.8 ± 33.3 (n=10) |
| M9 gap to oracle B0 from the collapse (s, lower is better) | 110.3 ± 75.9 (n=5) | 153.9 ± 70.5 (n=3) | 102.7 ± 57.6 (n=5) | 113.8 ± 75.5 (n=5) | 99.6 ± 61.8 (n=5) |
| M9 gap to oracle B0 from the declaration (s, lower is better) | 72.5 ± 59.9 (n=5) | 119.7 ± 120.8 (n=3) | 65.0 ± 43.3 (n=5) | 71.4 ± 61.1 (n=5) | 65.0 ± 42.6 (n=5) |
| M10 alerts per volunteer (alerts, lower is better) | 3.0 ± 0.9 (n=10) | 5.9 ± 0.1 (n=10) | 2.9 ± 0.9 (n=10) | 3.1 ± 0.7 (n=10) | 3.5 ± 0.9 (n=10) |
| M10 Jain index of tasks (0-1, higher is better) | 0.3 ± 0.1 (n=10) | 0.4 ± 0.1 (n=10) | 0.3 ± 0.1 (n=10) | 0.3 ± 0.1 (n=10) | 0.4 ± 0.1 (n=10) |
| M10 minutes on false alarms (min, lower is better) | 47.7 ± 22.6 (n=10) | 62.5 ± 18.9 (n=10) | 48.0 ± 23.9 (n=10) | 50.9 ± 22.0 (n=10) | 59.5 ± 25.4 (n=10) |
| M11 location recipients per case (agents, lower is better) | 4.5 ± 0.5 (n=10) | 4.0 ± 0.5 (n=10) | 4.5 ± 0.6 (n=10) | 4.4 ± 0.4 (n=10) | 4.4 ± 0.4 (n=10) |
| M13 time to CPR, central cells (s, lower is better) | 75.2 ± 95.0 (n=3) | 232.1 (n=1) | 75.4 ± 96.1 (n=3) | 72.2 ± 83.0 (n=3) | 70.3 ± 76.8 (n=3) |
| M13 time to CPR, peripheral cells (s, lower is better) | 57.1 ± 25.8 (n=5) | 290.1 ± 539.5 (n=2) | 57.2 ± 25.5 (n=5) | 69.5 ± 14.0 (n=5) | 57.4 ± 25.5 (n=5) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=10) | 0.1 ± 0.2 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| P1 incidents, total over seeds (count) | 16.0 (n=10) | 16.0 (n=10) | 16.0 (n=10) | 16.0 (n=10) | 16.0 (n=10) |
| M6 patients, total over seeds (count) | 7.0 (n=10) | 7.0 (n=10) | 7.0 (n=10) | 7.0 (n=10) | 7.0 (n=10) |

## C3 surge with contention

| Metric | Ours | B1 naive broadcast | k = 1 | k = 3 | No guidance |
|---|---|---|---|---|---|
| M1 verification latency (s, lower is better) | 49.5 ± 3.5 (n=10) | 39.1 ± 4.7 (n=10) | 49.4 ± 3.4 (n=10) | 49.7 ± 3.3 (n=10) | 49.3 ± 3.2 (n=10) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) |
| M2 recall (detectable) (%, higher is better) | 80.3 ± 10.8 (n=10) | 81.5 ± 9.6 (n=10) | 80.3 ± 10.8 (n=10) | 80.3 ± 10.8 (n=10) | 81.5 ± 9.6 (n=10) |
| M2 recall (reported) (%, higher is better) | 95.7 ± 5.2 (n=10) | 95.9 ± 4.9 (n=10) | 95.7 ± 5.2 (n=10) | 95.7 ± 5.2 (n=10) | 95.9 ± 4.9 (n=10) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M2 false dispatches with a witness (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M2 false dispatches from sensors only (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M3 time to CPR (s, lower is better) | 75.1 ± 25.2 (n=10) | 361.6 ± 81.0 (n=10) | 75.4 ± 24.9 (n=10) | 75.0 ± 25.0 (n=10) | 339.3 ± 36.6 (n=10) |
| M3 CPR started by a bystander (%, higher is better) | 88.4 ± 9.9 (n=10) | 0.0 ± 0.0 (n=10) | 85.9 ± 9.8 (n=10) | 85.9 ± 9.8 (n=10) | 0.0 ± 0.0 (n=10) |
| M4 time to AED (s, lower is better) | 521.0 ± 74.5 (n=9) | 705.4 ± 279.8 (n=6) | 485.9 ± 55.1 (n=9) | 527.6 ± 62.6 (n=9) | 519.9 ± 72.1 (n=9) |
| M5 time to EMS (s, lower is better) | 547.9 ± 56.3 (n=10) | 535.8 ± 54.3 (n=10) | 549.7 ± 59.8 (n=10) | 547.9 ± 56.3 (n=10) | 546.8 ± 56.9 (n=10) |
| M6 survival proxy (%, higher is better) | 24.8 ± 10.8 (n=8) | 13.9 ± 7.0 (n=8) | 24.5 ± 11.1 (n=8) | 24.9 ± 10.3 (n=8) | 17.1 ± 8.7 (n=8) |
| M7 volunteer before EMS (%, higher is better) | 74.5 ± 16.2 (n=10) | 49.2 ± 15.4 (n=10) | 76.3 ± 15.0 (n=10) | 79.6 ± 16.6 (n=10) | 74.5 ± 16.2 (n=10) |
| M7 AED before EMS (%, higher is better) | 40.9 ± 18.0 (n=10) | 18.1 ± 12.8 (n=10) | 44.8 ± 17.6 (n=10) | 42.6 ± 20.1 (n=10) | 42.1 ± 18.1 (n=10) |
| M8 messages per candidate (msgs, lower is better) | 218.4 ± 16.0 (n=10) | 146.3 ± 10.8 (n=10) | 212.6 ± 15.9 (n=10) | 232.0 ± 18.8 (n=10) | 208.7 ± 15.6 (n=10) |
| M8 all messages, heartbeats included (msgs per run, lower is better) | 17649.4 ± 335.2 (n=10) | 17158.4 ± 204.8 (n=10) | 17582.4 ± 309.8 (n=10) | 17810.2 ± 385.2 (n=10) | 17612.3 ± 316.9 (n=10) |
| M8 background messages (P23, P25, P27) (msgs per run, lower is better) | 16107.9 ± 60.7 (n=10) | 16111.1 ± 38.7 (n=10) | 16081.4 ± 32.2 (n=10) | 16169.1 ± 76.3 (n=10) | 16115.2 ± 56.1 (n=10) |
| M9 gap to oracle B0 from the collapse (s, lower is better) | 212.1 ± 49.0 (n=10) | 242.3 ± 90.7 (n=10) | 220.7 ± 46.8 (n=10) | 194.3 ± 33.6 (n=10) | 212.0 ± 48.9 (n=10) |
| M9 gap to oracle B0 from the declaration (s, lower is better) | 162.0 ± 48.5 (n=10) | 195.8 ± 90.1 (n=10) | 169.3 ± 46.3 (n=10) | 143.2 ± 34.3 (n=10) | 161.8 ± 48.7 (n=10) |
| M10 alerts per volunteer (alerts, lower is better) | 4.5 ± 0.5 (n=10) | 5.8 ± 0.3 (n=10) | 4.4 ± 0.5 (n=10) | 4.8 ± 0.6 (n=10) | 4.5 ± 0.5 (n=10) |
| M10 Jain index of tasks (0-1, higher is better) | 0.5 ± 0.1 (n=10) | 0.6 ± 0.1 (n=10) | 0.3 ± 0.1 (n=10) | 0.6 ± 0.1 (n=10) | 0.5 ± 0.1 (n=10) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M11 location recipients per case (agents, lower is better) | 4.8 ± 0.6 (n=10) | 5.1 ± 0.3 (n=10) | 3.7 ± 0.3 (n=10) | 6.5 ± 1.2 (n=10) | 4.8 ± 0.7 (n=10) |
| M13 time to CPR, central cells (s, lower is better) | 78.4 ± 26.2 (n=10) | 355.5 ± 82.1 (n=10) | 78.2 ± 26.1 (n=10) | 77.8 ± 26.2 (n=10) | 346.5 ± 49.8 (n=10) |
| M13 time to CPR, peripheral cells (s, lower is better) | 192.3 ± 161.1 (n=5) | 422.8 (n=1) | 220.2 ± 187.6 (n=5) | 210.3 ± 214.9 (n=5) | 292.4 ± 67.0 (n=5) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| P1 incidents, total over seeds (count) | 56.0 (n=10) | 56.0 (n=10) | 56.0 (n=10) | 56.0 (n=10) | 56.0 (n=10) |
| M6 patients, total over seeds (count) | 15.0 (n=10) | 15.0 (n=10) | 15.0 (n=10) | 15.0 (n=10) | 15.0 (n=10) |

## C4 degraded periphery

| Metric | Ours | B1 naive broadcast | No guidance |
|---|---|---|---|
| M1 verification latency (s, lower is better) | 41.3 ± 9.0 (n=10) | 27.7 ± 10.0 (n=10) | 39.6 ± 12.5 (n=10) |
| M2 precision (%, higher is better) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) |
| M2 recall (detectable) (%, higher is better) | 95.5 ± 6.8 (n=10) | 95.5 ± 6.8 (n=10) | 95.5 ± 6.8 (n=10) |
| M2 recall (reported) (%, higher is better) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) | 100.0 ± 0.0 (n=10) |
| M2 false dispatches (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M2 false dispatches with a witness (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M2 false dispatches from sensors only (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M3 time to CPR (s, lower is better) | 164.4 ± 107.5 (n=10) | 383.1 ± 83.0 (n=9) | 411.1 ± 52.2 (n=10) |
| M3 CPR started by a bystander (%, higher is better) | 60.0 ± 26.5 (n=10) | 0.0 ± 0.0 (n=9) | 0.0 ± 0.0 (n=10) |
| M4 time to AED (s, lower is better) | 598.7 ± 147.6 (n=7) | 767.1 ± 180.3 (n=5) | 607.5 ± 188.0 (n=7) |
| M5 time to EMS (s, lower is better) | 759.7 ± 79.2 (n=9) | 831.6 ± 186.7 (n=10) | 863.4 ± 216.6 (n=10) |
| M6 survival proxy (%, higher is better) | 16.1 ± 6.8 (n=10) | 9.1 ± 5.4 (n=10) | 12.8 ± 6.5 (n=10) |
| M7 volunteer before EMS (%, higher is better) | 91.0 ± 10.8 (n=10) | 70.2 ± 23.1 (n=10) | 95.0 ± 7.5 (n=10) |
| M7 AED before EMS (%, higher is better) | 46.5 ± 30.3 (n=10) | 15.3 ± 15.4 (n=10) | 49.7 ± 31.4 (n=10) |
| M8 messages per candidate (msgs, lower is better) | 130.5 ± 14.7 (n=10) | 94.1 ± 9.5 (n=10) | 130.8 ± 17.4 (n=10) |
| M8 all messages, heartbeats included (msgs per run, lower is better) | 15042.9 ± 169.5 (n=10) | 14975.6 ± 141.9 (n=10) | 15262.4 ± 262.1 (n=10) |
| M8 background messages (P23, P25, P27) (msgs per run, lower is better) | 14625.4 ± 47.1 (n=10) | 14677.6 ± 42.1 (n=10) | 14740.1 ± 50.6 (n=10) |
| M9 gap to oracle B0 from the collapse (s, lower is better) | 241.8 ± 76.2 (n=10) | 268.1 ± 84.5 (n=9) | 252.1 ± 70.2 (n=10) |
| M9 gap to oracle B0 from the declaration (s, lower is better) | 202.9 ± 79.7 (n=10) | 235.7 ± 94.8 (n=9) | 213.4 ± 65.9 (n=10) |
| M10 alerts per volunteer (alerts, lower is better) | 1.9 ± 0.6 (n=10) | 3.1 ± 1.0 (n=10) | 2.5 ± 1.1 (n=10) |
| M10 Jain index of tasks (0-1, higher is better) | 0.5 ± 0.1 (n=10) | 0.6 ± 0.1 (n=10) | 0.5 ± 0.1 (n=10) |
| M10 minutes on false alarms (min, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M11 location recipients per case (agents, lower is better) | 6.0 ± 0.8 (n=10) | 5.9 ± 0.6 (n=10) | 5.4 ± 0.8 (n=10) |
| M12 recovery after hub crash (s, lower is better) | 21.1 ± 1.7 (n=10) | 22.2 ± 1.7 (n=10) | 20.8 ± 1.9 (n=10) |
| M13 time to CPR, central cells (s, lower is better) | 257.5 ± 244.4 (n=6) | 357.5 ± 112.6 (n=5) | 452.3 ± 144.8 (n=6) |
| M13 time to CPR, peripheral cells (s, lower is better) | 109.8 ± 54.3 (n=9) | 389.3 ± 86.6 (n=9) | 457.2 ± 150.1 (n=9) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=10) | 0.3 ± 0.3 (n=10) | 0.6 ± 0.5 (n=10) |
| P1 incidents, total over seeds (count) | 29.0 (n=10) | 29.0 (n=10) | 29.0 (n=10) |
| M6 patients, total over seeds (count) | 15.0 (n=10) | 15.0 (n=10) | 15.0 (n=10) |

## C5 adversarial sources

| Metric | Ours | B1 naive broadcast | No reputation |
|---|---|---|---|
| M1 verification latency (s, lower is better) | 39.9 ± 12.9 (n=8) | 30.6 ± 10.6 (n=8) | 39.7 ± 12.6 (n=8) |
| M2 precision (%, higher is better) | 28.3 ± 15.0 (n=10) | 15.3 ± 7.6 (n=10) | 15.8 ± 7.6 (n=10) |
| M2 recall (detectable) (%, higher is better) | 83.0 ± 25.7 (n=9) | 83.0 ± 25.7 (n=9) | 83.0 ± 25.7 (n=9) |
| M2 recall (reported) (%, higher is better) | 100.0 ± 0.0 (n=8) | 100.0 ± 0.0 (n=8) | 100.0 ± 0.0 (n=8) |
| M2 false dispatches (per run, lower is better) | 3.0 ± 0.7 (n=10) | 7.1 ± 1.1 (n=10) | 6.9 ± 1.2 (n=10) |
| M2 false dispatches with a witness (per run, lower is better) | 3.0 ± 0.7 (n=10) | 7.1 ± 1.1 (n=10) | 6.9 ± 1.2 (n=10) |
| M2 false dispatches from sensors only (per run, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| M3 time to CPR (s, lower is better) | 82.8 ± 64.0 (n=7) | 279.5 ± 61.0 (n=6) | 77.3 ± 44.8 (n=8) |
| M3 CPR started by a bystander (%, higher is better) | 85.7 ± 35.0 (n=7) | 0.0 ± 0.0 (n=6) | 87.5 ± 29.5 (n=8) |
| M4 time to AED (s, lower is better) | 263.8 ± 494.4 (n=2) | — | 281.2 ± 125.7 (n=3) |
| M5 time to EMS (s, lower is better) | 395.6 ± 33.8 (n=8) | 399.8 ± 31.2 (n=8) | 409.4 ± 30.1 (n=8) |
| M6 survival proxy (%, higher is better) | 36.7 ± 15.2 (n=7) | 27.9 ± 12.0 (n=7) | 36.3 ± 15.1 (n=7) |
| M7 volunteer before EMS (%, higher is better) | 55.6 ± 40.6 (n=9) | 48.1 ± 38.7 (n=9) | 55.6 ± 40.6 (n=9) |
| M7 AED before EMS (%, higher is better) | 16.7 ± 27.2 (n=9) | 0.0 ± 0.0 (n=9) | 27.8 ± 34.0 (n=9) |
| M8 messages per candidate (msgs, lower is better) | 110.7 ± 12.2 (n=10) | 109.7 ± 5.8 (n=10) | 140.6 ± 10.7 (n=10) |
| M8 all messages, heartbeats included (msgs per run, lower is better) | 17084.3 ± 305.8 (n=10) | 17097.2 ± 219.9 (n=10) | 17304.0 ± 375.3 (n=10) |
| M8 background messages (P23, P25, P27) (msgs per run, lower is better) | 16122.7 ± 86.2 (n=10) | 16163.9 ± 73.3 (n=10) | 16077.2 ± 72.6 (n=10) |
| M9 gap to oracle B0 from the collapse (s, lower is better) | 125.8 ± 86.5 (n=5) | 159.3 ± 89.1 (n=6) | 112.5 ± 79.2 (n=5) |
| M9 gap to oracle B0 from the declaration (s, lower is better) | 87.7 ± 65.6 (n=5) | 132.2 ± 93.8 (n=6) | 74.3 ± 58.1 (n=5) |
| M10 alerts per volunteer (alerts, lower is better) | 2.3 ± 0.7 (n=10) | 5.4 ± 0.5 (n=10) | 3.7 ± 0.8 (n=10) |
| M10 Jain index of tasks (0-1, higher is better) | 0.2 ± 0.1 (n=10) | 0.5 ± 0.1 (n=10) | 0.3 ± 0.1 (n=10) |
| M10 minutes on false alarms (min, lower is better) | 22.9 ± 8.3 (n=10) | 105.8 ± 12.9 (n=10) | 47.0 ± 14.3 (n=10) |
| M11 location recipients per case (agents, lower is better) | 3.7 ± 0.3 (n=10) | 4.7 ± 0.4 (n=10) | 3.6 ± 0.2 (n=10) |
| M13 time to CPR, central cells (s, lower is better) | 53.9 ± 74.4 (n=2) | 301.4 ± 193.2 (n=3) | 48.3 ± 23.7 (n=3) |
| M13 time to CPR, peripheral cells (s, lower is better) | 87.0 ± 78.6 (n=6) | 257.6 ± 76.5 (n=3) | 87.4 ± 62.5 (n=6) |
| Rule violations (count, lower is better) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) | 0.0 ± 0.0 (n=10) |
| P1 incidents, total over seeds (count) | 16.0 (n=10) | 16.0 (n=10) | 16.0 (n=10) |
| M6 patients, total over seeds (count) | 7.0 (n=10) | 7.0 (n=10) | 7.0 (n=10) |
