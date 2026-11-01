"""Make the demo PDFs, the config file, and the list of secrets.

Run it from the project folder:  python -m demo.build
The files go to data/demo/. You need `reportlab` (it is in the "dev" extras).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import case as c
from . import docs_en, docs_firm, docs_ro, layout

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "demo"

DOCUMENTS = [
    ("01_contract_transport.ro.pdf", docs_ro.contract),
    ("02_notificare_punere_in_intarziere.ro.pdf", docs_firm.notice),
    ("03_cerere_chemare_in_judecata.ro.pdf", docs_firm.claim),
    ("04_contract_asistenta_juridica.ro.pdf", docs_firm.engagement),
    ("05_settlement_agreement.en.pdf", docs_en.settlement),
]

# The lawyer lists the parties when the case opens. The tool finds the other
# names (driver, dispatcher, witness, ...) without help.
CONFIG = f"""\
# Known entities of the case. The tool hides them in every document, also where the model misses them.
keep_public_bodies: true     # courts and ministries stay visible
entities:
  - type: ORGANIZATION
    name: {c.CLIENT_MIXED}
    aliases: ["{c.CLIENT}", "{c.CLIENT_SHORT}"]
  - type: PERSON
    name: {c.ADMIN}
    aliases: ["{c.ADMIN_REVERSED}", "Cristian Bălan", "dl. Bălan", "Bălan"]
  - type: ORGANIZATION
    name: {c.DEF_MIXED}
    aliases: ["{c.DEF}", "{c.DEF_SHORT}", "Carpatica"]
  - type: PERSON
    name: {c.DEF_REP}
    aliases: ["Gabriel Lazăr", "dl. Lazăr", "Lazăr"]
  - type: ORGANIZATION
    name: {c.FIRM}
    aliases: ["{c.FIRM_SHORT}"]
  - type: PERSON
    name: {c.LAWYER}
    aliases: ["Anca Rusu", "av. Rusu"]
  - type: ORGANIZATION
    name: {c.UK}
    aliases: ["Northgate"]
  - type: PERSON
    name: {c.UK_DIRECTOR}
    aliases: ["Ms Ellison", "Ellison"]
"""


def main() -> None:
    assert abs(sum(row[5] for row in c.DELAYS) - c.PENALTIES) < 0.005, c.DELAYS
    assert abs(c.TOTAL - 994_008.00) < 0.01, c.TOTAL
    OUT.mkdir(parents=True, exist_ok=True)
    layout.setup()
    for name, factory in DOCUMENTS:
        story, meta = factory()
        layout.build(OUT / name, story, meta)
        print("wrote", OUT / name)
    (OUT / "matter.yaml").write_text(CONFIG, encoding="utf-8")
    (OUT / "gold.json").write_text(
        json.dumps({"must_hide": c.MUST_HIDE, "must_keep": c.MUST_KEEP, "visible_ok": c.VISIBLE_OK}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
