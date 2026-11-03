# Adversarial review: Legal Document Anonymizer MVP

Date: 2026-11-02. Reviewer: an adversarial review agent. Scope: the code, tests, evaluation, docs and Jira board LDA, as of commit `4e34411` (branch `feature/LDA01-init`).

Note: the task said that the work of 2026-11-02 was not committed. That is not correct now. `git status` shows a clean tree. The work is in commit `4e34411` (2026-11-02 15:00, author Marcus Pop). I reviewed that commit.

All probe scripts and their outputs are in `/private/tmp/claude-501/-Users-marcuspop-projects/9bd24060-9ac0-4ce2-9536-999717b1370f/scratchpad/review/work/`. I ran them against a copy of the project in `work/proj/` (with `PYTHONPATH=proj/src`). I did not change the project or Jira.

## 1. Verdict

1. No. Today, the claim "a lawyer can use it on client documents" cannot be trusted. The claim "the data stays on the computer" is true for the models, but the hidden output can still contain client names.
2. At the default level, a party whose surname is also a common word (`Brown`, `White`, `Negru`) stays visible when the batch also has that word in lowercase. The leak check then says "no leak" (R-01).
3. In `.docx` files, names stay in parts and attributes that the tool does not touch (`people.xml`, alt text, field codes, custom properties). The leak check cannot see the attribute leaks (R-03).
4. Restore leaves changed ids (`[person_001]`, `PERSON_001`, `[PERSOANA_001]`) in the file with no warning and exit code 0. The Romanian form rules join different people (`Andrei`/`Andra`) and change place names (`Popești-Leordeni` becomes `Popescu-Leordeni`) (R-02, R-04, R-05).
5. The recall numbers come from 3 + 3 EU judgments and 12 ECHR cases. They do not include the failure modes above. No number exists for a real Romanian contract. The MVP is a good demo and a good base, but it is not ready for real client files.

## 2. Findings, ranked by severity

Effort: S = less than one day, M = 1 to 3 days, L = more than 3 days.

### Critical

**R-01 (E, F). A surname that is also a common word leaks at the default level, and the leak check says "clean".**
- Claim attacked: "A missed name is a leak, recall decides"; `is_common_word` only removes common nouns such as `Șoferul`.
- Evidence: `src/legal_anonymizer/detector.py:155` and `:187-197`. A model span of one word is dropped when the lowercase form is anywhere in the batch (`context` is the text of all documents). `refine` first cuts the title (`Mr`, `Ms`, `Domnul`), so `Mr Brown` becomes the one-word span `Brown`. The LLM spans get the same filter (`detector.py:167`), so level `high` cannot repair it.
- Real models, level `low` (`work/probe_real_common.py`, `.out`):
  - Input: `Mr Brown signed ... The vehicle was brown. ... Ms White is the witness. The walls are white.` Output: unchanged. Vault: empty. `leaks: []`.
  - Romanian: `Pârâtul Negru a semnat ... de culoare negru ...` Output: unchanged. `leaks: []`.
  - Control (`work/probe_real_common_control.py`, `.out`): the same text without the lowercase word gives `Mr [PERSON_001]`, `Ms [PERSON_002]`, `Pârâtul [PERSON_001]`.
- Why it matters: English surnames such as Brown, White, Black, Green, King, Young, Wood, Hill, Moore, Long, and Romanian surnames such as Negru, Rus, Albu, Lupu, Lungu, are common. A 30-page batch almost always has the lowercase word. The leak goes to the AI provider. The tool reports success.
- Change: apply the filter only to a word at the start of a sentence or a line, never after a title or a role word (`Mr`, `dl.`, `Pârâtul`). Never apply it to LLM spans. Add a test with a list of common-word surnames.
- Effort: S.

### High

