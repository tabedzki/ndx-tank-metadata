"""Generate the extension's YAML from the field registry (src/pynwb/ndx_tank_metadata/virmen_fields.yaml).

Every in_spec registry entry becomes a column or attribute here. Add fields by editing the registry, not this file.
"""

import importlib.util
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 (development dependency)
    import tomli as tomllib

from hdmf.spec import AttributeSpec
from pynwb.spec import NWBDatasetSpec, NWBGroupSpec, NWBNamespaceBuilder, export_spec

REPO = Path(__file__).resolve().parents[2]
# The checkout version takes precedence over potentially stale installed metadata.
with (REPO / "pyproject.toml").open("rb") as project_file:
    __version__ = tomllib.load(project_file)["project"]["version"]

PACKAGE = REPO / "src" / "pynwb" / "ndx_tank_metadata"
# TimeIntervals columns the core schema already declares.
INHERITED_COLUMNS = {"start_time", "stop_time"}


def _load_registry():
    # Load the file directly: importing the package needs the spec this script writes.
    module_spec = importlib.util.spec_from_file_location("_virmen_registry", PACKAGE / "registry.py")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module  # dataclasses look their module up here
    module_spec.loader.exec_module(module)
    return module.load_registry(PACKAGE / "virmen_fields.yaml")


def _dims(shape):
    return [f"dim_{i}" for i in range(len(shape))]


def _index_spec(name, target):
    return NWBDatasetSpec(
        name=f"{name}_index",
        neurodata_type_inc="VectorIndex",
        doc=f"Index into {target}, which has a variable number of values per row.",
        quantity="?",
    )


def _column_specs(field):
    """The datasets of one registry field: its columns, each with the indexes its shape needs."""
    specs = []
    for name in field.nwb_names:
        if name in INHERITED_COLUMNS:
            continue
        if field.dtype == "region":
            specs.append(
                NWBDatasetSpec(name=name, neurodata_type_inc="DynamicTableRegion", doc=field.doc, quantity="?")
            )
            continue
        depth = sum(dim is None for dim in field.shape)
        fixed = field.shape if depth == 0 else ()
        shape = {"shape": [None, *fixed], "dims": ["num_rows", *_dims(fixed)]} if fixed else {}
        specs.append(
            NWBDatasetSpec(
                name=name, neurodata_type_inc="VectorData", dtype=field.dtype, doc=field.doc, quantity="?", **shape
            )
        )
        target = name
        for _ in range(depth):
            specs.append(_index_spec(target, target))
            target = f"{target}_index"
    return specs


def _attribute_spec(field):
    shape = {"shape": list(field.shape), "dims": _dims(field.shape)} if field.shape else {}
    return AttributeSpec(name=field.name, doc=field.doc, dtype=field.dtype, required=field.required, **shape)


def _in_spec(registry, destination):
    return [field for field in registry if field.in_spec and field.destination == destination]


def _table(registry, destination, type_name, parent, doc):
    datasets = [spec for field in _in_spec(registry, destination) for spec in _column_specs(field)]
    return NWBGroupSpec(doc=doc, neurodata_type_def=type_name, neurodata_type_inc=parent, datasets=datasets)


def _attribute_type(registry, destination, type_name, doc, groups=()):
    return NWBGroupSpec(
        doc=doc,
        neurodata_type_def=type_name,
        neurodata_type_inc="LabMetaData",
        attributes=[_attribute_spec(field) for field in _in_spec(registry, destination)],
        groups=list(groups),
    )


def _settings_table():
    columns = (
        ("key", "ViRMEn log path of the value, with 1-based indexes for struct arrays."),
        ("value", "The recorded value, as text."),
        # Not "description": a column of that name collides with the table's own description attribute.
        ("meaning", "What the value means, from the field registry."),
    )
    return NWBGroupSpec(
        doc="Key/value table of ViRMEn settings whose meaning is unknown or defined by each experiment.",
        neurodata_type_def="VirmenSettings",
        neurodata_type_inc="DynamicTable",
        datasets=[NWBDatasetSpec(name=name, neurodata_type_inc="VectorData", dtype="text", doc=doc) for name, doc in columns],
    )


def main(output_dir=None):
    registry = _load_registry()
    ns_builder = NWBNamespaceBuilder(
        doc="type for storing metadata for Tank lab",
        name="ndx-tank-metadata",
        version=__version__,
        author=["Szonja Weigl", "Luiz Tauffer", "Ben Dichter", "Christian Tabedzki"],
        contact=["ben.dichter@gmail.com", "ct5868@princeton.edu"],
    )
    for type_name in ("LabMetaData", "DynamicTable", "TimeIntervals", "VectorData", "VectorIndex", "DynamicTableRegion"):
        ns_builder.include_type(type_name, namespace="core")

    groups = [
        NWBGroupSpec(name="rig", neurodata_type_inc="RigExtension", doc="type for storing rig information"),
        NWBGroupSpec(name="mazes", neurodata_type_inc="MazeExtension", doc="type for storing maze information"),
        NWBGroupSpec(name="animal", neurodata_type_inc="AnimalSettings", doc="settings of the animal", quantity="?"),
        NWBGroupSpec(name="settings", neurodata_type_inc="VirmenSettings", doc="other ViRMEn settings", quantity="?"),
        NWBGroupSpec(
            name="stimulus_pairs", neurodata_type_inc="StimulusPairs", doc="stimulus pairs (PWM task)", quantity="?"
        ),
    ]
    new_types = [
        _attribute_type(
            registry, "lab_meta_attribute", "LabMetaDataExtension", "type for storing metadata for Brody and Tank labs", groups
        ),
        _attribute_type(registry, "rig_attribute", "RigExtension", "type for storing rig information"),
        _attribute_type(registry, "animal_attribute", "AnimalSettings", "settings of the animal from the training GUI"),
        _table(registry, "maze_column", "MazeExtension", "DynamicTable", "type for storing maze information, one row per maze"),
        _table(registry, "trial_column", "VirmenTrials", "TimeIntervals", "ViRMEn trials, one row per trial"),
        _table(registry, "epoch_column", "VirmenEpochs", "TimeIntervals", "ViRMEn blocks, one row per block"),
        _table(
            registry, "stimulus_pairs_column", "StimulusPairs", "DynamicTable",
            "Stimulus pairs (PWM task), one row per (block, pair): the pair set can change between blocks",
        ),
        _settings_table(),
    ]
    # Export once: export_spec mutates the namespace builder by adding its types.
    directory = REPO / "spec" if output_dir is None else Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    export_spec(ns_builder, new_types, str(directory))


if __name__ == "__main__":
    main()
