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
| `ro-law` | Romanian | 40 acts, 70,698 words | Real Romanian legal acts (8 types x 5) from legislatie.just.ro, through the export of `scriptogre/romanian-law-data`. `python -m eval.ro_law_corpus` | **No gold list**: we measure hits and read them, we cannot measure recall. Legislation, not contracts. The data is not in git. |
| `agent-test` | Romanian, English | 3 Word files | A real AI tool (a subagent) edits hidden Word files. `docs/agent-test/` | One agent, one run, one prompt with the rules. |
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

### EXP-006: a local LLM as a checker (level `high`) with Qwen3.5

*Question:* Does a small LLM that reads the hidden text and lists the names it still sees add recall at an acceptable cost?
*Setup:* Ollama 0.40.13 on the Mac (M1 Pro, 16 GB). Qwen3.5 in four sizes (0.8b, 2b, 4b, 9b; the default tags of Ollama), `think: false`,
temperature 0, pieces of 1,500 characters, a prompt that asks for JSON. Each run is compared with `medium+lexemes` (same code, same set), because the
LLM comes after GLiNER. 9b ran on MAPA English and TAB only (time). The LLM sees only the hidden text, and the code accepts only strings that are really in it.
"Gold +" is the number of gold tokens (MAPA) or mentions (TAB, demo) that only the LLM covers. "Noise +" is the increase of the other tokens
that the tool hides (MAPA) or of the false hits (TAB, demo).

| Dataset | Model | Recall (medium → high) | Gold + | Noise + | F2 change | Unreadable replies |
|---|---|---|---|---|---|---|
| mapa-en (343 tokens) | 0.8b | 93.3% → 93.3% | 0 | 312 | −0.076 | 0 of 98 |
| | 2b | 93.3% → 93.3% | 0 | 183 | −0.047 | 1 of 98 |
| | 4b | 93.3% → **94.2%** | **3** | 123 | −0.027 | 0 of 98 |
| | 9b | 93.3% → 93.3% | 0 | 50 | −0.014 | 0 of 98 |
| mapa-ro (223 tokens) | 0.8b | 94.2% → **96.0%** | **4** | 194 | −0.037 | 0 of 107 |
| | 2b | 94.2% → 94.2% | 0 | 368 | −0.080 | 1 of 107 |
| | 4b | 94.2% → 94.2% | 0 | 119 | −0.029 | 0 of 107 |
| corpus-tab-en (468 mentions) | 0.8b | 86.3% → 86.3% | 0 | 16 | −0.005 | 1 of 93 |
| | 2b | 86.3% → 86.3% | 0 | 12 | −0.004 | 5 of 93 |
| | 4b | 86.3% → 86.3% | 0 | 107 | −0.030 | 0 of 93 |
| | 9b | 86.3% → 86.3% | 0 | 45 | −0.013 | 0 of 93 |
| corpus-demo (241 mentions) | 0.8b | 99.6% → 99.6% | 0 | 7 | −0.005 | 0 of 32 |
| | 2b | 99.6% → 99.6% | 0 | 33 | −0.024 | 0 of 32 |
| | 4b | 99.6% → 99.6% | 0 | 0 | 0.000 | 0 of 32 |