**R-02 (D, F). Restore leaves changed ids in the file, with no warning. The README claim is false, and the test hides it.**
- Claim attacked: README line 46: restore "accepts small changes ... for example `[PERSON_1]`, `[ person_001 ]`". Agent test: "110/110 restored".
- Evidence: `work/probe_restore.py`, `.out`. Not restored and not reported as unknown (exit code 0): `[person_001]`, `[Person_001]`, `PERSON_001`, `(PERSON_001)`, `{PERSON_001}`, `[PERSON_001` (no bracket), `[PERSOANA_001]`, `[ORGANIZATION_001]`, `[PERSON_001 și PERSON_002]`, `[PERSON_001/002]`, full-width brackets. `[PERSON_001]ului` becomes `Ion Popescuului`. `[[PERSON_001]]` becomes `[Ion Popescu]`.
- `PLACEHOLDER_RE` (`vault.py:77-80`) is case-sensitive. The test `tests/test_vault.py:70` passes `"[person_001]".upper()`. So the test checks the upper-case string, not the lowercase string that the README names.
- Why it matters: the lawyer gets a "restored" file that still has ids, or wrong words, and nothing says so. `restored == 110` in the agent test only shows a dictionary lookup for well-formed ids.
- Change: match the tags with `re.IGNORECASE`. Accept a missing bracket and the long type names (`ORGANIZATION`). After restore, search for any id-like text (`[A-Za-zĂÂÎȘȚăâîșț_]+[ _-]?\d{1,4}`) and report it as "suspect"; exit 1. Fix the test and the README.
- Effort: S.

**R-03 (E). In `.docx`, names stay in parts and attributes that the tool does not change. The leak check is blind to the attributes.**
- Claim attacked: "For .docx we change only the text nodes. The styles, tables and images stay"; `scrub` removes authors; leak check by `scan_text`.
- Evidence: `work/probe_docx.py`, `probe_docx_attr.py` and their `.out`. A made-up file with `Ion Popescu` in each part. Changed correctly: body, split runs, header, footer, footnote, comment, text box, content-control text, tracked-change author. Left visible: `word/people.xml` (`w15:author`, `w15:userId` with the e-mail), `wp:docPr descr` and `title` (alt text), `w:fldSimple w:instr`, `w:instrText` (HYPERLINK mailto), `word/_rels/document.xml.rels` (link target), `word/glossary/document.xml`, `customXml/item1.xml`, `docProps/custom.xml`.
- When only the attribute leaks are left, `engine.leaks == []` and `verify == []`: `scan_text` removes all tags with their attributes (`documents.py:248`).
- Why it matters: Word writes `people.xml` when people comment or track changes. A document management system writes client and matter data into custom properties. Lawyers' files have both. An AI tool that unzips the file reads them.
- Change: process or empty `people.xml`, `customXml/*`, `docProps/custom.xml`, `glossary/*`. Rewrite or empty `descr`/`title` of `docPr`, `fldSimple@instr`, `instrText`, hyperlink targets. Make `scan_text` keep attribute values. Add the probe file as a test.
- Effort: M.

