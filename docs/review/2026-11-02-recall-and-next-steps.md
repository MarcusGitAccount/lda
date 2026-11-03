# Recall and next steps: Legal Document Anonymizer MVP

Date: 2026-11-02. Basis: my copy of commit `4e34411` in `review/work/proj/`. I did not read the live project. It is changing.

Labels in this file:
- **[checked]**: I ran it, or I read it in code, raw data or a source.
- **[opinion]**: my judgement. It is not measured.

The probe scripts and outputs are in `/private/tmp/claude-501/-Users-marcuspop-projects/9bd24060-9ac0-4ce2-9536-999717b1370f/scratchpad/review/work/`.

Machine note: the load average was 22 to 31 during this work (a Java process and a game). My run times are not reliable. The counts are reliable.

## 0. Three facts that change the plan

1. **[checked] The public sets have almost no real misses left.** We cannot use them to steer recall work.
   - TAB at `medium` (`probe_tab_misses.py`, `probe_tab_misses_medium.out`): 64 misses in 468 mentions. 17 are case or application numbers. 12 have no capital letter (gold noise, for example `magistrates`). 31 are "partly hidden".
   - Of the visible words in the partly hidden mentions (`probe_tab_partial.out`), 10 are a possessive `'s`, and about 16 are words of a kept country (`United Kingdom`, `Northern Ireland`). These are measurement and policy effects, not names.
   - Real name misses that are left: about 3 or 4.
   - MAPA-RO at `medium` (`probe_mapa_ro_misses.out`): the 13 missed tokens are EU case names (`CIF` ×6, `Impact` ×4, `van Gend en Loos`) and punctuation. `CIF` is also in the keep list, as a field label.
2. **[checked] The leaks that matter come from failure classes that the public sets do not contain:**
   - common-word surnames (R-01),
   - `.docx` metadata (R-03),
   - Romanian word forms and false joins (R-04, R-05),
   - a surname alone (LDA-20),
   - identifiers with no pattern (`probe_patterns.out`).
3. **[checked] Entity-level numbers are worse than the mention number.** TAB `medium`: mention recall 0.863, entity recall 0.810 (166 of 205 entities have every mention hidden). 12 of 12 documents have at least one leaked gold mention. A "document leak rate" shows the risk better than mention recall. Some of these leaks are measurement effects (see fact 1).

Conclusion **[opinion]**: the next gain does not come from a bigger model. It comes from three things:
- fixes of known structural gaps,
- document-structure cues that feed the vault,
- a test set that contains the hard cases.

## Part 1. How to raise recall: ranked by expected gain / effort

Gain is for real Romanian and English client documents **[opinion]**. Effort: S < 1 day, M = 1 to 3 days, L > 3 days.

| Rank | Change | Gain | Effort | Evidence |
|---|---|---|---|---|
| 1 | Fix the common-word filter (R-01). The author is doing it. | High | S | [checked] `probe_real_common.out`: `Mr Brown`, `Ms White`, `Pârâtul Negru` leak at `low`. |
| 2 | Party cues feed the vault (see 1.3). | High | S–M | [checked, weak] `probe_party_cues.out`: regex cues alone find 8 of 8 seeded parties in the demo. The demo text was written by the same AI, so this is weak evidence. |
| 3 | Defined aliases: `denumită în continuare „Alfa”` → `Alfa` joins the entity of the party. | High for contracts | S | [opinion] Short aliases are in almost every Romanian contract. Today they leak or get a new id. |
| 4 | A surname alone after a full name (LDA-20), only with a title or role before it (`dl.`, `pârâtul`, `Mr`), and only when exactly one entity has that surname. | High | M | [opinion] This is very common in court filings and letters. |
| 5 | Pattern gaps (1.4). | Medium | S each | [checked] TAB: 17 of 64 misses are codes. `probe_patterns.out`: CNP with spaces, new ONRC number, car plates, CF/cadastral and policy numbers are missed. |
| 6 | "Visible capitalized word" review pass (1.5). | Medium | M | [opinion] It is a safety net for every class that the models miss. |
| 7 | A first-name gazetteer as a booster (1.6). | Medium | M | [opinion] |
| 8 | A second GLiNER model for Romanian: `knowledgator/gliner-x-*` (Apache-2.0, Romanian is listed). Test it with the union of hits. | Unknown, maybe medium for RO | M | [checked] licence and languages (sources). [opinion] gain. |
| 9 | Fine-tune a Romanian model on synthetic contracts (1.7). | Unknown | L | [opinion] Risk: it learns our templates. |
| 10 | LLM as a free-form checker (EXP-006 design). | Low | M | [checked] EXP-006: 0 to 4 tokens. Headroom was 13 to 23 tokens. |
| 11 | GLiNER threshold tuning. | ~0 | S | [checked] EXP-003: ±1 point. |

