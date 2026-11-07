"""The spec is generated from the registry, and every generated type writes, reads and validates."""

from datetime import datetime, timezone
import importlib.util
from pathlib import Path

import h5py
import numpy as np
import pytest
from hdmf.common import DynamicTableRegion, VectorData, VectorIndex
from pynwb import NWBHDF5IO, NWBFile, get_class, get_type_map, validate

from ndx_tank_metadata import (
    AnimalSettings,
    LabMetaDataExtension,
    MazeExtension,
    RigExtension,
    StimulusPairs,
    VirmenEpochs,
    VirmenSettings,
    VirmenTrials,
)
from ndx_tank_metadata.registry import load_registry
from pynwb.epoch import TimeIntervals
from tests.helpers import SESSION_START, make_lab_metadata

REGISTRY = load_registry()
REPO = Path(__file__).resolve().parent.parent
NAMESPACE = "ndx-tank-metadata"
TYPE_FOR_DESTINATION = {
    "trial_column": "VirmenTrials",
    "epoch_column": "VirmenEpochs",
    "maze_column": "MazeExtension",
    "stimulus_pairs_column": "StimulusPairs",
}
ATTRIBUTE_TYPE_FOR_DESTINATION = {
    "rig_attribute": "RigExtension",
    "animal_attribute": "AnimalSettings",
    "lab_meta_attribute": "LabMetaDataExtension",
}
INHERITED_COLUMNS = {"start_time", "stop_time"}
DTYPE_IN_FILE = {"bool": "bool", "int8": "int8", "int16": "int16", "int32": "int32", "float32": "float32",
                 "float64": "float64"}


def _spec(type_name):
    return get_type_map().namespace_catalog.get_spec(NAMESPACE, type_name)


def _columns(destination):
    return [f for f in REGISTRY if f.in_spec and f.destination == destination]


def _column_names(destination):
    return [name for f in _columns(destination) for name in f.nwb_names if name not in INHERITED_COLUMNS]


def _sample(dtype, n):
    """n sample values of a registry dtype, with zero/False first to exercise falsy values."""
    if dtype == "text":
        return np.array([""] + ["a"] * (n - 1), dtype=object)[:n] if n else np.array([], dtype=object)
    if dtype == "bool":
        return np.array(([False, True] * n)[:n], dtype=bool)
    return np.arange(n, dtype=dtype)


def _make_columns(destination, n_rows):
    """Typed columns for every in-spec field of a table, in the form the converter hands to hdmf."""
    columns = []
    for field in _columns(destination):
        if field.dtype == "region":
            continue
        for name in field.nwb_names:
            if name in INHERITED_COLUMNS:
                continue
            description = field.description
            if field.shape == ():
                columns.append(VectorData(name=name, description=description, data=_sample(field.dtype, n_rows)))
            elif field.shape == (None,):
                flat = VectorData(name=name, description=description, data=_sample(field.dtype, n_rows * 2))
                index = VectorIndex(name=f"{name}_index", data=np.arange(1, n_rows + 1, dtype="uint32") * 2, target=flat)
                columns += [flat, index]
            elif field.shape == (None, None):
                flat = VectorData(name=name, description=description, data=_sample(field.dtype, n_rows * 2))
                inner = VectorIndex(name=f"{name}_index", data=np.arange(1, n_rows * 2 + 1, dtype="uint32"), target=flat)
                outer = VectorIndex(name=f"{name}_index_index", data=np.arange(1, n_rows + 1, dtype="uint32") * 2, target=inner)
                columns += [flat, inner, outer]
            else:
                width = field.shape[0]
                data = np.resize(_sample(field.dtype, width), (n_rows, width))
                columns.append(VectorData(name=name, description=description, data=data))
    return columns


def _make_table(cls, destination, n_rows, name, **kwargs):
    return cls(name=name, description=name, columns=_make_columns(destination, n_rows), **kwargs)


def _write_read_validate(tmp_path, build):
    nwbfile = NWBFile("description", "id", SESSION_START)
    build(nwbfile)
    path = tmp_path / "schema.nwb"
    with NWBHDF5IO(str(path), "w") as io:
        io.write(nwbfile)
    errors = validate(path=str(path))
    errors = errors[0] if isinstance(errors, tuple) else errors
    assert list(errors) == []
    return path


