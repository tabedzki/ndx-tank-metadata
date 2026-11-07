"""The ViRMEn field registry: one validated entry per log field, the single source of truth for the spec."""

import re
from dataclasses import replace

import pytest

from ndx_tank_metadata.registry import (
    DESTINATIONS,
    DTYPES,
    SPEC_DESTINATIONS,
    Field,
    Registry,
    RegistryError,
    load_registry,
)


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def _field(**overrides):
    values = dict(path="log.block.trial.x", destination="trial_column", name="x", dtype="int8", shape=(),
                  description="a field", in_spec=True)
    values.update(overrides)
    return Field(**values)


def test_float32_is_only_declared_for_single_precision_sources(registry):
    # Fields logged as double are float64. Only ViRMEn's reducePrecision trial fields may be float32.
    for field in registry:
        if field.dtype == "float32":
            assert field.path.startswith("log.block.trial."), field.path


def test_every_surveyed_field_has_one_entry(registry):
    paths = [f.path for f in registry]
    assert len(paths) == len(set(paths))
    # 553 surveyed log paths, plus decoded CS and trial-bank members and stimulusTable columns.
    assert len(paths) >= 553


@pytest.mark.parametrize("path", [
    "log.block.trial.choice", "log.block.trial.position", "log.animal.name", "log.version.rig.squal",
    "log.version.mazes.criteria.warmupNTrials", "log.version.variables.lCue",
    "log.block.trial.CS.modality", "log.block.trial.stimulusTable.PostProb",
])
def test_lookup_by_path(registry, path):
    assert registry[path].path == path


def test_lookup_of_an_unregistered_path_is_none(registry):
    assert registry.get("log.block.trial.notAField") is None
    with pytest.raises(KeyError):
        registry["log.block.trial.notAField"]


def test_entries_use_declared_vocabulary(registry):
    for field in registry:
        assert field.destination in DESTINATIONS, field.path
        assert field.dtype is None or field.dtype in DTYPES, field.path
        assert field.description.strip(), field.path


def test_stored_fields_declare_dtype_shape_and_name(registry):
    for field in registry:
        if field.destination in {"drop", "structural"}:
            continue
        assert field.name, field.path
        assert field.dtype, field.path
        assert field.shape is not None, field.path


def test_dropped_fields_say_why(registry):
    for field in registry:
        if field.destination == "drop":
            assert field.notes, field.path


def test_only_spec_destinations_are_in_spec(registry):
    for field in registry:
        if field.in_spec:
            assert field.destination in SPEC_DESTINATIONS, field.path


def test_names_are_unique_within_a_destination(registry):
    seen = {}
    for field in registry:
        if not field.name or field.destination == "settings":
            continue
        for name in field.nwb_names:
            key = (field.destination, name)
            assert key not in seen, f"{field.path} and {seen.get(key)} both write {name}"
            seen[key] = field.path


def test_spec_names_are_valid_identifiers(registry):
    for field in registry:
        if field.in_spec:
            assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field.name), field.path


def test_unknown_meaning_fields_stay_out_of_the_spec(registry):
    for field in registry:
        if field.meaning_known is False:
            assert not field.in_spec, field.path


def test_experiment_variables_go_to_settings_except_track_lengths(registry):
    for field in registry:
        if field.path.startswith("log.version.variables."):
            assert field.destination == "settings", field.path
    for leaf in ("lStart", "lCue", "lMemory"):
        field = registry[f"log.version.mazes.variable.{leaf}"]
        assert (field.destination, field.name, field.in_spec) == ("maze_column", leaf, True)
        assert field.dtype == "float64"


@pytest.mark.parametrize("leaf", ["collision", "moonBeaconEnabled", "wallGuide", "isClampTrial"])
def test_binary_trial_fields_are_bool(registry, leaf):
    assert registry[f"log.block.trial.{leaf}"].dtype == "bool"


def test_easy_block_flag_is_bool(registry):
    assert registry["log.block.easyBlockFlag"].dtype == "bool"


@pytest.mark.parametrize("path, codes", [
    ("log.block.trial.lsrON", {0, 1}),
    ("log.block.trial.probeTrial", {0, 1}),
    ("log.block.trial.forcedChoice", {0, 1}),
    ("log.block.context", {1, 2, 3}),
    ("log.block.trial.LaserTrialType", {0, 1, 2}),
])
def test_coded_flags_are_small_ints_with_known_codes(registry, path, codes):
    field = registry[path]
    assert field.dtype == "int8"
    assert set(field.codes) == codes