### 1.1 Structural gaps compared with tuning gaps

**Structural** gaps cannot be fixed with a better threshold or a bigger model. They need code or policy:
- Names with no capital letter, or names that are also common words (R-01).
- Case and application numbers with no context word (`36110/97`).
- Quasi-identifiers: dates, amounts, unique facts, court plus date of a case (LDA-23).
- Text outside the `.docx` text nodes (R-03).
- A surname alone, initials (`I. Popescu`), short defined aliases.
- Romanian forms (R-04, R-05, LDA-21).
- Scanned PDFs: no OCR. The tool refuses them, which is safe. But many law-firm files are scans **[opinion]**.
- NFD text (R-12).

**Tuning** gaps: model thresholds, chunk size, the GLiNER label set, which model is in the union. **[opinion]** These give a few points at most on Romanian contracts, and we cannot measure them before the test set of 1.8 exists.

### 1.2 Models that run on the lawyer's computer

| Model | Licence | Romanian? | Note |
|---|---|---|---|
| `dumitrescustefan/bert-base-romanian-ner` (in use) | MIT, trained on RONEC (MIT) | yes | [checked, sources 1–2] Good for commercial use. |
| `urchade/gliner_multi_pii-v1` (in use, `medium`) | Apache-2.0 | **no**: PII fine-tune in en, fr, de, es, pt, it | [checked, source 3] This explains the very small Romanian gain (2 tokens). |
| `urchade/gliner_multi-v2.1` (base of the above) | Apache-2.0 | multilingual base | [checked, source 4] The older `gliner_multi` is CC BY-NC 4.0. Do not use it. |
| `knowledgator/gliner-x-small/base/large` | Apache-2.0 | listed | [checked, source 5] Large is 0.9B parameters. No Romanian benchmark is published. Test small or base first. |
| `Babelscape/wikineural-multilingual-ner` | CC BY-NC-SA 4.0 | no | [checked, source 6] Not allowed: non-commercial. |
| LegalNERo (data) | CC BY-NC-ND 4.0 | yes | [checked, source 7] Do not train on it. Evaluation only, with legal advice first. |
| `dslim/bert-large-NER` (in use, EN) | not checked here | en | Check the licence before shipping (LDA-24). |

**Two models with a union of hits** **[opinion]**:
- The pipeline already takes the union (BERT + GLiNER).
- For Romanian, swap or add a GLiNER that lists Romanian (gliner-x). Measure on the new set (1.8), not on MAPA.
- The union raises recall and lowers precision. The common-word and capital-letter rules decide how much noise stays.

**A small LLM as a second pass** **[opinion]**:
- Do not ask it to "find what is missed" in free text (EXP-006).
- Give it a closed list of candidates from 1.5 and ask a yes/no question per candidate: "Is `Brown` in `Mr Brown signed` the name of a person or an organization?"
- It may only add hits. Code checks that each candidate is in the text.
- This is a classifier job, which suits small models better than open search.
- Do not apply `is_common_word` to its answers. Do not tell it "skip common words".
- Only do this when Ollama or an embedded runtime ships (LDA-24). Today, this is not on the 4-week path.

### 1.3 Pipeline tricks (document structure)

- **Party cues → vault before pass 2.** Patterns:
  - `X, cu sediul în`, `X, domiciliat(ă) în`, `X, identificat(ă) cu CI`, `X, CNP`;
  - `reprezentată prin (dl./dna) X`, `în calitate de`;
  - `Subsemnatul/Subsemnata X`;
  - signature blocks (`Semnătura`, `Nume și prenume:`, `Signed by`, `Name:`);
  - English `of [address]`, `a company incorporated`, `represented by`.
  - Every name found this way is a vault entity for the whole batch. So the existing batch sweep hides the later mentions that the model misses.
  - Prototype: `probe_party_cues.py` [checked, weak evidence].
- **Defined aliases.** `denumită în continuare „Prestatorul”` is a role and stays visible (role list). `denumită în continuare „Alfa”` is a name and must join the entity of the party. Rule: the quoted alias is hidden when it is not a role word.
- **Context windows for a surname alone.** Join a bare surname to a known person only when:
  - a title or role is before it, and
  - exactly one known entity has that surname.
  When two entities share the surname, give a new id and show it for review (risk R-04).