class TestSpecMatchesRegistry:
    @pytest.mark.parametrize("destination, type_name", sorted(TYPE_FOR_DESTINATION.items()))
    def test_every_in_spec_column_is_declared_optional(self, destination, type_name):
        declared = {d.name: d for d in _spec(type_name).datasets}
        for name in _column_names(destination):
            assert name in declared, f"{type_name}.{name} missing"
            assert declared[name].quantity == "?", name

    @pytest.mark.parametrize("destination, type_name", sorted(TYPE_FOR_DESTINATION.items()))
    def test_no_column_outside_the_registry_is_declared(self, destination, type_name):
        declared = {d.name for d in _spec(type_name).datasets}
        allowed = set(_column_names(destination)) | {f"{n}_index" for n in _column_names(destination)}
        allowed |= {f"{n}_index_index" for n in _column_names(destination)}
        own = {d.name for d in declared_own(type_name)}
        assert own <= allowed, own - allowed
        assert declared  # the type has columns at all

    @pytest.mark.parametrize("destination, type_name", sorted(TYPE_FOR_DESTINATION.items()))
    def test_column_dtypes_match(self, destination, type_name):
        declared = {d.name: d for d in _spec(type_name).datasets}
        for field in _columns(destination):
            for name in field.nwb_names:
                if name in INHERITED_COLUMNS or field.dtype == "region":
                    continue
                assert declared[name].dtype == field.dtype, name

    @pytest.mark.parametrize("destination, type_name", sorted(TYPE_FOR_DESTINATION.items()))
    def test_ragged_columns_declare_their_indexes(self, destination, type_name):
        declared = {d.name: d for d in _spec(type_name).datasets}
        for field in _columns(destination):
            for name in field.nwb_names:
                if name in INHERITED_COLUMNS or field.dtype == "region":
                    continue
                if field.shape == (None,):
                    assert declared[f"{name}_index"].neurodata_type_inc == "VectorIndex", name
                    assert f"{name}_index_index" not in declared
                elif field.shape == (None, None):
                    assert declared[f"{name}_index_index"].neurodata_type_inc == "VectorIndex", name
                else:
                    assert f"{name}_index" not in declared, name

    def test_stimulus_pair_is_a_region_column(self):
        declared = {d.name: d for d in _spec("VirmenTrials").datasets}
        assert declared["stimulus_pair"].neurodata_type_inc == "DynamicTableRegion"

    @pytest.mark.parametrize("destination, type_name", sorted(ATTRIBUTE_TYPE_FOR_DESTINATION.items()))
    def test_every_in_spec_attribute_is_declared(self, destination, type_name):
        declared = {a.name: a for a in _spec(type_name).attributes}
        for field in _columns(destination):
            assert field.name in declared, f"{type_name}.{field.name} missing"
            attribute = declared[field.name]
            assert attribute.dtype == field.dtype, field.name
            assert attribute.required == field.required, field.name

    def test_docs_carry_units_and_codes(self):
        declared = {d.name: d.doc for d in _spec("VirmenTrials").datasets}
        assert "iterations" in declared["iCueEntry"]
        assert "1=" in declared["forcedChoice"].replace(" = ", "=")

    def test_settings_only_fields_are_not_in_the_spec(self):
        attributes = {a.name for a in _spec("RigExtension").attributes}
        assert "laserIP" not in attributes
        assert "virmenIP" not in attributes

    def test_per_trial_fields_are_no_longer_maze_columns(self):
        declared = {d.name for d in _spec("MazeExtension").datasets}
        assert declared.isdisjoint({"rule", "forcedChoice", "StartCycle", "pairNum", "stimulusTable"})

    def test_maze_track_lengths_are_typed(self):
        declared = {d.name: d for d in _spec("MazeExtension").datasets}
        for name in ("lStart", "lCue", "lMemory"):
            assert declared[name].dtype == "float64"

    def test_settings_table_has_key_value_meaning(self):
        declared = {d.name: d for d in _spec("VirmenSettings").datasets}
        assert {"key", "value", "meaning"} <= set(declared)
        assert all(declared[n].dtype == "text" for n in ("key", "value", "meaning"))

    def test_trials_and_epochs_subclass_time_intervals(self):
        assert issubclass(VirmenTrials, TimeIntervals)
        assert issubclass(VirmenEpochs, TimeIntervals)


