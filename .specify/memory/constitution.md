<!-- SYNC IMPACT REPORT: Constitution v1.1.1 TDD Workflow Clarification (2026-02-24)
================================================================================
VERSION CHANGE: v1.1.0 → v1.1.1 (PATCH)
RATIONALE: Clarified TDD approval workflow—tests approved locally, not in draft PRs.
Tests + implementation submitted together to PR (no test-only PRs).

CHANGES MADE:
✅ CLARIFIED Principle V: Test approval happens locally, before PR is opened
✅ REFINED Development Workflow: Updated 4-phase process to 5-phase with explicit
   Phase 2 (Local) and Phase 5 (Open PR) separation:
   Phase 1: Test Design (local)
   Phase 2: Test Approval (local, outside PR)
   Phase 3: Implementation (after local approval)
   Phase 4: Refactor (clean code)
   Phase 5: Open PR (tests + implementation together, no test-only PRs)
✅ CLARIFIED Approval Gates: PR review verifies tests were approved locally BEFORE
   implementation (not approved as part of PR)

NO PRINCIPLE CHANGES: Workflow refinement only
VERSIONING: v1.1.0 → v1.1.1 (PATCH per policy: clarifications + wording refinements)

KEY DISTINCTION:
- v1.1.0: Tests approved "in draft PR"
- v1.1.1: Tests approved "locally before PR opens"
- Result: Tests + implementation code enter PR together, no separate test PRs

NO UNEXPLAINED PLACEHOLDERS: ✅ (All tokens resolved)
DATES IN ISO FORMAT (YYYY-MM-DD): ✅
VERSIONING RULES DEFINED: ✅
PRINCIPLES DECLARATIVE & TESTABLE: ✅
================================================================================ -->

# ndx-tank-metadata Constitution

## Core Principles

### I. DataJoint-First Database Access

MUST use DataJoint for all database operations. DataJoint abstracts database complexity and enables
seamless integration with the BrainCOGS U19-pipeline and other external systems that depend on
DataJoint-based schemas. No direct SQL calls or alternative ORMs. This ensures consistency across
the ecosystem and simplifies deployment in containerized environments.

### II. Modern Python Practices (Python >=3.12)

Target and enforce Python 3.12+. Use type hints on all public functions and classes. Leverage
newer language features (pattern matching, structural subtyping, improved performance). This ensures
better IDE support, safer refactoring, and clearer intent. All dependencies MUST support Python 3.12+.

### III. Structural Reuse Before Creation

Before adding new models, schemas, enums, or database tables, verify they don't already exist in:
- The local `src/` and `tests/` directories
- The BrainCOGS U19-pipeline (submodule or external dependency)
- Published NWB extensions (ndx-tank-metadata or other ndx-* packages in use)

Reuse reduces duplication, simplifies maintenance, and strengthens ecosystem coherence.

### IV. Explicit State Modeling via Enums (NON-NEGOTIABLE)

Use Python `Enum` classes to model all domain states (e.g., task status, rig state, session phase,
maze difficulty). Enums provide:
- Type-safe state representation (no magic strings)
- Clear enumeration of valid states (discoverability)
- IDE autocomplete and linting support
- Self-documenting constraints

Enums MUST be defined in dedicated `enums.py` or alongside models. Every DataJoint table using
states or categorical values MUST reference an Enum in its comments or type hints.

### V. Test-First Development (NON-NEGOTIABLE)

TDD mandatory: Test design and approval MUST precede implementation. Red-Green-Refactor cycle
strictly enforced: (1) Write failing tests locally → (2) Get approval locally → (3) Implement to
pass tests → (4) Refactor. Tests FIRST, code AFTER. Every new feature must have unit, integration,
and contract tests written and approved before any implementation code is committed. Approval
happens locally before opening any PR. Each feature must be independently testable—if only that
feature is implemented, it must deliver standalone value. Integration tests MUST verify interaction
with DataJoint schemas and external systems (BrainCOGS pipeline).

## Technology Stack & Constraints

- **Language**: Python >=3.12 (no older versions supported)
- **Database Access**: DataJoint MUST be used for all DB operations
- **Primary Dependencies**: pynwb >=3.0.0, datajoint
- **Testing Framework**: pytest with pytest-cov for coverage tracking
- **Type Checking**: Use type hints; Pylance/pyright for static analysis
- **Code Quality**: Black for formatting, isort for imports, ruff for linting

**Rationale**: DataJoint integration is non-negotiable for ecosystem compatibility with BrainCOGS.
Modern Python ensures performance, type safety, and long-term maintainability.

## Development Workflow & Review

1. **Feature Branch**: Create branch from `main` (e.g., `feature/enum-states` or `fix/datajoint-schema`)
2. **Test-Driven Development (Mandatory Process)**:
   - **Phase 1 - Test Design (Local)**: Write failing unit, integration, and contract tests that define the feature
   - **Phase 2 - Test Approval (Local)**: Submit tests for maintainer review locally (outside of PR); tests must fail before approval
   - **Phase 3 - Implementation**: After local approval, implement code to pass ALL tests (Red-Green-Refactor)
   - **Phase 4 - Refactor**: Clean up implementation while maintaining test pass rate
   - **Phase 5 - Open PR**: Submit feature branch with tests + implementation together to PR (no test-only PRs)
   - **No Implementation Code Without Approved Tests**: Zero exceptions—feature code without pre-written, locally-approved tests will be rejected
3. **Code Quality During Development**:
   - Check existing structures first (principle III)
   - Write Enum definitions before any code that uses categorical data (principle IV)
   - Include type hints on all public functions (principle II)
   - Use DataJoint for all DB queries (principle I)
4. **Test Execution**: Run full test suite (pytest) before submitting PR; verify ≥80% coverage on new code
5. **Code Review**: All PRs require:
   - Verification that tests were written and approved locally BEFORE implementation (principle V)
   - Principle compliance verification (DataJoint use, Enum modeling, no duplication)
   - Minimum Python 3.12 compatibility
   - Test coverage for new code (≥80%)
   - Documentation for public APIs and schema changes
6. **Merge**: Squash and merge to maintain clean history; delete feature branch

**Approval Gate**: PR merge blocked until:
- All tests pass (unit, integration, contract)
- Code review approved
- Tests pre-date and pre-approved before implementation (TDD process verified)
- No unresolved principle violations

## Governance

**Constitution Authority**: This document is the source of truth for all development practices.
Practices not documented here MUST NOT override these principles.

**Amendment Process**:
1. Open issue documenting the change rationale and impact
2. Propose updated constitution text (create amendment branch)
3. Review by project maintainers for consistency and feasibility
4. Merge amendment; update LAST_AMENDED_DATE and bump version
5. All new guide docs and templates aligned with amendment within one sprint

**Compliance Verification**:
- Every PR title or description MUST cite which principles it addresses (e.g., "feat: add RigStateEnum (Principle IV)")
- Feature plans MUST note principle-driven structure decisions upfront: "Uses Enum for status modeling (Principle IV)"
- Task lists MUST include principle-auditing tasks where violations are suspected (e.g., "Audit schema for DataJoint usage")

**Versioning**: MAJOR.MINOR.PATCH
- **MAJOR**: Removal or redefinition of a core principle (rare; alignment required)
- **MINOR**: New principle added or existing principle expanded with mandatory new requirements
- **PATCH**: Clarifications, wording refinements, grammar/typo fixes, non-semantic guidance updates

**Version**: 1.1.1 | **Ratified**: 2026-02-24 | **Last Amended**: 2026-02-24
