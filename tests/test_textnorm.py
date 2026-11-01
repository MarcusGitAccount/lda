from legal_anonymizer.textnorm import entity_key, fold, fix_cedilla


def test_fold_keeps_length_and_removes_accents_and_case():
    text = "ȘTEFAN Țurcanu — Brașov şi Ţara"
    assert len(fold(text)) == len(text)
    assert fold(text) == "stefan turcanu - brasov si tara"


def test_cedilla_fix_keeps_length():
    assert fix_cedilla("ţară şi Şcoală") == "țară și Școală"


def test_person_key_ignores_order_case_accents_and_titles():
    keys = {
        entity_key("PERSON", s)
        for s in ["Ion Popescu", "POPESCU ION", "dl. Popescu Ion", "Mr. ion popescu", "Ión  Popescu"]
    }
    assert len(keys) == 1
    assert entity_key("PERSON", "Ion Popescu") != entity_key("PERSON", "Ion Popescu Jr")


def test_org_key_ignores_prefix_case_and_dots_but_not_the_legal_form():
    same = {entity_key("ORGANIZATION", s) for s in ["SC Alfa Construct SRL", "ALFA CONSTRUCT S.R.L.", "Alfa Construct srl"]}
    assert len(same) == 1
    assert entity_key("ORGANIZATION", "Alfa Construct SRL") != entity_key("ORGANIZATION", "Alfa Construct SA")
    assert entity_key("ORGANIZATION", "Alfa Construct SRL") != entity_key("ORGANIZATION", "Alfa Construct")


def test_phone_and_digit_keys():
    phones = {entity_key("PHONE_NUMBER", s) for s in ["0722 123 456", "+40 722 123 456", "0040722123456", "0722.123.456"]}
    assert len(phones) == 1
    assert entity_key("RO_CUI", "RO 2816464") == entity_key("RO_CUI", "2816464")
    assert entity_key("IBAN_CODE", "RO49 AAAA 1B31 0075 9384 0000") == entity_key("IBAN_CODE", "ro49aaaa1b31007593840000")
    assert entity_key("EMAIL_ADDRESS", "Ion.Popescu@Alfa.RO") == "ion.popescu@alfa.ro"
