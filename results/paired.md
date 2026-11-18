# Paired comparisons

Commit `de13290a48e40ba4098fa5da95639c68366acece`. Each cell is the mean over seeds of (variant − ours) with a 95 % confidence interval, and in how many seeds ours was better. An interval that excludes 0 is a difference beyond the seed-to-seed variation. The column "B1 − No guidance" compares two variants without bystander guidance, so it isolates verification, Contract Net and reputation; there "ours" is "No guidance".

## C1 base urban

| Metric | B1 naive broadcast − Ours | 10 % message loss − Ours | 20 % message loss − Ours | B1 − No guidance | No guidance − Ours |
|---|---|---|---|---|---|
| M1 verification latency (s, lower is better) | -7.0 ± 2.7 (n=10); ours better 0/10 | +6.5 ± 5.6 (n=10); ours better 7/10 | +11.6 ± 7.1 (n=9); ours better 8/9 | -7.2 ± 2.6 (n=10); ours better 0/10 | +0.1 ± 0.3 (n=10); ours better 5/10 |
| M2 precision (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 recall (detectable) (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | -15.8 ± 22.9 (n=10); ours better 3/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 recall (reported) (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | -15.8 ± 22.9 (n=10); ours better 3/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 false dispatches (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 false dispatches with a witness (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 false dispatches from sensors only (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M3 time to CPR (s, lower is better) | +258.0 ± 39.3 (n=7); ours better 7/7 | +123.2 ± 102.3 (n=10); ours better 10/10 | +127.4 ± 118.8 (n=9); ours better 9/9 | +55.2 ± 50.6 (n=7); ours better 6/7 | +177.6 ± 51.4 (n=10); ours better 10/10 |
| M3 CPR started by a bystander (%, higher is better) | -100.0 ± 0.0 (n=7); ours better 7/7 | -40.0 ± 32.8 (n=10); ours better 5/10 | -33.3 ± 33.3 (n=9); ours better 4/9 | +0.0 ± 0.0 (n=7); ours better 0/7 | -95.0 ± 11.3 (n=10); ours better 10/10 |
| M4 time to AED (s, lower is better) | +42.4 (n=1); ours better 1/1 | +73.7 ± 108.0 (n=5); ours better 5/5 | +385.0 ± 662.6 (n=4); ours better 4/4 | +42.8 (n=1); ours better 1/1 | -0.3 ± 1.5 (n=5); ours better 2/5 |
| M5 time to EMS (s, lower is better) | -6.6 ± 3.0 (n=10); ours better 1/10 | +58.8 ± 37.4 (n=10); ours better 10/10 | +77.3 ± 56.3 (n=9); ours better 9/9 | -6.7 ± 2.8 (n=10); ours better 1/10 | +0.1 ± 0.6 (n=10); ours better 5/10 |
| M6 survival proxy (%, higher is better) | -10.5 ± 1.7 (n=10); ours better 10/10 | -13.2 ± 8.8 (n=10); ours better 10/10 | -21.8 ± 12.3 (n=10); ours better 10/10 | -3.5 ± 2.8 (n=10); ours better 8/10 | -7.0 ± 2.6 (n=10); ours better 10/10 |
| M7 volunteer before EMS (%, higher is better) | -25.8 ± 35.8 (n=10); ours better 5/10 | -5.0 ± 11.3 (n=10); ours better 1/10 | -35.0 ± 29.4 (n=10); ours better 5/10 | -25.8 ± 35.8 (n=10); ours better 5/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M7 AED before EMS (%, higher is better) | -23.3 ± 24.6 (n=10); ours better 4/10 | +12.5 ± 15.2 (n=10); ours better 0/10 | -10.0 ± 22.6 (n=10); ours better 1/10 | -23.3 ± 24.6 (n=10); ours better 4/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M8 messages per candidate (msgs, lower is better) | -38.7 ± 7.9 (n=10); ours better 0/10 | -46.9 ± 13.1 (n=10); ours better 0/10 | -55.6 ± 36.2 (n=10); ours better 1/10 | -33.7 ± 7.4 (n=10); ours better 0/10 | -4.9 ± 0.9 (n=10); ours better 0/10 |
| M8 all messages, heartbeats included (msgs per run, lower is better) | -66.1 ± 106.1 (n=10); ours better 3/10 | -150.7 ± 83.6 (n=10); ours better 1/10 | -404.1 ± 154.6 (n=10); ours better 0/10 | -65.5 ± 105.7 (n=10); ours better 4/10 | -0.6 ± 57.9 (n=10); ours better 6/10 |
| M8 background messages (P23, P25, P27) (msgs per run, lower is better) | +37.0 ± 58.1 (n=10); ours better 7/10 | -134.5 ± 76.3 (n=10); ours better 1/10 | -322.4 ± 71.6 (n=10); ours better 0/10 | +25.1 ± 68.2 (n=10); ours better 5/10 | +11.9 ± 57.3 (n=10); ours better 8/10 |
| M9 gap to oracle B0 from the collapse (s, lower is better) | +57.4 ± 45.4 (n=7); ours better 6/7 | +65.1 ± 35.0 (n=10); ours better 10/10 | +191.0 ± 138.7 (n=8); ours better 7/8 | +57.8 ± 45.2 (n=7); ours better 6/7 | +0.0 ± 0.6 (n=10); ours better 2/10 |
| M9 gap to oracle B0 from the declaration (s, lower is better) | +62.8 ± 45.4 (n=7); ours better 6/7 | +59.6 ± 35.6 (n=10); ours better 10/10 | +182.6 ± 136.4 (n=8); ours better 7/8 | +63.2 ± 45.4 (n=7); ours better 6/7 | -0.1 ± 0.4 (n=10); ours better 4/10 |
| M10 alerts per volunteer (alerts, lower is better) | +1.1 ± 0.4 (n=10); ours better 10/10 | -0.0 ± 0.1 (n=10); ours better 2/10 | -0.2 ± 0.5 (n=10); ours better 3/10 | +1.1 ± 0.4 (n=10); ours better 10/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M10 Jain index of tasks (0-1, higher is better) | +0.0 ± 0.0 (n=10); ours better 4/10 | +0.0 ± 0.0 (n=10); ours better 3/10 | -0.0 ± 0.1 (n=9); ours better 5/9 | +0.0 ± 0.0 (n=10); ours better 4/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M10 minutes on false alarms (min, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M11 location recipients per case (agents, lower is better) | -0.2 ± 1.0 (n=10); ours better 4/10 | -0.1 ± 0.9 (n=10); ours better 4/10 | -0.7 ± 0.7 (n=9); ours better 2/9 | -0.2 ± 1.0 (n=10); ours better 4/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M13 time to CPR, central cells (s, lower is better) | +250.6 ± 77.9 (n=5); ours better 5/5 | +90.6 ± 135.8 (n=7); ours better 6/7 | +146.2 ± 183.8 (n=7); ours better 6/7 | +84.6 ± 65.5 (n=4); ours better 4/4 | +154.3 ± 62.6 (n=6); ours better 6/6 |
| M13 time to CPR, peripheral cells (s, lower is better) | +262.3 ± 37.9 (n=5); ours better 5/5 | +91.9 ± 110.4 (n=7); ours better 6/7 | +61.6 ± 78.6 (n=7); ours better 7/7 | +50.7 ± 84.4 (n=4); ours better 3/4 | +187.3 ± 78.9 (n=7); ours better 7/7 |
| Rule violations (count, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.2 ± 0.3 (n=10); ours better 2/10 | +0.4 ± 0.5 (n=10); ours better 3/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |

## C2 noise and false alarms

| Metric | B1 naive broadcast − Ours | AlertFirst − Ours | ConfirmFirst − Ours | No reputation − Ours |
|---|---|---|---|---|
| M1 verification latency (s, lower is better) | -9.7 ± 5.6 (n=7); ours better 0/7 | -1.3 ± 3.2 (n=7); ours better 3/7 | +3.9 ± 10.5 (n=7); ours better 5/7 | -2.1 ± 5.1 (n=7); ours better 1/7 |
| M2 precision (%, higher is better) | +1.8 ± 12.1 (n=10); ours better 5/10 | -0.6 ± 3.9 (n=10); ours better 1/10 | +1.8 ± 3.4 (n=10); ours better 1/10 | -0.5 ± 3.4 (n=10); ours better 4/10 |
| M2 recall (detectable) (%, higher is better) | +7.4 ± 17.1 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +3.7 ± 8.5 (n=9); ours better 0/9 | +3.7 ± 8.5 (n=9); ours better 0/9 |
| M2 recall (reported) (%, higher is better) | +12.5 ± 29.5 (n=8); ours better 0/8 | +0.0 ± 0.0 (n=8); ours better 0/8 | +6.2 ± 14.7 (n=8); ours better 0/8 | +6.2 ± 14.7 (n=8); ours better 0/8 |
| M2 false dispatches (per run, lower is better) | +4.7 ± 1.4 (n=10); ours better 10/10 | -0.1 ± 0.2 (n=10); ours better 0/10 | +0.2 ± 0.6 (n=10); ours better 2/10 | +1.1 ± 0.8 (n=10); ours better 6/10 |
| M2 false dispatches with a witness (per run, lower is better) | +0.2 ± 0.3 (n=10); ours better 2/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 false dispatches from sensors only (per run, lower is better) | +4.5 ± 1.4 (n=10); ours better 10/10 | -0.1 ± 0.2 (n=10); ours better 0/10 | +0.2 ± 0.6 (n=10); ours better 2/10 | +1.1 ± 0.8 (n=10); ours better 6/10 |
| M3 time to CPR (s, lower is better) | +216.6 ± 445.5 (n=2); ours better 2/2 | +0.2 ± 0.6 (n=7); ours better 4/7 | +5.4 ± 12.6 (n=7); ours better 3/7 | -1.9 ± 4.8 (n=7); ours better 2/7 |
| M3 CPR started by a bystander (%, higher is better) | -100.0 ± 0.0 (n=2); ours better 2/2 | +0.0 ± 0.0 (n=7); ours better 0/7 | +0.0 ± 0.0 (n=7); ours better 0/7 | +0.0 ± 0.0 (n=7); ours better 0/7 |
| M4 time to AED (s, lower is better) | — | +1.5 (n=1); ours better 1/1 | +1.1 (n=1); ours better 1/1 | +1.0 (n=1); ours better 1/1 |
| M5 time to EMS (s, lower is better) | -11.8 ± 6.4 (n=7); ours better 0/7 | -0.2 ± 0.7 (n=7); ours better 3/7 | +3.2 ± 10.3 (n=7); ours better 2/7 | -2.4 ± 4.7 (n=7); ours better 2/7 |
| M6 survival proxy (%, higher is better) | -9.3 ± 4.5 (n=7); ours better 6/7 | +0.0 ± 0.1 (n=7); ours better 1/7 | -0.4 ± 1.0 (n=7); ours better 3/7 | +0.0 ± 0.1 (n=7); ours better 2/7 |
| M7 volunteer before EMS (%, higher is better) | -29.6 ± 68.4 (n=9); ours better 5/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 |
| M7 AED before EMS (%, higher is better) | -5.6 ± 12.8 (n=9); ours better 1/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 |
| M8 messages per candidate (msgs, lower is better) | -11.5 ± 7.6 (n=10); ours better 1/10 | -11.7 ± 4.3 (n=10); ours better 0/10 | +15.7 ± 7.8 (n=10); ours better 10/10 | +6.8 ± 4.9 (n=10); ours better 9/10 |
| M8 all messages, heartbeats included (msgs per run, lower is better) | -176.8 ± 183.1 (n=10); ours better 4/10 | +208.7 ± 82.6 (n=10); ours better 10/10 | -369.0 ± 118.7 (n=10); ours better 0/10 | -136.4 ± 75.6 (n=10); ours better 1/10 |
| M8 background messages (P23, P25, P27) (msgs per run, lower is better) | -12.1 ± 71.5 (n=10); ours better 6/10 | -25.3 ± 61.6 (n=10); ours better 5/10 | -188.8 ± 55.8 (n=10); ours better 0/10 | -230.7 ± 39.7 (n=10); ours better 0/10 |
| M9 gap to oracle B0 from the collapse (s, lower is better) | — | -7.5 ± 19.9 (n=5); ours better 2/5 | +3.5 ± 16.9 (n=5); ours better 2/5 | -10.6 ± 19.4 (n=5); ours better 0/5 |
| M9 gap to oracle B0 from the declaration (s, lower is better) | — | -7.5 ± 19.7 (n=5); ours better 2/5 | -1.2 ± 1.7 (n=5); ours better 2/5 | -7.5 ± 20.0 (n=5); ours better 1/5 |
| M10 alerts per volunteer (alerts, lower is better) | +3.0 ± 0.9 (n=10); ours better 10/10 | -0.1 ± 0.1 (n=10); ours better 0/10 | +0.2 ± 0.3 (n=10); ours better 3/10 | +0.6 ± 0.4 (n=10); ours better 7/10 |
| M10 Jain index of tasks (0-1, higher is better) | +0.1 ± 0.1 (n=10); ours better 1/10 | -0.0 ± 0.0 (n=10); ours better 3/10 | +0.0 ± 0.0 (n=10); ours better 2/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M10 minutes on false alarms (min, lower is better) | +14.8 ± 11.1 (n=10); ours better 9/10 | +0.4 ± 2.6 (n=10); ours better 1/10 | +3.2 ± 5.4 (n=10); ours better 2/10 | +11.8 ± 9.0 (n=10); ours better 8/10 |
| M11 location recipients per case (agents, lower is better) | -0.6 ± 0.6 (n=10); ours better 3/10 | -0.0 ± 0.2 (n=10); ours better 2/10 | -0.2 ± 0.5 (n=10); ours better 1/10 | -0.2 ± 0.5 (n=10); ours better 3/10 |
| M13 time to CPR, central cells (s, lower is better) | +172.2 (n=1); ours better 1/1 | +0.1 ± 1.5 (n=3); ours better 2/3 | -3.1 ± 12.1 (n=3); ours better 0/3 | -5.0 ± 18.4 (n=3); ours better 0/3 |
| M13 time to CPR, peripheral cells (s, lower is better) | +251.6 (n=1); ours better 1/1 | +0.1 ± 1.0 (n=5); ours better 2/5 | +12.4 ± 21.3 (n=5); ours better 3/5 | +0.3 ± 1.5 (n=5); ours better 3/5 |
| Rule violations (count, lower is better) | +0.1 ± 0.2 (n=10); ours better 1/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |

## C3 surge with contention

| Metric | B1 naive broadcast − Ours | k = 1 − Ours | k = 3 − Ours | B1 − No guidance | No guidance − Ours |
|---|---|---|---|---|---|
| M1 verification latency (s, lower is better) | -10.3 ± 2.3 (n=10); ours better 0/10 | -0.0 ± 0.2 (n=10); ours better 5/10 | +0.3 ± 0.3 (n=10); ours better 8/10 | -10.2 ± 2.8 (n=10); ours better 0/10 | -0.2 ± 0.9 (n=10); ours better 6/10 |
| M2 precision (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 recall (detectable) (%, higher is better) | +1.1 ± 2.5 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +1.1 ± 2.5 (n=10); ours better 0/10 |
| M2 recall (reported) (%, higher is better) | +0.2 ± 0.5 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.2 ± 0.5 (n=10); ours better 0/10 |
| M2 false dispatches (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 false dispatches with a witness (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 false dispatches from sensors only (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M3 time to CPR (s, lower is better) | +286.4 ± 76.4 (n=10); ours better 10/10 | +0.3 ± 2.6 (n=10); ours better 5/10 | -0.1 ± 2.6 (n=10); ours better 3/10 | +22.3 ± 68.0 (n=10); ours better 6/10 | +264.1 ± 33.5 (n=10); ours better 10/10 |
| M3 CPR started by a bystander (%, higher is better) | -88.4 ± 9.9 (n=10); ours better 10/10 | -2.5 ± 5.6 (n=10); ours better 1/10 | -2.5 ± 5.6 (n=10); ours better 1/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | -88.4 ± 9.9 (n=10); ours better 10/10 |
| M4 time to AED (s, lower is better) | +194.6 ± 383.6 (n=5); ours better 4/5 | -35.1 ± 45.2 (n=9); ours better 4/9 | +6.5 ± 42.7 (n=9); ours better 6/9 | +196.4 ± 389.6 (n=5); ours better 4/5 | -1.2 ± 4.7 (n=9); ours better 5/9 |
| M5 time to EMS (s, lower is better) | -12.1 ± 3.7 (n=10); ours better 0/10 | +1.8 ± 3.8 (n=10); ours better 6/10 | -0.0 ± 0.5 (n=10); ours better 3/10 | -11.0 ± 3.2 (n=10); ours better 0/10 | -1.1 ± 2.8 (n=10); ours better 4/10 |
| M6 survival proxy (%, higher is better) | -10.9 ± 5.7 (n=8); ours better 8/8 | -0.3 ± 0.5 (n=8); ours better 7/8 | +0.1 ± 0.8 (n=8); ours better 4/8 | -3.1 ± 3.4 (n=8); ours better 6/8 | -7.7 ± 4.4 (n=8); ours better 7/8 |
| M7 volunteer before EMS (%, higher is better) | -25.3 ± 17.2 (n=10); ours better 7/10 | +1.8 ± 5.8 (n=10); ours better 1/10 | +5.1 ± 5.9 (n=10); ours better 0/10 | -25.3 ± 17.2 (n=10); ours better 7/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M7 AED before EMS (%, higher is better) | -22.8 ± 26.2 (n=10); ours better 7/10 | +3.9 ± 6.2 (n=10); ours better 0/10 | +1.8 ± 7.0 (n=10); ours better 1/10 | -24.0 ± 26.1 (n=10); ours better 7/10 | +1.2 ± 2.8 (n=10); ours better 0/10 |
| M8 messages per candidate (msgs, lower is better) | -72.1 ± 9.0 (n=10); ours better 0/10 | -5.7 ± 2.3 (n=10); ours better 0/10 | +13.6 ± 5.1 (n=10); ours better 9/10 | -62.4 ± 7.8 (n=10); ours better 0/10 | -9.7 ± 4.6 (n=10); ours better 0/10 |
| M8 all messages, heartbeats included (msgs per run, lower is better) | -491.0 ± 153.0 (n=10); ours better 0/10 | -67.0 ± 48.1 (n=10); ours better 1/10 | +160.8 ± 69.1 (n=10); ours better 9/10 | -453.9 ± 132.8 (n=10); ours better 0/10 | -37.1 ± 56.0 (n=10); ours better 2/10 |
| M8 background messages (P23, P25, P27) (msgs per run, lower is better) | +3.2 ± 62.6 (n=10); ours better 5/10 | -26.5 ± 44.1 (n=10); ours better 3/10 | +61.2 ± 37.7 (n=10); ours better 9/10 | -4.1 ± 48.4 (n=10); ours better 7/10 | +7.3 ± 31.6 (n=10); ours better 5/10 |
| M9 gap to oracle B0 from the collapse (s, lower is better) | +30.3 ± 71.0 (n=10); ours better 7/10 | +8.6 ± 27.7 (n=10); ours better 7/10 | -17.7 ± 49.0 (n=10); ours better 5/10 | +30.3 ± 71.0 (n=10); ours better 7/10 | -0.1 ± 0.6 (n=10); ours better 4/10 |
| M9 gap to oracle B0 from the declaration (s, lower is better) | +33.8 ± 72.7 (n=10); ours better 7/10 | +7.3 ± 27.9 (n=10); ours better 6/10 | -18.8 ± 49.0 (n=10); ours better 4/10 | +34.0 ± 72.7 (n=10); ours better 7/10 | -0.2 ± 0.5 (n=10); ours better 4/10 |
| M10 alerts per volunteer (alerts, lower is better) | +1.3 ± 0.4 (n=10); ours better 10/10 | -0.0 ± 0.1 (n=10); ours better 0/10 | +0.4 ± 0.1 (n=10); ours better 9/10 | +1.3 ± 0.4 (n=10); ours better 10/10 | +0.0 ± 0.1 (n=10); ours better 1/10 |
| M10 Jain index of tasks (0-1, higher is better) | +0.1 ± 0.1 (n=10); ours better 1/10 | -0.2 ± 0.1 (n=10); ours better 9/10 | +0.1 ± 0.1 (n=10); ours better 0/10 | +0.1 ± 0.1 (n=10); ours better 1/10 | +0.0 ± 0.0 (n=10); ours better 1/10 |
| M10 minutes on false alarms (min, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M11 location recipients per case (agents, lower is better) | +0.3 ± 0.8 (n=10); ours better 6/10 | -1.1 ± 0.4 (n=10); ours better 0/10 | +1.7 ± 0.8 (n=10); ours better 9/10 | +0.3 ± 0.9 (n=10); ours better 7/10 | -0.0 ± 0.2 (n=10); ours better 1/10 |
| M13 time to CPR, central cells (s, lower is better) | +277.2 ± 77.8 (n=10); ours better 10/10 | -0.1 ± 3.2 (n=10); ours better 4/10 | -0.6 ± 3.2 (n=10); ours better 2/10 | +9.1 ± 82.8 (n=10); ours better 5/10 | +268.1 ± 55.3 (n=10); ours better 10/10 |
| M13 time to CPR, peripheral cells (s, lower is better) | +224.3 (n=1); ours better 1/1 | +28.0 ± 34.4 (n=5); ours better 5/5 | +18.0 ± 76.8 (n=5); ours better 4/5 | +188.3 (n=1); ours better 1/1 | +100.1 ± 155.4 (n=5); ours better 4/5 |
| Rule violations (count, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |

## C4 degraded periphery

| Metric | B1 naive broadcast − Ours | B1 − No guidance | No guidance − Ours |
|---|---|---|---|
| M1 verification latency (s, lower is better) | -13.6 ± 7.7 (n=10); ours better 0/10 | -11.9 ± 4.6 (n=10); ours better 0/10 | -1.7 ± 8.8 (n=10); ours better 5/10 |
| M2 precision (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 recall (detectable) (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 recall (reported) (%, higher is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 false dispatches (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 false dispatches with a witness (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M2 false dispatches from sensors only (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M3 time to CPR (s, lower is better) | +258.5 ± 91.3 (n=9); ours better 9/9 | -17.6 ± 116.6 (n=9); ours better 3/9 | +246.8 ± 96.9 (n=10); ours better 9/10 |
| M3 CPR started by a bystander (%, higher is better) | -66.7 ± 24.9 (n=9); ours better 8/9 | +0.0 ± 0.0 (n=9); ours better 0/9 | -60.0 ± 26.5 (n=10); ours better 8/10 |
| M4 time to AED (s, lower is better) | +115.4 ± 293.9 (n=4); ours better 2/4 | +18.5 ± 158.0 (n=4); ours better 2/4 | +67.5 ± 133.2 (n=6); ours better 5/6 |
| M5 time to EMS (s, lower is better) | +62.4 ± 155.6 (n=9); ours better 3/9 | -31.8 ± 195.7 (n=10); ours better 3/10 | +95.4 ± 199.8 (n=9); ours better 3/9 |
| M6 survival proxy (%, higher is better) | -7.0 ± 4.7 (n=10); ours better 9/10 | -3.8 ± 3.6 (n=10); ours better 7/10 | -3.3 ± 6.0 (n=10); ours better 7/10 |
| M7 volunteer before EMS (%, higher is better) | -20.8 ± 23.7 (n=10); ours better 4/10 | -24.8 ± 23.4 (n=10); ours better 5/10 | +4.0 ± 9.0 (n=10); ours better 0/10 |
| M7 AED before EMS (%, higher is better) | -31.2 ± 30.2 (n=10); ours better 6/10 | -34.3 ± 30.8 (n=10); ours better 6/10 | +3.2 ± 30.7 (n=10); ours better 1/10 |
| M8 messages per candidate (msgs, lower is better) | -36.4 ± 11.5 (n=10); ours better 0/10 | -36.7 ± 20.6 (n=10); ours better 1/10 | +0.3 ± 22.7 (n=10); ours better 6/10 |
| M8 all messages, heartbeats included (msgs per run, lower is better) | -67.3 ± 85.2 (n=10); ours better 3/10 | -286.8 ± 166.6 (n=10); ours better 0/10 | +219.5 ± 128.0 (n=10); ours better 10/10 |
| M8 background messages (P23, P25, P27) (msgs per run, lower is better) | +52.2 ± 38.9 (n=10); ours better 9/10 | -62.5 ± 31.9 (n=10); ours better 2/10 | +114.7 ± 41.1 (n=10); ours better 10/10 |
| M9 gap to oracle B0 from the collapse (s, lower is better) | +44.8 ± 55.2 (n=9); ours better 6/9 | +31.4 ± 142.1 (n=9); ours better 5/9 | +10.3 ± 97.6 (n=10); ours better 5/10 |
| M9 gap to oracle B0 from the declaration (s, lower is better) | +50.7 ± 49.4 (n=9); ours better 7/9 | +39.1 ± 140.7 (n=9); ours better 5/9 | +10.5 ± 95.1 (n=10); ours better 5/10 |
| M10 alerts per volunteer (alerts, lower is better) | +1.2 ± 0.5 (n=10); ours better 10/10 | +0.6 ± 0.6 (n=10); ours better 7/10 | +0.6 ± 0.6 (n=10); ours better 7/10 |
| M10 Jain index of tasks (0-1, higher is better) | +0.1 ± 0.1 (n=10); ours better 3/10 | +0.1 ± 0.1 (n=10); ours better 4/10 | +0.1 ± 0.1 (n=10); ours better 3/10 |
| M10 minutes on false alarms (min, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M11 location recipients per case (agents, lower is better) | -0.1 ± 0.5 (n=10); ours better 4/10 | +0.5 ± 0.7 (n=10); ours better 6/10 | -0.6 ± 0.7 (n=10); ours better 1/10 |
| M12 recovery after hub crash (s, lower is better) | +1.1 ± 2.4 (n=10); ours better 7/10 | +1.4 ± 3.4 (n=10); ours better 6/10 | -0.3 ± 2.4 (n=10); ours better 4/10 |
| M13 time to CPR, central cells (s, lower is better) | +153.0 ± 190.6 (n=5); ours better 4/5 | -84.3 ± 269.7 (n=5); ours better 3/5 | +194.8 ± 310.4 (n=6); ours better 4/6 |
| M13 time to CPR, peripheral cells (s, lower is better) | +279.5 ± 110.6 (n=9); ours better 9/9 | -67.9 ± 139.3 (n=9); ours better 1/9 | +347.4 ± 170.0 (n=9); ours better 9/9 |
| Rule violations (count, lower is better) | +0.3 ± 0.3 (n=10); ours better 3/10 | -0.3 ± 0.6 (n=10); ours better 1/10 | +0.6 ± 0.5 (n=10); ours better 5/10 |

## C5 adversarial sources

| Metric | B1 naive broadcast − Ours | No reputation − Ours |
|---|---|---|
| M1 verification latency (s, lower is better) | -9.3 ± 3.9 (n=8); ours better 0/8 | -0.2 ± 1.3 (n=8); ours better 4/8 |
| M2 precision (%, higher is better) | -12.9 ± 8.2 (n=10); ours better 8/10 | -12.5 ± 8.4 (n=10); ours better 8/10 |
| M2 recall (detectable) (%, higher is better) | +0.0 ± 0.0 (n=9); ours better 0/9 | +0.0 ± 0.0 (n=9); ours better 0/9 |
| M2 recall (reported) (%, higher is better) | +0.0 ± 0.0 (n=8); ours better 0/8 | +0.0 ± 0.0 (n=8); ours better 0/8 |
| M2 false dispatches (per run, lower is better) | +4.1 ± 1.2 (n=10); ours better 10/10 | +3.9 ± 1.4 (n=10); ours better 10/10 |
| M2 false dispatches with a witness (per run, lower is better) | +4.1 ± 1.2 (n=10); ours better 10/10 | +3.9 ± 1.4 (n=10); ours better 10/10 |
| M2 false dispatches from sensors only (per run, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
| M3 time to CPR (s, lower is better) | +196.9 ± 132.8 (n=5); ours better 5/5 | -0.3 ± 36.8 (n=7); ours better 3/7 |
| M3 CPR started by a bystander (%, higher is better) | -80.0 ± 55.6 (n=5); ours better 4/5 | +0.0 ± 0.0 (n=7); ours better 0/7 |
| M4 time to AED (s, lower is better) | — | +0.1 ± 23.5 (n=2); ours better 1/2 |
| M5 time to EMS (s, lower is better) | +4.1 ± 34.2 (n=8); ours better 1/8 | +13.8 ± 33.1 (n=8); ours better 5/8 |
| M6 survival proxy (%, higher is better) | -8.8 ± 4.3 (n=7); ours better 6/7 | -0.3 ± 1.0 (n=7); ours better 2/7 |
| M7 volunteer before EMS (%, higher is better) | -7.4 ± 61.2 (n=9); ours better 3/9 | +0.0 ± 0.0 (n=9); ours better 0/9 |
| M7 AED before EMS (%, higher is better) | -16.7 ± 27.2 (n=9); ours better 2/9 | +11.1 ± 25.7 (n=9); ours better 0/9 |
| M8 messages per candidate (msgs, lower is better) | -1.0 ± 10.9 (n=10); ours better 3/10 | +29.9 ± 8.2 (n=10); ours better 10/10 |
| M8 all messages, heartbeats included (msgs per run, lower is better) | +12.9 ± 149.3 (n=10); ours better 5/10 | +219.7 ± 120.7 (n=10); ours better 9/10 |
| M8 background messages (P23, P25, P27) (msgs per run, lower is better) | +41.2 ± 99.1 (n=10); ours better 7/10 | -45.5 ± 42.8 (n=10); ours better 4/10 |
| M9 gap to oracle B0 from the collapse (s, lower is better) | +66.4 ± 194.1 (n=3); ours better 3/3 | -13.2 ± 36.0 (n=5); ours better 2/5 |
| M9 gap to oracle B0 from the declaration (s, lower is better) | +79.2 ± 196.9 (n=3); ours better 3/3 | -13.4 ± 35.8 (n=5); ours better 1/5 |
| M10 alerts per volunteer (alerts, lower is better) | +3.2 ± 0.5 (n=10); ours better 10/10 | +1.4 ± 0.4 (n=10); ours better 10/10 |
| M10 Jain index of tasks (0-1, higher is better) | +0.3 ± 0.1 (n=10); ours better 0/10 | +0.0 ± 0.1 (n=10); ours better 3/10 |
| M10 minutes on false alarms (min, lower is better) | +82.9 ± 13.3 (n=10); ours better 10/10 | +24.1 ± 14.7 (n=10); ours better 9/10 |
| M11 location recipients per case (agents, lower is better) | +1.0 ± 0.5 (n=10); ours better 9/10 | -0.2 ± 0.2 (n=10); ours better 4/10 |
| M13 time to CPR, central cells (s, lower is better) | +277.5 ± 810.9 (n=2); ours better 2/2 | -2.1 ± 21.0 (n=2); ours better 0/2 |
| M13 time to CPR, peripheral cells (s, lower is better) | +140.1 ± 210.9 (n=3); ours better 3/3 | +0.3 ± 45.6 (n=6); ours better 3/6 |
| Rule violations (count, lower is better) | +0.0 ± 0.0 (n=10); ours better 0/10 | +0.0 ± 0.0 (n=10); ours better 0/10 |
