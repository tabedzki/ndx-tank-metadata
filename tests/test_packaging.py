"""Exercise release artifacts, never the editable checkout (requires uv and network/cache)."""

import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
from zipfile import ZipFile

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRATCH = Path(os.environ.get("PACKAGING_TMPDIR", tempfile.gettempdir()))
SPEC_FILES = {"ndx-tank-metadata.namespace.yaml", "ndx-tank-metadata.extensions.yaml"}
REGISTRY_IN_WHEEL = "ndx_tank_metadata/virmen_fields.yaml"
STRAY = {"__pycache__", "tests", ".claude", "uv.lock", ".specify"}


def run(*args, cwd):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("VIRTUAL_ENV", None)
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def wheel_files(path):
    with ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}


@pytest.fixture(scope="module")
def artifacts():
    with tempfile.TemporaryDirectory(prefix="ndx-packaging-", dir=SCRATCH) as directory:
        work = Path(directory)
        assert not work.is_relative_to(REPO)
        dist = work / "dist"
        for kind in ("wheel", "sdist"):
            run("uv", "build", "--python", "3.13", f"--{kind}", "--out-dir", str(dist), cwd=REPO)
        yield work, next(dist.glob("*.whl")), next(dist.glob("*.tar.gz"))


@pytest.mark.packaging
@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_distribution_installs_and_loads_namespace(artifacts, kind):
    work, wheel, sdist = artifacts
    files = wheel_files(wheel)
    assert {n for n in files if n.endswith((".yaml", ".yml"))} == {
        REGISTRY_IN_WHEEL, *(f"ndx_tank_metadata/spec/{name}" for name in SPEC_FILES)
    }
    assert not any(STRAY.intersection(Path(n).parts) or n.endswith(".pyc") for n in files)
    assert all(n.startswith(("ndx_tank_metadata/", "ndx_tank_metadata-")) for n in files)
    expected = {name: (REPO / "spec" / name).read_text() for name in SPEC_FILES}
    for name, text in expected.items():
        assert files[f"ndx_tank_metadata/spec/{name}"].decode() == text

    if kind == "sdist":
        source = work / "source"
        with tarfile.open(sdist) as archive:
            assert not any(
                {"__pycache__", ".claude", ".specify", "matnwb"}.intersection(Path(n).parts)
                or any(part in {".git", ".github", ".gitmodules", ".gitattributes"} for part in Path(n).parts)
                for n in archive.getnames()
            )
            assert not any("/src/pynwb/ndx_tank_metadata/spec/" in n for n in archive.getnames())
            archive.extractall(source, filter="data")
        run("uv", "build", "--python", "3.13", "--wheel", "--out-dir", str(work / "rebuilt"),
            cwd=next(source.iterdir()))
        # Compare every file, including metadata; RECORD describes the other files.
        rebuilt_wheel = next((work / "rebuilt").glob("*.whl"))
        assert wheel_files(rebuilt_wheel) == files

    venv = work / f"venv-{kind}"
    run("uv", "venv", "--python", "3.13", str(venv), cwd=work)
    python = str(venv / "bin" / "python")
    run("uv", "pip", "install", "--python", python, str(wheel if kind == "wheel" else rebuilt_wheel), cwd=work)
    output = run(python, "-I", "-c", '''
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import json
import ndx_tank_metadata as ndx
from ruamel.yaml import YAML
spec = Path(ndx.__file__).parent / "spec"
rig = ndx.RigExtension(name="rig")
mazes = ndx.MazeExtension(name="mazes", description="mazes")
mazes.add_row(world=1)
lab = ndx.LabMetaDataExtension(
    name="metadata", experiment_name="test", world_file_name="test", protocol_name="test",
    stimulus_bank_path="test", commit_id="test", location="test", num_trials=1,
    session_end_time=datetime.now(timezone.utc), rig=rig, mazes=mazes)
assert lab.rig is rig and lab.mazes is mazes
from ndx_tank_metadata.registry import load_registry
assert load_registry()["log.block.trial.choice"].in_spec
v = version("ndx-tank-metadata")
assert getattr(ndx, "__version__", v) == v
assert YAML(typ="safe").load((spec / "ndx-tank-metadata.namespace.yaml").read_text())["namespaces"][0]["version"] == v
print(json.dumps({"version": v, "spec": {p.name: p.read_text() for p in spec.glob("*.yaml")}}))
''', cwd=work)
    installed = json.loads(output)
    assert installed["spec"] == expected
    assert wheel.name.split("-")[1] == installed["version"]


@pytest.mark.packaging
def test_regeneration_writes_only_root_spec_from_project_version():
    # Stage the actual generator without an installed copy of this project nearby.
    import shutil
    import sys

    from ruamel.yaml import YAML

    with tempfile.TemporaryDirectory(prefix="ndx-generator-", dir=SCRATCH) as directory:
        checkout = Path(directory)
        generator = checkout / "src" / "spec" / "create_extension_spec.py"
        generator.parent.mkdir(parents=True)
        (checkout / "spec").mkdir()
        shutil.copyfile(REPO / "src" / "spec" / generator.name, generator)
        package = checkout / "src" / "pynwb" / "ndx_tank_metadata"
        package.mkdir(parents=True)
        for name in ("registry.py", "virmen_fields.yaml"):
            shutil.copyfile(REPO / "src" / "pynwb" / "ndx_tank_metadata" / name, package / name)
        (checkout / "pyproject.toml").write_text('[project]\nversion = "9.8.7"\n')
        run(sys.executable, "-I", str(generator), cwd=checkout)
        for name in SPEC_FILES:
            public = checkout / "spec" / name
            assert public.is_file()
        assert not (checkout / "src" / "pynwb" / "ndx_tank_metadata" / "spec").exists()
        ns = YAML(typ="safe").load((checkout / "spec" / "ndx-tank-metadata.namespace.yaml").read_text())
        assert ns["namespaces"][0]["version"] == "9.8.7"


def test_source_has_only_root_spec():
    assert not (REPO / "src" / "pynwb" / "ndx_tank_metadata" / "spec").exists()


@pytest.mark.packaging
def test_editable_install_loads_root_spec_once(artifacts):
    work, _, _ = artifacts
    venv = work / "venv-editable"
    run("uv", "venv", "--python", "3.13", str(venv), cwd=work)
    python = str(venv / "bin" / "python")
    run("uv", "pip", "install", "--python", python, "-e", str(REPO), cwd=work)
    output = run(python, "-I", "-c", """
from pathlib import Path
from unittest.mock import patch
import json
import pynwb
with patch("pynwb.load_namespaces", wraps=pynwb.load_namespaces) as load:
    import ndx_tank_metadata as ndx
assert load.call_count == 1
namespace = Path(load.call_args.args[0]).resolve()
assert not (Path(ndx.__file__).parent / "spec").exists()
assert ndx.MazeExtension(name="mazes", description="mazes") is not None
print(json.dumps(str(namespace)))
""", cwd=work)
    assert Path(json.loads(output)) == REPO / "spec" / "ndx-tank-metadata.namespace.yaml"
