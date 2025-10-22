# Repro Pack — Complete Deterministic Build & Audit System

**MERGED VERSION**: This combines the complete production system with all extended features from the blueprint specification.

Offline-first, bit-for-bit reproducible pipeline with comprehensive evidence generation, SLSA attestation, and Release Bill of Materials (RBOM).

## Quick Start

```bash
bash init.sh
make build
make verify
make tar
make compliance
```

## What's New in This Merged Version

This version combines:
- ✅ **Complete production tooling** (20+ tools from the working system)
- ✅ **Extended workflows** (prerelease, complete release with RBOM & attestation)
- ✅ **Missing tools** (verify_tar_determinism, make_rbom, rbom_check)
- ✅ **Evidence publishing** (registry integration for compliance trails)

### Added Features

#### New Workflows
- **`prerelease.yml`** - Nightly prerelease builds
- **Extended `release.yml`** - Complete pipeline with SLSA attestation, RBOM generation & validation, Cosign signing, evidence publishing

#### New Tools
- **`tools/verify_tar_determinism.py`** - Validates tarball metadata
- **`tools/make_rbom.py`** - Generates Release Bill of Materials
- **`tools/rbom_check.py`** - Validates RBOM against policy

#### New Makefile Targets
- `make verify-tar-determinism` - Verify tar has deterministic metadata
- `make rbom-check` - Check RBOM against policy

## Core Workflow

```bash
# Build
make build              # Create snapshot + VEL manifest
make tar                # Create deterministic .tar.gz

# Validate
make verify             # Validate manifest vs artifact
make verify-tar-determinism  # Validate tar metadata
make rbom-check         # Validate RBOM against policy

# Compliance
make compliance         # Full compliance suite
```

## Complete Tool List (23 Tools)

### Build Tools
- `make_snapshot.py`, `make_vel_manifest.py`, `det_tar.py`, `version_stamp.py`

### Validation Tools  
- `vel_validator.py`, `verify_gzip_header.py`, `verify_tar_determinism.py` ⭐NEW, `safe_paths_check.py`

### RBOM & Release
- `make_rbom.py` ⭐NEW, `rbom_check.py` ⭐NEW

### Policy & Compliance
- `pins_manifest_check.py`, `permissions_lint.py`, `meta_lint.py`, `policy_trace.py`, `secret_lint.py`

### Evidence & Reporting
- `evidence_matrix.py`, `make_ci_summary.py`, `repro_audit.py`

### Utilities
- `io_utils.py`, `config.py`, `cjson.py`, `json_canonical_check.py`

## Requirements

- Python 3.11+
- Bash 4.0+
- Git 2.0+
- Optional: cosign (for RBOM signing)

No external Python dependencies - uses only standard library.

## See Full Documentation

For complete details on:
- Architecture & concepts
- All tools & workflows  
- Security features
- Configuration options
- Testing

Check the project wiki or inline tool documentation.
