# Test of a real AI tool on hidden Word files

Date: 2026-11-02. Ticket: LDA-19. Files in this folder:

| File | What it is |
|---|---|
| `prompt.md` | The prompt that the subagent got (the rules for ids, three tasks, a report). |
| `agent-report.md` | The final report of the subagent, word for word. It is the agent's claim. |
| `output/` | The three files that the agent made. They have ids and no real data. |
| `result.md` | This file: what we checked, and what we found. |

## The question

In the demo, a script plays the AI tool. A script never breaks an id. Does a real agent keep the ids when it edits
a hidden Word file, and does the restore bring back the real data?

## Setup

1. We hid the five demo Word files with the current code (`lda anonymize`, level `low`, `data/demo/matter.yaml`).
2. We gave three hidden files and the prompt to one subagent (`general-purpose`, the default model). The agent got no vault, no
   original file, and no config file. The prompt told it to read only the work folder and to write only the output folder.
   The harness does not enforce this (see "Limits").
3. The tasks were the work of a lawyer: change a contract and add an article (Word, Romanian), write a cover e-mail
   (Romanian), write a one-page summary of a settlement (English).
4. We did not trust the report. We counted the ids in each output file, looked for ids with another form or with
   a suffix, looked for ids that the vault does not know, restored the files, and compared the result with the original.
   The checker is a short script that we ran in the scratch folder, not part of the project.

## Result

| Check | Result |
|---|---|
| Ids in the revised contract | 73 ids, 32 different. The same 32 ids as in the input; no id lost, none added, no count changed. |
| Ids in the cover e-mail / the summary | 20 (10 different) / 17 (8 different). |
| An id with another form (`[PERSON_1]`, `[PERSON 001]`, lower case) | 0 |
| A Romanian ending or a letter stuck to an id (`[ORG_001]ului`) | 0. The agent put the case on the word before the id (`societății [ORG_001]`, `dl. [PERSON_001]`). |
| An invented id (not in the vault) | 0 |
| Restore | 110 of 110 ids restored. 0 unknown. 0 ids left in the files. |
| The requested changes in the contract | Done: `0,5%` to `0,7%`, `20%` to `25%`, a new article with three clauses. |
| Format of the revised contract | The 84 paragraphs that did not change keep the same style, alignment and run format. 3 tables and 1 section as before. The new paragraphs use `Heading 1`, `Clause`, `Sub-clause` of the document. |
| Other text that changed after the restore | Two company names (below). |

## What we found

1. **With the rules in the prompt, the ids survived.** The rule "if a Romanian word needs an ending, write the ending in a separate word"
   worked: the agent did not write one ending after an id, and it told us where the case was hard.
2. **The restore changes the written form of a company name.** `S.C. CARPATICA LOGISTIC SOLUTIONS S.A.` came back as
   `Carpatica Logistic Solutions S.A.`, and `S.C. MUREȘUL AGRO TRANS S.R.L.` as `Mureșul Agro Trans S.R.L.`. The restore writes the name from the
   config file, not the form the document had (the `S.C.` and the capital letters are lost). This is the known limit "one written form comes back".
   It is now seen in a real run, and it is not only a Romanian-ending problem. It is in ticket LDA-21.
3. **The agent found a legal point that we did not ask for.** The notice (file 02) uses the old terms of Article 9.2 (0,5% and 20%).
   The signed contract needs an `act adițional` to change them. This is useful, and it is the agent's opinion, not a check.
4. **The agent made choices without us.** It numbered the new article `9¹`, so that Articles 10 to 15 and their references stay as they are.
   It guessed who the client is in the summary, and it computed dates and a total. A lawyer must read these. It said so in its report.

## Limits of this test

- **One agent, one model, one run, one prompt.** The prompt had the rules for ids. A lawyer may write a short prompt without them. The next test must
  run the same tasks with a plain prompt, and with other tools (Codex, Copilot).
- **No enforced boundary.** The harness gave the agent all its tools. It reported that it read nothing outside the work folder and wrote one helper script
  outside the output folder, which it deleted. We checked that nothing was written outside `out/` and that the vault did not change. We cannot check what it read.
- **The agent did not see the real names.** This is the point of the tool. It also means that the agent could not use the real names (a vocative form,
  for example `Stimate domnule [PERSON_002]`). The restore gives the base name in this place.
- **The summary page was not opened in Word.** The agent could not render it, and we did not open it in Word either.
- **The data is made up.** The demo files are written by us. A real contract can be longer, with more styles, comments and tracked changes.
  The tracked changes are covered by the tests of the project, and not by this run.

## How to repeat it

```bash
python -m demo.run_docx                    # makes the five Word files in demo-docx/
export LDA_HOME=/path/to/scratch/home
lda anonymize demo-docx/multi-file/1-original/*.docx --matter agentcase --config data/demo/matter.yaml --out hidden/
# give the agent only hidden/ and prompt.md; then:
lda restore out/*.docx --matter agentcase --out restored/
```
