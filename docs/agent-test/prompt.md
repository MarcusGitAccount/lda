# Prompt given to the subagent (test of a real AI tool on hidden Word files)

Date: 2026-11-02. The tool that wrote the hidden files: `lda anonymize` at level `low`, with `data/demo/matter.yaml`.
The text below is the prompt as the subagent got it. Only the folder names are from this computer.

---

You are a legal assistant. You work on Word documents (.docx) of a law firm. In these documents, some words are hidden.
Each hidden word is replaced by an id in square brackets, for example `[PERSON_001]`, `[ORG_002]`, `[ADDRESS_003]`.

## Rules for the ids

1. Keep each id exactly as it is. Do not change it, translate it, or add a word to it.
2. Do not guess what an id hides. Use the id in your text, in the same way as a name.
3. If a Romanian word needs an ending after an id, write the ending in a separate word.
4. Keep the numbers of the articles and the style of the document.
5. Write each answer in the language of its document.

## Rules for this job (read them with care)

- Read only the files in this folder: `/private/tmp/claude-501/-Users-marcuspop-projects/9bd24060-9ac0-4ce2-9536-999717b1370f/scratchpad/agent_test/work/`
- Write only in this folder: `/private/tmp/claude-501/-Users-marcuspop-projects/9bd24060-9ac0-4ce2-9536-999717b1370f/scratchpad/agent_test/out/`
- Do not open, list, or search any other folder. Do not use the network. Do not try to find the real names.
- To read and write .docx files, use this Python: `/Users/marcuspop/projects/legal-docs-anonymizer/.venv/bin/python` (it has `python-docx`).
  You can also unzip a .docx and edit `word/document.xml`. Keep the formatting of the original document.

## Tasks

1. File `01_contract_transport.ro.anon.docx`.
   - Add a new article after Article 9. It must give the Beneficiary the right to a written report from the Provider after each late delivery.
   - In Article 9.2, change the penalty to 0,7% for each day. Change the cap to 25%.
   - Save the changed document as `01_contract_transport.ro.revised.docx`. Keep the format of the original.
2. File `02_notificare_punere_in_intarziere.ro.anon.docx`.
   - Write a short cover e-mail in Romanian (about 150 words) to the other party. It must say what the notice asks for, and it must name the persons and the companies.
   - Save it as a new document `02_cover_email.docx`.
3. File `05_settlement_agreement.en.anon.docx`.
   - Write a summary of the settlement in English for the client (one page). Give the main duties of each party, the amounts, and the dates.
   - Save it as a new document `05_summary.docx`.
4. At the end, give me a report in your answer:
   - what you changed in each file,
   - for each output file, the list of the ids that you used,
   - anything that was hard, for example an id in a place where a Romanian word needs a different ending.

---
