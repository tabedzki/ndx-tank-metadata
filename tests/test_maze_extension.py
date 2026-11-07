"""MazeExtension is a DynamicTable: one row per maze, one optional spec-declared column per maze field."""

import math

import numpy as np
import pytest
from ndx_tank_metadata import MazeExtension
from pynwb import get_type_map

from tests.helpers import make_lab_metadata


def _mazes(*rows):
    mazes = MazeExtension(name="mazes", description="mazes")
    for row in rows:
        mazes.add_row(**row)
    return mazes


def _read_mazes(round_trip, mazes):
    return round_trip(make_lab_metadata(mazes=mazes)).mazes


def test_maze_spec_declares_no_attributes_that_shadow_columns():
    # Regression: 20 attributes once collided with columns ("'forcedChoice' already exists in mazes.datasets").
    spec = get_type_map().namespace_catalog.get_spec("ndx-tank-metadata", "MazeExtension")
    own = {a.name for a in spec.attributes} - {"namespace", "neurodata_type", "object_id", "colnames", "description"}
    assert own.isdisjoint({d.name for d in spec.datasets})


def test_columns_are_declared_in_the_spec_not_only_in_python():
    spec = get_type_map().namespace_catalog.get_spec("ndx-tank-metadata", "MazeExtension")
    assert {"world", "lStart", "lCue", "lMemory", "warmupNTrials"} <= {d.name for d in spec.datasets}


def test_single_row_mixed_types(round_trip):
    row = dict(world=1, lStart=5.0, turnHint_Puff=True, numTrials=10.0)
    back = _read_mazes(round_trip, _mazes(row))
    assert len(back) == 1
    assert back["world"].data[0] == 1
    assert back["lStart"].data[0] == 5.0
    assert bool(back["turnHint_Puff"].data[0]) is True
    assert back["numTrials"].data[0] == 10
    assert back.id.data[0] == 0


def test_several_rows(round_trip):
    rows = [dict(world=1, maxBias=0.2), dict(world=2, maxBias=0.1), dict(world=3, maxBias=0.0)]
    back = _read_mazes(round_trip, _mazes(*rows))
    assert list(back["world"].data[:]) == [1, 2, 3]
    assert list(back["maxBias"].data[:]) == [0.2, 0.1, 0.0]


def test_zero_values_are_kept(round_trip):
    back = _read_mazes(round_trip, _mazes(dict(world=0, performance=0.0, turnHint_Puff=False)))
    assert back["world"].data[0] == 0
    assert back["performance"].data[0] == 0.0
    assert bool(back["turnHint_Puff"].data[0]) is False


def test_nan_and_inf_round_trip(round_trip):
    # Criteria use NaN and Inf: easyBlockNTrials has no value when unset, maxBias is Inf for no limit.
    back = _read_mazes(round_trip, _mazes(dict(easyBlockNTrials=math.nan, maxBias=math.inf),
                                          dict(easyBlockNTrials=5.0, maxBias=-math.inf)))
    assert math.isnan(back["easyBlockNTrials"].data[0])
    assert back["easyBlockNTrials"].data[1] == 5.0
    assert list(back["maxBias"].data[:]) == [math.inf, -math.inf]


def test_ragged_column_with_add_row(round_trip):
    back = _read_mazes(round_trip, _mazes(dict(warmupMaze=[]), dict(warmupMaze=[4.0]), dict(warmupMaze=[4.0, 3.0])))
    np.testing.assert_array_equal(back["warmupMaze"][2], [4.0, 3.0])
    assert len(back["warmupMaze"][0]) == 0


def test_undeclared_column_is_rejected():
    # Per-trial fields that used to be offered as maze columns now live in the trials table.
    with pytest.raises(ValueError, match="forcedChoice"):
        _mazes(dict(world=1), dict(world=2, forcedChoice=0))


def test_only_some_columns_present(round_trip):
    back = _read_mazes(round_trip, _mazes(dict(world=1)))
    assert back.colnames == ("world",)


def test_empty_table_round_trips(round_trip):
    back = _read_mazes(round_trip, _mazes())
    assert len(back) == 0
    assert back.colnames == ()


def test_none_in_first_row_leaves_the_column_out(round_trip):
    # HDF5 has no null. For an optional predefined column, None means "column not present".
    back = _read_mazes(round_trip, _mazes(dict(world=None, lStart=5.0), dict(world=None, lStart=6.0)))
    assert back.colnames == ("lStart",)
    assert list(back["lStart"].data[:]) == [5.0, 6.0]


def test_none_for_existing_column_is_rejected():
    mazes = _mazes(dict(world=1, lStart=5.0))
    with pytest.raises(TypeError, match="None is not allowed"):
        mazes.add_row(world=None, lStart=6.0)


def test_missing_value_in_later_row_is_rejected():
    mazes = _mazes(dict(world=1, lStart=5.0))
    with pytest.raises(ValueError):
        mazes.add_row(world=2)
