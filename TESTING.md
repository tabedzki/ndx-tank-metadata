# Test Organization Guide

## Overview

Tests for ndx-tank-metadata NWB export handler are organized in the `tests/` directory with categorization by database dependency.

## Directory Structure

```
ndx-tank-metadata-clean/
├── tests/
│   ├── __init__.py                              # Package marker
│   ├── conftest.py                              # Pytest configuration, markers & sys.path bootstrap
│   ├── test_ndx_tank_metadata.py               # NWB extension tests
│   ├── test_nwb_export_handler.py              # Legacy integration test suite
│   └── nwb_export/                             # Feature 001 modular tests
│       ├── __init__.py
│       ├── test_status_enums.py                # T075 — NwbExportStatusEnum (no_db)
│       ├── test_errors.py                      # T076 — exception hierarchy (no_db)
│       ├── test_config.py                      # T077 — pipeline constants (no_db)
│       ├── test_state_machine.py               # T015 — state transitions (no_db)
│       └── test_dandi_credentials.py           # T010 — AES-256-GCM encrypt/decrypt (no_db)
├── pyproject.toml                              # Pytest configuration
└── specs/
    └── 001-nwb-export-handler/
        └── tasks.md                            # Implementation task list
```

## Test Markers

Tests are categorized using pytest markers to distinguish between database-dependent and database-independent tests:

### `@pytest.mark.no_db`

**Use case**: Tests that don't require database connection

**Examples**:
- Enum validation tests (checking state definitions exist)
- Import tests (verifying modules load)
- Type/signature validation tests
- Any test using only mocks, not real DataJoint operations

**Run only no_db tests**:
```bash
pytest -m no_db
```

**Run no_db tests with verbose output**:
```bash
pytest -m no_db -v
```

### `@pytest.mark.with_db`

**Use case**: Tests that require active database connection

**Examples**:
- DataJoint table creation and queries
- Job submission and status tracking
- Credential storage and retrieval
- Status transition logging
- Validation result storage

**Run only with_db tests**:
```bash
pytest -m with_db
```

**Run with_db tests with verbose output**:
```bash
pytest -m with_db -v
```

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Categories

**Unit tests (no database required)**:
```bash
pytest -m no_db
# Runs quickly, no setup needed
```

**Integration tests (database required)**:
```bash
pytest -m with_db
# Requires DataJoint connection configured
```

### Run Specific Test Files
```bash
pytest tests/test_nwb_export_handler.py
```

### Run Specific Test Class
```bash
# Run all tests in TestNwbExportStatusEnum (no_db)
pytest tests/test_nwb_export_handler.py::TestNwbExportStatusEnum

# Run all tests in TestNwbExportJobSchema (with_db)
pytest tests/test_nwb_export_handler.py::TestNwbExportJobSchema
```

### Run Specific Test Method
```bash
pytest tests/test_nwb_export_handler.py::TestNwbExportStatusEnum::test_enum_defines_all_required_states
```

## Test Organization by Marker

### No Database Required (`@pytest.mark.no_db`)

```python
@pytest.mark.no_db
class TestNwbExportStatusEnum:
    """Tests for NWB export status enumeration."""
    # - test_enum_defines_all_required_states
    # - test_enum_has_numeric_values
    # - test_enum_ordered_by_pipeline_stage
```

Tests enum definitions without touching database. Can run as unit tests in CI/CD.

### Database Required (`@pytest.mark.with_db`)

```python
@pytest.mark.with_db
class TestNwbExportJobSchema:
    """Tests for NwbExportJob DataJoint table."""
    # - test_job_creation_with_valid_session
    # - test_job_has_auto_increment_id
    # - test_job_tracks_actual_file_size

@pytest.mark.with_db
class TestNwbExportModalityTable:
    """Tests for NwbExportModality association table."""
    # - test_associate_behavior_modality
    # - test_associate_ephys_modality_raw
    # - test_associate_imaging_modality_processed
    # - test_support_multiple_modalities_per_job

@pytest.mark.with_db
class TestDandiCredentialsTable:
    """Tests for DANDI credential storage."""
    # - test_store_dandi_credentials
    # - test_credentials_encryption_field_exists
    # - test_missing_api_key_allowed
    # - test_missing_dandiset_allowed

@pytest.mark.with_db
class TestNwbExportLogStatus:
    """Tests for status transition logging."""
    # - test_log_status_transition
    # - test_log_captures_error_on_failure
    # - test_query_full_job_history

@pytest.mark.with_db
class TestNwbExportValidation:
    """Tests for NWB output validation results."""
    # - test_store_validation_results
    # - test_validation_with_warnings
```

