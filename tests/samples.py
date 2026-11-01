"""Synthetic test case: one client (Alfa Construct) in four documents.

All people and companies are fictional. The numbers have valid checksums but
they do not belong to real people.

Run `python tests/samples.py` to write the files into data/samples/.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from legal_anonymizer.patterns import _CNP_KEY, _CUI_KEY

ROOT = Path(__file__).resolve().parent.parent


def make_cnp(prefix12: str) -> str:
    total = sum(int(d) * int(k) for d, k in zip(prefix12, _CNP_KEY))
    control = total % 11
    return prefix12 + str(1 if control == 10 else control)


def make_cui(body: str) -> str:
    total = sum(int(d) * k for d, k in zip(reversed(body), reversed(_CUI_KEY)))
    result = (total * 10) % 11
    return body + str(0 if result == 10 else result)


def make_iban(country: str, bban: str) -> str:
    digits = "".join(str(int(c, 36)) for c in bban + country + "00")
    return f"{country}{98 - int(digits) % 97:02d}{bban}"


CNP_ION = make_cnp("175041840123")
CNP_MARIA = make_cnp("288110212045")
CUI_ALFA = make_cui("3141592")
CUI_BETA = make_cui("2718281")
IBAN_ALFA = make_iban("RO", "BTRL" + "RONCRT0123456789")
IBAN_MARIA = make_iban("RO", "RNCB" + "0082044231234567")

CONTRACT_RO = f"""CONTRACT DE PRESTĂRI SERVICII nr. 45/2024

Încheiat astăzi, 15.03.2024, între:

1. SC ALFA CONSTRUCT SRL, societate cu sediul în Cluj-Napoca, str. Memorandumului nr. 12, bl. A2, sc. 1, ap. 4, jud. Cluj, înregistrată la Registrul Comerțului sub nr. J12/345/2018, CUI RO{CUI_ALFA}, cont IBAN {IBAN_ALFA} deschis la Banca Transilvania, reprezentată legal de dl. Ion Popescu, administrator, CNP {CNP_ION}, posesor al CI seria RX nr. 123456, telefon 0722 123 456, e-mail ion.popescu@alfaconstruct.ro, în calitate de BENEFICIAR,

și

2. Doamna Maria Ionescu, domiciliată în București, Calea Victoriei nr. 100, sector 1, CNP {CNP_MARIA}, telefon 0744 987 654, în calitate de PRESTATOR.

Art. 1. Obiectul contractului
Prestatorul se obligă să execute lucrări de proiectare pentru imobilul situat în Brașov, str. Lungă nr. 45, în folosul Beneficiarului, conform legislației din România.

Art. 2. Prețul și plata
Prețul total este de 25.000 EUR. Plata se face în contul {IBAN_MARIA} deschis la BCR pe numele IONESCU MARIA. Beneficiarul răspunde pentru plată prin dl. Popescu.

Art. 3. Litigii
Orice litigiu se soluționează de Tribunalul București. Părțile declară că dosarul nr. 1234/3/2024 nu are legătură cu prezentul contract.

BENEFICIAR,                                  PRESTATOR,
SC ALFA CONSTRUCT SRL                        Maria Ionescu
Ion Popescu
"""

NOTICE_RO = f"""Către: Doamna IONESCU MARIA
Adresa: Calea Victoriei nr. 100, sector 1, București

De la: Alfa Construct SRL, prin administrator Popescu Ion
Cluj-Napoca, 01.06.2024

NOTIFICARE DE REZILIERE

Referitor la contractul de prestări servicii nr. 45/2024, vă comunicăm rezilierea acestuia începând cu data de 01.07.2024, pentru neexecutarea obligațiilor asumate.

Lucrările vor fi preluate de Beta Logistic SA, CUI RO{CUI_BETA}, cu sediul în Timișoara. Pentru lămuriri ne puteți contacta la ion.popescu@alfaconstruct.ro sau la 0722 123 456.

În caz de neconformare, vom sesiza Judecătoria Cluj-Napoca. Maria Ionescu poate răspunde în scris.
"""

SETTLEMENT_EN = f"""SETTLEMENT AGREEMENT

This Settlement Agreement is made on 2 July 2024 between:

(1) ALFA CONSTRUCT SRL, a company registered in Romania (CUI RO{CUI_ALFA}), whose registered office is at str. Memorandumului nr. 12, Cluj-Napoca, represented by Mr. Ion Popescu (the "Company"); and

(2) Northwind Traders Ltd, a company registered in England, with offices at 14 Baker Street, London, represented by Ms. Jane Doe, e-mail jane.doe@northwind.co.uk, tel. +44 20 7946 0958 (the "Contractor").

