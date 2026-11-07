"""The ViRMEn field registry: where every field of a ViRMEn log goes in NWB.

``virmen_fields.yaml`` is the single source of truth. ``src/spec/create_extension_spec.py`` generates the
schema from its ``in_spec`` entries, and converters use it to coerce, validate and place each field.

To promote a field into the schema: edit its entry, bump the project version, rerun the generator.

This module must stay importable on its own (no pynwb): the generator loads it to create the spec that
importing the package requires.
"""

from dataclasses import dataclass, field, fields
from pathlib import Path

from ruamel.yaml import YAML

DESTINATIONS = frozenset(
    {
        "trial_column",  # column of the trials table
        "epoch_column",  # column of the epochs table
        "maze_column",  # column of the mazes table
        "stimulus_pairs_column",  # column of the StimulusPairs table
        "rig_attribute",  # attribute of RigExtension
        "animal_attribute",  # attribute of AnimalSettings
        "lab_meta_attribute",  # attribute of LabMetaDataExtension
        "timeseries",  # per-frame data stored as core TimeSeries types
        "timestamps",  # the frame clock shared by those TimeSeries
        "nwbfile",  # a core NWBFile field
        "subject",  # a core Subject field
        "settings",  # one row per value of the key/value VirmenSettings table
        "drop",  # deliberately not converted; notes says why
        "structural",  # a container whose members have their own entries
    }
)
SPEC_DESTINATIONS = frozenset(
    {
        "trial_column",
        "epoch_column",
        "maze_column",
        "stimulus_pairs_column",
        "rig_attribute",
        "animal_attribute",
        "lab_meta_attribute",
    }
)
_UNSTORED = frozenset({"drop", "structural"})
_INT_RANGES = {"int8": (-(2**7), 2**7 - 1), "int16": (-(2**15), 2**15 - 1), "int32": (-(2**31), 2**31 - 1)}
DTYPES = frozenset({"text", "bool", "float32", "float64", "isodatetime", "region", *_INT_RANGES})
TRANSFORMS = frozenset(
    {
        "enum_name",  # MATLAB enumeration member, stored by name
        "function_name",  # MATLAB function handle, stored by function name
        "datevec",  # MATLAB [Y M D h m s], stored as a timezone-aware datetime
        "seconds_from_session_start",  # datevec, stored as seconds since the session started
        "str2double",  # number logged as a MATLAB expression string
        "empty_to_missing",  # [] becomes NaN or the declared missing code in a column, and leaves an attribute out
        "complementary_pair",  # scalar p becomes [p, 1 - p]
        "pad_pair",  # scalar x becomes [x, NaN]
        "left_right",  # {left, right} cell or 2xN matrix, stored as <name>_left and <name>_right
        "licks",  # 2xN [iteration; value], stored as <name>_iteration and <name>_value
    }
)
_NAME_SUFFIXES = {"left_right": ("_left", "_right"), "licks": ("_iteration", "_value")}


class RegistryError(ValueError):
    """The registry contains an invalid entry."""


@dataclass(frozen=True)
class Field:
    """One ViRMEn log field. ``shape`` is the canonical shape of one value; None marks a variable length."""

    path: str
    destination: str
    description: str
    name: str | None = None
    dtype: str | None = None
    shape: tuple | None = None
    unit: str | None = None
    codes: dict | None = field(default=None, hash=False)
    transform: str | None = None
    missing: int | None = None  # integer code stored for NaN or []; other integer fields reject NaN
    in_spec: bool = False
    required: bool = False
    meaning_known: bool = True
    notes: str | None = None

    @property
    def nwb_names(self):
        """The NWB columns or attributes this field writes."""
        if not self.name or self.destination in _UNSTORED:
            return ()
        suffixes = _NAME_SUFFIXES.get(self.transform)
        return tuple(self.name + suffix for suffix in suffixes) if suffixes else (self.name,)

    @property
    def doc(self):
        """The description, with the unit and known codes: what a reader of the schema or file needs."""
        parts = [self.description.strip()]
        if self.unit:
            parts.append(f"Unit: {self.unit}.")
        if self.codes:
            parts.append("Codes: " + ", ".join(f"{code}={meaning}" for code, meaning in self.codes.items()) + ".")
        return " ".join(parts)