Tests DataJoint operations and require database connection. Run only in environments with configured database.

### Mixed Marker (`TestNwbExportHandler`)

Some test classes have both markers applied at method level:

```python
class TestNwbExportHandler:
    """Handler tests - some no_db, some with_db."""

    @pytest.mark.no_db
    def test_handler_can_be_imported(self):
        """No database required - just imports."""

    @pytest.mark.with_db
    @patch('u19_pipeline.nwb_production.NwbExportJob')
    def test_pipeline_handler_queries_active_jobs(self, mock_nwb_job):
        """Database required - tests job queries."""

    @pytest.mark.with_db
    def test_data_validation_returns_tuple(self):
        """Database required - tests job state."""
```

## Configuration Files

### `tests/conftest.py`

Registers custom pytest markers:
```python
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "no_db: mark test as not requiring database connection"
    )
    config.addinivalue_line(
        "markers",
        "with_db: mark test as requiring database connection"
    )
```

### `pyproject.toml`

Pytest configuration:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "no_db: mark test as not requiring database connection (run without DataJoint DB)",
    "with_db: mark test as requiring database connection (requires active DataJoint connection)",
]
```

## CI/CD Integration

### Development Workflow

```bash
# 1. Run fast no_db tests first (no setup needed)
pytest -m no_db

# 2. If no_db tests pass, run with_db tests (requires DB)
pytest -m with_db

# 3. Run everything
pytest tests/
```

### Recommended CI Pipeline

```yaml
# Stage 1: Fast unit tests (no database)
pytest -m no_db

# Stage 2: Integration tests (database required)
# (conditional, only if Stage 1 passes)
pytest -m with_db
```

## Best Practices

1. **Keep no_db tests fast**: They should run in < 1 second total
2. **Mark mocked tests as `no_db`**: Use when testing with `@patch` decorators
3. **Mark actual DB operations as `with_db`**: Any direct DataJoint `.insert1()`, `.fetch()`, etc.
4. **Document database requirements**: Include "Database connection required" in docstring
5. **Individual method markers**: For mixed test classes, mark methods individually, not the class

## Adding New Tests

### For enum/import tests (no_db):
```python
@pytest.mark.no_db
class TestNewFeature:
    """Tests for feature that doesn't touch database."""

    def test_something(self):
        """No database required."""
        pass
```

### For database operations (with_db):
```python
@pytest.mark.with_db
class TestNewFeature:
    """Tests for feature requiring database."""

    def test_something(self):
        """Database connection required."""
        nwb_production.SomeTable.insert1({...})
```

### For mixed test classes:
```python
class TestMixedFeature:
    """Some tests need DB, some don't."""

    @pytest.mark.no_db
    def test_import(self):
        """No database."""
        pass

    @pytest.mark.with_db
    def test_database_operation(self):
        """Database required."""
        nwb_production.SomeTable.insert1({...})
```

## Troubleshooting

**"Marker 'no_db' not registered" error**:
- Ensure `tests/conftest.py` exists in tests directory
- Ensure `pyproject.toml` has `[tool.pytest.ini_options]` section with markers list

**Tests still trying to access database**:
- Check that all DataJoint operations are marked with `@pytest.mark.with_db`
- Verify fixtures creating database records are only used by with_db tests

**Can't import modules in tests**:
- Ensure `tests/__init__.py` exists (even if empty)
- Check that `u19_pipeline` is installed/discoverable
- Run pytest from project root: `pytest` not `pytest tests/test_file.py` from within tests/

## Summary

| Marker | Use | Speed | Database | Run |
|--------|-----|-------|----------|-----|
| `@pytest.mark.no_db` | Unit tests, imports, enums | Fast | Not needed | `pytest -m no_db` |
| `@pytest.mark.with_db` | Integration tests, DataJoint ops | Slower | Required | `pytest -m with_db` |
| Both | Mixed test classes | Varies | Conditional | `pytest -m no_db` then `pytest -m with_db` |
