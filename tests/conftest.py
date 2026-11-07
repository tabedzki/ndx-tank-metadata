"""Fixtures for the ndx-tank-metadata tests."""

import pytest
from pynwb import NWBHDF5IO

from tests.helpers import write_nwb


@pytest.fixture
def round_trip(tmp_path):
    """Write a LabMetaDataExtension, then yield the one read back from disk (file stays open)."""
    ios = []

    def _round_trip(lab_metadata):
        path = write_nwb(tmp_path / "labmetadata.nwb", lab_metadata)
        io = NWBHDF5IO(str(path), "r", load_namespaces=True)
        ios.append(io)
        return io.read().lab_meta_data[lab_metadata.name]

    yield _round_trip
    for io in ios:
        io.close()
