# Prompt for the AI tool

Use this text with Claude Code, Codex, or Copilot. Give the AI tool the folder `demo-output/hidden/`.
Do not give it the PDFs, the vault, or `matter.yaml`.

---

You get a legal document in Romanian or English. Some words are hidden.
Each hidden word has an id in square brackets, for example `[ORG_001]` or `[PERSON_002]`.

Rules:

1. Keep each id exactly as it is. Do not change it, translate it, or add a word to it.
2. Do not guess what an id hides. Use the id in your text, in the same way as a name.
3. If a Romanian word needs an ending after an id, write the ending in a separate word.
4. Keep the numbers of the articles and the style of the document.
5. Write your answer in the language of the document.

Task for `01_contract_transport.ro.anon.txt`:

1. Add a new article after Article 9. It must give the Beneficiary the right to a written report from the Provider after each late delivery.
2. In Article 9.2, change the penalty to 0,7% per day. Change the cap to 25%.
3. List what you changed.

Save the changed document as a text file.

---

Then run:

```bash
lda restore demo-output/ai/01_contract_transport.ro.anon.txt --matter demo --out demo-output/final
```

To use the text of a real AI tool in the demo script, save it as a file and run:

```bash
python -m demo.run_demo --revised my_revision.txt
```
