"""session_end_time is stored as an ISO 8601 (isodatetime) attribute and read back as a datetime."""

from datetime import datetime, timedelta, timezone

import h5py
import pytest

from tests.helpers import make_lab_metadata, write_nwb


@pytest.mark.parametrize(
    "end_time",
    [
        datetime(2026, 8, 7, 12, 33, 5, 250000, tzinfo=timezone.utc),
        datetime(2026, 8, 7, 12, 33, 5, tzinfo=timezone(timedelta(hours=-4))),
        datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))),
    ],
)
def test_tz_aware_datetime_round_trips(round_trip, end_time):
    back = round_trip(make_lab_metadata(session_end_time=end_time)).session_end_time
    assert isinstance(back, datetime)
    assert back == end_time
    assert back.utcoffset() == end_time.utcoffset()


def test_stored_as_iso8601_string_attribute(tmp_path):
    end_time = datetime(2026, 8, 7, 12, 33, 5, 250000, tzinfo=timezone(timedelta(hours=-4)))
    path = write_nwb(tmp_path / "end.nwb", make_lab_metadata(session_end_time=end_time))
    with h5py.File(path, "r") as f:
        raw = f["general/LabMetaData"].attrs["session_end_time"]
    raw = raw.decode() if isinstance(raw, bytes) else raw
    assert raw == "2026-08-07T12:33:05.250000-04:00"


def test_session_end_time_is_required():
    with pytest.raises(TypeError, match="session_end_time"):
        make_lab_metadata(session_end_time=None)


def test_spec_dtype_is_isodatetime():
    from pynwb import get_type_map

    spec = get_type_map().namespace_catalog.get_spec("ndx-tank-metadata", "LabMetaDataExtension")
    # "datetime" is an alias that round-trips but fails pynwb.validate ("expected 'datetime', got 'utf'").
    assert spec.get_attribute("session_end_time").dtype == "isodatetime"


def test_iso_string_is_rejected():
    # session_end_time was text up to 0.2.0; callers still passing .isoformat() must fail loudly.
    with pytest.raises(TypeError, match="session_end_time"):
        make_lab_metadata(session_end_time="2026-08-07T12:33:05+00:00")


def test_naive_datetime_writes_but_fails_validation(tmp_path):
    from pynwb import validate

    path = write_nwb(tmp_path / "naive.nwb", make_lab_metadata(session_end_time=datetime(2026, 8, 7, 12, 33, 5)))
    errors = validate(path=str(path))
    assert any("timezone" in str(e) for e in errors), errors
