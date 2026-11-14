# Paired comparisons

Commit `67a012b025537940270e195071482f39dcd74b44`. Each cell is the mean over seeds of (variant − ours) with a 95 % confidence interval, and in how many seeds ours was better. An interval that excludes 0 is a difference beyond the seed-to-seed variation.

## C1 base urban

| Metric | B1 naive broadcast − Ours | No guidance − Ours |
|---|---|---|
| M1 verification latency (s, lower is better) | -7.1 ± 2.3 (n=10); ours better 0/10 | +0.0 ± 0.4 (n=10); ours better 4/10 |
| M2 precision (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 recall (detectable) (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 recall (reported) (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 false dispatches (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M3 time to CPR (s, lower is better) | +243.4 ± 57.0 (n=7); ours better 7/7 | +174.6 ± 54.6 (n=10); ours better 10/10 |
| M3 CPR started by a bystander (%, higher is better) | -92.9 ± 17.5 (n=7); ours better 7/7 | -90.0 ± 15.1 (n=10); ours better 10/10 |
| M4 time to AED (s, lower is better) | — | +0.0 ± 0.5 (n=5); ours better 2/5 |
| M5 time to EMS (s, lower is better) | -7.0 ± 2.3 (n=10); ours better 0/10 | +0.1 ± 0.8 (n=10); ours better 5/10 |
| M6 survival proxy (%, higher is better) | -10.5 ± 1.9 (n=10); ours better 10/10 | -6.8 ± 2.9 (n=10); ours better 10/10 |
| M7 volunteer before EMS (%, higher is better) | -30.8 ± 33.5 (n=10); ours better 6/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M7 AED before EMS (%, higher is better) | -25.8 ± 23.9 (n=10); ours better 5/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M8 messages per candidate (msgs, lower is better) | -39.8 ± 8.5 (n=10); ours better 0/10 | -4.9 ± 0.9 (n=10); ours better 0/10 |
| M9 gap to oracle B0 (s, lower is better) | +51.7 ± 50.6 (n=7); ours better 5/7 | +0.2 ± 0.7 (n=10); ours better 6/10 |
| M10 alerts per volunteer (alerts, lower is better) | +1.1 ± 0.4 (n=10); ours better 10/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M10 minutes on false alarms (min, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M11 location recipients per case (agents, lower is better) | -0.3 ± 1.0 (n=10); ours better 3/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| Rule violations (count, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |

## C2 noise and false alarms

| Metric | B1 naive broadcast − Ours | AlertFirst − Ours | ConfirmFirst − Ours | No reputation − Ours |
|---|---|---|---|---|
| M1 verification latency (s, lower is better) | -8.3 ± 4.0 (n=8); ours better 0/8 | -2.8 ± 5.6 (n=8); ours better 4/8 | +7.2 ± 10.0 (n=8); ours better 4/8 | -0.5 ± 1.8 (n=8); ours better 4/8 |
| M2 precision (%, higher is better) | -17.2 ± 21.0 (n=9); ours better 4/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.8 ± 1.8 (n=9); ours better 0/9 |
| M2 recall (detectable) (%, higher is better) | +9.6 ± 11.5 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +2.2 ± 5.1 (n=9); ours better 0/9 |
| M2 recall (reported) (%, higher is better) | +9.4 ± 15.5 (n=8); ours better 0/8 | +0.0 ± 0.0 (n=8); ours better 0/8 | +0.0 ± 0.0 (n=8); ours better 0/8 | +3.1 ± 7.4 (n=8); ours better 0/8 |
| M2 false dispatches (per run, lower is better) | +1.6 ± 0.8 (n=10); ours better 9/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M3 time to CPR (s, lower is better) | +209.9 ± 60.5 (n=3); ours better 3/3 | +9.0 ± 19.7 (n=8); ours better 5/8 | +17.1 ± 25.9 (n=8); ours better 5/8 | +9.0 ± 19.8 (n=8); ours better 6/8 |
| M3 CPR started by a bystander (%, higher is better) | -100.0 ± 0.0 (n=3); ours better 3/3 | -12.5 ± 29.5 (n=8); ours better 1/8 | -12.5 ± 29.5 (n=8); ours better 1/8 | -12.5 ± 29.5 (n=8); ours better 1/8 |
| M4 time to AED (s, lower is better) | — | +0.1 ± 2.5 (n=2); ours better 1/2 | +15.5 ± 187.5 (n=2); ours better 2/2 | +0.2 ± 8.3 (n=2); ours better 1/2 |
| M5 time to EMS (s, lower is better) | -0.8 ± 8.2 (n=8); ours better 3/8 | +0.1 ± 0.2 (n=8); ours better 5/8 | +8.2 ± 10.2 (n=8); ours better 5/8 | +3.1 ± 7.1 (n=8); ours better 5/8 |
| M6 survival proxy (%, higher is better) | -3.7 ± 13.2 (n=7); ours better 5/7 | -0.0 ± 0.1 (n=7); ours better 3/7 | -0.4 ± 1.0 (n=7); ours better 4/7 | -0.0 ± 0.1 (n=7); ours better 4/7 |
| M7 volunteer before EMS (%, higher is better) | -40.7 ± 44.0 (n=9); ours better 4/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 |
| M7 AED before EMS (%, higher is better) | -16.7 ± 27.2 (n=9); ours better 2/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 |
| M8 messages per candidate (msgs, lower is better) | +5.6 ± 18.1 (n=10); ours better 5/10 | -22.8 ± 12.7 (n=10); ours better 1/10 | +24.3 ± 13.5 (n=9); ours better 9/9 | +1.3 ± 3.2 (n=10); ours better 1/10 |
| M9 gap to oracle B0 (s, lower is better) | +43.7 ± 13.3 (n=2); ours better 2/2 | +0.2 ± 0.5 (n=6); ours better 2/6 | +8.9 ± 14.1 (n=6); ours better 4/6 | +0.5 ± 0.7 (n=6); ours better 5/6 |
| M10 alerts per volunteer (alerts, lower is better) | +2.7 ± 0.5 (n=10); ours better 10/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.1 ± 0.2 (n=10); ours better 1/10 |
| M10 minutes on false alarms (min, lower is better) | +9.7 ± 10.0 (n=10); ours better 10/10 | +0.0 ± 0.0 (n=10); ours better 1/10 | +0.0 ± 0.0 (n=10); ours better 1/10 | +0.0 ± 0.0 (n=10); ours better 1/10 |
| M11 location recipients per case (agents, lower is better) | +0.1 ± 0.6 (n=9); ours better 5/9 | -0.1 ± 0.1 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.1 ± 0.1 (n=9); ours better 1/9 |
| Rule violations (count, lower is better) | +0.1 ± 0.2 (n=10); ours better 1/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |

## C3 surge with contention

| Metric | B1 naive broadcast − Ours | k = 1 − Ours | k = 3 − Ours | No guidance − Ours |
|---|---|---|---|---|
| M1 verification latency (s, lower is better) | -10.2 ± 1.7 (n=10); ours better 0/10 | +0.1 ± 0.4 (n=10); ours better 6/10 | +1.1 ± 2.5 (n=10); ours better 6/10 | -0.2 ± 1.4 (n=10); ours better 7/10 |
| M2 precision (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 recall (detectable) (%, higher is better) | +5.6 ± 4.3 (n=10); ours better 0/10 | +1.0 ± 2.3 (n=10); ours better 0/10 | +2.2 ± 3.4 (n=10); ours better 0/10 | +2.1 ± 3.2 (n=10); ours better 0/10 |
| M2 recall (reported) (%, higher is better) | +5.0 ± 4.3 (n=10); ours better 0/10 | +1.0 ± 2.3 (n=10); ours better 0/10 | +2.2 ± 3.4 (n=10); ours better 0/10 | +1.2 ± 2.3 (n=10); ours better 0/10 |
| M2 false dispatches (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M3 time to CPR (s, lower is better) | +239.1 ± 63.4 (n=10); ours better 10/10 | -0.6 ± 2.3 (n=10); ours better 5/10 | +7.4 ± 15.7 (n=10); ours better 6/10 | +269.0 ± 34.5 (n=10); ours better 10/10 |
| M3 CPR started by a bystander (%, higher is better) | -85.4 ± 9.9 (n=10); ours better 10/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +2.7 ± 5.6 (n=10); ours better 0/10 | -85.4 ± 9.9 (n=10); ours better 10/10 |
| M4 time to AED (s, lower is better) | +178.3 ± 326.2 (n=5); ours better 3/5 | -0.6 ± 91.3 (n=9); ours better 4/9 | +12.6 ± 55.4 (n=9); ours better 5/9 | +31.0 ± 65.3 (n=9); ours better 6/9 |
| M5 time to EMS (s, lower is better) | +14.2 ± 56.3 (n=10); ours better 1/10 | +0.1 ± 0.9 (n=10); ours better 4/10 | +26.0 ± 58.3 (n=10); ours better 8/10 | -0.6 ± 3.5 (n=10); ours better 5/10 |
| M6 survival proxy (%, higher is better) | -9.2 ± 6.7 (n=8); ours better 7/8 | -0.1 ± 0.7 (n=8); ours better 4/8 | +0.8 ± 3.6 (n=8); ours better 3/8 | -7.1 ± 4.7 (n=8); ours better 6/8 |
| M7 volunteer before EMS (%, higher is better) | -25.0 ± 18.5 (n=10); ours better 6/10 | -0.2 ± 7.7 (n=10); ours better 2/10 | +4.3 ± 5.0 (n=10); ours better 0/10 | -4.7 ± 5.5 (n=10); ours better 3/10 |
| M7 AED before EMS (%, higher is better) | -22.2 ± 25.4 (n=10); ours better 8/10 | +0.2 ± 4.5 (n=10); ours better 1/10 | -3.2 ± 12.4 (n=10); ours better 2/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M8 messages per candidate (msgs, lower is better) | -65.3 ± 8.3 (n=10); ours better 0/10 | -3.7 ± 6.0 (n=10); ours better 1/10 | +15.5 ± 10.4 (n=10); ours better 8/10 | -7.9 ± 6.9 (n=10); ours better 1/10 |
| M9 gap to oracle B0 (s, lower is better) | -17.6 ± 70.3 (n=10); ours better 4/10 | +6.7 ± 33.3 (n=10); ours better 4/10 | -20.1 ± 49.1 (n=10); ours better 3/10 | -0.3 ± 14.9 (n=10); ours better 3/10 |
| M10 alerts per volunteer (alerts, lower is better) | +1.4 ± 0.4 (n=10); ours better 10/10 | -0.1 ± 0.1 (n=10); ours better 0/10 | +0.4 ± 0.2 (n=10); ours better 7/10 | +0.0 ± 0.1 (n=10); ours better 2/10 |
| M10 minutes on false alarms (min, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M11 location recipients per case (agents, lower is better) | -0.0 ± 0.9 (n=10); ours better 4/10 | -1.2 ± 0.4 (n=10); ours better 0/10 | +1.6 ± 0.7 (n=10); ours better 9/10 | -0.1 ± 0.2 (n=10); ours better 2/10 |
| Rule violations (count, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |

## C4 degraded periphery

| Metric | B1 naive broadcast − Ours | No guidance − Ours |
|---|---|---|
| M1 verification latency (s, lower is better) | -11.0 ± 8.2 (n=10); ours better 0/10 | -0.5 ± 12.3 (n=10); ours better 4/10 |
| M2 precision (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 recall (detectable) (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 recall (reported) (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 false dispatches (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M3 time to CPR (s, lower is better) | +275.7 ± 103.1 (n=10); ours better 9/10 | +196.5 ± 120.1 (n=10); ours better 9/10 |
| M3 CPR started by a bystander (%, higher is better) | -56.7 ± 27.0 (n=10); ours better 8/10 | -56.7 ± 27.0 (n=10); ours better 8/10 |
| M4 time to AED (s, lower is better) | +301.4 ± 511.7 (n=4); ours better 4/4 | +3.3 ± 92.6 (n=6); ours better 2/6 |
| M5 time to EMS (s, lower is better) | -47.2 ± 107.8 (n=10); ours better 4/10 | -47.6 ± 78.8 (n=10); ours better 5/10 |
| M6 survival proxy (%, higher is better) | -9.0 ± 7.1 (n=10); ours better 9/10 | -6.9 ± 7.3 (n=10); ours better 8/10 |
| M7 volunteer before EMS (%, higher is better) | -6.3 ± 37.6 (n=10); ours better 4/10 | +9.5 ± 26.8 (n=10); ours better 1/10 |
| M7 AED before EMS (%, higher is better) | -32.3 ± 28.0 (n=10); ours better 6/10 | -1.7 ± 29.0 (n=10); ours better 2/10 |
| M8 messages per candidate (msgs, lower is better) | -50.3 ± 15.6 (n=10); ours better 0/10 | -5.4 ± 7.8 (n=10); ours better 3/10 |
| M9 gap to oracle B0 (s, lower is better) | -23.8 ± 189.9 (n=9); ours better 3/9 | -116.7 ± 186.3 (n=10); ours better 2/10 |
| M10 alerts per volunteer (alerts, lower is better) | +0.5 ± 0.5 (n=10); ours better 8/10 | -0.1 ± 0.2 (n=10); ours better 4/10 |
| M10 minutes on false alarms (min, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M11 location recipients per case (agents, lower is better) | -0.6 ± 0.7 (n=10); ours better 2/10 | -0.3 ± 0.5 (n=10); ours better 4/10 |
| M12 recovery after hub crash (s, lower is better) | -0.3 ± 1.1 (n=10); ours better 4/10 | +0.5 ± 2.1 (n=10); ours better 6/10 |
| Rule violations (count, lower is better) | -0.1 ± 0.2 (n=10); ours better 0/10 | -0.1 ± 0.4 (n=10); ours better 1/10 |

## C5 adversarial sources

| Metric | B1 naive broadcast − Ours | No reputation − Ours |
|---|---|---|
| M1 verification latency (s, lower is better) | -8.4 ± 3.1 (n=8); ours better 0/8 | +0.9 ± 1.6 (n=8); ours better 5/8 |
| M2 precision (%, higher is better) | -11.3 ± 7.3 (n=10); ours better 8/10 | -10.5 ± 7.3 (n=10); ours better 8/10 |
| M2 recall (detectable) (%, higher is better) | +3.7 ± 8.6 (n=9); ours better 0/9 | +3.7 ± 8.6 (n=9); ours better 0/9 |
| M2 recall (reported) (%, higher is better) | +6.2 ± 14.7 (n=8); ours better 0/8 | +6.2 ± 14.7 (n=8); ours better 0/8 |
| M2 false dispatches (per run, lower is better) | +4.1 ± 1.2 (n=10); ours better 10/10 | +3.5 ± 1.3 (n=10); ours better 10/10 |
| M3 time to CPR (s, lower is better) | +245.4 ± 106.7 (n=4); ours better 4/4 | +8.2 ± 19.4 (n=7); ours better 3/7 |
| M3 CPR started by a bystander (%, higher is better) | -100.0 ± 0.0 (n=4); ours better 4/4 | +0.0 ± 0.0 (n=7); ours better 0/7 |
| M4 time to AED (s, lower is better) | -51.3 (n=1); ours better 0/1 | -0.6 ± 7.0 (n=2); ours better 0/2 |
| M5 time to EMS (s, lower is better) | +9.1 ± 33.8 (n=8); ours better 2/8 | +18.9 ± 34.1 (n=8); ours better 3/8 |
| M6 survival proxy (%, higher is better) | -9.3 ± 4.4 (n=7); ours better 6/7 | +0.0 ± 0.0 (n=7); ours better 2/7 |
| M7 volunteer before EMS (%, higher is better) | -11.1 ± 60.2 (n=9); ours better 3/9 | +11.1 ± 25.7 (n=9); ours better 0/9 |
| M7 AED before EMS (%, higher is better) | -5.6 ± 12.8 (n=9); ours better 1/9 | +11.1 ± 25.7 (n=9); ours better 0/9 |
| M8 messages per candidate (msgs, lower is better) | +0.4 ± 11.6 (n=10); ours better 3/10 | +27.9 ± 7.6 (n=10); ours better 10/10 |
| M9 gap to oracle B0 (s, lower is better) | +94.4 ± 770.2 (n=2); ours better 2/2 | +11.0 ± 31.3 (n=5); ours better 2/5 |
| M10 alerts per volunteer (alerts, lower is better) | +3.2 ± 0.5 (n=10); ours better 10/10 | +1.3 ± 0.4 (n=10); ours better 10/10 |
| M10 minutes on false alarms (min, lower is better) | +81.8 ± 12.9 (n=10); ours better 10/10 | +24.1 ± 14.7 (n=10); ours better 10/10 |
| M11 location recipients per case (agents, lower is better) | +0.9 ± 0.5 (n=10); ours better 8/10 | -0.1 ± 0.2 (n=10); ours better 2/10 |
| Rule violations (count, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