*Result:* In 14 comparisons, the LLM found something new in only two: 4b on MAPA English (3 tokens, +0.9 points) and 0.8b on MAPA Romanian
(4 tokens, +1.8 points). That is at most 4 tokens. In all other cases it found nothing that the models had missed. In every comparison it hid other text as well, and the
F2 score went down or stayed (never up). The extra hits that we read on TAB are not missed names. They are nationalities (`British`, `Swedish`, `Somali`), dates
(`June 1982`), currencies (`DKK 275,000`), legal references (`Rule 39 of the Rules of Court`, `Article 6 para. 1`), and single words such as `Convention` (61 times
with 4b) and `Act` (20 times with 9b). A bigger model is quieter (9b: 45 to 50), but it finds nothing more.
*What the LLM cannot show:* MAPA and TAB label only part of the sensitive text, so a hit that the gold list does not know is counted as noise. We read the
TAB hits and found no name among them. We did not read the MAPA hits. A messy real contract (typing errors, unusual names) is a different case: the Romanian
test set of the lawyer (LDA-22) is where `high` can still show a gain.
*Problems of the setup that the first real runs found (both fixed, with tests):*
(1) Ollama answers `501 structured output is unavailable` to every request with a `format` field for Qwen3.5. The checker asks for JSON in the prompt, tries the
schema once, and goes on without it; `parse_items` reads the reply with a code fence or extra words. Without forced JSON, 0 to 5 replies of 93 to 107 were unreadable.
(2) Qwen3.5 2b repeated itself without end on one piece of text. The request ran until the 300 s timeout, and the whole document failed (two runs). The reply is now
limited to 512 tokens, and a piece that times out is skipped with a warning and a counter (`skipped_pieces`; 0 in all later runs).
The two 2b runs on MAPA were made again with the fixed code. The 4b runs of 2026-11-02 01:41 to 02:00 used the code without the limit.
*Speed (clean run, nothing else running except the usual background load, load average 6 to 7):* the first document of MAPA English (12,115 tokens)
takes 33 s at `low`, 68 s at `medium` (2.1 times), and 143 s at `high` with Qwen3.5 4b (4.3 times; 46 requests, about 1.6 s each).
The run times in the table of `docs/results.md` for the first runs of 2026-11-02 (until about 02:00) are not reliable:
another program used a CPU core during that time. For example, `medium+lexemes` on MAPA English shows 22 tokens/s, and the clean value is about 180.
The recall and noise numbers are not affected.
*Decision:* keep `high` in the code as an experimental level. Do not recommend it, and do not make it a default. The cost is large (twice the time of level `medium`, see the
speed note below) and the gain is 0 to 4 tokens with a lot of noise. Next (LDA-28): reject hits that have digits or are a nationality or a currency, test a prompt with examples,
and test the LLM on the Romanian documents of the lawyer.

### EXP-007: Romanian word forms of names (`romanian.py`)

*Question:* The sweep needs a whole word. Does a known name leak when the text has another Romanian form of it
(`Popescului`, `Popeștii`, `Mariei`, `Brașovului`)? And does a model that finds the form give it a second id?
*Setup:* a probe with a stub detector that finds only the base name, so that only the sweep acts (11 cases: article, genitive,
vocative, family plural, feminine `-a` to `-ei`, `-ca` to `-cii`, `București`, `Iași`, `Cluj-Napoca`, `Ana-Maria`, capitals, the old cedilla letters).
The second scenario: the stub also finds the other form, as a real model would.
*Result before the change:* 11 of 11 cases leaked the other form. In the second scenario the same person had 2 or 3 ids
(`[PERSON_001]`, `_002`, `_003`).
*Change:* `src/legal_anonymizer/romanian.py` lists the forms of a word by rules and does not stem. The sweep looks for the forms of each word
of a person or a place. The vault gives the same id to a form that a rule makes from a known name. The restore writes the base form.
*Result after the change:* 0 leaks and 1 id in all 11 cases. Names that can belong to two people stay apart (`Pop`/`Popa`, `Radu`/`Rad`, `Ion`/`Ioan`).
No regression on the real sets (reruns with the new code):

| Dataset | `low` before → after | `medium` before → after |
|---|---|---|
| mapa-en | 81.6% → 81.6% | 93.3% → 93.3% |
| mapa-ro | 93.3% → 93.3% | 94.2% → 94.2% |
| corpus-tab-en (hidden) | 80.3% → 80.3% | 86.3% → 86.3% |
| corpus-demo | 99.2% → 99.2% | 99.6% → 99.6% |

*Why no change:* these sets have few inflected forms that the models miss, and `mapa_eval` does not use the sweep.
The gain shows on the probe, and it will show on real Romanian contracts. We cannot measure it before we have them.
*Decision:* keep. *Known limits:* the restore writes the base form (ticket LDA-21); a surname alone does not link to the full name (LDA-20).

### EXP-008: a real AI tool on hidden Word files (`docs/agent-test/`)

*Question:* Does a real agent keep the ids when it edits a hidden Word file?
*Setup and result:* see `docs/agent-test/result.md`. In short: one subagent, three tasks, a prompt with the rules for ids. 110 ids in the output,
0 lost, 0 changed, 0 with a Romanian ending, 0 invented. All 110 restored. The restore changed the written form of two company names
(`S.C. CARPATICA LOGISTIC SOLUTIONS S.A.` came back as `Carpatica Logistic Solutions S.A.`).
*Decision:* the rules in the prompt work for this agent. Next: the same tasks with a plain prompt, and with other tools. The written form is LDA-21.