def _check_codes(entry):
    if entry.dtype in _INT_RANGES:
        low, high = _INT_RANGES[entry.dtype]
        valid = all(isinstance(code, int) and low <= code <= high for code in entry.codes)
    else:
        valid = entry.dtype == "text" and all(isinstance(code, str) for code in entry.codes)
    if not valid:
        raise RegistryError(f"{entry.path}: codes {list(entry.codes)} do not fit dtype {entry.dtype}")


def _check_field(entry):
    path = entry.path
    if entry.destination not in DESTINATIONS:
        raise RegistryError(f"{path}: unknown destination {entry.destination!r}")
    if not entry.description or not entry.description.strip():
        raise RegistryError(f"{path}: description is empty")
    if entry.transform is not None and entry.transform not in TRANSFORMS:
        raise RegistryError(f"{path}: unknown transform {entry.transform!r}")
    if entry.dtype is not None and entry.dtype not in DTYPES:
        raise RegistryError(f"{path}: unknown dtype {entry.dtype!r}")
    if entry.destination == "drop" and not entry.notes:
        raise RegistryError(f"{path}: a dropped field needs notes saying why")
    if entry.destination not in _UNSTORED and not (entry.name and entry.dtype and entry.shape is not None):
        raise RegistryError(f"{path}: a stored field needs name, dtype and shape")
    if entry.in_spec and entry.destination not in SPEC_DESTINATIONS:
        raise RegistryError(f"{path}: in_spec needs a spec destination, not {entry.destination!r}")
    if entry.in_spec and not entry.meaning_known:
        raise RegistryError(f"{path}: a field of unknown meaning cannot be in_spec")
    if entry.required and not entry.in_spec:
        raise RegistryError(f"{path}: required needs in_spec")
    if entry.codes:
        _check_codes(entry)
    if entry.missing is not None and (entry.dtype not in _INT_RANGES or entry.missing not in (entry.codes or {})):
        raise RegistryError(f"{path}: missing {entry.missing} must be a declared code of an integer field")


class Registry:
    """A validated set of fields, looked up by log path."""

    def __init__(self, entries):
        self._by_path = {}
        written_by = {}
        for entry in entries:
            _check_field(entry)
            if entry.path in self._by_path:
                raise RegistryError(f"{entry.path}: duplicate entry")
            self._by_path[entry.path] = entry
            if entry.destination == "settings":
                continue
            for name in entry.nwb_names:
                other = written_by.setdefault((entry.destination, name), entry.path)
                if other != entry.path:
                    raise RegistryError(f"{other} and {entry.path} both write {entry.destination}.{name}")

    def __iter__(self):
        return iter(self._by_path.values())

    def __len__(self):
        return len(self._by_path)

    def __getitem__(self, path):
        return self._by_path[path]

    def get(self, path):
        return self._by_path.get(path)


def _field_from_yaml(raw):
    known = {f.name for f in fields(Field)}
    unknown = set(raw) - known
    if unknown:
        raise RegistryError(f"{raw.get('path')}: unknown keys {sorted(unknown)}")
    values = dict(raw)
    if values.get("shape") is not None:
        values["shape"] = tuple(values["shape"])
    if values.get("codes") is not None:
        values["codes"] = dict(values["codes"])
    return Field(**values)


def load_registry(path=None):
    """Load and validate a registry file, by default the one shipped with this package."""
    path = Path(__file__).with_name("virmen_fields.yaml") if path is None else Path(path)
    document = YAML(typ="safe").load(path.read_text())
    return Registry(_field_from_yaml(raw) for raw in document["fields"])
