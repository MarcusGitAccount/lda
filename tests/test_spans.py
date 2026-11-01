from legal_anonymizer.spans import Span, keep_set, refine, resolve_overlaps

KEEP = keep_set()


def cut(text, span):
    return text[span.start : span.end]


def refined(text, entity_type, start, end):
    result = refine(text, Span(start, end, entity_type), KEEP)
    return cut(text, result) if result else None


def test_title_and_role_words_are_trimmed():
    text = "Reclamanta Ţurcanu Elena a depus"
    assert refined(text, "PERSON", 0, text.index(" a depus")) == "Ţurcanu Elena"
    text = "dl. Ion Popescu"
    assert refined(text, "PERSON", 0, len(text)) == "Ion Popescu"
    text = "IONESCU MARIA, administrator"
    assert refined(text, "PERSON", 0, len(text)) == "IONESCU MARIA"


def test_pure_role_words_are_dropped():
    for word in ["PRESTATOR", "administrator", "Claimant", "the Defendant"]:
        assert refined(word, "PERSON", 0, len(word)) is None, word
    assert refined("Claimant", "ORGANIZATION", 0, 8) is None


def kept(text, entity_type, start, end, extra=None):
    """True if the policy keeps the span visible. Such a span has the type KEEP."""
    result = refine(text, Span(start, end, entity_type), keep_set(extra))
    return result is not None and result.type == "KEEP"


def test_keep_list_keeps_countries_but_not_cities():
    assert kept("România", "LOCATION", 0, 7)
    assert kept("Spain", "LOCATION", 0, 5)
    assert not kept("Cluj-Napoca", "LOCATION", 0, 11)
    assert refined("Cluj-Napoca", "LOCATION", 0, 11) == "Cluj-Napoca"
    assert kept("Tribunalul Bucureşti", "ORGANIZATION", 0, 20, ["Tribunalul București"])  # old cedilla letter


def test_kept_text_protects_a_known_name_inside_it():
    text = "Tribunalul Mureș a decis"
    spans = [Span(0, 16, "KEEP"), Span(11, 16, "LOCATION", 1.0, "vault")]
    assert resolve_overlaps(spans, text) == []
    # A known place outside the kept text is still hidden.
    text = "Tribunalul Mureș din Mureș"
    spans = [Span(0, 16, "KEEP"), Span(11, 16, "LOCATION", 1.0, "vault"), Span(21, 26, "LOCATION", 1.0, "vault")]
    assert [(s.start, s.end) for s in resolve_overlaps(spans, text)] == [(21, 26)]


def test_common_words_and_headings_are_not_names():
    assert refined("personal calificat", "PERSON", 0, 8) is None  # lowercase
    assert refined("2. S.C. Alfa S.R.L.", "ORGANIZATION", 0, 19) == "S.C. Alfa S.R.L."  # list number, last dot kept
    assert refined("DE TRANSPORT RUTIER", "ORGANIZATION", 0, 19) is None  # heading
    assert refined("„Beneficiarul”", "PERSON", 0, 14) is None
    assert refined("L.", "ORGANIZATION", 0, 2) is None  # one letter
    assert refined("B.", "PERSON", 0, 2) == "B"  # the initial of a person (a name cut by a line break)
    text = "Ramona Ciobanu, dispecer"
    assert refined(text, "PERSON", 0, len(text)) == "Ramona Ciobanu"


def test_an_abbreviation_keeps_its_last_dot():
    text = "S.C. ALFA S.R.L., cu sediul"
    assert refined(text, "ORGANIZATION", 0, 16) == "S.C. ALFA S.R.L."
    text = "Popescu."
    assert refined(text, "PERSON", 0, 8) == "Popescu"


def test_edge_punctuation_is_removed():
    text = "(Alfa Construct SRL),"
    assert refined(text, "ORGANIZATION", 0, len(text)) == "Alfa Construct SRL"


def test_a_separator_between_two_names_is_not_part_of_a_name():
    """A header like "Alfa S.R.L. / Beta S.A." or "Contract – Alfa" must come back with its slash and dash."""
    text = "Alfa Construct S.R.L. / Beta S.A."
    assert refined(text, "ORGANIZATION", 0, 23) == "Alfa Construct S.R.L."  # last dot kept
    assert refined(text, "ORGANIZATION", 24, len(text)) == "Beta S.A."
    text = "Contract – Alfa Construct |"
    assert refined(text, "ORGANIZATION", 8, len(text)) == "Alfa Construct"
    text = "Ionescu-"
    assert refined(text, "PERSON", 0, len(text)) == "Ionescu"
    assert refined("Cristian-Mihai Bălan", "PERSON", 0, 20) == "Cristian-Mihai Bălan"  # a hyphen inside a name stays