- **Gazetteer and batch sweep together.** The sweep already hides known names everywhere. Party cues make the "known" list bigger at the start. This gives more value than a bigger model **[opinion]**.

### 1.4 Patterns to add (each S)

| Item | Example | Note |
|---|---|---|
| CNP with spaces or dots | `180 0101 221144` | [checked] missed today |
| New ONRC number | `J` + year + 6 digits + county + check digit, no slashes; since 26 July 2024 | [checked, sources 8–9]; `python-stdnum` has `stdnum.ro.onrc` (LGPL) |
| Old ONRC with full date | `J40/1234/20.03.2020` | [checked] only partly hidden today |
| Car plates | `B-123-ABC`, `CJ 12 XYZ` | [checked] missed |
| Land register, cadastral | `CF nr. 123456`, `nr. cadastral 234567` | [checked] missed. These identify a property and so an owner. |
| Insurance policy, invoice, contract numbers | `polița RCA nr. …`, `contract nr. 128/22.03.2024` | [checked] missed. Contract numbers are optional: an AI tool may need them. |
| Bare application/case number after a context word | `cererea nr. 36110/97`, `application no. 36110/97` | [checked] TAB: 0 of 17 |
| Rural address | `sat …, com. …, jud. …` | [checked] missed by patterns; the NER may catch parts |

### 1.5 The "visible capitalized word" safety net

- After hiding, list every capitalized word that is visible and is not:
  - at the start of a sentence,
  - in a Romanian or English word list,
  - in the keep list or the role list.
- Show the list to the lawyer before the file goes out (and optionally to the LLM classifier of 1.2).
- **[opinion]** This is the cheapest way to catch the classes that no test set covers. It also gives the lawyer a review step that takes minutes. A Romanian word list with a licence is needed (for example a Hunspell `ro_RO` dictionary; check its licence).

### 1.6 Gazetteers, with the common-word problem in mind

- **First names**: use them as a booster. A capitalized first name followed by a capitalized word is a PERSON candidate. Romanian first names are rarely common words **[opinion]**.
- **Surnames**: never hide on the list alone (Negru, Lungu, Bunu, Rus are words). Use the list only to keep a model hit that a filter would drop.
- **Places**: SIRUTA (13,755 localities) **[checked, source 10]**. The licence of the data is not clear. Ask before shipping. Use it to tell a place from a person (`Popești` is a place). Do not use it to hide more.
- Sources for names: Wikidata given-name and family-name items (CC0) **[opinion: not checked here]**; the DEPABD statistics give the most common names, not full lists **[checked, source 11]**.

### 1.7 Fine-tune (later, L)

- `bert-base-romanian-cased-v1` (MIT) + RONEC (MIT) + synthetic contract sentences (1.8) → a Romanian NER that knows party blocks and legal forms.
- Or fine-tune GLiNER on synthetic Romanian PII.
- Risk: the model learns the generator, not real documents. Only train on the "dev" templates. Measure on the holdout and on real documents.
- **[opinion]** Do it only if the test set shows that model misses (not structural gaps) are the main cause of leaks.

### 1.8 Measurement: a Romanian test set with gold by construction

**Name:** `ro-contracts-synth`.

**Size:** 60 documents.
- 30 dev (developers may read them) and 30 holdout (frozen; only a script reads them; numbers are reported once per milestone).
- About 2,000 entity mentions and 400 entities.
- **[checked: arithmetic]** With 2,000 mentions, a recall of 0.98 has a 95% interval of about ±0.6 points. With 400 entities, about ±1.4 points.

**Document types (12):** sale of real estate, sale of a car, lease, service contract, transport contract, employment contract, power of attorney, formal notice (notificare), statement of claim (cerere de chemare în judecată), defence (întâmpinare), company resolution (hotărâre AGA), e-mail thread. Some are in English (settlement, NDA, email).

**Construction:**
- A template with typed slots (`{PARTY1.name}`, `{PARTY1.name|gen}`, `{PARTY1.alias}`, `{PARTY1.cnp}`).
- A renderer writes `.docx` and records the gold offsets of each slot at render time. The gold is exact by construction: mention level, with the entity id.
- Also write a text-layer PDF of 20% of the documents.

