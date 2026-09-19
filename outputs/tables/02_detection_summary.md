# Event detection summary

## i-80
- exact duplicate rows dropped: 0 of 4,566,387 (0.0%)
- rows after dedup: 4,566,387
- recording periods: 3
- mainline rows: 4,411,990
- raw lane-change transitions: 2,226
- after stability filter (>=3s each side): 1,729
- with a follower in the target lane: 1,693
- with a complete follower response window: 1,484

| class | vehicles | vehicle-hours | lane changes | per vehicle-hour |
|---|---:|---:|---:|---:|
| motorcycle | 55 | 0.5 | 25 | 49.24 |
| car | 5,408 | 117.4 | 1,425 | 12.14 |
| truck | 215 | 4.6 | 34 | 7.31 |
- matched control observations: 4,452

## us-101
- exact duplicate rows dropped: 704,000 of 4,802,933 (14.7%)
- rows after dedup: 4,098,933
- recording periods: 3
- mainline rows: 4,028,788
- raw lane-change transitions: 1,805
- after stability filter (>=3s each side): 1,226
- with a follower in the target lane: 1,221
- with a complete follower response window: 1,047

| class | vehicles | vehicle-hours | lane changes | per vehicle-hour |
|---|---:|---:|---:|---:|
| motorcycle | 45 | 0.6 | 34 | 57.50 |
| car | 5,916 | 109.0 | 993 | 9.11 |
| truck | 137 | 2.4 | 20 | 8.51 |
- matched control observations: 3,139

## totals
- events: 2,531
- controls: 7,591
- events by car lane-changer: 2,418
- events by motorcycle lane-changer: 59
- events by truck lane-changer: 54