def test_same_type_overlap_is_joined():
    text = "Ion Popescu Junior"
    out = resolve_overlaps([Span(0, 11, "PERSON", 0.9), Span(4, 18, "PERSON", 0.8)], text)
    assert [(s.start, s.end) for s in out] == [(0, 18)]


def test_structured_span_wins_and_keeps_the_rest_of_the_weaker_span():
    text = "Ion Popescu, CNP 1800312080014"
    person = Span(0, len(text), "PERSON", 0.99)
    cnp = Span(17, len(text), "RO_CNP", 1.0)
    out = resolve_overlaps([person, cnp], text)
    assert [(s.type, cut(text, s)) for s in out] == [
        ("PERSON", "Ion Popescu, CNP"),  # the rest of the NER span stays hidden
        ("RO_CNP", "1800312080014"),
    ]


def test_known_entity_wins_over_a_model_span_of_another_type():
    # "SC ALFA SRL      Maria Ionescu": the model joins the company name and "Maria".
    text = "SC ALFA SRL      Maria Ionescu"
    model = Span(0, 17, "ORGANIZATION", 0.9, "presidio")
    known = [Span(0, 11, "ORGANIZATION", 1.0, "vault"), Span(17, 30, "PERSON", 1.0, "vault")]
    out = resolve_overlaps([model, *known], text)
    assert [(s.type, cut(text, s)) for s in out] == [("ORGANIZATION", "SC ALFA SRL"), ("PERSON", "Maria Ionescu")]


def test_known_entity_does_not_cut_a_value_with_a_fixed_shape():
    text = "scrieti la ion.popescu@alfa.ro azi"
    email = Span(11, 30, "EMAIL_ADDRESS", 1.0, "presidio")
    name = Span(15, 22, "PERSON", 1.0, "vault")
    out = resolve_overlaps([email, name], text)
    assert [(s.type, cut(text, s)) for s in out] == [("EMAIL_ADDRESS", "ion.popescu@alfa.ro")]


def test_known_entity_with_the_same_range_decides_the_type():
    text = "In Alfa."
    out = resolve_overlaps([Span(3, 7, "LOCATION", 0.9, "presidio"), Span(3, 7, "ORGANIZATION", 1.0, "vault")], text)
    assert [(s.type, cut(text, s)) for s in out] == [("ORGANIZATION", "Alfa")]


def test_known_short_name_inside_a_longer_model_name_of_the_same_type_is_joined():
    text = "Popescu Ion"
    out = resolve_overlaps([Span(0, 7, "PERSON", 1.0, "vault"), Span(0, 11, "PERSON", 0.9, "presidio")], text)
    assert [cut(text, s) for s in out] == ["Popescu Ion"]


def test_inflected_role_words_are_not_entities():
    for word in ["Beneficiarului", "prestatorilor", "Reclamanta", "reclamantei", "Administratorul", "Claimants", "Contractor's"]:
        assert refined(word, "PERSON", 0, len(word)) is None, word
    text = "Beneficiarul Ion Popescu"
    assert refined(text, "PERSON", 0, len(text)) == "Ion Popescu"


def test_no_overlap_in_result():
    text = "x" * 100
    spans = [Span(0, 40, "PERSON"), Span(30, 60, "ORGANIZATION"), Span(50, 90, "ADDRESS")]
    out = resolve_overlaps(spans, text)
    for a, b in zip(out, out[1:]):
        assert a.end <= b.start


def test_the_rest_of_a_cut_name_that_is_only_function_words_is_dropped():
    # The KEEP spans cut three names out of one long name. "of" and "and" must not stay as names:
    # the vault would learn them, and the sweep would then hide every "and" in every document.
    text = "against the United Kingdom of Great Britain and Northern Ireland lodged"
    whole = text.index("United")
    spans = [
        Span(whole, text.index(" lodged"), "ORGANIZATION", 0.9, "vault"),
        Span(whole, whole + len("United Kingdom"), "KEEP", 1.0, "presidio"),
        Span(text.index("Great"), text.index("Great") + len("Great Britain"), "KEEP", 1.0, "presidio"),
        Span(text.index("Northern"), text.index("Northern") + len("Northern Ireland"), "KEEP", 1.0, "presidio"),
    ]
    assert resolve_overlaps(spans, text) == []


def test_the_rest_of_a_cut_name_with_a_real_word_stays():
    # A known person cuts two parts out of a company name. "Construct" is left, and it is still hidden.
    text = "Alfa Construct Beta"
    spans = [
        Span(0, len(text), "ORGANIZATION", 0.9, "presidio"),
        Span(0, 4, "PERSON", 1.0, "vault"),
        Span(15, 19, "PERSON", 1.0, "vault"),
    ]
    assert [(text[s.start : s.end], s.type) for s in resolve_overlaps(spans, text)] == [
        ("Alfa", "PERSON"),
        ("Construct", "ORGANIZATION"),
        ("Beta", "PERSON"),
    ]
