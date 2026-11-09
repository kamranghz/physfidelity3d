"""The released records are complete and unchanged."""

from physfidelity3d.__main__ import validate
from physfidelity3d.records import verify_checksums


def test_checksums():
    assert verify_checksums() == []


def test_validate_passes():
    assert validate()