1. The Contractor shall pay EUR 18,000 to the account {IBAN_ALFA} of the Company within 30 days.
2. The parties confirm that Case No. 2024-CV-00456 is closed and that no claim remains between them.
3. This Agreement is governed by the laws of Romania.
"""

# Strings that must not be in any anonymized file.
MUST_HIDE = [
    "Ion Popescu", "POPESCU ION", "Popescu Ion", "Maria Ionescu", "IONESCU MARIA",
    "ALFA CONSTRUCT", "Alfa Construct", "Beta Logistic", "Northwind", "Jane Doe",
    CNP_ION, CNP_MARIA, CUI_ALFA, CUI_BETA, IBAN_ALFA, IBAN_MARIA,
    "ion.popescu@alfaconstruct.ro", "jane.doe@northwind.co.uk", "0722 123 456",
    "0744 987 654", "+44 20 7946 0958", "Memorandumului", "Calea Victoriei",
    "Baker Street", "J12/345/2018", "1234/3/2024", "2024-CV-00456", "RX nr. 123456",
    "Cluj-Napoca", "Timișoara", "Brașov", "Lungă",
]  # fmt: skip

# Courts stay visible: the config of the sample case has `keep_public_bodies: true`.
VISIBLE_OK = ["Judecătoria Cluj-Napoca"]

# Words that must stay: the reader needs them, and they are not private.
MUST_KEEP = ["BENEFICIAR", "PRESTATOR", "Contractor", "25.000 EUR", "EUR 18,000", "România", "Romania", "Art. 1"]


# --- a small .docx with the hard cases ----------------------------------------------

W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
R_NS = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def run(text: str, bold: bool = False) -> str:
    props = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:r>{props}<w:t xml:space="preserve">{text}</w:t></w:r>'


def para(*parts: str) -> str:
    return "<w:p>" + "".join(parts) + "</w:p>"


def build_docx(
    *,
    author: str = "Andrei Avocat",
    company: str = "Cabinet Avocat Test",
    comment: str | None = None,
    extra_links: tuple[tuple[str, str], ...] = (),
) -> bytes:
    body = "".join([
        para(run("CONTRACT DE PRESTĂRI SERVICII", bold=True)),
        # The name is in two runs with different format.
        para(run("Beneficiar: "), run("Ion ", bold=True), run("Popescu", bold=True), run(", telefon 0722 123 456.")),
        # A company name that was added with tracked changes, and a deleted name.
        para(
            run("Prestator: "),
            '<w:ins w:id="1" w:author="Andrei Avocat" w:date="2024-03-01T10:00:00Z">' + run("Maria Ionescu") + "</w:ins>",
            '<w:del w:id="2" w:author="Andrei Avocat" w:date="2024-03-01T10:00:00Z"><w:r><w:delText>Vasile Georgescu</w:delText></w:r></w:del>',
        ),
        # A tab between a label and a value. A tab stop in the paragraph properties.
        '<w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="2000"/></w:tabs></w:pPr>'
        + run("Sediu:") + "<w:r><w:tab/></w:r>" + run("Cluj-Napoca") + "</w:p>",
        # An e-mail in a hyperlink.
        para(run("Contact: "), '<w:hyperlink w:anchor="x">' + run("ion.popescu@alfaconstruct.ro") + "</w:hyperlink>"),
        # A table.
        "<w:tbl><w:tr><w:tc>" + para(run("Societate")) + "</w:tc><w:tc>" + para(run("SC ALFA CONSTRUCT SRL")) + "</w:tc></w:tr></w:tbl>",
        # A text box.
        "<w:p><w:r><w:pict><v:shape xmlns:v='urn:schemas-microsoft-com:vml'><v:textbox><w:txbxContent>"
        + para(run("Semnat de Maria Ionescu")) + "</w:txbxContent></v:textbox></v:shape></w:pict></w:r></w:p>",
        para(run("Prețul este de 25.000 EUR."), '<w:r><w:footnoteReference w:id="1"/></w:r>'),
    ])
    if comment:
        body = body.replace(
            para(run("CONTRACT DE PRESTĂRI SERVICII", bold=True)),
            '<w:p><w:commentRangeStart w:id="0"/>' + run("CONTRACT DE PRESTĂRI SERVICII", bold=True)
            + '<w:commentRangeEnd w:id="0"/><w:r><w:commentReference w:id="0"/></w:r></w:p>',
        )
    sect = '<w:sectPr><w:headerReference w:type="default" r:id="rId1"/></w:sectPr>'
    body += sect
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W_NS} {R_NS}><w:body>{body}</w:body></w:document>'
    header = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {W_NS}>{para(run("Alfa Construct SRL - confidențial"))}</w:hdr>'
    footnotes = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:footnotes {W_NS}>'
        '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
        '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
        f'<w:footnote w:id="1">{para(run("Vezi dosarul nr. 1234/3/2024."))}</w:footnote></w:footnotes>'
    )
    ct = "application/vnd.openxmlformats-officedocument.wordprocessingml"
    overrides = {
        "/word/document.xml": f"{ct}.document.main+xml",
        "/word/header1.xml": f"{ct}.header+xml",
        "/word/footnotes.xml": f"{ct}.footnotes+xml",
        "/word/comments.xml": f"{ct}.comments+xml",
        "/docProps/core.xml": "application/vnd.openxmlformats-package.core-properties+xml",
        "/docProps/app.xml": "application/vnd.openxmlformats-officedocument.extended-properties+xml",
    }
    if not comment:
        del overrides["/word/comments.xml"]
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    doc_rels = [("rId1", "header", "header1.xml"), ("rId2", "footnotes", "footnotes.xml")]
    if comment:
        doc_rels.append(("rId3", "comments", "comments.xml"))
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            + "".join(f'<Override PartName="{n}" ContentType="{t}"/>' for n, t in overrides.items())
            + "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{rel}/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            f'<Relationship Id="rId3" Type="{rel}/extended-properties" Target="docProps/app.xml"/></Relationships>'
        ),
        "word/_rels/document.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(f'<Relationship Id="{i}" Type="{rel}/{t}" Target="{f}"/>' for i, t, f in doc_rels)
            + "".join(f'<Relationship Id="{i}" Type="{rel}/hyperlink" Target="{t}" TargetMode="External"/>' for i, t in extra_links)
            + "</Relationships>"
        ),
        "word/document.xml": document,
        "word/header1.xml": header,
        "word/footnotes.xml": footnotes,
        "docProps/core.xml": f'<?xml version="1.0" encoding="UTF-8"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Contract Alfa Construct</dc:title><dc:creator>{author}</dc:creator><cp:lastModifiedBy>{author}</cp:lastModifiedBy></cp:coreProperties>',
        "docProps/app.xml": f'<?xml version="1.0" encoding="UTF-8"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Company>{company}</Company></Properties>',
    }
    if comment:
        parts["word/comments.xml"] = (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:comments {W_NS}>'
            f'<w:comment w:id="0" w:author="Andrei Avocat" w:initials="AA">{para(run(comment))}</w:comment></w:comments>'
        )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in parts.items():
            z.writestr(name, content)
    return buffer.getvalue()


DOCX_MUST_HIDE = [
    "Ion Popescu", "Maria Ionescu", "Vasile Georgescu", "Alfa Construct", "ALFA CONSTRUCT",
    "0722 123 456", "Cluj-Napoca", "ion.popescu@alfaconstruct.ro", "1234/3/2024",
    "Andrei Avocat", "Cabinet Avocat Test",
]  # fmt: skip

MATTER_CONFIG = """\
# Known entities. The tool hides them in every document, also where the model does not find them.
keep_public_bodies: true
entities:
  - type: PERSON
    name: Ion Popescu
    aliases: [Popescu, dl. Popescu]
  - type: PERSON
    name: Maria Ionescu
  - type: ORGANIZATION
    name: SC Alfa Construct SRL
    aliases: [Alfa Construct, Alfa]
"""


def main() -> None:
    out = ROOT / "data" / "samples"
    out.mkdir(parents=True, exist_ok=True)
    (out / "01_contract_prestari_servicii.ro.txt").write_text(CONTRACT_RO, encoding="utf-8")
    (out / "02_notificare_reziliere.ro.txt").write_text(NOTICE_RO, encoding="utf-8")
    (out / "03_settlement_agreement.en.txt").write_text(SETTLEMENT_EN, encoding="utf-8")
    (out / "04_contract_cu_urmarire_modificari.ro.docx").write_bytes(build_docx(comment="Verificați CNP-ul lui Ion Popescu."))
    (out / "matter.yaml").write_text(MATTER_CONFIG, encoding="utf-8")
    (out / "gold.json").write_text(
        json.dumps({"must_hide": MUST_HIDE, "must_keep": MUST_KEEP, "visible_ok": VISIBLE_OK, "docx_must_hide": DOCX_MUST_HIDE}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote samples to {out}")


if __name__ == "__main__":
    main()
