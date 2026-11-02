# Legal document anonymizer (MVP)

This tool hides sensitive data in Romanian and English legal documents. It puts an id in place of each name, number, and address. You can then give the hidden documents to an AI tool (Claude Code, Codex, Copilot). When the AI tool finishes, the tool puts the real data back.

```
 original documents ──► lda anonymize ──► hidden documents ──► AI tool ──► revised hidden documents
        │                    │                                                      │
        │                    ▼                                                      ▼
        │                  vault  ◄──────────────────────────────────────────  lda restore
        │          (real data + ids,                                      (real data in the
        │           stays on your computer)                                final documents)
```

Example. The original text is:

> reprezentată legal de dl. Ion Popescu, CNP 1750418401237, telefon 0722 123 456

The AI tool gets:

> reprezentată legal de dl. [PERSON_001], CNP [CNP_001], telefon [PHONE_001]

## What the MVP does

- It finds people, companies, places, addresses, e-mails, phone numbers, IBANs, Romanian CNP, CUI, ID card and trade register numbers, court case numbers, and more.
- One entity has one id in all documents of a case. `Ion Popescu`, `POPESCU ION`, and `dl. Popescu` get the same id.
- It reads `.txt`, `.md`, `.docx`, and PDF files that have a text layer. For `.docx` it also processes tracked changes, headers, footers, footnotes, comments, tables, and text boxes. It removes author names from the metadata.
- For a PDF it reads only the text. So the PDF properties (author, title) never reach the output. The output for a PDF is a text file, because an AI tool cannot edit a PDF.
- It finds a known name again in all documents, also where the model missed it (the "sweep").
- It knows the Romanian forms of a name. `Popescului`, `Popeștii`, `Mariei`, and `Brașovului` are found by the sweep, and they get the id of `Popescu`, `Maria`, and `Brașov`.
- It checks the output for known sensitive text (`verify`).
- It works from the command line (`lda`) and as a local HTTP API.

## How it works