**R-04 (B). The Romanian form rules join two different people.**
- Claim attacked: "0 leaks, 1 id"; "names that can belong to two people stay apart".
- Evidence: `work/probe_romanian.py`, `.out`, part 1. `Andra Popescu` and `Andrei Popescu` get the same id. The canonical form is `Andra Popescu`, so a document about Andrei restores with Andra's name. Also `Mata`/`Matei`, `Paul`/`Pau`. Cause: `romanian.bases` maps `-ei` to `-a` (`romanian.py:76-77`), and `related()` (`:86-93`) joins in both directions. `Andrei`, `Matei`, `Bartolomei` are male names. `Andra` is a common female name. Siblings with these names are common.
- Checks that hold: `Pop`/`Popa`, `Ion`/`Ioan`, `Ioan`/`Ioana`, `Dan`/`Dana`, `Maria`/`Marin`, `Andreea`/`Andrei` stay apart.
- Why it matters: a wrong name in a restored legal document is worse than a second id (the project's own rule, LDA-20).
- Change: in the vault, never join by form when both written forms are base names that the model found (`Andrei` and `Andra`). Join only a form that a rule makes from a known base, and only one way (`derives_from`, not `related`). Keep a list of names that end in `-ei`/`-ii` as base names. Show every join by form in `lda entities` for review.
- Effort: M.

**R-05 (B). The sweep with the form rules hides place names and common words as a person, and restore writes the wrong word.**
- Evidence: `work/probe_romanian.out`, part 2 (stub detector, so only the sweep acts):
  - Person `Popescu`, text `orașul Popești-Leordeni` → `[PERSON_001]-Leordeni` → restored `Popescu-Leordeni`.
  - Person `Ionescu`, text `comuna Ionești` → restored `comuna Ionescu`.
  - Person `Bunu`: `bunul imobil`, `bunului` (the asset) → `[PERSON_001]` → restored `Bunu imobil`, `Valoarea Bunu`.
  - Person `Lungu`: `lungul drum`; person `Rus`: `cetățeanul rus, rusul`; place `Satu Mare`: `Satul mare`.
- Cause: `inflections()` makes `-ești` plurals from `-escu` (`romanian.py:43-45`) and `-ul`/`-ului` from every name, and the sweep is case-insensitive (`engine.py:236`, `fold`). Romania has hundreds of places that end in `-ești`, and `-escu` names are the most common surnames.
- Why it matters: the restored contract has a wrong place or a wrong word. The text that the AI tool reads is wrong too.
- Change: for an inflected form, match only when the text has a capital letter at the start of the word. Remove the `-ești` family plural (it is rare in contracts; `Popeștii` is the only gain). Do not let a PERSON form match inside a hyphenated place name.
- Effort: S to M.

**R-06 (A, H). The headline numbers measure a narrow thing on very small sets. Nothing measures the failure modes R-01 to R-05.**
- Claim attacked: "Recall 93.3% on MAPA-EN with medium", "86.3% on TAB", "99.2% on the demo".
- Evidence (raw `eval/results/*.json`):
  - MAPA-EN and MAPA-RO have 3 documents each. MAPA-EN gold is 343 tokens (131 person, 191 organization, 21 address). MAPA-RO gold is 223 tokens. The low → medium gain on MAPA-RO is 2 tokens (15 → 13 misses).
  - `eval/mapa_eval.py:146` calls `detector.detect` per document. It does not use the engine, the vault, the sweep, or `resolve_overlaps`. So MAPA numbers do not measure the word-form work (EXP-007 says this) and do not measure the false joins.
  - The measure is tokens, not mentions. A name with one of three tokens visible counts as 67% hidden. It is a leak.
  - `kept_on_purpose` (`mapa_eval.py:45-50`) takes titles, role words and kept places out of the gold. The `--raw` number is not reported anywhere.
  - TAB: 12 cases, 468 mentions. `eval/tab_corpus.py` leaves out the TAB quasi-identifiers (DATETIME, QUANTITY, DEM, MISC). 17 CODE mentions are all missed. 29 gold mentions have no capital letter (`magistrates` ×9), which the tool cannot hide by design (`work/probe_tab_gold.out`).
  - Demo: `data/demo/matter.yaml` is loaded by `corpus_eval.py:139` and gives 8 seed entities with 26 names and aliases, which cover 13 of the 57 `must_hide` items. The demo also runs with `keep_public_bodies: true`, and `visible_ok` excludes `Tribunalul Brașov` although `Brașov` is a `must_hide` item. The same assistant wrote the documents, the gold list and the detector. `docs/experiments.md` says "do not trust its numbers", but it does not say that the run is seeded.
  - Every result file has `"dirty": true`. The `commit` field does not identify the code that ran.
- Check that holds: the numbers in `docs/results.md`, `docs/experiments.md` and Jira match the raw JSON (I checked all MAPA tp/fn values, the TAB medium mentions 404/468, and the LLM gain and noise counts). `eval/metrics.py` computes P, R, F1 and F2 correctly.
- Why it matters: a reader of the README or Jira sees "93%" and thinks of a lawyer's contract. The sets are EU and ECHR judgments. They have few common-word surnames, no `.docx` metadata, and no Romanian name forms in context.
- Change: put "3 documents, 343 tokens, detector only" next to each MAPA number. Report the `--raw` number. Say that the demo is seeded. Record the diff hash of a dirty tree in the result file. Add a synthetic Romanian test set now (see section 7).
- Effort: S for the docs, M for the tracker.

**R-07 (E). Re-identification is not measured, and the hidden files keep strong clues.**
- Claim attacked: the epic goal "no client data leaves the lawyer's computer".
- Evidence: the agent-test output `docs/agent-test/output/01_contract_transport.ro.revised.docx` still has `Oficiul Registrului Comerțului de pe lângă Tribunalul Brașov` (public-body policy). It shows the county of the company although `Brașov` is a `must_hide` item in `data/demo/gold.json`. The hidden files keep contract numbers and dates (`nr. 128 din 22.03.2024`), exact amounts, the dates of events, and court names. Dates and job titles are off by default. Patterns miss many Romanian identifiers: a CNP with spaces, the new ONRC number format (`J2020001234408`), car plates, land-register and cadastral numbers, insurance policy numbers, a rural address with no `str.`/`nr.` (`work/probe_patterns.out`).
- Why it matters: for a court case, the court, the date and the object of the case are enough to find the parties on the public court portal. For a company client, the county, the contract number and the amount can be enough. LDA-23 exists but has no plan or threshold.
- Change: state in the README that the tool is pseudonymization with known residual risk. Run LDA-23 on the demo and on TAB before any real use. Add the missing patterns (S each).
- Effort: M.

### Medium

**R-08 (B). Restore loses the grammatical form. The lawyer must proofread every restored Romanian text.**
- Evidence: `work/probe_romanian.out`, part 3: `Cererea Mariei Ionescu` → `Cererea Maria Ionescu`; `Casa Popeștilor` → `Casa Popescu`; `Tribunalul Brașovului` → `Tribunalul Brașov`. With R-02: `[PERSON_001]ului` → `Popescuului`. Upper-case headings and `S.C.` are lost (LDA-21, agent test).
- How bad: the meaning is clear, but the text has grammar errors. A lawyer cannot send it without a full read. For a court filing, this is not acceptable. The prompt rule "write the ending in a separate word" helps only when the agent follows it.
- Change: LDA-21 option (a): keep the suffix outside the id when the form is base + suffix. Store the written form of each occurrence for option (b). Raise LDA-21 to High.
- Effort: M.

**R-09 (B). The sweep is case-insensitive, and the canonical form is the most common form. A name that is also a word breaks the text and the name.**
- Evidence: `work/probe_romanian.out`, case "English: first name Will". All `will` become `[PERSON_001]`. The vault now has `will` (2 times) and `Will` (1 time). The canonical form is `will`, so restore writes `will signed.` in lowercase. Same for `Negru`/`negru`.
- Change: match lowercase text only for forms that the vault saw in lowercase. Prefer a capitalized form as canonical.
- Effort: S.

**R-10 (C). The LLM verdict is fair for these sets, but the sets could not show a gain. The conclusion is worded too strongly.**
- Claim attacked: "Level `high` did not pay off" (README:192), "no useful gain" (memory note).
- Checks that hold: Ollama 0.40.13 answers HTTP 501 for every `format` (schema, `"json"`, with or without `think`). `think: false` works: no thinking field, content returned. Without `think: false`, 200 reply tokens give an empty content (`work/probe_ollama.out`). Temperature 0 is set. The prompt is clear. The numbers match the JSON.
- Weak points:
  - Headroom: after `medium`, only 23 (MAPA-EN) and 13 (MAPA-RO) gold tokens were missed. On TAB, 17 of 64 misses are case numbers, which the LLM is not asked for (`LLM_TYPES`), and 9 are the lowercase `magistrates`, which `refine` drops. So the test could find at most a small gain.
  - The real gap of the tool (R-01: a visible `Mr Brown`) is a good job for the LLM. But the prompt says "do not list common words", and `_llm_spans` applies `is_common_word` again. So the design blocks the best use.
  - The 4b runs used older code (no 512-token limit). The docs say this.
- Decision check: "high stays experimental" is right. "Did not pay off" should read "showed no gain on public judgments, where the baseline left little to find".
- Change: retest after R-01 with a set that has common-word surnames and messy names. Try the LLM as a filter of GLiNER hits and as a check of capitalized words that stay visible.
- Effort: M.

**R-11 (B, F). There is no command to remove a wrong entity or to split a false join. Noise in the vault spreads to every later document of the matter.**
- Evidence: `cli.py` has `merge` and `alias` but no `forget`, `split` or `unmerge`. The sweep hides every known form in every document (`engine.py:232-240`). EXP-002 shows one case (`and` hidden 463 times). R-04 and R-05 create more such entries.
- Change: add `lda forget ID` (mark as not sensitive, add to keep) and `lda split ID FORM`. Show the new joins by form after each run.
- Effort: M.

**R-12 (E, F). Text in decomposed Unicode (NFD) is not swept and the leak check does not see it.**
- Evidence: `work/probe_romanian.out`, part 4. Vault knows `Ștefan Țăranu`. A second document has the same name in NFD (combining comma). Output: unchanged, `leaks: []`, `verify: []`. `fold` keeps one code point per code point (`textnorm.py:47-56`), so the combining marks stay in the folded text and break the match. No input is normalized to NFC.
- Why it matters: text from macOS file names, some PDF text layers and some copy-paste is NFD. The sweep and the leak check are the safety nets, and both fail here.
- Change: normalize every unit to NFC at `open_document` and keep an offset map, or fold combining marks to empty with an offset map.
- Effort: S to M.

**R-13 (F). Some tests repeat the implementation; mutations survive.**
- Evidence: `work/mutate.py`, `mutate.out` (22 mutations, fast tests only). Survived: remove the vocative `-ule`; remove the `-ești` → `-escu` base rule; remove the LLM "verbatim in the text" check; remove the LLM "no overlap with an existing span" check. The cedilla mutant also survived, but it is equivalent (NFD already removes the cedilla), so that line is dead code. The test at `tests/test_vault.py:70` calls `.upper()` on the lowercase case (R-02). The rules and the probes were written together, so the tests contain only the cases the rules handle; there are no tests for `Andrei`/`Andra`, `-ești` places, or common-word names.
- Checks that hold: 342 tests pass in 82 s (`work/pytest_full.txt`); the model tests run by default (they are marked, not skipped); 18 of 22 mutations were killed.
- Change: add negative tests from R-01, R-04, R-05, R-09, R-12 and the restore cases of R-02.
- Effort: S.

**R-14 (D). The agent test proves little, and the docs say so only in part.**
- Checks that hold: the prompt in `docs/agent-test/prompt.md` is the same text as the Agent call in the session transcript (0 different lines, `general-purpose`, 2026-11-01 23:19 UTC). The output files have 110 well-formed ids, no id-like variants, and no gold name of the demo except the kept `Tribunalul Brașov` (`work/probe_agent_out.out`). Two outputs have `creator: python-docx` in their core properties.
- Weak points: one run, one model of the same family as the author, the rules in the prompt, the instruction "do not try to find the real names", and no hostile or lazy behavior. "110/110 restored" is a lookup of well-formed ids (see R-02 for what is not handled).
- Change: in LDA-31, include a plain prompt, a translation task (EN → RO), a reformat task, a mail-merge task, and file names with ids. Count silent leftovers with the R-02 check.
- Effort: M.

**R-15 (G). The Jira board does not show the state of the work in a reliable way.**
- Evidence (`work/jira_dump.txt`, read with JQL `project = LDA`): all 31 issues have priority Medium. All 19 "Done" issues have status category `indeterminate` and resolution empty, so "resolution = Unresolved" filters, burndown and "created vs resolved" reports count them as open. No ticket has acceptance criteria; descriptions report results after the fact. LDA-8 says "Ollama `/api/chat` with a JSON schema", which is no longer true (LDA-15). LDA-14 says 84 tests; the file now has 94 (LDA-29 added tests). LDA-12 says EXP-001 to EXP-005; the log now has EXP-011. No ticket exists for R-01, R-02, R-03, R-04, R-05, R-09, R-11, R-12. The descriptions are in clear, short sentences (close to STE).
- Change: see section 5.
- Effort: S.

**R-16 (A). Results are not reproducible from the result files.**
- Evidence: every JSON has `"dirty": true`. The 4b LLM runs ran on code without the reply limit. The speed numbers of 2026-11-01 23:00 to 2026-11-02 02:00 UTC were made under load (documented). Load average during my review was 6 to 7 with no job of mine.
- Change: refuse to record a run from a dirty tree, or store the diff hash and the diff.
- Effort: S.

### Low

**R-17 (F). The vault join is quadratic in the number of entities.** `vault._other_form` reads every key for every new name. Synthetic vault (`work/probe_perf.out`): 200 names 0.1 s, 1,000 names 1.9 s, 3,000 names 16 s; one new name at 3,000: 18 ms. The sweep regex is 716,000 characters at 3,000 names, 1 s to build, 0.45 s per 30 KB, and it is built 3 times per document. This is fine for the MVP. Index the keys by word. Effort: S.

**R-18 (F). `anonymize` writes the output file also when the leak check finds a leak.** `cli.py:94-109` writes the file, prints a warning, and exits 1. A user who does not read the console sends the file. Write such files with a `.LEAK` suffix or to a quarantine folder. Effort: S.

**R-19 (C). Prompt injection in a document can make the LLM add hits, not remove them.** A document can tell the model to list words. `refine` drops lowercase words and titles, `is_common_word` drops many single words, and the LLM spans cannot overlap existing spans (`llm_check.py:197`). The worst effect is over-hiding of capitalized words, which then stay in the vault (R-11). The user rule "the LLM may only add hits" holds. The overlap check has no test (R-13). Effort: S.

**R-20 (F). Smaller code points.** `CEDILLA_TO_COMMA` in `_fold_char` is dead code (NFD already removes the cedilla). `corpus_eval.py:166` calls `vault.resolve` while it measures, which can add keys to the vault under test. Two processes on one matter can read the same `MAX(number)` in `_next_number` and then fail on the UNIQUE constraint (not silent). Effort: S.

**R-21 (user decision). Vault security and wording.** The vault is a plain SQLite file with mode 0600 (LDA-25, deferred). "Pseudonymization" wording is accepted. Ollama will probably not ship (LDA-24). I list these only for completeness.

## 3. Claims that hold up

| Claim | My check |
|---|---|
| Tests pass | 342 passed, 0 skipped, 82 s, in the copy (`work/pytest_full.txt`). |
| Numbers in the docs match the raw results | All MAPA tp/fn and recall values, TAB 404/468, LLM gain and noise counts: same as in `eval/results/*.json`. |
| Metric formulas | `eval/metrics.py`: precision, recall, F-beta are standard. |
| `fold` keeps the length | True per code point: `_fold_char` always returns one character (`ß`, `İ`, ligatures, combining marks). The semantic problem is R-12, not the length. |
| Regex injection | All entity text goes through `re.escape` (`engine.py:65-74`, `engine.py:250`, `llm_check.py:196`). |
| Catastrophic backtracking | None found for EMAIL, RO_ADDRESS, EN_ADDRESS, CASE_NUMBER_EN, JOB_TITLE on hostile inputs up to 72,000 characters (`work/probe_regex.out`). |
| Ollama 501 for Qwen3.5 and `think: false` | Reproduced with qwen3.5:0.8b (`work/probe_ollama.out`). |
| The LLM can only add hits | Holds by design (`llm_check.py:178-199`, `detector.py:158-169`). |
| Names that must stay apart | `Pop`/`Popa`, `Ion`/`Ioan`, `Ioan`/`Ioana`, `Dan`/`Dana`, `Maria`/`Marin`, `Andreea`/`Andrei`. |
| Diacritics with and without, cedilla, capitals | `Stefan Taranu`, `Ştefan Ţăranu`, `STEFAN TARANU` all get the id (`probe_romanian.out` part 4). |
| `.docx` text parts | Body, split runs, header, footer, footnote, comment, text box, content control, tracked text, tracked-change author: all handled. |
| Agent test prompt and output | The prompt is the transcript prompt. The outputs have 110 well-formed ids and no gold name except the kept court. |
| Romanian ID patterns | CNP, CUI/CIF (with and without RO), J-number (old format), IBAN with spaces, case numbers `dosar nr. 1234/3/2024`, urban addresses with `bl./sc./et./ap.`, Romanian phone formats: all found (`work/probe_patterns.out`). |

## 4. What I could not verify, and why

- How the tool does on real Romanian contracts: no such data exists (LDA-22).
- Codex and Copilot behavior: not available here.
- Speed on an 8 GB laptop: not available. My timings are on the shared M1 Pro with load average 6 to 7.
- I did not rerun MAPA, TAB, demo or the LLM matrix (rule: no long jobs). I checked the numbers against the raw files only.
- Whether the BERT models detect NFD text by themselves (R-12 shows only that the sweep and the leak check do not).
- The claim "we read the TAB hits and found no names" (EXP-006): the review files are in `_review/` with real text, and I did not read them.
- The Jira workflow scheme itself: I read the status categories of the issues, not the workflow configuration.
- Full transcript: I read only the Agent call of the agent test.

## 5. Suggested Jira changes (not made)

New tickets:
1. **Bug, Highest: a surname that is also a common word leaks (`Mr Brown`, `Pârâtul Negru`).** Fix `is_common_word` and add tests (R-01).
2. **Bug, High: restore leaves changed ids with no warning (`[person_001]`, `PERSON_001`, translated tags).** Case-insensitive match, suspect-id report, exit 1; fix the test and the README (R-02).
3. **Bug, High: `.docx` leaks in `people.xml`, alt text, field codes, link targets, custom XML, custom properties, glossary; the leak check does not read attributes** (R-03).
4. **Bug, High: the vault joins `Andrei` and `Andra` (and `Matei`/`Mata`)** (R-04).
5. **Bug, High: the sweep hides `-ești` places and common words as a person; restore writes `Popescu-Leordeni`** (R-05).
6. **Bug, Medium: case-insensitive sweep and a lowercase canonical form (`will`)** (R-09).
7. **Task, Medium: NFC normalization with an offset map** (R-12).
8. **Task, Medium: `lda forget` and `lda split` for wrong vault entries** (R-11).
9. **Task, High: synthetic Romanian contract test set with gold by construction** (section 7, step 3).
10. **Task, Medium: missing Romanian patterns (CNP with spaces, new ONRC number, plates, land register, cadastral, policy numbers, rural addresses)** (R-07).
11. **Task, Low: record the diff hash of a dirty tree in each result file** (R-16).
12. **Task, Low: write files with a leak to a quarantine folder** (R-18).

Tickets to reopen or re-scope:
- **LDA-14 (Done):** reopen or link to tickets 4 and 5. The claim "names that must not join" is not complete.
- **LDA-29 (Done):** add a note that the leak check does not see NFD text.
- **LDA-19 (Done):** add a note that "110/110 restored" covers well-formed ids only (ticket 2).
- **LDA-21:** raise to High. It is a defect that a lawyer sees in every Romanian restore.
- **LDA-23:** add a plan and a pass threshold (for example: a strong model names no party in 20 hidden documents). Raise to High.
- **LDA-28:** re-scope: test the LLM on the R-01 class (visible capitalized words) after ticket 1, not only prompt variants.
- **LDA-8:** update the description (no JSON schema with Qwen3.5).
- **LDA-12:** update the title (EXP-001 to EXP-011).

Board hygiene:
- Map the status "Done" to the status category "Done" and set a resolution on transition. Then fix the 19 Done tickets.
- Set real priorities. Today every ticket is Medium.
- Add acceptance criteria to every open ticket (a test or a number that decides "done").

Nothing to close: I found no duplicate tickets.

## 6. Suggested order of work for the next two weeks

Week 1 (stop the leaks and the silent failures):
1. R-01 common-word filter, with tests (day 1).
2. R-02 restore: case-insensitive, suspect-id report, exit 1 (day 1).
3. R-03 `.docx` parts and attributes, and an attribute-aware leak check (days 2 to 3).
4. R-04, R-05, R-09 form rules: one-way joins, capital letter for inflected forms, no `-ești` plural, review list of joins (days 3 to 4).
5. R-12 NFC normalization (day 5).

Week 2 (measure what matters):
6. Build the synthetic Romanian proxy set (step 7 below). Run `low` and `medium` through `corpus_eval` (the whole pipeline), not `mapa_eval`.
7. Run LDA-23 (re-identification) on the demo and on 5 TAB cases.
8. Run LDA-31 (plain prompt, hostile tasks) and count silent leftovers with the new restore check.
9. Add `lda forget`/`lda split` (R-11).
10. Fix the Jira board (section 5) and the README numbers (R-06).

## 7. Is waiting for the lawyer's documents (LDA-22) the right plan?

Not alone. LDA-22 is necessary, but it is blocked and it will give only 10 to 15 documents. A proxy can start now:
- **Synthetic contracts with gold by construction.** Use public Romanian contract templates (sale, lease, transport, employment, power of attorney) and fill them with names from frequency lists of Romanian first names and surnames. Add on purpose: common-word surnames (Negru, Rus, Lupu, Albu), `-escu` surnames next to `-ești` places, `Andrei`/`Andra` pairs, genitive and vocative forms in context, initials, ALL-CAPS party blocks, CNP with spaces, new ONRC numbers, rural addresses, comments and tracked changes from named reviewers, custom properties. The gold is known, so recall and false joins are exact. The weak point (the same author writes text and gold) is smaller, because the test targets known failure classes and not the rules.
- **Public Romanian court decisions** (they are published with names removed, but the anonymization marks show where names were): useful to test over-hiding and the layout of real filings.
- **LegalNERo**: its license (CC BY-NC-ND) may allow internal, non-commercial evaluation without derivatives. Ask a lawyer before use; do not put it in git.
Then LDA-22 confirms the proxy, instead of being the first and only test.