### EXP-009: Romanian legal acts, no gold list (`eval/hits_report.py`)

*Question:* What does the tool hide in public Romanian legal text? This is not a recall test.
*Setup:* 40 acts (`eval/corpora/ro-law/`), level `low`, public bodies hidden (the default).
*Result (first run):* 3,056 hits in 70,698 words, 43 for each 1,000 words: 1,322 organizations, 897 persons, 802 places, 20 phone numbers (false hits).
Real names are found (decrees and decisions name people). The hits to read:
the genitive `României` was hidden 156 times and `ROMÂNIEI` 13 times, because the keep-list has only the base form; ranks and professions are hidden
as persons (`Cavaler` 18, `Credincios` 15, `Ofițer` 15, `medicul veterinar` 9); common words are hidden as organizations
(`județean` 34, `Curtea` 33, `Secția` 11, the bare `S.A.` 14); a span runs over table border characters (`Județean │ │ │ │`).
Number sequences in tables are hidden as phone numbers.
*Decision:* tickets LDA-30 (the keep-list and the false hits). The public-body policy explains most of the 1,322 organization hits
(`Guvernului` 113, `CNFIS` 78): with `keep_public_bodies: true` they stay visible.

### EXP-010: spelling variants (LDA-29) and country forms in the keep list (LDA-30)

*Question:* After EXP-007, which variants of a known name still leak, and what does the tool over-hide in real Romanian legal text?
*Probe (stub detector):* `Ana Maria` and `Ana-Maria`, `Zorgbla-Quux` and `Zorgbla Quux`, `SRL` and `S.R.L.`, `SRL` and `S.R.L.-ul`, an optional `S.C.`: 5 of 5 cases leaked, and the variants got another id.
*Change:* `person_key` treats a hyphen as a space (one key for `Ana-Maria Popescu` and `Ana Maria Popescu`); the sweep allows a space or a hyphen between the words of a person, optional dots in a legal form
(`SRL`, `S.R.L.`), and an optional `S.C.`; the owner of a match is found with the same key as the vault uses. The keep list (countries, the European Union) also keeps the Romanian forms:
`România` keeps `României`; multi-word genitives (`Uniunii Europene`, `Republicii Moldova`, `Regatului Unit`) are listed. A different legal form is still a different company (`SRL` and `SA`).
*Result:* the probe: 0 leaks, 1 id. Tests: 342 pass (308 without the models). Recall with the final code (`low+forms`, `medium+forms`):

| Dataset | `low` before → after | `medium` before → after |
|---|---|---|
| mapa-en | 81.6% → 81.6% | 93.3% → 93.3% |
| mapa-ro | 93.3% → 93.2% (208/223 → 207/222) | 94.2% → 94.1% (210/223 → 209/222) |
| corpus-tab-en (hidden) | 80.3% → 80.3% | 86.3% → 86.3% |
| corpus-demo | 99.2% → 99.2% | 99.6% → 99.6% |

The Romanian MAPA numbers change by one token in both the numerator and the denominator. The cause is a change of the evaluation, not of the tool: a genitive of a country (`României`) was a gold token that
the tool had to hide, but the policy keeps it visible. `eval/mapa_eval.py` now uses the keep list of the detector. The stale result file of the `low` run was deleted and the run was repeated.
Romanian legal acts (EXP-009): 3,056 → 2,864 hits (43.2 → 40.5 for each 1,000 words). `României` (156) and `ROMÂNIEI` (13) are no longer hidden as places, `Uniunii Europene` (22) stays visible,
and an organization is no longer cut at a country: `Băncii Naționale a` + `României` is now one hit, `Băncii Naționale a României`.
*Not fixed (LDA-30 stays open):* ranks and professions as persons (`Cavaler`, `Ofițer`, `medicul veterinar`), common words as organizations (`județean`, `Curtea`), the bare `S.A.`, spans over table borders.
*Decision:* keep. *Known limit:* the probe cannot show the gain on real Romanian contracts (LDA-22).

### EXP-011: optional types DATE_TIME and JOB_TITLE (ticket LDA-16)

