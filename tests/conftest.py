import pytest

from legal_anonymizer.config import Settings
from legal_anonymizer.detector import Detector
from legal_anonymizer.vault import Vault


@pytest.fixture
def vault(tmp_path):
    with Vault(tmp_path / "case.db") as v:
        yield v


@pytest.fixture(scope="session")
def detector():
    """One detector for the whole run. The models load only on the first use."""
    return Detector(Settings())
