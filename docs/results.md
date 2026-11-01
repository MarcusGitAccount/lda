# Results of the experiments

Made by `python -m eval.report` from `eval/results/`. Do not edit.

## corpus-demo

| when | name | level | public bodies | recall | P | F1 | F2 | split | merged | leaked | restore words | words/s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-01 20:57 | baseline-bert | low | kept | 99.2% | 0.79 | 0.88 | 0.94 | n/a | n/a | 0 | 98.6% | 483.2 |
| 2026-11-01 20:58 | bert+gliner-t0.5 | medium | kept | 99.6% | 0.77 | 0.87 | 0.94 | n/a | n/a | 0 | 98.5% | 145.8 |

## corpus-tab-en

| when | name | level | public bodies | recall | P | F1 | F2 | split | merged | leaked | restore words | words/s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-01 20:41 | baseline-bert | low | hidden | 80.3% | 0.56 | 0.66 | 0.74 | 37/152 | 7 | 32 | 99.9% | 328.4 |
| 2026-11-01 20:43 | bert+gliner-t0.5 | medium | hidden | 86.3% | 0.55 | 0.67 | 0.77 | 41/171 | 8 | 29 | 99.9% | 164.7 |
| 2026-11-01 20:44 | baseline-bert | low | kept | 78.6% | 0.73 | 0.76 | 0.77 | 33/149 | 7 | 44 | 100.0% | 331.4 |
| 2026-11-01 20:46 | bert+gliner-t0.5 | medium | kept | 84.2% | 0.68 | 0.75 | 0.80 | 38/167 | 8 | 46 | 99.9% | 157.8 |
| 2026-11-01 20:52 | bert+gliner2-pii-t0.5 | medium | hidden | 83.5% | 0.54 | 0.65 | 0.75 | 39/161 | 7 | 32 | 99.9% | 144.8 |
| 2026-11-01 21:02 | bert+gliner-t0.4 | medium | kept | 84.0% | 0.67 | 0.74 | 0.80 | 37/166 | 6 | 47 | 99.9% | 147.7 |
| 2026-11-01 21:04 | bert+gliner-t0.6 | medium | kept | 84.0% | 0.70 | 0.76 | 0.81 | 38/166 | 7 | 47 | 99.9% | 161.6 |

## mapa-en-test+validation

| when | name | level | public bodies | recall | persons | orgs | addresses | P | F1 | F2 | tokens/s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-01 20:17 | baseline-bert | low | hidden | 81.6% | 91.6% | 74.9% | 81.0% | 0.35 | 0.49 | 0.65 | 357.5 |
| 2026-11-01 20:20 | bert+gliner-t0.4 | medium | hidden | 93.6% | 94.7% | 93.2% | 90.5% | 0.31 | 0.46 | 0.66 | 182.1 |
| 2026-11-01 20:22 | bert+gliner-t0.5 | medium | hidden | 93.3% | 94.7% | 93.2% | 85.7% | 0.31 | 0.46 | 0.66 | 181.4 |
| 2026-11-01 20:25 | bert+gliner-t0.6 | medium | hidden | 92.1% | 94.7% | 91.1% | 85.7% | 0.33 | 0.48 | 0.68 | 166.0 |
| 2026-11-01 20:50 | bert+gliner2-pii-t0.5 | medium | hidden | 86.6% | 92.4% | 83.2% | 81.0% | 0.32 | 0.46 | 0.64 | 180.5 |

## mapa-ro-test+validation

| when | name | level | public bodies | recall | persons | orgs | addresses | P | F1 | F2 | tokens/s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-01 20:10 | baseline-bert | low | hidden | 93.3% | 96.2% | 90.7% | 100.0% | 0.22 | 0.36 | 0.57 | 1008.5 |
| 2026-11-01 20:12 | bert+gliner-t0.4 | medium | hidden | 94.2% | 97.5% | 91.5% | 100.0% | 0.18 | 0.30 | 0.51 | 244.2 |
| 2026-11-01 20:14 | bert+gliner-t0.5 | medium | hidden | 94.2% | 97.5% | 91.5% | 100.0% | 0.18 | 0.31 | 0.52 | 250.6 |
| 2026-11-01 20:16 | bert+gliner-t0.6 | medium | hidden | 93.3% | 96.2% | 90.7% | 100.0% | 0.19 | 0.32 | 0.52 | 241.7 |
| 2026-11-01 20:54 | bert+gliner2-pii-t0.5 | medium | hidden | 93.7% | 97.5% | 90.7% | 100.0% | 0.20 | 0.33 | 0.54 | 233.9 |