**Hard-case quotas** (each document type gets some, written as a list before any fix):
- common-word surnames;
- `-escu` people next to `-ești` places;
- `Andrei`/`Andra` siblings;
- genitive, vocative and article forms in real sentences;
- ALL CAPS party blocks;
- initials;
- hyphenated double names;
- names with no diacritics, cedilla letters and NFD;
- foreign names (Hungarian, Ukrainian, English);
- short defined aliases;
- e-mails made from names;
- every Romanian ID type;
- names in tables, headers, footers, comments, tracked changes, `people.xml`, custom properties and alt text;
- split runs.

**Keep it honest:**
1. The person or agent who writes templates and slot values does not see the detector code or the probes.
2. The hard-case list is written from the error taxonomy before the fixes, and frozen.
3. The holdout is never opened by the developers. Only the counts leave the script.
4. Add 10 documents that a human writes freely (a law student or the lawyer, with fake data), not from templates. This checks that the templates are not too easy.
5. Run with no seed list. A seeded run is a separate number.
6. Report each hard-case class on its own line. Never report only one number.

**Metrics:**
- **Mention recall**: every letter and digit of the mention is hidden. This is the existing `covered` rule, which is correct.
- **Entity recall**: every mention of the entity in every document is hidden. This is the main number for a lawyer.
- **Document leak rate**: the share of documents with at least one leaked direct identifier.
- **False joins**: two gold entities with one id. The target is 0. Any value above 0 blocks a release.
- **Splits**: one entity with more than one id.
- **Silent restore failures**: id-like text that stays after restore. The target is 0.
- **Restore form accuracy**: the share of mentions restored in the written form of the original.
- **Over-hiding**: non-gold hidden spans per 1,000 words, with a sampled review.
- **Speed**: words per second at `low` and `medium` on a quiet machine.

## Part 2. Next steps: a 4-week plan to an MVP that a lawyer can try on real files

**Goal of the 4 weeks [opinion]:** the lawyer runs the tool on 3 real files on their own computer, reviews a short report, and sends hidden files to their AI tool. The lawyer must find no client identifier in what goes out.

| Week | Step | Goal | Done when | Risk |
|---|---|---|---|---|
| 1 | 1. Finish R-01 to R-05, R-09, R-11, R-12, the R-02 restore check and the R-03 `.docx` parts (in progress). | No known silent leak | Every probe case in my review is a test, and it passes. 0 id-like leftovers on the 30 restore cases of `probe_restore.py`. The attribute-only `.docx` probe gives 0 names and the leak check sees attributes. | The fixes add over-hiding. Watch the ro-law hits per 1,000 words (today 40.5). |
| 1–2 | 2. Build `ro-contracts-synth` (1.8): the generator, 30 dev + 30 holdout, and 10 free documents. | A number that means something for Romanian contracts | At least 1,500 gold mentions. All hard-case quotas are met. A gold validator passes (each gold span equals the rendered text). The holdout is frozen with a hash. | The same author writes text and gold. Use the rules of 1.8. |
| 2 | 3. Party cues, defined aliases, surname alone with context, pattern gaps (ranks 2–5). | Recall on the classes that matter | On dev: entity recall ≥ 0.98 for direct identifiers. False joins = 0. Silent restore failures = 0. | The cues over-fit the templates. Check on the 10 free documents. |
| 3 | 4. Review report for the lawyer. One page per batch: the entities and their ids, the new joins by form, the visible capitalized words (1.5), the leak check result. Files with a leak go to a quarantine folder (R-18). | The lawyer catches what the tool misses | A 10-page contract can be reviewed in 5 minutes (try it with one person). | The lawyer skips the review. Make the "send" folder contain only reviewed files. |
| 3 | 5. Re-identification test (LDA-23) on 5 synthetic documents and 3 demo files. | Know the residual risk | A written result: how many parties a strong model names. A decision on the `DATE_TIME` default. | The result is bad. Then say so in the README, and turn on dates by default for court filings. |
| 3 | 6. Restore form (LDA-21, option a: the suffix stays outside the id). Agent test part 2 (LDA-31) with a plain prompt. | Restored Romanian text that a lawyer can send | Restore form accuracy ≥ 0.95 on dev. 0 silent restore failures in the plain-prompt agent run. | The agent breaks the ids more with the new format. |
| 4 | 7. Pilot packaging: one install script, models offline (`HF_HUB_OFFLINE=1`), `low` by default, `medium` optional for English. | The lawyer can run it | Works on a clean user account on a Mac with no network after setup. | The lawyer has 8 GB RAM or Windows. Ask first. |
| 4 | 8. Pilot on 3 real files on the lawyer's computer (see below). Run the holdout once. Go or no-go meeting. | A real number | The lawyer marks 0 visible client identifiers in the 3 hidden files, or every miss gets a ticket. Holdout: entity recall and document leak rate reported per class. | A real miss. That is the point of the pilot. Fix and repeat. |