def declared_own(type_name):
    """Datasets this type declares itself, not those inherited from its parent."""
    spec = _spec(type_name)
    catalog = get_type_map().namespace_catalog
    namespace = "core" if spec.neurodata_type_inc == "TimeIntervals" else "hdmf-common"
    inherited = {d.name for d in catalog.get_spec(namespace, spec.neurodata_type_inc).datasets}
    return [d for d in spec.datasets if d.name not in inherited]


def _time_columns(n_rows):
    start = np.arange(n_rows, dtype="float64")
    return [
        VectorData(name="start_time", description="start", data=start),
        VectorData(name="stop_time", description="stop", data=start + 0.5),
    ]


def _full_table(cls, destination, n_rows, name):
    columns = [*_time_columns(n_rows), *_make_columns(destination, n_rows)]
    return cls(name=name, description=name, columns=columns)


class TestTrialsAndEpochs:
    @pytest.mark.parametrize("n_rows", [0, 1, 3])
    @pytest.mark.parametrize("cls, destination, attribute, name", [
        (VirmenTrials, "trial_column", "trials", "trials"),
        (VirmenEpochs, "epoch_column", "epochs", "epochs"),
    ])
    def test_all_columns_write_read_validate(self, tmp_path, cls, destination, attribute, name, n_rows):
        table = _full_table(cls, destination, n_rows, name)
        path = _write_read_validate(tmp_path, lambda nwbfile: setattr(nwbfile, attribute, table))
        with NWBHDF5IO(str(path), "r", load_namespaces=True) as io:
            back = getattr(io.read(), attribute)
            assert isinstance(back, cls)
            assert len(back) == n_rows

    def test_declared_dtypes_survive_on_disk(self, tmp_path):
        table = _full_table(VirmenTrials, "trial_column", 3, "trials")
        path = _write_read_validate(tmp_path, lambda nwbfile: setattr(nwbfile, "trials", table))
        with h5py.File(path, "r") as f:
            group = f["intervals/trials"]
            for field in _columns("trial_column"):
                if field.dtype in DTYPE_IN_FILE:
                    for name in field.nwb_names:
                        if name not in INHERITED_COLUMNS:
                            assert group[name].dtype == np.dtype(DTYPE_IN_FILE[field.dtype]), name

    def test_absent_optional_columns_cost_nothing(self, tmp_path):
        table = VirmenTrials(name="trials", description="t", columns=_time_columns(2))
        path = _write_read_validate(tmp_path, lambda nwbfile: setattr(nwbfile, "trials", table))
        with NWBHDF5IO(str(path), "r", load_namespaces=True) as io:
            assert set(io.read().trials.colnames) == {"start_time", "stop_time"}

    def test_empty_ragged_cell_round_trips(self, tmp_path):
        flat = VectorData(name="cuePos_left", description="d", data=np.array([1.5, 2.5], dtype="float32"))
        index = VectorIndex(name="cuePos_left_index", data=np.array([0, 2, 2], dtype="uint32"), target=flat)
        table = VirmenTrials(name="trials", description="t", columns=[*_time_columns(3), flat, index])
        path = _write_read_validate(tmp_path, lambda nwbfile: setattr(nwbfile, "trials", table))
        with NWBHDF5IO(str(path), "r", load_namespaces=True) as io:
            back = io.read().trials["cuePos_left"]
            assert [len(back[i]) for i in range(3)] == [0, 2, 0]
            assert back.target.data.dtype == np.dtype("float32")

    def test_nan_and_inf_round_trip(self, tmp_path):
        values = np.array([np.nan, np.inf], dtype="float64")
        column = VectorData(name="trialParams_cueMaxProbability", description="d", data=values)
        table = VirmenEpochs(name="epochs", description="e", columns=[*_time_columns(2), column])
        path = _write_read_validate(tmp_path, lambda nwbfile: setattr(nwbfile, "epochs", table))
        with NWBHDF5IO(str(path), "r", load_namespaces=True) as io:
            back = io.read().epochs["trialParams_cueMaxProbability"].data[:]
            assert np.isnan(back[0]) and np.isinf(back[1])


