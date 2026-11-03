"""Synthetic Romanian legal documents with the gold list made by construction.

The text and the gold come from the same renderer, so each offset is exact. The documents are made up:
every name, number and company is invented. The set is for the failure classes that the public sets
(MAPA, TAB) do not have: surnames that are common words, Romanian word forms, names that look like
other names, places that look like surnames, short names of a party, names in lower case, and
identifiers with a fixed shape. The adversarial review of 2026-11-02 asked for it (R-06, section 7).

Each mention has a `case` (the hard-case class). `python -m eval.synth_eval` reports recall per class.
A document is a text (.txt). The tool reads the same text for a Word file.
"""

from __future__ import annotations

import random
import unicodedata
from dataclasses import dataclass, field


@dataclass
class Mention:
    entity: str  # id of the entity in the gold list
    start: int
    end: int
    case: str  # the hard-case class
    kind: str = "hide"  # "hide": must be hidden. "stay": a word that must stay visible (over-hiding test)


@dataclass
class Doc:
    name: str
    matter: str
    text: str
    mentions: list[Mention] = field(default_factory=list)


class Builder:
    """Write a text and note where each entity is."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.mentions: list[Mention] = []
        self.pos = 0

    def t(self, text: str) -> "Builder":
        self.parts.append(text)
        self.pos += len(text)
        return self

    def m(self, entity: str, surface: str, case: str = "plain", kind: str = "hide") -> "Builder":
        self.mentions.append(Mention(entity, self.pos, self.pos + len(surface), case, kind))
        return self.t(surface)

    def text(self) -> str:
        return "".join(self.parts)


# --- identifiers with a valid checksum ----------------------------------------------------------


def make_cnp(rng: random.Random, female: bool = False) -> str:
    sex = rng.choice("26" if female else "15")
    body = f"{sex}{rng.randint(60, 99):02d}{rng.randint(1, 12):02d}{rng.randint(1, 28):02d}{rng.randint(1, 40):02d}{rng.randint(1, 999):03d}"
    total = sum(int(d) * int(k) for d, k in zip(body, "279146358279"))
    control = total % 11
    return body + str(1 if control == 10 else control)


def make_cui(rng: random.Random) -> str:
    body = str(rng.randint(10_000_00, 99_999_99))
    key = [7, 5, 3, 2, 1, 7, 5, 3, 2]
    total = sum(int(d) * k for d, k in zip(reversed(body), reversed(key)))
    result = (total * 10) % 11
    return body + str(0 if result == 10 else result)


def make_iban(rng: random.Random) -> str:
    bban = "BTRL" + "".join(rng.choice("0123456789") for _ in range(16))
    digits = "".join(str(int(c, 36)) for c in bban + "RO00")
    check = 98 - int(digits) % 97
    return f"RO{check:02d}{bban}"


# --- pools -------------------------------------------------------------------------------------

STREETS = ["Lalelelor", "Unirii", "Mihai Viteazu", "Libertății", "Păcii", "Fabricii"]
CITIES = ["Brașov", "Cluj-Napoca", "Iași", "Timișoara", "Sibiu", "Oradea"]
COUNTIES = {"Brașov": "BV", "Cluj-Napoca": "CJ", "Iași": "IS", "Timișoara": "TM", "Sibiu": "SB", "Oradea": "BH"}
COMPANIES = [("Alfa Construct", "ALFA CONSTRUCT"), ("Delta Logistic", "DELTA LOGISTIC"), ("Nordic Trans", "NORDIC TRANS"),
             ("Verde Agro", "VERDE AGRO"), ("Orion Soft", "ORION SOFT"), ("Carpatica Foods", "CARPATICA FOODS")]  # fmt: skip

# (first name, surname, hard-case label of the surname)
PEOPLE = [
    ("Ion", "Popescu", "plain"), ("Maria", "Negru", "common_word_surname"), ("Andrei", "Ionescu", "plain"),
    ("Andra", "Ionescu", "false_join_pair"), ("Ana-Maria", "Lupu", "common_word_surname"),
    ("Ștefan", "Țăranu", "diacritics"), ("Radu", "Rusu", "common_word_surname"), ("Paul", "Bunu", "common_word_surname"),
    ("Pau", "Lungu", "false_join_pair"), ("Vasile", "Mare", "common_word_surname"), ("Elena", "Albu", "common_word_surname"),
    ("Mihai", "Georgescu", "plain"), ("Cristina", "Dumitrescu", "plain"), ("Gheorghe", "Stan", "plain"),
]  # fmt: skip


def ascii_lower(text: str) -> str:
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().lower()


def genitive(surname: str) -> str:
    """The genitive and dative of a surname, with the article (Popescu -> Popescului, Mare -> Marelui)."""
    if surname.endswith(("u", "e")):
        return surname + "lui"
    if surname.endswith("a"):
        return surname[:-1] + "ei"
    return surname + "ului"


def person_docs(rng: random.Random, matter: str, a: tuple, b: tuple, c: tuple, company: tuple, city: str) -> list[Doc]:
    """Four documents of one matter. `a` is the client, `b` the other side, `c` a witness."""
    fa, sa, ca = a
    fb, sb, cb = b
    fc, sc, _ = c
    co, co_caps = company
    # Two people with one surname (the pair Andrei and Andra Ionescu) cannot be told apart by the surname alone:
    # their short mentions are written in full, so the gold stays exact.
    same_surname = sa == sb
    sb_alone = f"{fb} {sb}" if same_surname else sb
    case_alone = "plain" if same_surname else "surname_alone"
    cnp_a, cnp_b = make_cnp(rng), make_cnp(rng, female=fb.endswith("a"))
    cui, iban = make_cui(rng), make_iban(rng)
    street, county = rng.choice(STREETS), COUNTIES[city]
    county_name = {"BV": "Brașov", "CJ": "Cluj", "IS": "Iași", "TM": "Timiș", "SB": "Sibiu", "BH": "Bihor"}[county]
    village = sa[:-2] + "ti" if sa.endswith("escu") else "Popești"  # looks like the plural of a surname: Popești, Ionești
    plate = f"{county} {rng.randint(10, 99)} {''.join(rng.choice('ABCDEFGHJKLMNPRSTUVXZ') for _ in range(3))}"
    phone = f"07{rng.randint(20, 99)} {rng.randint(100, 999)} {rng.randint(100, 999)}"
    email = f"{ascii_lower(fa.split('-')[0])}.{ascii_lower(sa)}@exemplu-test.ro"
    docs = []

    # 1. Contract: the parties block, definitions, the short name of the company, the signature block.
    b1 = Builder()
    b1.t("CONTRACT DE VÂNZARE\n\nÎncheiat astăzi între:\n")
    b1.t("1. S.C. ").m("org", f"{co} S.R.L.", "org_variant").t(", cu sediul în ").m("loc_city", city, "plain").t(", str. ")
    b1.m("addr", f"{street} nr. {rng.randint(1, 80)}", "address").t(", CUI ").m("cui", f"RO{cui}", "identifier")
    b1.t(", cont IBAN ").m("iban", iban, "identifier").t(", reprezentată prin administrator ").m("pa", f"{fa} {sa}", "plain")
    b1.t(", CNP ").m("cnp_a", cnp_a, "identifier").t(", denumită în continuare ").t("„").m("org", co.split()[0], "short_name").t("”;\n")
    b1.t("2. " + ("Dna " if fb.endswith("a") else "Dl. ")).m("pb", f"{fb} {sb}", cb if cb != "false_join_pair" else "plain")
    b1.t(", domiciliat în ").m("loc_city", city, "plain").t(", CNP ").m("cnp_b", cnp_b, "identifier").t(", telefon ")
    b1.m("phone", phone, "identifier").t(", denumit în continuare „Cumpărătorul”.\n\n")
    b1.t("Art. 1. Vânzătorul vinde autoturismul de culoare negru, nr. de înmatriculare ").m("plate", plate, "identifier").t(".\n")
    b1.t("Art. 2. Cumpărătorul, " + ("dna " if fb.endswith("a") else "dl. ")).m("pb", sb_alone, case_alone).t(", plătește prețul de 15.000 EUR către ").m("org", co.split()[0], "short_name")
    b1.t(".\nArt. 3. Notificările se trimit la ").m("email", email, "identifier").t(".\n\n")
    b1.t("Semnături:\n").m("org", co_caps + " SRL", "allcaps").t("\nprin ").m("pa", f"{sa.upper()} {fa.upper()}", "allcaps").t("\n")
    docs.append(Doc(f"{matter}_01_contract.txt", matter, b1.text(), b1.mentions))

    # 2. Notice: genitive, dative, surname alone after a title, a word that is also a surname.
    b2 = Builder()
    b2.t("NOTIFICARE\n\nCătre ").m("pb", f"{fb} {sb}", "plain").t(",\n\n")
    b2.t("Prin prezenta, în numele clientului nostru ").m("org", f"{co} S.R.L.", "org_variant").t(", vă notificăm că ")
    b2.t("obligațiile ").m("pb", sb_alone if same_surname else genitive(sb), "plain" if same_surname else "genitive").t(" nu au fost îndeplinite. Cererea ").m("pa", f"{fa} {sa}" if same_surname else genitive(sa), "plain" if same_surname else "genitive")
    b2.t(" a fost înregistrată. Domnul ").m("pb", sb_alone, case_alone).t(" a fost informat. ")
    b2.t("Vă rugăm să răspundeți până la 30 de zile de la primire.\n\nAvocat ").m("pc", f"{fc} {sc}", "plain").t("\n")
    docs.append(Doc(f"{matter}_02_notificare.txt", matter, b2.text(), b2.mentions))

    # 3. Court filing: the label, a name at the start of a sentence, a place that looks like a form of a surname.
    b3 = Builder()
    b3.t("CERERE DE CHEMARE ÎN JUDECATĂ\n\nReclamant: ").m("org", f"S.C. {co} S.R.L.", "org_variant").t(", prin ").m("pa", f"{fa} {sa}", "plain")
    b3.t("\nPârât: ").m("pb", f"{fb} {sb}", "plain").t("\n\n")
    b3.m("pb", sb_alone, "plain" if same_surname else "surname_alone_sentence_start").t(" a primit autoturismul la ").m("loc_city", city, "plain")
    b3.t(". ").m("pb", f"{fb} {sb}", "plain").t(" locuiește în comuna ").m("loc_village", village, "place_like_form")
    b3.t(", jud. ").m("loc_city" if county_name == city else "loc_village", county_name, "plain")  # the county can have the name of the city.t(". Valoarea ").m("noun", "bunului", "common_noun", kind="stay")
    b3.t(" este mare, iar ").m("noun", "bunul", "common_noun", kind="stay").t(" imobil a fost predat.\n")
    docs.append(Doc(f"{matter}_03_cerere.txt", matter, b3.text(), b3.mentions))

    # 4. A short message in lower case, with a name that the other documents already show.
    b4 = Builder()
    b4.t("bună ziua, am vorbit azi cu ").m("pb", f"{fb.lower()} {sb.lower()}", "lowercase")
    b4.t(" și ").m("pb", sb_alone.lower(), "lowercase" if same_surname else "lowercase_surname_alone").t(" a zis că vorbește cu ").m("pa", f"{fa} {sa}".lower() if same_surname else sa.lower(), "lowercase" if same_surname else "lowercase_surname_alone")
    b4.t(". trimite-mi te rog contractul la ").m("email", email, "identifier").t(".\n")
    docs.append(Doc(f"{matter}_04_mesaj.txt", matter, b4.text(), b4.mentions))
    return docs


def build_set(seed: int = 7, matters: int = 6) -> list[Doc]:
    """`matters` matters with four documents each. The seed makes the set the same every time."""
    rng = random.Random(seed)
    docs: list[Doc] = []
    for i in range(matters):
        a, b = PEOPLE[(2 * i) % len(PEOPLE)], PEOPLE[(2 * i + 1) % len(PEOPLE)]
        c = PEOPLE[(2 * i + 5) % len(PEOPLE)]
        docs += person_docs(rng, f"M{i + 1}", a, b, c, COMPANIES[i % len(COMPANIES)], CITIES[i % len(CITIES)])
    return docs
