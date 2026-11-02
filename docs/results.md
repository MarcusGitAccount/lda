# Results of the experiments

Made by `python -m eval.report` from `eval/results/`. Do not edit.

## corpus-demo

| when | name | level | public bodies | recall | P | F1 | F2 | split | merged | leaked | restore words | words/s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-01 20:57 | baseline-bert | low | kept | 99.2% | 0.79 | 0.88 | 0.94 | n/a | n/a | 0 | 98.6% | 483.2 |
| 2026-11-01 20:58 | bert+gliner-t0.5 | medium | kept | 99.6% | 0.77 | 0.87 | 0.94 | n/a | n/a | 0 | 98.5% | 145.8 |
| 2026-11-01 23:15 | low+lexemes | low | kept | 99.2% | 0.79 | 0.88 | 0.94 | n/a | n/a | 0 | 98.6% | 33.5 |
| 2026-11-01 23:41 | medium+lexemes | medium | kept | 99.6% | 0.77 | 0.87 | 0.94 | n/a | n/a | 0 | 98.5% | 149.8 |
| 2026-11-02 00:02 | high-qwen3.5-4b | high | kept | 99.6% | 0.77 | 0.87 | 0.94 | n/a | n/a | 0 | 98.5% | 49.4 |
| 2026-11-02 00:28 | high-qwen3.5-2b | high | kept | 99.6% | 0.70 | 0.82 | 0.92 | n/a | n/a | 0 | 98.4% | 64.9 |
| 2026-11-02 00:39 | high-qwen3.5-0.8b | high | kept | 99.6% | 0.75 | 0.86 | 0.94 | n/a | n/a | 0 | 98.5% | 92.6 |
| 2026-11-02 01:12 | low+forms | low | kept | 99.2% | 0.79 | 0.88 | 0.94 | n/a | n/a | 0 | 98.6% | 478.1 |
| 2026-11-02 01:24 | medium+forms | medium | kept | 99.6% | 0.77 | 0.87 | 0.94 | n/a | n/a | 0 | 98.5% | 148.7 |

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
| 2026-11-01 23:11 | low+lexemes | low | hidden | 80.3% | 0.56 | 0.66 | 0.74 | 37/152 | 7 | 32 | 99.9% | 233.0 |
| 2026-11-01 23:40 | medium+lexemes | medium | hidden | 86.3% | 0.55 | 0.67 | 0.77 | 41/171 | 8 | 29 | 99.9% | 154.5 |
| 2026-11-01 23:59 | high-qwen3.5-4b | high | hidden | 86.3% | 0.48 | 0.62 | 0.74 | 41/171 | 8 | 29 | 99.9% | 57.9 |
| 2026-11-02 00:26 | high-qwen3.5-2b | high | hidden | 86.3% | 0.54 | 0.66 | 0.77 | 40/171 | 8 | 29 | 99.9% | 63.0 |
| 2026-11-02 00:38 | high-qwen3.5-0.8b | high | hidden | 86.3% | 0.54 | 0.66 | 0.77 | 41/171 | 8 | 29 | 99.9% | 108.2 |
| 2026-11-02 00:56 | high-qwen3.5-9b | high | hidden | 86.3% | 0.52 | 0.65 | 0.76 | 42/171 | 9 | 29 | 99.9% | 38.5 |
| 2026-11-02 01:12 | low+forms | low | hidden | 80.3% | 0.56 | 0.66 | 0.74 | 37/152 | 7 | 32 | 99.9% | 311.0 |
| 2026-11-02 01:23 | medium+forms | medium | hidden | 86.3% | 0.55 | 0.67 | 0.77 | 41/171 | 8 | 29 | 99.9% | 143.0 |

## hits-ro-law

| when | name | level | public bodies | documents | words | hits | hits / 1,000 words | by type | words/s |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-01 23:38 | ro-law-low+lexemes | low | hidden | 40 | 70698 | 3056 | 43.2 | ORGANIZATION 1322, PERSON 897, LOCATION 802, PHONE_NUMBER 20, ADDRESS 4, IP_ADDRESS 4, URL 3, CASE_NUMBER 3, RO_TRADE_REG 1 | 148.5 |
| 2026-11-02 01:16 | low+forms | low | hidden | 40 | 70698 | 2864 | 40.5 | ORGANIZATION 1299, PERSON 897, LOCATION 633, PHONE_NUMBER 20, ADDRESS 4, IP_ADDRESS 4, URL 3, CASE_NUMBER 3, RO_TRADE_REG 1 | 348.3 |
| 2026-11-02 01:34 | low+dates+titles | low | hidden | 40 | 70698 | 4006 | 56.7 | ORGANIZATION 1299, PERSON 943, LOCATION 633, JOB_TITLE 602, DATE_TIME 494, PHONE_NUMBER 20, ADDRESS 4, IP_ADDRESS 4, URL 3, CASE_NUMBER 3, RO_TRADE_REG 1 | 388.2 |

## mapa-en-test+validation

