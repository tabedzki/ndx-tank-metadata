"""RigExtension: scalar attributes plus three 1-D vector attributes."""

import numpy as np
import pytest
from ndx_tank_metadata import RigExtension

from tests.helpers import RIG, make_lab_metadata

VECTOR_ATTRS = {
    "sensorDotsPerRev": [1967.6, 1967.6, 1967.6, 1967.6],
    "colorAdjustment": [0.0, 0.4, 0.5],
    "nidaqLines": [0, 11],
}


def test_full_rig_round_trips(round_trip):
    back = round_trip(make_lab_metadata()).rig
    for key, value in RIG.items():
        if key in VECTOR_ATTRS:
            np.testing.assert_array_equal(getattr(back, key), value, err_msg=key)
        else:
            assert getattr(back, key) == value, key


@pytest.mark.parametrize("attr", ["sensorDotsPerRev", "nidaqLines"])
def test_one_element_vector_round_trips(round_trip, attr):
    value = VECTOR_ATTRS[attr][:1]
    back = round_trip(make_lab_metadata(rig=RigExtension(name="rig", **{attr: value}))).rig
    np.testing.assert_array_equal(getattr(back, attr), value)
    assert np.asarray(getattr(back, attr)).shape == (1,)


@pytest.mark.parametrize("attr", sorted(VECTOR_ATTRS))
def test_numpy_vector_round_trips(round_trip, attr):
    value = np.asarray(VECTOR_ATTRS[attr])
    back = round_trip(make_lab_metadata(rig=RigExtension(name="rig", **{attr: value}))).rig
    np.testing.assert_array_equal(getattr(back, attr), value)


@pytest.mark.parametrize("attr", sorted(VECTOR_ATTRS))
@pytest.mark.parametrize("scalar", [1.0, 0, np.float64(2.5)])
def test_scalar_for_vector_attr_is_rejected(attr, scalar):
    # The spec declares shape [null]; a MATLAB scalar must be wrapped in a list by the caller.
    with pytest.raises(TypeError, match=attr):
        RigExtension(name="rig", **{attr: scalar})


@pytest.mark.parametrize("value", [[0.0, 0.4], [0.0, 0.4, 0.5, 0.6]])
def test_color_adjustment_needs_exactly_rgb(value):
    with pytest.raises((TypeError, ValueError), match="colorAdjustment"):
        RigExtension(name="rig", colorAdjustment=value)


@pytest.mark.parametrize("attr", ["ballCircumference", "rewardSize", "nidaqDevice"])
def test_vector_for_scalar_attr_is_rejected(attr):
    with pytest.raises((TypeError, ValueError), match=attr):
        RigExtension(name="rig", **{attr: [1, 2]})


def test_zero_valued_scalars_round_trip(round_trip):
    rig = RigExtension(name="rig", rewardChannel=0, simulationMode=False, soundAdjustment=0.0)
    back = round_trip(make_lab_metadata(rig=rig)).rig
    assert back.rewardChannel == 0
    assert not back.simulationMode
    assert back.simulationMode is not None
    assert back.soundAdjustment == 0.0


def test_all_rig_attrs_are_optional(round_trip):
    back = round_trip(make_lab_metadata(rig=RigExtension(name="rig"))).rig
    assert back.rig_type is None
    assert back.sensorDotsPerRev is None


def test_puff_channel_docs_match_their_side():
    from pynwb import get_type_map

    spec = get_type_map().namespace_catalog.get_spec("ndx-tank-metadata", "RigExtension")
    docs = {a.name: a.doc.lower() for a in spec.attributes}
    assert "right" in docs["rightPuffChannel"] and "left" not in docs["rightPuffChannel"]
    assert "left" in docs["leftPuffChannel"] and "right" not in docs["leftPuffChannel"]
