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
- It checks the output for known sensitive text (`verify`).
- It works from the command line (`lda`) and as a local HTTP API.

## How it works

1. **Read.** For a PDF, the tool joins the lines of each paragraph again, keeps the columns of a table apart with a tab, and removes page numbers and the headers and footers that repeat on many pages. A name must not be cut in two by a line break.
2. **Detect.** Presidio runs these recognizers:
   - Romanian text: the model [`dumitrescustefan/bert-base-romanian-ner`](https://huggingface.co/dumitrescustefan/bert-base-romanian-ner).
   - English text: the model [`dslim/bert-large-NER`](https://huggingface.co/dslim/bert-large-NER).
   - Patterns with checksums (CNP, CUI, IBAN), and patterns for e-mail, phone, address, case numbers, and UK company numbers and postcodes.
3. **Clean.** The tool removes titles and role words (`dl.`, `Reclamanta`, `BENEFICIAR`). They are not private, and the AI tool needs them. It also removes common words that the model marks as names (a word that the batch also writes in lowercase is not a name), list numbers (`2. S.C. Alfa S.R.L.`), and headings in capital letters.
4. **Sweep.** The tool looks in all documents of the batch for every known entity. It ignores case, accents, and spaces.
5. **Give ids.** The vault (a local SQLite file for one case) gives each entity an id. A new written form of a known entity gets the old id.
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

The folder `data/demo/` has a made-up case with five long PDF documents. A Romanian farm exporter (the client) sues its transport company for spoiled goods and late deliveries. The same client also settles a claim with a UK freight company.

| File | Content | Pages |
|---|---|---|
| `01_contract_transport.ro.pdf` | Transport contract with 15 articles, a tariff table, and a contact table | 6 |
| `02_notificare_punere_in_intarziere.ro.pdf` | Notice from the law firm, with a table of 17 late deliveries | 3 |
| `03_cerere_chemare_in_judecata.ro.pdf` | Court claim, with facts, legal grounds, evidence, and a calculation | 4 |
| `04_contract_asistenta_juridica.ro.pdf` | Engagement contract and power of attorney, with an ID card and a CNP | 3 |
| `05_settlement_agreement.en.pdf` | English settlement agreement with a UK company, with bank details | 5 |

The pages have a letterhead, numbered articles, tables, signature blocks, a running header, and page numbers. About 6,500 words in total.

```bash
python -m demo.run_demo            # all steps, about 25 seconds
python -m demo.run_demo --pause    # waits for Enter before each step (for a live demo)
```

The steps: (1) show the PDFs, (2) hide all five with one command, (3) show what the AI tool gets, (4) show that one entity has one id in all documents, and run `verify`, (5) change the contract like an AI tool does, (6) put the real data back, (7) join two written forms of one company with `merge`. The output goes to `demo-output/`.

To use a real AI tool in step 5, give it the folder `demo-output/hidden/` and the prompt in `data/demo/ai_prompt.md`. Save its text for the contract and run `python -m demo.run_demo --revised FILE.txt`. Set `HF_HUB_OFFLINE=1` to show that the models run with no network.

What to show and say:

- The documents are long and look like real ones. The tool reads the PDF text. It does not use the PDF properties.
- One command hides all documents. The client has the same id in the Romanian and in the English document.
- The tool finds people that nobody listed: the driver, the dispatcher, the buyer's manager, and the witness. The config file lists only the parties.
- The court and the laws stay visible, and so do amounts, dates, and article numbers. The config file decides this.
- `verify` finds no known text in the hidden files. After the AI step, the restore gives the real names back, also in the new clause.
- Say the limits: the tool does not find 100%, so read the hidden files. Say that the restored text has one written form for each entity, and that the vault is not encrypted.

To make the PDFs again, run `python -m demo.build`. The documents are test data. The articles of law that they name are real, but no lawyer has checked the documents. Ask the lawyer to read them before you call them examples of good drafting.

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

## The config file

The config file is optional. Use it to tell the tool about known entities, to keep some text visible, and to change what the tool hides. The file has real names. Keep it outside the folder that the AI tool can read.

```yaml
hide: [PERSON, ORGANIZATION, LOCATION, ADDRESS, DATE_TIME]  # default: all types except DATE_TIME, MONEY and NRP
keep: ["Tribunalul București", "ANAF"]   # never hide these texts
keep_public_bodies: true                  # do not hide courts, ministries, EU bodies (default: false)
min_score: 0.4                            # lower value = more recall, more false hits
en_model: dslim/bert-base-NER             # a smaller English model is 4 times faster
entities:                                 # known entities, hidden in every document
  - type: PERSON
    name: Ion Popescu                     # the name that the restore step writes
    aliases: [Popescu, dl. Popescu]
  - type: ORGANIZATION
    name: SC Alfa Construct SRL
    aliases: [Alfa Construct, Alfa]
```

Entity types: `PERSON ORGANIZATION LOCATION ADDRESS EMAIL_ADDRESS PHONE_NUMBER IBAN_CODE CREDIT_CARD URL IP_ADDRESS RO_CNP RO_CUI RO_TRADE_REG COMPANY_NUMBER ID_DOCUMENT CASE_NUMBER NRP DATE_TIME MONEY`.

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

There are 116 tests (94 of them run without the models, in under 1 second). They cover the patterns and checksums, the vault, the Word and PDF file handling, the restore step with changed ids, the multi-document rules, the CLI, the API, and two full runs with the real models: on the sample case and on the demo case. In the first run, none of 32 listed secrets stays in any output. In the second run, none of 57 listed secrets stays in the five PDFs, the client has the same id in all five documents, and no common word is hidden as a name.

The first run on the demo PDFs found problems that the short sample texts did not show: the model marked common words as names (`personal`, `poștal`, `jud`), date ranges were read as phone numbers, e-mail addresses with an unknown domain ending were not found, and the word sweep then spread each of these errors through all documents. The tests now guard against them.

**Detection quality.** The script `eval/mapa_eval.py` measures the detector on [MAPA](https://huggingface.co/datasets/joelniklaus/mapa), a set of EU legal texts with anonymization labels (CC-BY-4.0). It counts tokens. A token of a person, an organization, or an address counts as found if any span covers it, with any type. Tokens that the policy keeps on purpose (titles, role words, country names) do not count.

| Language | Model | Recall, any type | Persons | Organizations | Addresses |
|---|---|---|---|---|---|
| Romanian | `bert-base-romanian-ner` | **93.3%** (208 of 223 tokens) | 96.2% | 90.7% | 100% |
| English | `bert-large-NER` | **81.6%** (280 of 343 tokens) | 91.6% | 74.9% | 81.0% |

Before the last changes to the clean-up rules, I tested three English models on the same data: `bert-base-NER` gave 77.6%, `roberta-large-ner-english` gave 80.2%, and `bert-large-NER` gave 83.1%. `bert-large-NER` is about 4 times slower than `bert-base-NER`. Set `en_model` in the config file to change the model. The clean-up rules for the demo documents cost about one point of recall on MAPA (Romanian 93.7% to 93.3%, English 83.1% to 81.6%). The recall for persons did not fall.

The tool hides more than MAPA marks. For example, the Romanian set has 129 organization tokens in the labels, and the tool hides 792, because it hides all organizations by default. With `keep_public_bodies: true` it hides 367 (Romanian) and 390 (English). Recall does not change in Romanian and falls by 0.6 points in English. Choose the setting for your documents.

Read these numbers with care:

- The test set is small (one to two documents for each language, about 100 to 200 person tokens). The numbers show the size of the problem. They are not a guarantee.
- MAPA is EU case law. Your documents (contracts, letters) are different. The remaining misses on MAPA are mostly names of court cases (`CIF`, `Impact`) and public bodies (`the Czech Government`).
- **The models do not find 100%.** This is why the tool has the sweep, the config file, `verify`, and the rule "read the output".

To run the benchmark again, download `test.jsonl` and `validation.jsonl` from the dataset page into `eval/mapa_raw/`, and run `python eval/mapa_eval.py --lang ro` (or `--lang en`).

## Limits of the MVP

- **Detection is not perfect.** See above. Inflected Romanian names (`Popescului`) and names in unusual places can be missed or get their own id.
- **A short name is a new entity.** `Popescu` alone does not get the id of `Ion Popescu`, unless you add an alias or run `merge`. The tool does not guess, because a wrong guess puts the wrong name into a legal document.
- **Companies with different legal forms stay apart.** `Alfa SRL` and `Alfa SA` get two ids. `Alfa` alone is a third one. In the demo, `FreshMart Distribuție` and `FreshMart Distribuție S.R.L.` get two ids, and step 7 joins them with `lda merge`.
- **One written form comes back.** If an entity has several written forms (`POPESCU ION`, `Ion Popescu`), restore writes the name from the config file, or else the most common form. The restored text can differ from the original in these places. A short name that you list as an alias also comes back as the full name: `(Northgate)` becomes `(Northgate Freight Forwarding Ltd)`. The demo documents show this.
- **The AI tool can break an id.** The restore step accepts small changes. It does not accept an id with a Romanian ending (`[PERSON_001]ului`). Tell the AI tool to keep ids as they are, and to put the ending in a separate word.
- **A language for each file.** The tool detects `ro` or `en` for the whole file. Use `--lang` to force it. The patterns work in both languages.
- **File types.** A PDF needs a text layer. A scanned PDF gives an error (there is no OCR). A page without text in a mixed PDF gets a visible note in the output. No `.doc`: save it as `.docx`. The output for a PDF is a text file, not a PDF or a Word file. In `.docx`, the tool does not change images, embedded objects, field codes, or link targets. `verify` reports known text that it finds in them.
- **PDF layout.** The tool finds paragraphs again from the place of the lines. It works on the demo PDFs, which a PDF library made. Test it on your own PDFs before you trust it. Table cells can run together in one line, text boxes and columns can change the reading order, and a header or footer that repeats on many pages is removed (a header on the first page stays).
- **Dates and amounts stay visible** unless you add `DATE_TIME` or `MONEY` to `hide`. Facts that are not names can still identify a person. The tool does not look for vehicle plates, dates of birth (only the CNP), signatures, stamps, or photos.
- **Not tested in Word.** The tests check the file structure. No test opened the result in Microsoft Word or LibreOffice.
- **No encryption, no login, one user.** The vault is a plain file. The API is for one local user.

## Next steps

- Test GLiNER next to the two BERT models. Presidio 2.2.366 has a `GLiNERRecognizer` (it needs the `gliner` package).
- Add a small local LLM (for example Qwen3.5 through Ollama) as a checker. It reads the hidden text and lists the names that it still sees. The code finds these texts and hides them. The LLM never edits the document and never removes a hit. It must run on this computer.
- Add an encrypted vault, and a small web page where the lawyer sees and corrects the hidden items.
- Link short names to full names with a review step.
- Add OCR for scanned PDFs, and Word or PDF output for the final document.
- Measure on real, labeled legal documents from the firm.

## Data and licenses

- Romanian model: MIT (trained on RONEC). English model: MIT.
- PDF reader: `pdfminer.six` (MIT). The demo PDFs are made with `reportlab` (BSD, in the `dev` extras) and a serif font from your system (Times New Roman, Liberation Serif, or DejaVu Serif). The PDFs are in `data/demo/`, so you need neither to run the demo.
- Benchmark data: MAPA (CC-BY-4.0). The sample and demo documents are made up. All names are fictional, and the checksums are valid only in form. E-mail addresses use the reserved `.example` domain, and the UK phone number is in the range that Ofcom keeps for television drama.
- The Romanian legal NER set LegalNERo is CC-BY-NC-ND. It is not used here.