*Question:* Can the tool hide calendar dates and job titles in Romanian and English, without hiding durations, years and clause numbers?
*Setup:* patterns (`patterns.py`) for dates and for a list of occupations, off by default. The Romanian NER model also marks dates, but it marks durations
(`30 de zile`) and years (`Anul 2024`) too, so the detector keeps only its calendar dates. English has no date model, so the pattern is the only source there.
There is no gold list, so there is no recall. We tested with 37 pattern tests (13 date forms and 8 things that are not dates in 2 languages, 8 titles and 4 words that are not titles),
2 tests with the real models, and a run on the 40 Romanian legal acts with `--hide` set to the default types plus the two (`low+dates+titles`).
*Result on the legal acts:* 4,006 hits (56.7 for each 1,000 words), against 2,864 without the two types: 494 dates (7.0 for each 1,000 words, 230 different strings) and 602 job titles (8.5, 77 different strings).
The hits that we read are what we expect: dates such as `19 iulie 2016` and `10-03-2025`, and occupations such as `șef` (168), `judecător`, `Inspector`, `director general`. We found no duration, no year alone and no clause number among the dates.
*Decision:* keep both types off by default. A hidden date stops an AI tool from working out a deadline, and a hidden title hides the role of a person (`șef` is a title but also a part of a role). The lawyer chooses by case.
*Not measured:* whether hiding them lowers the chance that a strong model guesses who the parties are (LDA-23).

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

- **A stub that matches inside a word.** The first probe of the Romanian forms used a stub detector that found `Zorgblatt` inside
  `Zorgblattului`. The output `[PERSON_001]ului` looked like a good result. A real model returns the whole word. The probe now uses word boundaries.
- **A fake server that is too kind.** The tests of the LLM checker used a fake Ollama server that accepts every request. The real server answers
  `501 structured output is unavailable` for all Qwen3.5 sizes. Only the first real run showed it. The fake server now rejects `format` when asked to.
- **Times under load.** Another program used one CPU core during part of the runs of 2026-11-02. The times of these runs are not reliable.
  The recall numbers are not affected. Measure the speed again on a quiet computer.
- **An evaluation that did not follow the policy.** After the keep list got the Romanian forms of the countries, MAPA Romanian lost one token, because the
  evaluation still counted `României` as a token to hide. The evaluation must use the same keep list as the detector (`eval/mapa_eval.py` does now).
Each of these made the tool look worse or better than it is. The measurement code needs tests like the code it measures (`tests/test_eval_tools.py`).

## What we do not know

1. **How the tool does on real Romanian contracts.** No number in this file answers that question. The Romanian
   models are weak where it matters (organizations: 90.7% on MAPA-RO), and a Romanian name has many forms (`Popescu`,
   `Popescului`, `lui Popescu`).
2. **How much the quasi-identifiers leak.** The tool hides names, numbers and addresses. A rare job title, an unusual amount or a date can still identify a person.
   Dates and job titles can now be hidden (`DATE_TIME`, `JOB_TITLE`, ticket LDA-16), but we have not measured what that does to a guess of the parties (LDA-23).
3. **What a real AI tool does to the ids, in general.** One subagent (one model, a prompt with the rules for ids) kept all 110 ids (EXP-008). We do not know what happens with
   a plain prompt, or with Claude Code, Codex or Copilot.
4. **How fast it is on the lawyer's computer.** All times here are from one Apple M1 Pro with 16 GB. A laptop with 8 GB is not tested.
5. **Whether the LLM checker helps on messy real contracts.** On the public sets it adds at most 4 tokens (EXP-006).
6. **How common a surname alone is in Romanian contracts**, and how often the models miss it (LDA-20). The sweep does not know it.

## Next experiments

1. Romanian corpus from the lawyer (10 to 15 documents): the same runs as above. This decides the default level for Romanian.
2. The LLM checker (EXP-006 is done: no useful gain). Only if there is a reason: a filter for the noise, a prompt with examples, and the Romanian documents of the lawyer (LDA-28).
3. The same agent test with a plain prompt (no rules for ids) and with other tools (LDA-19 follow-up).
4. Case and application numbers (`36110/97`): the recall on TAB is 0 of 17. It matters less for contracts, but it is a gap.
5. A re-identification test: give the hidden documents to a strong model, and ask it to guess who the parties are.