@pytest.mark.parametrize("leaf", ["choice", "finalchoice"])
def test_choice_codes_include_the_violation_state(registry, leaf):
    assert set(registry[f"log.block.trial.{leaf}"].codes) == {"L", "R", "nil"}


def test_trial_type_has_no_violation_code(registry):
    assert set(registry["log.block.trial.trialType"].codes) == {"L", "R"}


def test_laser_markers_are_labelled_as_commands(registry):
    for leaf, word in (("iLaserOn", "onset"), ("iLaserOff", "offset")):
        description = registry[f"log.block.trial.{leaf}"].description.lower()
        assert f"laser command {word} frame" in description


def test_decided_drops(registry):
    for path in ("log.block.trial.comment", "log.block.versionIndex", "log.block.trial.hitHistory",
                 "log.block.trial.classHistory", "log.block.trial.trialNum"):
        assert registry[path].destination == "drop", path


def test_turn_hint_declares_its_missing_sentinel(registry):
    assert registry["log.version.mazes.turnHint_Mem"].missing == -1


def test_only_coded_turn_hint_declares_a_sentinel(registry):
    # NaN into an integer field fails unless the registry declares what it becomes.
    assert [f.path for f in registry if f.missing is not None] == ["log.version.mazes.turnHint_Mem"]


def test_doorstop_licks_rule_is_recorded(registry):
    field = registry["log.block.trial.licks"]
    assert field.destination == "trial_column"
    assert field.transform == "licks"
    assert "doorstop" in field.notes.lower()


def test_kept_settings(registry):
    for path in ("log.animal.pretraining_instructions", "log.animal.posttraining_instructions",
                 "log.animal.pupillometry_video_acq_struct.video_acquisition_rate"):
        assert registry[path].destination == "settings", path
    for path in ("log.numTrialsTry", "log.consecutiveViolationTrials"):
        assert registry[path].destination == "lab_meta_attribute", path


def test_session_end_is_an_isodatetime_attribute(registry):
    field = registry["log.session.end"]
    assert (field.destination, field.name, field.dtype) == ("lab_meta_attribute", "session_end_time", "isodatetime")


def test_view_angle_and_angular_velocity_are_radians(registry):
    assert "rad" in registry["log.block.trial.position"].notes
    assert "rad/s" in registry["log.block.trial.velocity"].notes
    assert "AngularVelocity" in registry["log.block.trial.velocity"].notes


@pytest.mark.parametrize("name", ["PairNum", "Prob", "Side", "Sa", "Sb"])
def test_static_stimulus_table_columns_keep_the_sheet_names(registry, name):
    field = registry[f"log.block.trial.stimulusTable.{name}"]
    assert (field.destination, field.name) == ("stimulus_pairs_column", name)


@pytest.mark.parametrize("name", ["Hits", "NTotal", "PostProb"])
def test_running_stimulus_table_columns_are_ragged_trial_columns(registry, name):
    field = registry[f"log.block.trial.stimulusTable.{name}"]
    assert (field.destination, field.name, field.shape) == ("trial_column", name, (None,))


def test_left_right_cells_expand_to_two_ragged_columns(registry):
    field = registry["log.block.trial.cuePos"]
    assert field.nwb_names == ("cuePos_left", "cuePos_right")
    assert field.shape == (None,)


def test_licks_expand_to_iteration_and_value(registry):
    assert registry["log.block.trial.licks"].nwb_names == ("licks_iteration", "licks_value")


def test_scalar_fields_have_one_nwb_name(registry):
    assert registry["log.block.trial.iCueEntry"].nwb_names == ("iCueEntry",)


def test_field_without_a_name_expands_to_nothing(registry):
    assert registry["log.block.trial.comment"].nwb_names == ()


def test_no_researcher_attribution_fields():
    assert not {"experimenters", "experimenter", "users"} & set(Field.__dataclass_fields__)


