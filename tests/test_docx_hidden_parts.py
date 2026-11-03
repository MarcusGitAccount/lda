"""A .docx that has the name of a client in every part where Word can write it. No model is loaded.

Review R-03: names stayed in `people.xml`, alt text, field codes, link targets, custom XML, custom
properties and the glossary. The leak check did not see the attributes.
"""

import io
import re
import zipfile

from legal_anonymizer.config import Settings
from legal_anonymizer.engine import Engine
from legal_anonymizer.spans import Span

NAME = "Ion Popescu"
MAIL = "ion.popescu@alfa-test.ro"
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
WP = 'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"'
W15 = 'xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml"'


def para(text):
    return f"<w:p><w:r><w:t xml:space=\"preserve\">{text}</w:t></w:r></w:p>"


document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document {W} {R} {WP}><w:body>
{para("BODY: Contract cu " + NAME + ".")}
<w:p><w:r><w:t>SPLIT: Ion Pop</w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>escu a semnat.</w:t></w:r></w:p>
<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> HYPERLINK "mailto:{MAIL}" </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>FIELD: scrie-i</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>
<w:p><w:fldSimple w:instr=" AUTHOR {NAME} "><w:r><w:t>FLDSIMPLE: autor</w:t></w:r></w:fldSimple></w:p>
<w:p><w:hyperlink r:id="rIdLink"><w:r><w:t>LINK: profil</w:t></w:r></w:hyperlink></w:p>
<w:p><w:r><w:drawing><wp:inline><wp:docPr id="1" name="Semnatura" descr="ALTTEXT: semnatura lui {NAME}" title="{NAME}"/></wp:inline></w:drawing></w:r></w:p>
<w:p><w:r><w:pict><v:shape xmlns:v="urn:schemas-microsoft-com:vml"><v:textbox><w:txbxContent>{para("TEXTBOX: " + NAME)}</w:txbxContent></v:textbox></v:shape></w:pict></w:r></w:p>
<w:sdt><w:sdtPr><w:alias w:val="Client"/><w:dataBinding w:xpath="/root/client" w:storeItemID="{{X}}"/></w:sdtPr><w:sdtContent>{para("SDT: " + NAME)}</w:sdtContent></w:sdt>
<w:p><w:ins w:id="1" w:author="{NAME}" w:date="2026-01-01T00:00:00Z"><w:r><w:t>TRACKED: text nou</w:t></w:r></w:ins></w:p>
<w:p><w:r><w:t>Referință</w:t></w:r><w:r><w:footnoteReference w:id="1"/></w:r></w:p>
</w:body></w:document>"""

footnotes = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes {W}><w:footnote w:id="1">{para("FOOTNOTE: " + NAME)}</w:footnote></w:footnotes>"""
comments = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments {W}><w:comment w:id="0" w:author="{NAME}" w:initials="IP">{para("COMMENT: " + NAME)}</w:comment></w:comments>"""
header = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {W}>{para("HEADER: " + NAME)}</w:hdr>"""
footer = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {W}>{para("FOOTER: " + MAIL)}</w:ftr>"""
people = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w15:people {W15}><w15:person w15:author="{NAME}"><w15:presenceInfo w15:providerId="AD" w15:userId="{MAIL}"/></w15:person></w15:people>"""
glossary = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:glossaryDocument {W}><w:docParts><w:docPart><w:docPartBody>{para("GLOSSARY: " + NAME)}</w:docPartBody></w:docPart></w:docParts></w:glossaryDocument>"""
custom_xml = f"""<?xml version="1.0" encoding="UTF-8"?><root><client>CUSTOMXML: {NAME}</client></root>"""
core = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>{NAME}</dc:creator><cp:lastModifiedBy>{NAME}</cp:lastModifiedBy><dc:title>Contract {NAME}</dc:title></cp:coreProperties>"""
app = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Company>Alfa Test SRL</Company><Template>Normal.dotm</Template></Properties>"""
custom_props = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="2" name="ClientName"><vt:lpwstr>CUSTOMPROP: {NAME}</vt:lpwstr></property></Properties>"""
rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdLink" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="mailto:{MAIL}" TargetMode="External"/></Relationships>"""
content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>"""

parts = {
    "[Content_Types].xml": content_types,
    "word/document.xml": document,
    "word/_rels/document.xml.rels": rels,
    "word/footnotes.xml": footnotes,
    "word/comments.xml": comments,
    "word/header1.xml": header,
    "word/footer1.xml": footer,
    "word/people.xml": people,
    "word/glossary/document.xml": glossary,
    "customXml/item1.xml": custom_xml,
    "docProps/core.xml": core,
    "docProps/app.xml": app,
    "docProps/custom.xml": custom_props,
}
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    for n, c in parts.items():
        z.writestr(n, c)
SOURCE = buf.getvalue()


class Stub:
    def language_of(self, text, language=None):
        return "ro"

    def detect(self, text, language, settings=None, context=None):
        spans = []
        for needle, kind in ((NAME, "PERSON"), (MAIL, "EMAIL_ADDRESS"), ("Alfa Test SRL", "ORGANIZATION")):
            spans += [Span(m.start(), m.end(), kind, 0.9, "presidio") for m in re.finditer(re.escape(needle), text)]
        return spans


def parts_of(data: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {i.filename: z.read(i).decode("utf-8") for i in z.infolist()}


def test_no_part_of_the_file_keeps_the_name(vault):
    engine = Engine(vault, Settings(), Stub())
    result = engine.anonymize("probe.docx", SOURCE)
    assert result.leaks == []
    assert engine.find_leaks("probe.docx", result.data) == []
    for part, raw in parts_of(result.data).items():
        for secret in ("Popescu", "ion.popescu", "Pop</w:t>"):
            assert secret not in raw, f"{secret!r} stays in {part}"


def test_the_leak_check_sees_a_name_in_an_attribute(vault):
    engine = Engine(vault, Settings(), Stub())
    engine.anonymize("probe.docx", SOURCE)
    # Only the alt text has the name. Before the fix, `scan_text` cut all the attribute values.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document %s %s><w:body><w:p><w:r><w:drawing>'
            '<wp:docPr id="1" name="x" descr="semnatura lui Ion Popescu"/></w:drawing></w:r></w:p></w:body></w:document>' % (W, WP),
        )
    assert engine.find_leaks("leaky.docx", buffer.getvalue()) == ["[PERSON_001]"]


def test_the_hidden_strings_come_back_with_restore(vault):
    engine = Engine(vault, Settings(), Stub())
    hidden = engine.anonymize("probe.docx", SOURCE)
    restored = engine.restore("probe.anon.docx", hidden.data)
    assert restored.unknown == [] and restored.suspect == []
    after = parts_of(restored.data)
    assert NAME in after["docProps/custom.xml"]
    assert f"mailto:{MAIL}" in after["word/_rels/document.xml.rels"]
    assert NAME in after["word/glossary/document.xml"]
    assert f'descr="ALTTEXT: semnatura lui {NAME}"' in after["word/document.xml"]


def test_people_file_is_scrubbed(vault):
    result = Engine(vault, Settings(), Stub()).anonymize("probe.docx", SOURCE)
    people = parts_of(result.data)["word/people.xml"]
    assert 'w15:author="Author"' in people and MAIL not in people
