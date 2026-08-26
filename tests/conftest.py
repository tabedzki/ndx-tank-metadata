"""
Pytest configuration and fixtures for test suite.

Defines:
- Custom markers for test categorization (no_db, with_db)
- sys.path bootstrapping so u19_pipeline (U19-pipeline_python) tests can
  be run from the ndx-tank-metadata-clean venv without installing it as a
  package dependency.
"""

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path bootstrap — makes u19_pipeline importable in the test process.
# U19-pipeline_python lives next to ndx-tank-metadata-clean in the workspace.
# ---------------------------------------------------------------------------
_U19_PIPELINE_ROOT = Path(__file__).parent.parent.parent / "U19-pipeline_python"
if _U19_PIPELINE_ROOT.is_dir() and str(_U19_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_U19_PIPELINE_ROOT))


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "no_db: mark test as not requiring database connection (run without DataJoint DB)"
    )
    config.addinivalue_line(
        "markers", "with_db: mark test as requiring database connection (requires active DataJoint connection)"
    )