class TestStimulusPairs:
    def _pairs(self):
        return StimulusPairs(name="stimulus_pairs", description="pairs", columns=[
            VectorData(name="block", description="d", data=np.array([1, 1, 2], dtype="int32")),
            VectorData(name="PairNum", description="d", data=np.array([1, 2, 1], dtype="int32")),
            VectorData(name="Prob", description="d", data=np.array([0.0, 0.5, 1.0], dtype="float32")),
            VectorData(name="Side", description="d", data=np.array(["L", "R", "L"], dtype=object)),
            VectorData(name="Sa", description="d", data=np.array([3, 9, 16], dtype="float32")),
            VectorData(name="Sb", description="d", data=np.array([9, 3, 48], dtype="float32")),
        ])

    def test_trial_region_round_trips(self, tmp_path):
        pairs = self._pairs()

        def build(nwbfile):
            nwbfile.add_lab_meta_data(make_lab_metadata(stimulus_pairs=pairs))
            region = DynamicTableRegion(name="stimulus_pair", description="d", table=pairs, data=[2, 0])
            nwbfile.trials = VirmenTrials(name="trials", description="t", columns=[*_time_columns(2), region])

        path = _write_read_validate(tmp_path, build)
        with NWBHDF5IO(str(path), "r", load_namespaces=True) as io:
            read = io.read()
            assert isinstance(read.trials["stimulus_pair"], DynamicTableRegion)
            row = read.trials["stimulus_pair"][0]
            assert row["Sa"].iloc[0] == 16 and row["Side"].iloc[0] == "L"
            assert read.lab_meta_data["LabMetaData"].stimulus_pairs.colnames[0] == "block"

    def test_zero_rows(self, tmp_path):
        empty = StimulusPairs(name="stimulus_pairs", description="none")
        path = _write_read_validate(
            tmp_path, lambda nwbfile: nwbfile.add_lab_meta_data(make_lab_metadata(stimulus_pairs=empty))
        )
        with NWBHDF5IO(str(path), "r", load_namespaces=True) as io:
            assert len(io.read().lab_meta_data["LabMetaData"].stimulus_pairs) == 0

    def test_is_optional(self, round_trip):
        assert round_trip(make_lab_metadata()).stimulus_pairs is None


class TestAttributeTypes:
    @staticmethod
    def _value(field):
        if field.dtype == "isodatetime":
            return datetime(2026, 11, 1, 1, 30, tzinfo=timezone.utc)
        if field.shape == ():
            if field.dtype == "text":
                return "x"
            return np.zeros(1, dtype=field.dtype)[0].item()
        shape = tuple(2 if dim is None else dim for dim in field.shape)
        if field.dtype == "text":
            return ["x"] * shape[0]
        return np.zeros(shape, dtype=field.dtype)

    def _kwargs(self, destination):
        return {f.name: self._value(f) for f in _columns(destination)}

    def test_all_rig_attributes_round_trip(self, round_trip):
        rig = RigExtension(name="rig", **self._kwargs("rig_attribute"))
        back = round_trip(make_lab_metadata(rig=rig)).rig
        assert back.simulationMode is False or back.simulationMode == 0
        assert back.ballCircumference == 0

    def test_all_animal_attributes_round_trip(self, round_trip):
        animal = AnimalSettings(name="animal", **self._kwargs("animal_attribute"))
        back = round_trip(make_lab_metadata(animal=animal)).animal
        assert back.waterAlloc == 0
        assert back.rewardFactor.shape == (2, 2)

    def test_animal_settings_are_optional(self, round_trip):
        assert round_trip(make_lab_metadata()).animal is None

    def test_animal_attributes_are_all_optional(self, round_trip):
        back = round_trip(make_lab_metadata(animal=AnimalSettings(name="animal"))).animal
        assert back.waterAlloc is None

    def test_all_lab_metadata_attributes_round_trip(self, tmp_path):
        kwargs = self._kwargs("lab_meta_attribute")
        lab_meta = LabMetaDataExtension(name="LabMetaData", rig=RigExtension(name="rig"),
                                        mazes=MazeExtension(name="mazes", description="m"), **kwargs)
        _write_read_validate(tmp_path, lambda nwbfile: nwbfile.add_lab_meta_data(lab_meta))

    def test_required_lab_metadata_attributes_are_enforced(self):
        with pytest.raises(TypeError, match="session_end_time"):
            LabMetaDataExtension(name="LabMetaData", rig=RigExtension(name="rig"),
                                 mazes=MazeExtension(name="mazes", description="m"), num_trials=0)

    def test_initial_timestamp_keeps_its_offset(self, round_trip):
        stamp = datetime.fromisoformat("2026-11-01T01:30:00-05:00")
        assert round_trip(make_lab_metadata(initialTimestamp=stamp)).initialTimestamp == stamp