| when | name | level | public bodies | recall | persons | orgs | addresses | P | F1 | F2 | tokens/s | LLM adds (gold / other) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-01 20:17 | baseline-bert | low | hidden | 81.6% | 91.6% | 74.9% | 81.0% | 0.35 | 0.49 | 0.65 | 357.5 | - |
| 2026-11-01 20:20 | bert+gliner-t0.4 | medium | hidden | 93.6% | 94.7% | 93.2% | 90.5% | 0.31 | 0.46 | 0.66 | 182.1 | - |
| 2026-11-01 20:22 | bert+gliner-t0.5 | medium | hidden | 93.3% | 94.7% | 93.2% | 85.7% | 0.31 | 0.46 | 0.66 | 181.4 | - |
| 2026-11-01 20:25 | bert+gliner-t0.6 | medium | hidden | 92.1% | 94.7% | 91.1% | 85.7% | 0.33 | 0.48 | 0.68 | 166.0 | - |
| 2026-11-01 20:50 | bert+gliner2-pii-t0.5 | medium | hidden | 86.6% | 92.4% | 83.2% | 81.0% | 0.32 | 0.46 | 0.64 | 180.5 | - |
| 2026-11-01 23:09 | low+lexemes | low | hidden | 81.6% | 91.6% | 74.9% | 81.0% | 0.35 | 0.49 | 0.65 | 269.6 | - |
| 2026-11-01 23:35 | medium+lexemes | medium | hidden | 93.3% | 94.7% | 93.2% | 85.7% | 0.31 | 0.46 | 0.66 | 22.3 | - |
| 2026-11-01 23:47 | high-qwen3.5-4b | high | hidden | 94.2% | 97.0% | 93.2% | 85.7% | 0.28 | 0.43 | 0.64 | 78.8 | 3 / 123 |
| 2026-11-02 00:31 | high-qwen3.5-0.8b | high | hidden | 93.3% | 94.7% | 93.2% | 85.7% | 0.24 | 0.38 | 0.59 | 130.9 | 0 / 312 |
| 2026-11-02 00:47 | high-qwen3.5-9b | high | hidden | 93.3% | 94.7% | 93.2% | 85.7% | 0.29 | 0.45 | 0.65 | 59.2 | 0 / 50 |
| 2026-11-02 01:02 | high-qwen3.5-2b | high | hidden | 93.3% | 94.7% | 93.2% | 85.7% | 0.26 | 0.41 | 0.62 | 88.3 | 0 / 183 |
| 2026-11-02 01:10 | low+forms | low | hidden | 81.6% | 91.6% | 74.9% | 81.0% | 0.35 | 0.49 | 0.65 | 364.7 | - |
| 2026-11-02 01:18 | medium+forms | medium | hidden | 93.3% | 94.7% | 93.2% | 85.7% | 0.31 | 0.46 | 0.66 | 171.1 | - |

## mapa-ro-test+validation

| when | name | level | public bodies | recall | persons | orgs | addresses | P | F1 | F2 | tokens/s | LLM adds (gold / other) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-01 20:10 | baseline-bert | low | hidden | 93.3% | 96.2% | 90.7% | 100.0% | 0.22 | 0.36 | 0.57 | 1008.5 | - |
| 2026-11-01 20:12 | bert+gliner-t0.4 | medium | hidden | 94.2% | 97.5% | 91.5% | 100.0% | 0.18 | 0.30 | 0.51 | 244.2 | - |
| 2026-11-01 20:14 | bert+gliner-t0.5 | medium | hidden | 94.2% | 97.5% | 91.5% | 100.0% | 0.18 | 0.31 | 0.52 | 250.6 | - |
| 2026-11-01 20:16 | bert+gliner-t0.6 | medium | hidden | 93.3% | 96.2% | 90.7% | 100.0% | 0.19 | 0.32 | 0.52 | 241.7 | - |
| 2026-11-01 20:54 | bert+gliner2-pii-t0.5 | medium | hidden | 93.7% | 97.5% | 90.7% | 100.0% | 0.20 | 0.33 | 0.54 | 233.9 | - |
| 2026-11-01 23:10 | low+lexemes | low | hidden | 93.3% | 96.2% | 90.7% | 100.0% | 0.22 | 0.36 | 0.57 | 711.2 | - |
| 2026-11-01 23:38 | medium+lexemes | medium | hidden | 94.2% | 97.5% | 91.5% | 100.0% | 0.18 | 0.31 | 0.52 | 192.9 | - |
| 2026-11-01 23:53 | high-qwen3.5-4b | high | hidden | 94.2% | 97.5% | 91.5% | 100.0% | 0.17 | 0.28 | 0.49 | 73.4 | 0 / 119 |
| 2026-11-02 00:34 | high-qwen3.5-0.8b | high | hidden | 96.0% | 97.5% | 94.6% | 100.0% | 0.16 | 0.27 | 0.48 | 155.4 | 4 / 194 |
| 2026-11-02 01:06 | high-qwen3.5-2b | high | hidden | 94.2% | 97.5% | 91.5% | 100.0% | 0.14 | 0.24 | 0.44 | 99.4 | 0 / 368 |
| 2026-11-02 01:21 | medium+forms | medium | hidden | 94.1% | 97.5% | 91.5% | 100.0% | 0.19 | 0.31 | 0.52 | 220.4 | - |
| 2026-11-02 01:30 | low+forms | low | hidden | 93.2% | 96.2% | 90.7% | 100.0% | 0.22 | 0.36 | 0.57 | 903.9 | - |
