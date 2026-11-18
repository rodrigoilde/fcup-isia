# Missed P1/P2 incidents

Commit `de13290a48e40ba4098fa5da95639c68366acece`. P1/P2 incidents without a declared case at the patient, summed over seeds, by the furthest point their alerts reached (`src/cemr/metrics/misses.py`). The first column is the number of P1/P2 incidents.

## C1 base urban

| Variant | P1/P2 | undetectable | not_reported | alert_lost | discarded_as_p3 | not_located |
|---|---|---|---|---|---|---|
| Ours | 33 | 5 | 2 | 0 | 0 | 0 |
| B1 naive broadcast | 33 | 5 | 2 | 0 | 0 | 0 |
| 10 % message loss | 33 | 5 | 2 | 0 | 0 | 0 |
| 20 % message loss | 33 | 5 | 2 | 1 | 2 | 1 |
| No guidance | 33 | 5 | 2 | 0 | 0 | 0 |

## C2 noise and false alarms

| Variant | P1/P2 | undetectable | not_reported | discarded_as_p3 | other_incident |
|---|---|---|---|---|---|
| Ours | 23 | 5 | 3 | 1 | 1 |
| B1 naive broadcast | 23 | 5 | 3 | 0 | 0 |
| AlertFirst | 23 | 5 | 3 | 1 | 1 |
| ConfirmFirst | 23 | 5 | 3 | 0 | 1 |
| No reputation | 23 | 5 | 3 | 0 | 1 |

## C3 surge with contention

| Variant | P1/P2 | undetectable | not_reported | other_incident |
|---|---|---|---|---|
| Ours | 94 | 9 | 14 | 3 |
| B1 naive broadcast | 94 | 9 | 13 | 3 |
| k = 1 | 94 | 9 | 14 | 3 |
| k = 3 | 94 | 9 | 14 | 3 |
| No guidance | 94 | 9 | 13 | 3 |

## C4 degraded periphery

| Variant | P1/P2 | undetectable | not_reported |
|---|---|---|---|
| Ours | 33 | 3 | 2 |
| B1 naive broadcast | 33 | 3 | 2 |
| No guidance | 33 | 3 | 2 |

## C5 adversarial sources

| Variant | P1/P2 | undetectable | not_reported |
|---|---|---|---|
| Ours | 23 | 5 | 3 |
| B1 naive broadcast | 23 | 5 | 3 |
| No reputation | 23 | 5 | 3 |