class TestValidation:
    def test_valid_field_is_accepted(self):
        Registry([_field()])

    def test_duplicate_path_is_rejected(self):
        with pytest.raises(RegistryError, match="duplicate"):
            Registry([_field(), _field(name="y")])

    def test_unknown_destination_is_rejected(self):
        with pytest.raises(RegistryError, match="destination"):
            Registry([_field(destination="nowhere", in_spec=False)])

    def test_unknown_dtype_is_rejected(self):
        with pytest.raises(RegistryError, match="dtype"):
            Registry([_field(dtype="float16")])

    def test_in_spec_requires_a_spec_destination(self):
        with pytest.raises(RegistryError, match="in_spec"):
            Registry([_field(destination="settings", dtype="text")])

    def test_in_spec_with_unknown_meaning_is_rejected(self):
        with pytest.raises(RegistryError, match="meaning"):
            Registry([_field(meaning_known=False)])

    def test_missing_description_is_rejected(self):
        with pytest.raises(RegistryError, match="description"):
            Registry([_field(description=" ")])

    def test_drop_without_a_reason_is_rejected(self):
        with pytest.raises(RegistryError, match="notes"):
            Registry([_field(destination="drop", name=None, dtype=None, shape=None, in_spec=False)])

    def test_stored_field_without_dtype_is_rejected(self):
        with pytest.raises(RegistryError, match="dtype"):
            Registry([_field(dtype=None)])

    def test_codes_of_the_wrong_kind_are_rejected(self):
        with pytest.raises(RegistryError, match="codes"):
            Registry([_field(codes={"L": "left"})])

    def test_int_codes_outside_the_dtype_range_are_rejected(self):
        with pytest.raises(RegistryError, match="codes"):
            Registry([_field(codes={300: "too big"})])

    def test_codes_on_a_float_field_are_rejected(self):
        with pytest.raises(RegistryError, match="codes"):
            Registry([_field(dtype="float32", codes={1: "one"})])

    def test_zero_code_is_valid(self):
        Registry([_field(codes={0: "off", 1: "on"})])

    def test_negative_code_is_valid(self):
        Registry([_field(codes={-1: "not specified", 0: "off"})])

    def test_missing_must_be_a_declared_code(self):
        with pytest.raises(RegistryError, match="missing"):
            Registry([_field(codes={0: "off"}, missing=-1)])

    def test_missing_on_a_non_integer_field_is_rejected(self):
        with pytest.raises(RegistryError, match="missing"):
            Registry([_field(dtype="float32", missing=-1)])

    def test_zero_is_a_valid_missing_sentinel(self):
        assert Registry([_field(codes={0: "not specified"}, missing=0)])["log.block.trial.x"].missing == 0

    def test_same_name_in_a_destination_is_rejected(self):
        with pytest.raises(RegistryError, match="both write"):
            Registry([_field(), replace(_field(), path="log.block.trial.y")])

    def test_same_name_in_two_destinations_is_accepted(self):
        Registry([_field(), _field(path="log.block.x", destination="epoch_column")])

    def test_settings_may_share_a_name(self):
        Registry([_field(path="a", destination="settings", name="k", dtype="text", in_spec=False),
                  _field(path="b", destination="settings", name="k", dtype="text", in_spec=False)])

    def test_empty_registry_is_valid(self):
        assert list(Registry([])) == []

    def test_unknown_transform_is_rejected(self):
        with pytest.raises(RegistryError, match="transform"):
            Registry([_field(transform="magic")])

    def test_required_field_must_be_in_spec(self):
        with pytest.raises(RegistryError, match="required"):
            Registry([_field(destination="settings", dtype="text", in_spec=False, required=True)])

    def test_load_rejects_unknown_keys(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text("fields:\n- path: a\n  destination: drop\n  description: d\n  notes: n\n  experimenters: x\n")
        with pytest.raises(RegistryError, match="experimenters"):
            load_registry(path)


class TestClockDecisions:
    def test_block_wall_clock_stamp_keeps_its_own_epoch_column(self):
        # start_time is on the session clock; the stamp can disagree with it, so it's stored separately.
        field = load_registry()["log.block.start"]
        assert field.destination == "epoch_column"
        assert field.name == "wall_clock_start"
        assert field.in_spec

    def test_raw_ball_input_is_a_recorded_drop(self):
        field = load_registry()["log.block.trial.rawBallInput"]
        assert field.destination == "drop"
        assert "stays in the raw log" in field.notes


def test_difficulty_set_holds_a_percent_mix_or_a_scalar():
    """Some logs store one false, others the percent of easy, medium and hard trials, such as [50, 50, 0]."""
    field = load_registry()["log.block.trialParams.difficultySet"]
    assert field.dtype == "float64"
    assert field.shape == (None,)
    assert "easy, medium and hard" in field.description
