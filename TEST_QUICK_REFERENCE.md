# Test Execution Quick Reference

## Daily Commands

### Run Fast Unit Tests (No Database)
```bash
pytest -m no_db
```
- ✅ Runs enums, imports, type validation
- ✅ ~1 second total
- ✅ No database setup needed
- ✅ Perfect for quick feedback

### Run All Tests
```bash
pytest tests/
```
- Runs everything (no_db + with_db)
- ~30+ seconds (if database available)
- Requires DataJoint connection

### Run Integration Tests (Database Required)
```bash
pytest -m with_db
```
- ✅ Tests DataJoint operations
- ✅ Requires database connection
- ✅ ~20+ seconds

## Specific Test Patterns

### Run One Test Class
```bash
pytest tests/test_nwb_export_handler.py::TestNwbExportStatusEnum -v
```

### Run One Test Method
```bash
pytest tests/test_nwb_export_handler.py::TestNwbExportStatusEnum::test_enum_defines_all_required_states -v
```

### Run with Verbose Output
```bash
pytest -m no_db -v
```

### Run with Coverage
```bash
pytest tests/ --cov=u19_pipeline --cov-report=html
```

## Test Categories

| Command | Tests | Time | DB? |
|---------|-------|------|-----|
| `pytest -m no_db` | 5 enum/import | <1s | ❌ |
| `pytest -m with_db` | 20+ DataJoint | ~20s | ✅ |
| `pytest tests/` | All ~25+ | ~30s | ✅ |

## Before Committing

```bash
# 1. Fast check (always safe)
pytest -m no_db

# 2. Full verification (if DB available)
pytest tests/

# ✅ Then commit!
```

## CI/CD Recommended Matrix

```bash
# Pipeline Stage 1: Fast checks (run always)
pytest -m no_db

# Pipeline Stage 2: Integration (only if Stage 1 passes)
pytest -m with_db
```

## Adding to Your Git Workflow

```bash
# Make changes...

# ✅ Quick validation
pytest -m no_db

# ✅ Full validation (before git push)
pytest tests/

# ✅ Push
git push
```

## Where are the Tests?

```
ndx-tank-metadata-clean/
└── tests/
    ├── __init__.py
    ├── conftest.py          # Marker configuration
    └── test_nwb_export_handler.py  # Main test file
```

## What Each Marker Means

**`@pytest.mark.no_db`**
- No database required
- Test enums, imports, types
- Fast (<1 second)
- Run anytime, anywhere

**`@pytest.mark.with_db`**
- Database connection required
- Test DataJoint operations
- Slower (~1 second each)
- Requires configured DataJoint

## Troubleshooting

### Pytest says "marker not registered"
```bash
# Make sure you're in project root
cd /Users/ct5868/code/ndx-tank-metadata-clean/

# Check conftest exists
ls tests/conftest.py
```

### Can't import u19_pipeline
```bash
# Install in development mode
pip install -e /Users/ct5868/code/U19-pipeline_python

# Then run from project root
pytest -m no_db
```

### Database connection error
```bash
# If your tests need DB, check configuration
# For now, run only no_db tests
pytest -m no_db

# Actual DB tests can wait until DB is configured
```

## For More Details

See **`TESTING.md`** for comprehensive guide:
- Full test organization
- CI/CD integration strategies
- Best practices
- All troubleshooting

See **`TEST_REORGANIZATION.md`** for:
- Migration details
- Before/after comparison
- Benefits explanation