**What I would cut for these 4 weeks [opinion]:**
- level `high` and LDA-28 (the LLM prompt work);
- GLiNER2;
- the llama.cpp runtime (LDA-24, LLM part);
- the HTTP API server;
- PDF output styling;
- DATE/JOB tuning beyond the default decision;
- speed work (R-17);
- vault encryption (user decision, LDA-25);
- the fine-tune (1.7);
- a second GLiNER model, unless the dev set shows many model misses in Romanian.

**What to ask the lawyer first (the smallest useful request) [opinion]:**
1. **15 minutes of questions.**
   - Which AI tool? Which 3 tasks are most common?
   - Which document types are most common: contracts, court filings, e-mails?
   - Are the files `.docx` or scanned PDF?
   - Do the files have comments or tracked changes? Is there a document management system?
   - Which computer: macOS or Windows, and how much RAM?
2. **3 documents with no risk:** the firm's own templates or precedents (a contract, a court filing, a letter), in the original `.docx`, with real layout and style. The client data is replaced by the lawyer, or the documents come from a closed public case. Send them by an encrypted channel, or better, give them on a USB stick in person. These show real structure (party blocks, aliases, headers) without client data.
3. **Later, for the pilot:** the lawyer runs the tool on 3 real client files on their own computer. We never receive the files. The lawyer:
   - opens each hidden file,
   - highlights every visible item that could identify the client,
   - sends us only the counts and the type of each miss (for example "a surname after `pârâtul`"), not the text.
   This is the safe way to get real recall without a GDPR question about sharing client data **[opinion: confirm with the lawyer]**.

## Sources

1. [dumitrescustefan/bert-base-romanian-ner model card](https://huggingface.co/dumitrescustefan/bert-base-romanian-ner) (MIT, RONEC v2).
2. [RONEC dataset card](https://huggingface.co/datasets/ronec/blob/main/README.md) (MIT).
3. [urchade/gliner_multi_pii-v1](https://huggingface.co/urchade/gliner_multi_pii-v1) (Apache-2.0, six languages).
4. [GLiNER introduction, model list and licences](https://urchade.github.io/GLiNER/intro.html).
5. [knowledgator/gliner-x-large](https://huggingface.co/knowledgator/gliner-x-large) (Apache-2.0, Romanian listed, 0.9B).
6. [Babelscape/wikineural-multilingual-ner](https://huggingface.co/Babelscape/wikineural-multilingual-ner) (CC BY-NC-SA 4.0, no Romanian).
7. [LegalNERo on Zenodo](https://zenodo.org/records/4922385) (CC BY-NC-ND 4.0).
8. [New ONRC number format (fiscalitatea.ro)](https://www.fiscalitatea.ro/onrc-informatii-privind-noul-format-a-numarului-de-ordine-din-registrul-comertului-23681/).
9. [python-stdnum `ro/onrc.py`](https://sources.debian.org/src/python-stdnum/2.2-1/stdnum/ro/onrc.py).
10. [SIRUTA tools and CSV (strainu/SIRUTA)](https://github.com/strainu/SIRUTA); [romania-geo-data](https://packagist.org/packages/gabrieldevro/romania-geo-data).
11. [Most common Romanian first names (DEPABD figures)](https://www.stiripesurse.ro/almost-two-million-romanians-celebrate-their-name-day-on-friday-st-johns-day_2176335.html).
12. Car contract model, Order 1069/2016, annex 2 (an official template) and private template collections: [e-juridic.manager.ro](https://e-juridic.manager.ro/modele-de-contracte-183.html), [incorpo.ro](https://www.incorpo.ro/articles/contracte-auto-vanzare-cumparare-comodat-si-inchiriere/).

## Probe files for this answer

- `probe_tab_misses.py`, `probe_tab_misses_medium.out`: TAB miss classes, entity recall, document leak rate.
- `probe_tab_partial.py`, `probe_tab_partial.out`: the visible piece of a partly hidden mention.
- `probe_mapa_ro_misses.out`: the MAPA-RO misses at `medium`.
- `probe_party_cues.py`, `probe_party_cues.out`: the party-cue prototype on the demo.
- From the first review: `probe_real_common*.out`, `probe_patterns.out`, `probe_restore.out`, `probe_docx*.out`.
