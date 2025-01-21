import pytest
from mrc_utils import MRCUtils

@pytest.fixture
def mrc_utils():
    return MRCUtils()

def test_mrc_utils_initialization(mrc_utils):
    assert mrc_utils is not None

# TODO: Add more tests for MRCUtils functionality
