# Experiments

This file is the record of the ML work: what we tried, why, what happened, and what we decided.
The raw numbers are in `eval/results/` (one JSON file for each run) and in `docs/results.md` (a table that
`python -m eval.report` makes from those files).

## How we work

1. **One question for each experiment.** Change one thing. Give the run a clear name (`--name bert+gliner-t0.5`).
2. **Run it with a script, not by hand.** `python -m eval.mapa_eval ...` and `python -m eval.corpus_eval ...` write a
   result file with the settings, the package versions, the git commit, the time, and the metrics.
   A result without its settings is worth nothing a month later.
3. **Put the result files in git, and write the decision here.** Never edit a result file. If a run was wrong, delete it
   and run again, and say why in this file.
4. **Recall decides.** A missed name is a leak. A false hit only makes the text harder to read. So we look at recall first
   and at F2 second (F2 counts recall twice as much as precision). We also write F1, because the papers use it.
5. **Compare two runs only if the policy is the same.** `keep_public_bodies` changes both precision and recall.
   The result files and `docs/results.md` show it.
6. **Real client text never goes into git.** `_review/` folders and `eval/corpora/private/` are in `.gitignore`.

## Datasets

| Name | Language | Size | What it is | Limits |
|---|---|---|---|---|
| `mapa-ro` | Romanian | 3 documents, 26,277 tokens, 223 sensitive tokens | EU case law with labels (MAPA, CC-BY-4.0) | Very small: one point of recall is 2 tokens. Not a contract. |
| `mapa-en` | English | 3 documents, 25,895 tokens, 343 sensitive tokens | The same, in English | Small. Not a contract. |
| `corpus-demo` | Romanian, English | 5 PDFs, 6,490 words, 57 gold entities | Made-up contracts and letters for the demo | Written by us, so the tool is tuned on it. Do not trust its numbers. |
| `corpus-tab-en` | English | 12 ECHR cases, 20,463 words, 468 gold mentions | Real court cases with person, place, organization and case-number labels (TAB, MIT license). `python -m eval.tab_corpus` | Court judgments, not contracts. TAB also masks things that the tool does not hide by default (dates, quantities), so we leave them out. |
| `corpus-private` | Romanian | **does not exist yet** | 10 to 15 real documents of the lawyer | This is the missing piece. See "What we do not know". |

There is no open Romanian data set with real contracts and name labels. LegalNERo is CC-BY-NC-ND (no commercial use,
no derivatives). MAPA-RO is 3 documents. So the Romanian numbers in this file are weak.

## Log

### EXP-001: baseline (patterns + two BERT models)

*Question:* Where are we before we change anything?
*Setup:* level `low`, `keep_public_bodies` as in each dataset (see the table below).

| Dataset | Recall | Precision | F2 |
|---|---|---|---|
| mapa-ro | 93.3% (208/223 tokens) | 0.22 | 0.57 |
| mapa-en | 81.6% (280/343 tokens) | 0.35 | 0.65 |
| corpus-tab-en (public bodies hidden) | 80.3% | 0.56 | 0.74 |
| corpus-demo | 99.2% (239/241 mentions) | 0.79 | 0.94 |

The precision on MAPA is a lower bound: MAPA does not mark many things that the tool hides on purpose (see
`eval/mapa_eval.py`). Use it to compare runs, not as a number.

### EXP-002: add GLiNER as a second recognizer (level `medium`)

*Question:* Does a zero-shot model (`urchade/gliner_multi_pii-v1`, Apache-2.0) find names that the BERT models miss?
*Setup:* `--level medium --gliner-threshold 0.5`. The recognizer is `src/legal_anonymizer/gliner_ner.py`. It adds hits. It does not replace the BERT models.

| Dataset | Recall: baseline → GLiNER | Persons | Organizations | F2: baseline → GLiNER | Speed |
|---|---|---|---|---|---|
| mapa-en | 81.6% → **93.3%** | 91.6 → 94.7 | 74.9 → 93.2 | 0.65 → 0.66 | 2.0× slower |
| corpus-tab-en (hidden) | 80.3% → **86.3%** | | | 0.74 → 0.77 | 2.0× slower |
| corpus-tab-en (kept) | 78.6% → 84.2% | | | 0.77 → 0.80 | |
| mapa-ro | 93.3% → 94.2% | 96.2 → 97.5 | 90.7 → 91.5 | 0.57 → 0.52 | 4.0× slower |
| corpus-demo | 99.2% → 99.6% | | | 0.94 → 0.94 | 3.1× slower |

*Result:* For English, GLiNER is a clear gain: +11.7 points on MAPA-EN and +6.0 on TAB. For Romanian the gain is
2 tokens of 223. That is inside the noise of a 3-document test, and the model was not trained for Romanian.
*Decision:* keep it as level `medium`. **Do not make `medium` the default for Romanian until we have Romanian documents
that prove it.** The cost is real: 2 to 4 times the run time, one more model of about 1 GB, and more memory.

*A defect that this experiment found (and that is fixed).* The first run on TAB showed 799 false hits against 137 for the baseline.
Nearly all of them were two strings: `and` (463 times, as an organization) and `to the` (136 times, as a person). No model
predicted them. The cause was an old defect in `resolve_overlaps`. A known name such as `United Kingdom of Great Britain
and Northern Ireland` is cut around the three KEEP words (`United Kingdom`, `Great Britain`, `Northern Ireland`), and the
pieces that were left, `of` and `and`, became entities in the vault. Then the word sweep hid every `and` in every
document. The rule now is: the rest of a cut name that has only function words (`of`, `and`, `și`, `de`) is dropped
(`spans._only_function_words`, two tests). After the fix the false hits on TAB are 171 to 197. The old numbers are not in this table.

