import pytest

from legal_anonymizer.patterns import (
    _CNP_KEY,
    _CUI_KEY,
    build_pattern_recognizers,
    valid_cnp,
    valid_cui,
)


def make_cnp(prefix12: str) -> str:
    total = sum(int(d) * int(k) for d, k in zip(prefix12, _CNP_KEY))
    control = total % 11
    return prefix12 + str(1 if control == 10 else control)


def make_cui(body: str) -> str:
    total = sum(int(d) * k for d, k in zip(reversed(body), reversed(_CUI_KEY)))
    result = (total * 10) % 11
    return body + str(0 if result == 10 else result)


CNP = make_cnp("180031208001")  # synthetic: male, 1980-03-12
CUI = make_cui("1234567")


def find(text, language="ro"):
    found = []
    for recognizer in build_pattern_recognizers(language):
        for r in recognizer.analyze(text, None):
            found.append((r.entity_type, text[r.start : r.end]))
    return found


def test_cnp_checksum():
    assert valid_cnp(CNP)
    wrong = CNP[:-1] + str((int(CNP[-1]) + 1) % 10)
    assert not valid_cnp(wrong)
    assert not valid_cnp("123")
    assert not valid_cnp(make_cnp("180131308001"))  # month 13


def test_cui_checksum():
    assert valid_cui(CUI)
    assert valid_cui("RO " + CUI)
    assert not valid_cui(CUI[:-1] + str((int(CUI[-1]) + 1) % 10))


def test_cnp_found_and_invalid_cnp_ignored():
    assert ("RO_CNP", CNP) in find(f"cu CNP {CNP}, domiciliat")
    wrong = CNP[:-1] + str((int(CNP[-1]) + 1) % 10)
    assert not [f for f in find(f"numărul {wrong}") if f[0] == "RO_CNP"]


def test_cui_needs_context_or_ro_prefix():
    assert ("RO_CUI", CUI) in find(f"CUI {CUI}")
    assert ("RO_CUI", f"RO{CUI}") in find(f"cod fiscal RO{CUI}")
    assert ("RO_CUI", f"RO{CUI}") in find(f"VAT: RO{CUI}.")
    # A bare number without context is not a CUI.
    assert not [f for f in find("suma de 1234567 lei") if f[0] == "RO_CUI"]


def test_trade_register():
    assert ("RO_TRADE_REG", "J40/1234/2015") in find("înregistrată la ORC sub nr. J40/1234/2015.")


def test_id_card_and_passport():
    assert ("ID_DOCUMENT", "RX nr. 123456") in find("CI seria RX nr. 123456, eliberat")
    assert ("ID_DOCUMENT", "X1234567") in find("passport no. X1234567", "en")
    assert not [f for f in find("passport REQUIREMENTS apply", "en") if f[0] == "ID_DOCUMENT"]


def test_case_number_needs_context_and_ignores_dates():
    assert ("CASE_NUMBER", "1234/3/2024") in find("în dosarul nr. 1234/3/2024 al Tribunalului")
    assert ("CASE_NUMBER", "2023-CV-00123") in find("Case No. 2023-CV-00123 was filed", "en")
    assert not [f for f in find("la data de 12/03/2024 s-a semnat") if f[0] == "CASE_NUMBER"]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("domiciliat în str. Mihai Eminescu nr. 5, bl. A2, sc. 1, ap. 12, Cluj", "str. Mihai Eminescu nr. 5, bl. A2, sc. 1, ap. 12"),
        ("Strada Memorandumului nr. 12A, Cluj-Napoca", "Strada Memorandumului nr. 12A"),
        ("Calea Victoriei nr 100", "Calea Victoriei nr 100"),
        ("Bulevardul 1 Decembrie 1918 nr. 3", "Bulevardul 1 Decembrie 1918 nr. 3"),
    ],
)
def test_romanian_address(text, expected):
    assert ("ADDRESS", expected) in find(text)


def test_english_address_and_postal_code():
    assert ("ADDRESS", "14 Baker Street") in find("residing at 14 Baker Street, London", "en")
    assert ("ADDRESS", "400114") in find("cod poștal 400114")
    assert not [f for f in find("the str. unde locuiește nr. 5") if f[0] == "ADDRESS"]


def test_dates_and_short_numbers_are_not_phone_numbers():
    from legal_anonymizer.detector import looks_like_phone

    for value in ["01.06.2024", "1/6/2024", "2024-06-01", "12.03.80", "123456"]:
        assert not looks_like_phone(value), value
    for value in ["0722 123 456", "+40 722 123 456", "+44 20 7946 0958", "021.311.22.33"]:
        assert looks_like_phone(value), value