1. **Read.** For a PDF, the tool joins the lines of each paragraph again, keeps the columns of a table apart with a tab, and removes page numbers and the headers and footers that repeat on many pages. A name must not be cut in two by a line break.
2. **Detect.** Presidio runs these recognizers:
   - Romanian text: the model [`dumitrescustefan/bert-base-romanian-ner`](https://huggingface.co/dumitrescustefan/bert-base-romanian-ner).
   - English text: the model [`dslim/bert-large-NER`](https://huggingface.co/dslim/bert-large-NER).
   - Patterns with checksums (CNP, CUI, IBAN), and patterns for e-mail, phone, address, case numbers, and UK company numbers and postcodes.
   - Level `medium` and `high`: the zero-shot model [GLiNER](https://huggingface.co/urchade/gliner_multi_pii-v1) finds more names (see "Levels").
   - Level `high`: a small LLM on your computer (through Ollama) reads the hidden text and lists the names that remain (see "Levels").
3. **Clean.** The tool removes titles and role words (`dl.`, `Reclamanta`, `BENEFICIAR`). They are not private, and the AI tool needs them. It also removes common words that the model marks as names (a word that the batch also writes in lowercase is not a name), list numbers (`2. S.C. Alfa S.R.L.`), and headings in capital letters.
4. **Sweep.** The tool looks in all documents of the batch for every known entity. It ignores case, accents, and spaces. For a person or a place it also looks for the Romanian forms of each word: the article (`Popescul`), the genitive and dative (`Popescului`, `Mariei`, `Brașovului`), the vocative (`Popescule`), and the family (`Popeștii`). The rules are in `src/legal_anonymizer/romanian.py`. They do not stem: `Pop` and `Popa` stay two names.
5. **Give ids.** The vault (a local SQLite file for one case) gives each entity an id. A new written form of a known entity gets the old id. This includes a Romanian form that a rule makes from a known name. The restore step writes the base form (see the limits).
6. **Write and check.** The tool writes the new file and looks in it for known text.
7. **Restore.** `lda restore` finds the ids in a revised document and puts the real text back. It accepts small changes by the AI tool, for example `[PERSON_1]`, `[ person_001 ]`, or `\[PERSON\_001\]`.

## Install

You need Python 3.11 or newer.

```bash
cd legal-docs-anonymizer
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/lda setup        # downloads the models (about 1.7 GB), one time
```

The `dev` extras also install `reportlab`. Only the tests and the demo builder need it.

For the levels `medium` and `high` (see "Levels"), install GLiNER too, and for `high` install [Ollama](https://ollama.com) and pull a model:

```bash
.venv/bin/pip install -e ".[gliner]"       # GLiNER. It needs transformers 4.x, not 5.x.
.venv/bin/lda setup --level medium         # downloads GLiNER too (about 1 GB)
ollama pull qwen3.5:4b                     # only for level high
```

After this step, the tool works without a network. Document text never goes to a network at any time: the models run on your computer. To make sure that the tool does not even contact the model hub, set `HF_HUB_OFFLINE=1`.

## Quick start

The folder `data/samples/` has a made-up case: three text files and one Word file. Run `python tests/samples.py` to make them again.

```bash
# 1. Hide the data. One vault for each case (--matter).
lda anonymize data/samples/0*.txt data/samples/04*.docx \
    --matter demo --config data/samples/matter.yaml --out anonymized

# 2. Look at what the tool hid. This output has real data. Do not share it.
lda entities --matter demo

# 3. Give the folder "anonymized/" to your AI tool. Ask it to revise the documents.
#    It must keep the ids (for example [PERSON_001]) as they are.

# 4. Put the real data back.
lda restore anonymized/*.anon.txt --matter demo --out restored
```

## Demo for a lawyer

The demo has a made-up case with five long documents (four Romanian, one English, about 6,500 words). A Romanian farm exporter (the client) sues its transport company for spoiled goods and late deliveries. The same client also settles a claim with a UK freight company. The pages have a letterhead, numbered articles, tables, signature blocks, a running header, and page numbers. All people and companies are made up.

### Word files

A lawyer works in Word, so the best demo uses `.docx` files. For a `.docx` file the tool changes only the text. The styles, tables, headers, footers, and tracked changes stay. The hidden file looks like the original, and the restored file is a Word file again.

```bash
python -m demo.run_docx      # about 30 seconds (the first run loads the models)
```

The script makes the five documents as Word files (real styles such as Title, Heading 1, and Clause; real tables; a header from page 2; page numbers as fields). It writes two cases to `demo-docx/`:

| Case | Documents |
|---|---|
| `single-file/` | The transport contract. |
| `multi-file/` | All five documents, hidden together. The client has the same id in all of them. |

Each case has three folders:

| Folder | Content |
|---|---|
| `1-original/` | The Word files as the lawyer has them. |
| `2-anonymized/` | The files for the AI tool: the same files, with ids in place of the sensitive data. |
| `3-restored/` | The files after the AI tool changed them and the tool put the real data back. |

The AI step is a simulation. The script `demo/docx_edit.py` works on the anonymized files like an AI tool does. In the contract it changes two figures and adds a clause. In the notice it adds a paragraph. In the settlement it shortens a time limit and adds a clause. The changes are Word tracked changes by "AI assistant", and the new text has ids. Open a restored file in Word to see the changes in red, with the real names in the new text. The claim and the engagement contract have no change, so they come back as they were. The folder `demo-docx/_work/` has the vault (the real data) and the files that the simulated AI tool made.

The Word demo shows these points:

- The hidden file keeps the layout. Only the sensitive text is different.
- The tool also hides data in the header, the footer, and the table cells, and it removes the author from the file properties.
- The ids that the AI tool writes in a tracked change come back as real names, and the change stays a tracked change.
- In `multi-file/`, one entity has one id in all five files.

Limits of the Word demo:

- No real AI tool edited a `.docx` file in this project. The simulation changes the text in the way that Word does it. A real tool can do it in another way. It must keep the ids as they are.
- Restore gives one written form for each entity. In the demo, a header with `Rusu și Asociații` comes back as `Societatea Civilă de Avocați Rusu și Asociații`, and `S.C. CARPATICA LOGISTIC SOLUTIONS S.A.` comes back as `Carpatica Logistic Solutions S.A.`.
- The tool removes the author and the title from the file properties. Restore does not bring them back.
- The files pass an XML schema check, and a Mac preview shows them well. Nobody opened them in Microsoft Word or LibreOffice yet, so open them in Word before you show them. (The Mac preview ignores page breaks and some tab positions. This is a limit of the preview, not of the files.)

### PDF files

The folder `data/demo/` also has the five documents as PDF files. They show the PDF input of the tool.

| File | Content | Pages |
|---|---|---|
| `01_contract_transport.ro.pdf` | Transport contract with 15 articles, a tariff table, and a contact table | 6 |
| `02_notificare_punere_in_intarziere.ro.pdf` | Notice from the law firm, with a table of 17 late deliveries | 3 |
| `03_cerere_chemare_in_judecata.ro.pdf` | Court claim, with facts, legal grounds, evidence, and a calculation | 4 |
| `04_contract_asistenta_juridica.ro.pdf` | Engagement contract and power of attorney, with an ID card and a CNP | 3 |
| `05_settlement_agreement.en.pdf` | English settlement agreement with a UK company, with bank details | 5 |

```bash
python -m demo.run_demo            # all steps, about 25 seconds
python -m demo.run_demo --pause    # waits for Enter before each step (for a live demo)
```

The steps: (1) show the PDFs, (2) hide all five with one command, (3) show what the AI tool gets, (4) show that one entity has one id in all documents, and run `verify`, (5) change the contract like an AI tool does, (6) put the real data back, (7) join two written forms of one company with `merge`. The output goes to `demo-output/`.

Each output file is a text file, because an AI tool can edit text but not a PDF. The demo also writes a PDF copy of each text file, for people to look at (`demo/render_pdf.py`). In the PDF copy, each id has a yellow background. In `ai/`, the paragraphs that the AI tool changed are green. In `final/`, the PDF has the real names and no banner. A PDF copy has the same words as the text file. It does not have the layout of the original PDF. Give the AI tool the `.txt` files. To make PDF copies of other text files, run `python -m demo.render_pdf FILE.txt` (add `--restored` for a text with real data).

To use a real AI tool in step 5, give it the folder `demo-output/hidden/` and the prompt in `data/demo/ai_prompt.md`. Save its text for the contract and run `python -m demo.run_demo --revised FILE.txt`. Set `HF_HUB_OFFLINE=1` to show that the models run with no network.

What to show and say:

- The documents are long and look like real ones. The tool reads the PDF text. It does not use the PDF properties.
- One command hides all documents. The client has the same id in the Romanian and in the English document.
- The tool finds people that nobody listed: the driver, the dispatcher, the buyer's manager, and the witness. The config file lists only the parties.
- The court and the laws stay visible, and so do amounts, dates, and article numbers. The config file decides this.
- `verify` finds no known text in the hidden files. After the AI step, the restore gives the real names back, also in the new clause.
- Say the limits: the tool does not find 100%, so read the hidden files. Say that the restored text has one written form for each entity, and that the vault is not encrypted.

To make the PDFs again, run `python -m demo.build`. The Word demo makes its own Word files each time. The documents are test data. The articles of law that they name are real, but no lawyer has checked the documents. Ask the lawyer to read them before you call them examples of good drafting.

Other commands:

| Command | Use |
|---|---|
| `lda text FILES` | Show the text that the tool reads from a file. For a PDF, you see the paragraphs after the lines are joined. |
| `lda verify FILES -m CASE` | Look for known sensitive text in files. Exit code 1 if it finds any. |
| `lda merge PERSON_003 PERSON_001 -m CASE` | Say that two ids are one entity. Old documents still restore. |
| `lda alias PERSON_001 "dl. Popescu" -m CASE` | Add another name to an entity. |
| `lda entities -m CASE --json` | Show all entities as JSON. |
| `lda serve` | Start the local API on `127.0.0.1:8000`. |

`--home DIR` (or the variable `LDA_HOME`) sets the folder for the vaults. The default is `~/.legal-anonymizer`.

## Levels

A level says how hard the tool looks for names. A higher level finds more, and is slower.

| Level | What runs | Cost | Status |
|---|---|---|---|
| `low` (default) | patterns + the BERT models | the fastest | measured |
| `medium` | + GLiNER, a second model that adds hits | 2 times slower in English, 4 times in Romanian, about 1 GB more | measured |
| `high` | + a local LLM that reads the hidden text and lists the names that remain | the slowest (an LLM call for each 1,500 characters) | measured with Qwen3.5: **no useful gain, experimental** |

Choose the level with `--level` (`lda anonymize --level medium ...`) or with `level:` in the config file. On the test sets, `medium` raises the recall on English text a lot (see "Tests and results"). On Romanian text the gain is too small to measure, so `low` stays the default until we test on real Romanian documents.

**Level `high` did not pay off.** We measured Qwen3.5 in four sizes (0.8b, 2b, 4b, 9b) on the four test sets. In 14 comparisons with level `medium`, the LLM found a name that the models had missed in only two (3 and 4 tokens). It always hid other text as well (up to 368 tokens), and the F2 score never went up. The extra hits are nationalities, dates, currencies and legal references, not missed names (see `docs/experiments.md`, EXP-006). Use `medium`. The LLM can still help on messy real contracts, which we have not tested.

The LLM never edits the document and never removes a hit. It gets the text after hiding (tags in place of the data), and it returns a list of words. The tool accepts a word only if the word is really in that text. The LLM host must be on your computer (`127.0.0.1` or `localhost`). The tool refuses any other host, so the text cannot leave the computer. If a level cannot run (no GLiNER, no Ollama, no model), the tool stops with a clear message. It never goes to a lower level without telling you.

## The config file

The config file is optional. Use it to tell the tool about known entities, to keep some text visible, and to change what the tool hides. The file has real names. Keep it outside the folder that the AI tool can read.

```yaml
hide: [PERSON, ORGANIZATION, LOCATION, ADDRESS, DATE_TIME, JOB_TITLE]  # default: all types except DATE_TIME, JOB_TITLE, MONEY and NRP
keep: ["Tribunalul București", "ANAF"]   # never hide these texts
keep_public_bodies: true                  # do not hide courts, ministries, EU bodies (default: false)
min_score: 0.4                            # lower value = more recall, more false hits
level: low                                # low | medium | high (see "Levels")
gliner_model: urchade/gliner_multi_pii-v1 # medium and high. A GLiNER2 model (name with "gliner2") also works
gliner_threshold: 0.5                     # minimum GLiNER score
llm_model: qwen3.5:4b                     # high. The model must be in Ollama
llm_host: http://127.0.0.1:11434          # high. Only a host on this computer is accepted
en_model: dslim/bert-base-NER             # a smaller English model is 4 times faster
entities:                                 # known entities, hidden in every document
  - type: PERSON
    name: Ion Popescu                     # the name that the restore step writes
    aliases: [Popescu, dl. Popescu]
  - type: ORGANIZATION
    name: SC Alfa Construct SRL
    aliases: [Alfa Construct, Alfa]
```

Entity types: `PERSON ORGANIZATION LOCATION ADDRESS EMAIL_ADDRESS PHONE_NUMBER IBAN_CODE CREDIT_CARD URL IP_ADDRESS RO_CNP RO_CUI RO_TRADE_REG COMPANY_NUMBER ID_DOCUMENT CASE_NUMBER NRP DATE_TIME JOB_TITLE MONEY`.

`DATE_TIME` and `JOB_TITLE` are off by default. They are facts that can identify a person (a date of birth, "the general director of Alfa"), but an AI tool needs them: it cannot work out `30 days after [DATE_001]`. Turn them on with `hide:` in the config file or with `--hide`. `DATE_TIME` hides a calendar date only: `12.03.2024`, `2024-03-12`, `12 martie 2025`, `12th of March 2025`, `March 12, 2025`, `martie 2025`. A duration (`30 de zile`), a bare year (`anul 2024`), and a clause number (`4.1.10`) stay visible. `JOB_TITLE` comes from a list of Romanian and English occupations with their forms (`Directorul general`, `avocatul`, `Chief Executive Officer`, `Head of Sales`). A party role (`Vânzătorul`, `Beneficiarul`) is not a job title and stays visible.

`NRP` (nationality, religion, political group) is off by default. In legal text the model finds mostly words such as `român` in `societate de drept român`. Add `NRP` to `hide` if your documents describe people in this way.

Text that the policy keeps visible (a court, a country, a word in `keep`) also protects the words inside it. The `Mureș` in `Tribunalul Mureș` stays visible, also when `Mureș` is hidden in other places. `verify` does not count such text as a leak.

## Local API

```bash
lda serve
curl -F files=@contract.docx -F config=@matter.yaml localhost:8000/matters/demo/anonymize
curl -F files=@contract.anon.docx localhost:8000/matters/demo/restore
curl localhost:8000/matters/demo/entities
```

The API returns JSON. Each document has `content_base64`, and text files also have `text`. The API also accepts PDF files. The result for a PDF is text. The API listens on `127.0.0.1` only and has no login. Do not open it to a network.

## Privacy rules for the lawyer

1. **The vault is the key.** It holds the real data and the ids in plain text. The tool sets the file mode to `0600`. Use disk encryption (FileVault, BitLocker).
2. **Keep the AI tool away from the real files.** Make one folder for the AI tool, and put only the hidden documents in it. The original files, the vault, the config file, and the output of `lda entities` must stay outside this folder.
3. **Read the output before you use it.** The tool cannot find all sensitive data (see the limits). Read the first hidden documents of a case. Add missing names to the config file and run again.
4. **This is pseudonymization.** The vault can reverse it, so the law can still treat the hidden documents as personal data. It reduces risk. It does not remove the duty to protect the data. Ask your data protection officer.

## Tests and results

```bash
.venv/bin/python -m pytest                 # all tests (the first run downloads the models)
.venv/bin/python -m pytest -m "not models" # fast tests, no models, under 1 second
```

There are 342 tests (308 of them run without the models). They cover the patterns and checksums, the Romanian word forms of names, the dates and job titles, the vault, the Word and PDF file handling, the restore step with changed ids, the multi-document rules, the CLI, the API, the simulated AI edits with tracked changes, the GLiNER recognizer, the LLM checker (against a fake Ollama server, so no LLM is needed), the evaluation tools, and full runs with the real models: on the sample case, on the five demo PDFs, and on the five demo Word files. In the first run, none of 32 listed secrets stays in any output. In the other two runs, none of 57 listed secrets stays in the five files, the client has the same id in all five documents, and no common word is hidden as a name. For the Word files the tests also check that the layout, the styles, and the table rows stay, and that the author name is gone from the file properties, the headers, and the footers.

The first run on the demo PDFs found problems that the short sample texts did not show: the model marked common words as names (`personal`, `poștal`, `jud`), date ranges were read as phone numbers, e-mail addresses with an unknown domain ending were not found, and the word sweep then spread each of these errors through all documents. The tests now guard against them. The Word demo found one more: in a running header such as `Alfa S.R.L. / Beta S.A.`, the model put the `/` into the first name, and restore lost the slash. The clean-up now removes separators (`/`, `|`, dashes) at the edge of a name.

**Detection quality.** Two scripts measure it, and every run writes a result file (settings, package versions, time, metrics) to `eval/results/`. The notes about what we tried and decided are in [`docs/experiments.md`](docs/experiments.md). The table of all runs is in [`docs/results.md`](docs/results.md). We write recall, precision, F1, and F2. Recall decides: a missed name is a leak, and a false hit only makes the text harder to read. F2 counts recall twice as much as precision.

- `eval/mapa_eval.py` counts tokens on [MAPA](https://huggingface.co/datasets/joelniklaus/mapa), EU case law with anonymization labels (CC-BY-4.0). A token of a person, an organization, or an address counts as found if any span covers it, with any type. Tokens that the policy keeps on purpose (titles, role words, country names) do not count.
- `eval/hits_report.py` runs the pipeline on a folder with no gold list and shows the hits for each 1,000 words and the most common hidden strings. We use it on 40 real Romanian legal acts (`eval/ro_law_corpus.py`). It cannot measure recall. It finds over-hiding (for example `României` hidden as a place) and shows that the tool finds the people in decrees and decisions.
- `docs/agent-test/` has the test of a real AI tool (a subagent) on hidden Word files: the prompt, the agent's report, its output files, and our checks.
- `eval/corpus_eval.py` runs the whole pipeline (hide all documents together, then restore) on a folder of documents with a `gold.json` list of entities. It measures the mentions that the tool hides completely, the false hits (it writes them to a review file), the ids of one entity across documents, leaks in the output file, and how much of the text comes back unchanged. See the top of the file for the format. `python -m eval.tab_corpus` makes an English test corpus of 12 real court cases from [TAB](https://github.com/NorskRegnesentral/text-anonymization-benchmark) (MIT).

Recall of the mentions that the tool should hide:

| Test set | `low` (BERT) | `medium` (+ GLiNER) |
|---|---|---|
| MAPA Romanian (3 documents, 223 tokens) | 93.3% | 94.2% |
| MAPA English (3 documents, 343 tokens) | 81.6% | **93.3%** |
| TAB English (12 court cases, 468 mentions) | 80.3% | **86.3%** |
| Demo documents (5 made-up PDFs, 241 mentions) | 99.2% | 99.6% |

On English text, GLiNER adds 6 to 12 points of recall for the price of twice the run time. On the Romanian MAPA text it adds 2 tokens, which is within the noise of a 3-document test. The persons in MAPA English go from 91.6% to 94.7%, and the organizations from 74.9% to 93.2%. The newer model GLiNER2-PII (`fastino/gliner2-privacy-filter-PII-multi`) is worse than GLiNER: it has no label for organizations, and its model card does not list Romanian.

Before the latest changes, I tested three English models on MAPA: `bert-base-NER` gave 77.6%, `roberta-large-ner-english` gave 80.2%, and `bert-large-NER` gave 83.1%. `bert-large-NER` is about 4 times slower than `bert-base-NER`. Set `en_model` in the config file to change the model.

The tool hides more than MAPA marks. For example, the Romanian set has 129 organization tokens in the labels, and the tool hides 790, because it hides all organizations by default. With `keep_public_bodies: true` it hides fewer. Choose the setting for your documents. The precision on MAPA is a lower bound for this reason.

Read these numbers with care:

- **No test set is a Romanian contract with real names.** There is no open set like that. The Romanian numbers come from 3 documents of EU case law (one point is 2 tokens) and from made-up documents that we wrote ourselves. The 10 to 15 real documents of the lawyer are the missing test.
- TAB is English court cases, not contracts. MAPA is EU case law. Your documents are different. The misses that remain on MAPA are mostly names of court cases and public bodies. On TAB they are mostly public bodies and case numbers (`36110/97`, 0 of 17 found).
- The test sets are small. The numbers show the size of the problem. They are not a guarantee.
- **The models do not find 100%.** This is why the tool has the sweep, the config file, `verify`, and the rule "read the output".

To run the benchmarks again:

```bash
# MAPA: download test.jsonl and validation.jsonl from the dataset page into eval/mapa_raw/
.venv/bin/python -m eval.mapa_eval --lang en --level medium --name bert+gliner

# TAB: download echr_test.json from the TAB repository into eval/tab_raw/
.venv/bin/python -m eval.tab_corpus --count 12
.venv/bin/python -m eval.corpus_eval eval/corpora/tab-en --level medium --name bert+gliner

# Romanian legal acts (no gold list: it counts the hits and shows the most common hidden strings)
# 1. In a separate environment (pyarrow is not a dependency; the file is untrusted data):
#    python -I eval/ro_law_corpus.py documents.parquet --per-type 5    # documents.parquet: release of scriptogre/romanian-law-data
# 2. .venv/bin/python -m eval.hits_report eval/corpora/ro-law --level low

# your own documents: a folder with the files and a gold.json (see eval/corpus_eval.py)
.venv/bin/python -m eval.corpus_eval path/to/folder --level high --llm-model qwen3.5:4b --name bert+gliner+qwen3.5-4b

.venv/bin/python -m eval.report            # makes docs/results.md from eval/results/
```

The review files that `corpus_eval` writes (`_review/`) contain real text from the documents. They are in `.gitignore`. Keep your own test documents outside git too (`eval/corpora/private/` is ignored).

## Limits of the MVP

- **Detection is not perfect.** See above. The sweep knows the Romanian forms of a known name (`Popescului`, `Mariei`, `Brașovului`). It does not know a surname alone after the full name (`Popescu` after `Ion Popescu`), an initial (`I. Popescu`), or a form with a stem change that has no rule. A model can still miss a name in an unusual place.
- **A short name is a new entity.** `Popescu` alone does not get the id of `Ion Popescu`, unless you add an alias or run `merge`. The tool does not guess, because a wrong guess puts the wrong name into a legal document.
- **Companies with different legal forms stay apart.** `Alfa SRL` and `Alfa SA` get two ids. `Alfa` alone is a third one. In the demo, `FreshMart Distribuție` and `FreshMart Distribuție S.R.L.` get two ids, and step 7 joins them with `lda merge`.
- **One written form comes back.** If an entity has several written forms (`POPESCU ION`, `Ion Popescu`, `Popescului`), restore writes the name from the config file, or else the most common base form. The restored text can differ from the original in these places. In the test with a real AI tool, `S.C. CARPATICA LOGISTIC SOLUTIONS S.A.` came back as `Carpatica Logistic Solutions S.A.`. A short name that you list as an alias also comes back as the full name: `(Northgate)` becomes `(Northgate Freight Forwarding Ltd)`. The demo documents show this.
- **The AI tool can break an id.** The restore step accepts small changes. It does not accept an id with a Romanian ending (`[PERSON_001]ului`). Tell the AI tool to keep ids as they are, and to put the ending in a separate word. In one test (`docs/agent-test/`), a subagent with these rules kept all 110 ids in three files, and all 110 were restored. That is one agent, one run, and one prompt with the rules: test a plain prompt and other tools before you trust it.
- **A language for each file.** The tool detects `ro` or `en` for the whole file. Use `--lang` to force it. The patterns work in both languages.
- **File types.** A PDF needs a text layer. A scanned PDF gives an error (there is no OCR). A page without text in a mixed PDF gets a visible note in the output. No `.doc`: save it as `.docx`. The output for a PDF is a text file, not a PDF or a Word file. In `.docx`, the tool does not change images, embedded objects, field codes, or link targets. `verify` reports known text that it finds in them.
- **PDF layout.** The tool finds paragraphs again from the place of the lines. It works on the demo PDFs, which a PDF library made. Test it on your own PDFs before you trust it. Table cells can run together in one line, text boxes and columns can change the reading order, and a header or footer that repeats on many pages is removed (a header on the first page stays).
- **Dates, job titles, and amounts stay visible** unless you add `DATE_TIME`, `JOB_TITLE`, or `MONEY` to `hide`. Hidden dates stop an AI tool from working out deadlines. Facts that are not names can still identify a person. The tool does not look for vehicle plates, dates of birth (only the CNP), signatures, stamps, or photos.
- **Not tested in Word.** The tests check the file structure, and the demo files pass an XML schema check. No test opened the result in Microsoft Word or LibreOffice.
- **File properties.** For `.docx`, the tool removes the author, the title, and similar fields from the file properties of the hidden file. Restore does not bring them back.
- **Levels `medium` and `high` cost time and memory.** GLiNER makes the run 2 to 4 times slower and needs about 1 GB more. The LLM of level `high` needs Ollama and a model of 1 to 8 GB. All times in this file are from one Apple M1 Pro with 16 GB.
- **Level `high` is experimental.** Measured with Qwen3.5, it adds at most 4 tokens of recall and a lot of noise (see "Levels"). Ollama cannot force a JSON reply for Qwen3.5 (HTTP 501), so the tool asks for JSON in the prompt and reads the reply with care. A small model can repeat itself without end: the reply is limited, and a piece that times out is skipped with a warning.
- **No encryption, no login, one user.** The vault is a plain file. The API is for one local user.

## Next steps

The list with reasons and the open questions is in [`docs/experiments.md`](docs/experiments.md).

- Improve level `high` or drop it: filter the noise (nationalities, dates, currencies), test a prompt with examples, and test on the Romanian documents of the lawyer (LDA-28).
- Build the Romanian test set: 10 to 15 real documents of the firm, with a gold list. It decides the default level for Romanian.
- Test more AI tools (Claude Code, Codex, Copilot) and a plain prompt without the rules for ids. One subagent test is done (`docs/agent-test/`).
- Add an encrypted vault, and a small web page where the lawyer sees and corrects the hidden items.
- Link short names to full names with a review step (a surname alone, an initial). Restore each name in the form that the document had.
- Add OCR for scanned PDFs, and Word or PDF output for the final document.

## Data and licenses

- Romanian model: MIT (trained on RONEC). English model: MIT. GLiNER model `urchade/gliner_multi_pii-v1`: Apache-2.0. GLiNER2 model `fastino/gliner2-privacy-filter-PII-multi`: Apache-2.0. Qwen3.5 models: Apache-2.0 (check the license of the model that you choose in Ollama).
- PDF reader: `pdfminer.six` (MIT). The demo PDFs are made with `reportlab` (BSD, in the `dev` extras) and a serif font from your system (Times New Roman, Liberation Serif, or DejaVu Serif). The PDFs are in `data/demo/`, so you need neither to run the demo.
- Benchmark data: MAPA (CC-BY-4.0). TAB court cases (MIT): the script `eval/tab_corpus.py` makes the test corpus from the file that you download; the cases are not in this repository. The sample and demo documents are made up. All names are fictional, and the checksums are valid only in form. E-mail addresses use the reserved `.example` domain, and the UK phone number is in the range that Ofcom keeps for television drama.
- The Romanian legal NER set LegalNERo is CC-BY-NC-ND. It is not used here.
- Romanian legal acts for `eval/hits_report.py`: the export of legislatie.just.ro by [`scriptogre/romanian-law-data`](https://github.com/scriptogre/romanian-law-data) (the repository states no license). Romanian legislation is, as far as we know, outside copyright (Law 8/1996, art. 9): confirm this before you publish anything. The acts are not in this repository.