### EXP-003: the GLiNER threshold

*Question:* Does a higher minimum score for GLiNER give a better balance?
*Setup:* `--gliner-threshold` 0.4, 0.5, 0.6.

| Dataset | 0.4 | 0.5 | 0.6 |
|---|---|---|---|
| mapa-en recall / F2 | 93.6% / 0.66 | 93.3% / 0.66 | 92.1% / 0.68 |
| mapa-ro recall / F2 | 94.2% / 0.51 | 94.2% / 0.52 | 93.3% / 0.52 |
| corpus-tab-en (public bodies kept) recall / F2 | 84.0% / 0.80 | 84.2% / 0.80 | 84.0% / 0.81 |

*Result:* the differences are small. A higher value loses recall on MAPA and gains nothing on TAB.
*Decision:* default `gliner_threshold: 0.5`. We will not tune it more on these small sets.

### EXP-004: GLiNER2-PII (`fastino/gliner2-privacy-filter-PII-multi`)

*Question:* Is the new GLiNER2 PII model (Apache-2.0, 0.3B) better than GLiNER for our job?
*Setup:* `--gliner-model fastino/gliner2-privacy-filter-PII-multi --gliner-threshold 0.5`. Its model card lists seven
languages (no Romanian) and 42 labels (no label for organizations). We use `person`, `full_name`, `address`, `street_address`, `city`.

| Dataset | Recall: baseline → GLiNER → GLiNER2 | F2: baseline → GLiNER → GLiNER2 |
|---|---|---|
| mapa-en | 81.6% → 93.3% → 86.6% | 0.65 → 0.66 → 0.64 |
| corpus-tab-en (hidden) | 80.3% → 86.3% → 83.5% | 0.74 → 0.77 → 0.75 |
| mapa-ro | 93.3% → 94.2% → 93.7% | 0.57 → 0.52 → 0.54 |

*Result:* GLiNER2-PII is better than the baseline in English, and worse than GLiNER. It is no use for organizations,
and the model card says it does not cover Romanian.
*Decision:* not used. The code path stays (`gliner_model` can name a GLiNER2 model) so that we can test the next version.

### EXP-005: public bodies hidden or kept (`keep_public_bodies`)

*Question:* How much does this policy change the numbers on TAB?
*Result:* with the bodies hidden, the baseline has recall 80.3% and precision 0.56. With the bodies kept, it has recall
78.6% and precision 0.73. TAB masks the courts and governments *of a country* (`High Court of Western Denmark`), so
keeping them visible counts as misses. Hiding them counts the `Government` and `Chamber` of the ECHR as false hits.
*Decision:* measure with the default policy (hidden), because it is the safe one. Say the policy every time.

### EXP-006 (not done): a local LLM as a checker (level `high`)

*Question:* Does a small LLM that reads the hidden text and lists the names it still sees add recall at an
acceptable cost in time?
*Status:* the code is ready (`src/legal_anonymizer/llm_check.py`, 22 tests with a fake Ollama server). **Ollama is
not installed on this computer, so no real LLM has run.** The numbers for `high` do not exist.
*Plan:* install Ollama, then run the same four datasets with `--level high --llm-model <model>` for `qwen3.5:0.8b`,
`qwen3.5:2b`, `qwen3.5:4b`, `qwen3.5:9b`, and `qwen2.5:1.5b` (the default of Presidio's sample). For each model write:
recall gain, new false hits, seconds for each page, and how many replies were not valid JSON. The LLM sees only the
hidden text, and the code accepts only strings that are really in the text.

## Mistakes in the measurement itself (so that we do not repeat them)

- **Titles in the gold list.** TAB writes `Mr Abdisamad Adow Sufi`. The tool keeps `Mr` visible on purpose. The first
  version counted every such name as a miss, and showed 2.4% recall for persons. The real value is 88.9%.
  `eval/corpus_eval.py` now leaves the title out of the gold mention.
- **A flat gold list cannot measure consistency.** The demo list has `Northgate` and `Northgate Freight Forwarding Ltd` as two
  entries. The tool gives them one id, which is right, and the test called it a "merged id". Now the consistency
  numbers appear only when the gold list groups the forms of an entity (`"entities": [...]`).
- **A text file is one unit.** The first restore check compared units (paragraphs). For a `.txt` file, that is the whole file.
  The check now counts the words that come back as in the original.
- **A folder can have files that are not documents.** The demo folder has a prompt file. `gold.json` can now name its `documents`.

Each of these made the tool look worse or better than it is. The measurement code needs tests like the code it measures (`tests/test_eval_tools.py`).

## What we do not know

1. **How the tool does on real Romanian contracts.** No number in this file answers that question. The Romanian
   models are weak where it matters (organizations: 90.7% on MAPA-RO), and a Romanian name has many forms (`Popescu`,
   `Popescului`, `lui Popescu`).
2. **How much the quasi-identifiers leak.** The tool hides names, numbers and addresses. A rare job title, an unusual amount or a date can still identify a person.
3. **What a real AI tool does to the ids.** The demo uses a script. No test has let Claude Code, Codex or Copilot edit a hidden file.
4. **How fast it is on the lawyer's computer.** All times here are from one Apple M1 Pro with 16 GB.

## Next experiments

1. Romanian corpus from the lawyer (10 to 15 documents): the same runs as above. This decides the default level for Romanian.
2. EXP-006: the LLM checker with the Qwen3.5 models.
3. A prompt test for the LLM: examples in the prompt, Romanian and English text, and the size of a chunk.
4. Case and application numbers (`36110/97`): the recall on TAB is 0 of 17. It matters less for contracts, but it is a gap.
5. A re-identification test: give the hidden documents to a strong model, and ask it to guess who the parties are.