def test_email_with_any_domain_ending_is_found():
    # The Presidio e-mail recognizer needs a known domain ending. An internal or new one must also be hidden.
    assert ("EMAIL_ADDRESS", "ion.popescu@alfa-construct.example") in find("scrieti la ion.popescu@alfa-construct.example.")
    assert ("EMAIL_ADDRESS", "r.ciobanu@firma.co.uk") in find("mail: r.ciobanu@firma.co.uk, tel", "en")
    assert not [f for f in find("la adresa de mai sus @ si la nr. 5") if f[0] == "EMAIL_ADDRESS"]


def test_uk_postcode_company_number_and_consignment_note():
    assert ("ADDRESS", "LS11 9AQ") in find("Unit 4, Kingsway Park, Leeds LS11 9AQ", "en")
    assert ("ADDRESS", "SW1A 1AA") in find("London SW1A 1AA.", "en")
    assert ("COMPANY_NUMBER", "09876543") in find("a company with company number 09876543, whose", "en")
    assert ("COMPANY_NUMBER", "SC123456") in find("registered number SC123456", "en")
    assert not [f for f in find("the registered office is at Leeds", "en") if f[0] == "COMPANY_NUMBER"]
    assert ("CASE_NUMBER", "RO-2025-0417") in find("under CMR consignment note no. RO-2025-0417 (the Note)", "en")


def test_ranges_of_dates_and_table_rows_are_not_phone_numbers():
    from legal_anonymizer.detector import looks_like_phone

    for value in ["05.08.2024 – 14.02.2025", "2 23.10.2024", "4 30.01.2025", "12/03/2024 15/03/2024"]:
        assert not looks_like_phone(value), value


# --- optional types: calendar dates and job titles ----------------------------------


def dates(text, language="ro"):
    return [value for kind, value in find(text, language) if kind == "DATE_TIME"]


def titles(text, language="ro"):
    return [value for kind, value in find(text, language) if kind == "JOB_TITLE"]


@pytest.mark.parametrize(
    ("text", "language", "expected"),
    [
        ("semnat la 12.03.2024.", "ro", ["12.03.2024"]),
        ("din data de 12/03/2024", "ro", ["12/03/2024"]),
        ("semnat la 12 martie 2025", "ro", ["12 martie 2025"]),
        ("până la 1 Decembrie 2024", "ro", ["1 Decembrie 2024"]),
        ("născut la 5 mai 1980", "ro", ["5 mai 1980"]),
        ("în luna martie 2025", "ro", ["martie 2025"]),
        ("până pe 12 martie vine", "ro", ["12 martie"]),
        ("dated March 12, 2024 and", "en", ["March 12, 2024"]),
        ("on the 12th of March 2025", "en", ["12th of March 2025"]),
        ("born 1980-05-05", "en", ["1980-05-05"]),
        ("by 1 December 2024", "en", ["1 December 2024"]),
        ("in March 2025", "en", ["March 2025"]),
        ("due May 2025", "en", ["May 2025"]),
    ],
)
def test_calendar_dates(text, language, expected):
    assert dates(text, language) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Termen: 30 de zile",  # a duration
        "Anul 2024 a fost greu",  # a year
        "timp de 2 mai multe zile",  # "mai" is a common word
        "clauza 4.1.10 și 5.2.12",  # clause numbers
        "Version 1.2.3",
        "the parties may 2 times",
        "valoarea de 13.45.2024",  # not a date: month 45
        "12.34.5678",
    ],
)
def test_things_that_are_not_calendar_dates(text):
    assert dates(text, "ro") == [] and dates(text, "en") == []


@pytest.mark.parametrize(
    ("text", "language", "expected"),
    [
        ("Directorul general a semnat", "ro", ["Directorul general"]),
        ("comunicat Directorului financiar", "ro", ["Directorului financiar"]),
        ("administratorul unic al societății", "ro", ["administratorul unic"]),
        ("avocatul părții", "ro", ["avocatul"]),
        ("șeful de departament", "ro", ["șeful de departament"]),
        ("the Chief Executive Officer of", "en", ["Chief Executive Officer"]),
        ("our Managing Director", "en", ["Managing Director"]),
        ("the Head of Sales", "en", ["Head of Sales"]),
    ],
)
def test_job_titles(text, language, expected):
    assert titles(text, language) == expected


@pytest.mark.parametrize("text", ["Vânzătorul și Cumpărătorul", "Prestatorul", "the Buyer and the Seller", "directoral"])
def test_party_roles_and_other_words_are_not_job_titles(text):
    assert titles(text, "ro") == [] and titles(text, "en") == []
