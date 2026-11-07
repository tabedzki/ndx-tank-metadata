"""The committed YAML is exactly what create_extension_spec.py generates, and files written with it validate."""

import importlib.util
import re
from pathlib import Path

import pytest
from pynwb import NWBHDF5IO, validate
from ruamel.yaml import YAML

from tests.helpers import make_lab_metadata, write_nwb

REPO = Path(__file__).resolve().parent.parent
GENERATOR = REPO / "src" / "spec" / "create_extension_spec.py"
SPEC_DIRS = [REPO / "spec"]
SPEC_FILES = ["ndx-tank-metadata.namespace.yaml", "ndx-tank-metadata.extensions.yaml"]


def _load_generator():
    spec = importlib.util.spec_from_file_location("create_extension_spec", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse(path):
    return YAML(typ="safe").load(path.read_text())


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("spec")
    _load_generator().main(output_dir=str(out))
    return out


@pytest.mark.parametrize("spec_dir", SPEC_DIRS, ids=["spec"])
@pytest.mark.parametrize("filename", SPEC_FILES)
def test_committed_yaml_matches_generator(generated, spec_dir, filename):
    # Compare parsed YAML: line wrapping of long docs depends on the ruamel.yaml version.
    assert _parse(spec_dir / filename) == _parse(generated / filename)


def test_namespace_version_matches_generator():
    version = _load_generator().__version__
    for spec_dir in SPEC_DIRS:
        namespace = _parse(spec_dir / "ndx-tank-metadata.namespace.yaml")
        assert namespace["namespaces"][0]["version"] == version


def test_generated_yaml_has_no_non_schema_dtypes(generated):
    text = (generated / "ndx-tank-metadata.extensions.yaml").read_text()
    # utf-8 is a legal alias but the rest of the spec uses text; keep one spelling.
    assert not re.search(r"dtype:\s*utf-?8", text)


def test_namespace_loads_types():
    from pynwb import get_class

    for name in ["LabMetaDataExtension", "RigExtension", "MazeExtension"]:
        assert get_class(name, "ndx-tank-metadata") is not None


def test_written_file_passes_pynwb_validate(tmp_path):
    from ndx_tank_metadata import MazeExtension

    mazes = MazeExtension(name="mazes", description="mazes")
    mazes.add_row(world=1, lStart=5.0, turnHint_Mem=0, turnHint_Puff=False)
    path = write_nwb(tmp_path / "valid.nwb", make_lab_metadata(mazes=mazes))
    errors = validate(path=str(path))
    errors = errors[0] if isinstance(errors, tuple) else errors
    assert list(errors) == []


def test_written_file_caches_the_extension_namespace(tmp_path):
    path = write_nwb(tmp_path / "cached.nwb", make_lab_metadata())
    assert "ndx-tank-metadata" in NWBHDF5IO.get_namespaces(path=str(path))


def test_readme_example_runs(tmp_path, monkeypatch):
    readme = (REPO / "README.md").read_text()
    code = re.search(r"```python\n(.*?)```", readme, re.DOTALL).group(1)
    monkeypatch.chdir(tmp_path)
    exec(compile(code, "README.md", "exec"), {})
    errors = validate(path="test_labmetadata.nwb")
    errors = errors[0] if isinstance(errors, tuple) else errors
    assert list(errors) == []
