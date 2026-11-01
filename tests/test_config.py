import pytest

from legal_anonymizer.config import Settings, load_settings
from legal_anonymizer.entities import DEFAULT_HIDE


def test_defaults_hide_names_and_ids_but_not_dates_or_money():
    settings = Settings()
    assert settings.hide == DEFAULT_HIDE
    assert {"PERSON", "ORGANIZATION", "LOCATION", "ADDRESS", "RO_CNP", "IBAN_CODE"} <= settings.hide
    assert not {"DATE_TIME", "MONEY"} & settings.hide
    assert settings.keep_public_bodies is False  # safer to hide


def test_the_example_in_the_readme_loads(tmp_path):
    path = tmp_path / "matter.yaml"
    path.write_text(
        """
hide: [PERSON, ORGANIZATION, LOCATION, ADDRESS, DATE_TIME]
keep: ["Tribunalul București", "ANAF"]
keep_public_bodies: true
min_score: 0.6
en_model: dslim/bert-base-NER
entities:
  - type: PERSON
    name: Ion Popescu
    aliases: [Popescu, dl. Popescu]
  - type: ORGANIZATION
    name: SC Alfa Construct SRL
""",
        encoding="utf-8",
    )
    settings = load_settings(path)
    assert settings.hide == {"PERSON", "ORGANIZATION", "LOCATION", "ADDRESS", "DATE_TIME"}
    assert settings.keep == ["Tribunalul București", "ANAF"]
    assert settings.keep_public_bodies is True and settings.min_score == 0.6
    assert settings.en_model == "dslim/bert-base-NER"
    assert [(s.type, s.name, s.aliases) for s in settings.seeds] == [
        ("PERSON", "Ion Popescu", ["Popescu", "dl. Popescu"]),
        ("ORGANIZATION", "SC Alfa Construct SRL", []),
    ]


def test_command_line_hide_overrides_the_file(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text("hide: [PERSON]")
    assert load_settings(path, hide=["PERSON", "MONEY"]).hide == {"PERSON", "MONEY"}


def test_unknown_types_are_refused_with_a_clear_message(tmp_path):
    bad_hide = tmp_path / "a.yaml"
    bad_hide.write_text("hide: [PERSON, PERSONN]")
    with pytest.raises(ValueError, match="PERSONN"):
        load_settings(bad_hide)
    bad_seed = tmp_path / "b.yaml"
    bad_seed.write_text("entities:\n  - {type: COMPANY, name: Alfa}")
    with pytest.raises(ValueError, match="COMPANY"):
        load_settings(bad_seed)


def test_empty_config_file_gives_defaults(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    assert load_settings(path).hide == DEFAULT_HIDE