class TestMazes:
    @pytest.mark.parametrize("n_rows", [0, 1, 3])
    def test_all_columns_write_read_validate(self, tmp_path, n_rows):
        mazes = _make_table(MazeExtension, "maze_column", n_rows, "mazes")
        path = _write_read_validate(tmp_path, lambda nwbfile: nwbfile.add_lab_meta_data(make_lab_metadata(mazes=mazes)))
        with NWBHDF5IO(str(path), "r", load_namespaces=True) as io:
            assert len(io.read().lab_meta_data["LabMetaData"].mazes) == n_rows

    def test_ragged_criterion_with_empty_scalar_and_vector_cells(self, round_trip):
        # warmupNTrials is [] for no warmup, a scalar for one and a vector for several warmup mazes.
        flat = VectorData(name="warmupNTrials", description="d", data=np.array([10, 5, 30], dtype="float64"))
        index = VectorIndex(name="warmupNTrials_index", data=np.array([0, 1, 3], dtype="uint32"), target=flat)
        mazes = MazeExtension(name="mazes", description="m", columns=[flat, index])
        back = round_trip(make_lab_metadata(mazes=mazes)).mazes
        cells = [back["warmupNTrials"][i] for i in range(3)]
        assert [len(c) for c in cells] == [0, 1, 2]


class TestSettings:
    def _settings(self, rows):
        settings = VirmenSettings(name="settings", description="settings")
        for row in rows:
            settings.add_row(**row)
        return settings

    def test_rows_round_trip(self, round_trip):
        rows = [dict(key="log.version(1).variables.lCue", value="300", meaning="ViRMEn variable"),
                dict(key="log.animal.pretraining_instructions", value="", meaning="")]
        back = round_trip(make_lab_metadata(settings=self._settings(rows))).settings
        assert list(back["key"].data[:]) == [r["key"] for r in rows]
        assert list(back["value"].data[:]) == ["300", ""]

    def test_zero_rows(self, round_trip):
        assert len(round_trip(make_lab_metadata(settings=self._settings([]))).settings) == 0

    def test_is_optional(self, round_trip):
        assert round_trip(make_lab_metadata()).settings is None


def test_namespace_version_is_bumped_for_the_expansion():
    from ruamel.yaml import YAML

    namespace = YAML(typ="safe").load((REPO / "spec" / "ndx-tank-metadata.namespace.yaml").read_text())
    major, minor, _ = namespace["namespaces"][0]["version"].split(".")
    assert (int(major), int(minor)) >= (0, 4)


@pytest.mark.parametrize("name", ["VirmenTrials", "VirmenEpochs", "AnimalSettings", "StimulusPairs", "VirmenSettings"])
def test_new_types_are_registered(name):
    assert get_class(name, NAMESPACE) is not None


def test_file_reads_from_cached_spec_only(tmp_path):
    """A reader that never imported the extension can read it; the file carries its own schema."""
    import subprocess
    import sys

    path = _write_read_validate(tmp_path, lambda nwbfile: setattr(
        nwbfile, "trials", _full_table(VirmenTrials, "trial_column", 2, "trials")))
    code = (
        "import sys\nfrom pynwb import NWBHDF5IO\n"
        "with NWBHDF5IO(sys.argv[1], 'r', load_namespaces=True) as io:\n"
        "    t = io.read().trials\n"
        "    assert type(t).__name__ == 'VirmenTrials' and len(t) == 2\n"
        "    assert 'ndx_tank_metadata' not in sys.modules\n"
    )
    subprocess.run([sys.executable, "-c", code, str(path)], check=True, cwd=tmp_path)
