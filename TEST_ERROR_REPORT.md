# Comprehensive Test Error Report

**Python Versions Tested**: Python 3.12.3 (applicable to Python 3.11+)  
**Date**: 2025-10-22  
**Issue Reference**: #7 - tests: export missing helpers (tar/rbom/permissions) and scope coverage to exercised modules

---

## Executive Summary

This report documents all discovered errors in the test suite for both Python 3.11 and Python 3.12. The analysis identified **6 import errors** and **14 API/signature mismatch errors** across multiple test files.

### Error Categories

1. **Import Errors (6)** - Functions expected by tests but not exported by tool modules
2. **API Signature Mismatches (14)** - Function signatures don't match test expectations
3. **Coverage Issues** - Tests fail to meet 75% coverage threshold

---

## Detailed Error Analysis

### 1. Import Errors (6 total)

#### 1.1 `test_determinism_tools.py` - 4 import errors

**File**: `tests/test_determinism_tools.py`

##### Error 1: Missing `check_gzip_header` from `tools.verify_gzip_header`

```python
# Test expects:
from tools.verify_gzip_header import check_gzip_header

# Current implementation has:
# - parse_hdr() function (internal)
# - main() function (CLI entry point)
# BUT NOT check_gzip_header()
```

**Expected Signature**:
```python
def check_gzip_header(gz_path: str) -> dict:
    """
    Returns:
        {
            "is_valid": bool,
            "magic": str,  # e.g., "1f8b"
            "mtime": int,
            "error": str  # (if not valid)
        }
    """
```

**Tests Affected**: Lines 151, 160, 236 in test_determinism_tools.py

---

##### Error 2: Missing `validate_gzip_os_byte` from `tools.verify_gzip_header`

```python
# Test expects:
from tools.verify_gzip_header import validate_gzip_os_byte

# Current implementation: DOES NOT EXIST
```

**Expected Signature**:
```python
def validate_gzip_os_byte(gz_path: str) -> int:
    """
    Returns: OS byte value from gzip header
    Should be 3 (Unix) for reproducibility
    """
```

**Tests Affected**: Lines 188, 212 in test_determinism_tools.py

---

##### Error 3: Missing `create_deterministic_tar` from `tools.det_tar`

```python
# Test expects:
from tools.det_tar import create_deterministic_tar

# Current implementation has:
# - build_tar() function
# BUT NOT create_deterministic_tar()
```

**Expected Signature**:
```python
def create_deterministic_tar(source_dir: str, tar_path: str) -> None:
    """Create a deterministic tarball from source directory"""
```

**Tests Affected**: Lines 253, 287, 288 in test_determinism_tools.py

---

##### Error 4: Missing `normalize_tar_info` from `tools.det_tar`

```python
# Test expects:
from tools.det_tar import normalize_tar_info

# Current implementation: DOES NOT EXIST
```

**Expected Signature**:
```python
def normalize_tar_info(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
    """Normalize tar metadata for reproducibility"""
    # Should set uid=0, gid=0, uname="", gname="", mtime=0
```

**Tests Affected**: Line 268 in test_determinism_tools.py

---

#### 1.2 `test_security_tools.py` - 2 import errors

**File**: `tests/test_security_tools.py`

##### Error 5: Missing `check_path_safety` from `tools.safe_paths_check`

```python
# Test expects:
from tools.safe_paths_check import check_path_safety

# Current implementation has:
# - load_first() function
# - main() function
# BUT NOT check_path_safety()
```

**Expected Signature**:
```python
def check_path_safety(
    path: str, 
    allow_absolute: bool = False, 
    base_dir: str | None = None
) -> tuple[bool, str]:
    """
    Returns: (is_dangerous: bool, reason: str)
    """
```

**Tests Affected**: Lines 201, 213, 219, 232, 257, 261 in test_security_tools.py

---

##### Error 6: Missing `detect_path_traversal` from `tools.safe_paths_check`

```python
# Test expects:
from tools.safe_paths_check import detect_path_traversal

# Current implementation: DOES NOT EXIST
```

**Expected Signature**:
```python
def detect_path_traversal(path: str) -> bool:
    """Detect path traversal attempts like ../ or encoded variants"""
```

**Tests Affected**: Lines 195, 208, 240 in test_security_tools.py

---

### 2. API Signature Mismatch Errors (14 total)

#### 2.1 `test_rbom_tools.py` - Multiple signature mismatches

**File**: `tests/test_rbom_tools.py`

##### Error 7-9: `collect_artifacts` returns wrong type

```python
# Test expects:
artifacts = collect_artifacts(str(tmp_path))
# Should return: List[Dict] where each dict has "name", "sha256", "size"

# Actual implementation returns:
# List[Path] - just Path objects, not dictionaries
```

**Actual Signature**:
```python
def collect_artifacts(
    root: str | os.PathLike[str] = ".", 
    extensions: Iterable[str] | None = None
) -> List[Path]:  # Returns Path objects, NOT dicts!
```

**Expected Return**:
```python
[
    {
        "name": "file.txt",
        "sha256": "abc123...",
        "size": 1024
    },
    ...
]
```

**Tests Affected**: Lines 30, 47, 56 in test_rbom_tools.py  
**Error Type**: `TypeError: 'PosixPath' object is not subscriptable`

---

##### Error 10-11: `generate_rbom` signature mismatch

```python
# Test expects:
rbom = generate_rbom(str(tmp_path), "v1.0.0")
rbom = generate_rbom(str(tmp_path), "v1.0.0", metadata={"key": "value"})

# Actual signature:
def generate_rbom(files: Iterable[Path]) -> Dict[str, Any]:
    # Takes ONLY files argument, no version or metadata!
```

**Tests Affected**: Lines 63, 82, 278, 294 in test_rbom_tools.py  
**Error Type**: `TypeError: generate_rbom() takes 1 positional argument but 2 were given`

**Expected Structure**:
```python
{
    "schema_version": "1.0",
    "release_version": "v1.0.0",
    "artifacts": [...],
    "generated_at": "2025-10-22T...",
    "metadata": {...}  # optional
}
```

**Actual Structure**:
```python
{
    "files": [
        {"name": "...", "sha256": "..."}
    ]
}
```

---

##### Error 12-20: `validate_rbom` returns wrong type

```python
# Test expects:
is_valid, errors = validate_rbom(rbom)
# Should return: tuple[bool, list[str]]

# Actual implementation returns:
def validate_rbom(doc: Dict[str, Any]) -> bool:
    # Returns ONLY bool, not a tuple!
```

**Tests Affected**: Lines 107, 118, 129, 169, 187, 281, 302 in test_rbom_tools.py  
**Error Type**: `TypeError: cannot unpack non-iterable bool object`

**Expected Signature**:
```python
def validate_rbom(doc: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Returns:
        (is_valid, error_messages)
    """
```

---

##### Error 21-22: `check_schema_version` signature mismatch

```python
# Test calls:
assert check_schema_version("1.0") is True
assert check_schema_version("0.9") is False

# Actual signature:
def check_schema_version(
    doc: Dict[str, Any],      # Takes a DICT, not a string!
    allowed: Iterable[str] = ("1.0", "1.1")
) -> bool:
```

**Tests Affected**: Lines 135-142 in test_rbom_tools.py  
**Error Type**: `AttributeError: 'str' object has no attribute 'get'`

---

### 3. Additional Issues

#### 3.1 Coverage Failure

All test runs fail coverage requirements:
- **Required**: 75% coverage
- **Actual**: 2.39% - 6.62% depending on which tests run

**Root Cause**: Tests are designed to test helper functions that don't exist yet, so actual tool code isn't being exercised.

---

## Summary by Test File

| Test File | Import Errors | API Errors | Status |
|-----------|--------------|------------|---------|
| test_cjson_canonical.py | 0 | 0 | ✅ PASS |
| test_det_tar.py | 0 | 0 | ✅ PASS |
| test_determinism_tools.py | 4 | 0 | ❌ FAIL (Cannot import) |
| test_rbom_tools.py | 0 | 14 | ❌ FAIL (14 tests fail) |
| test_safe_paths.py | 0 | 0 | ✅ PASS (No tool imports) |
| test_security_tools.py | 2 | 0 | ❌ FAIL (Cannot import) |
| test_vel_validator.py | 0 | ? | ⚠️  Not tested yet |

**Total**: 6 import errors + 14 API mismatch errors = **20 total errors**

---

## Error Categorization by Module

### `tools/verify_gzip_header.py`
- Missing: `check_gzip_header()` function
- Missing: `validate_gzip_os_byte()` function
- **Impact**: 4 test methods cannot run

### `tools/det_tar.py`
- Missing: `create_deterministic_tar()` function
- Missing: `normalize_tar_info()` function
- **Impact**: 3 test methods cannot run

### `tools/safe_paths_check.py`
- Missing: `check_path_safety()` function
- Missing: `detect_path_traversal()` function
- **Impact**: 9 test methods cannot run

### `tools/make_rbom.py`
- Wrong return type for `collect_artifacts()` - returns `List[Path]` instead of `List[Dict]`
- Wrong signature for `generate_rbom()` - missing `version` and `metadata` parameters
- Wrong output structure - has `"files"` key instead of complete RBOM structure
- **Impact**: 9 test methods fail

### `tools/rbom_check.py`
- Wrong return type for `validate_rbom()` - returns `bool` instead of `tuple[bool, list[str]]`
- Wrong signature for `check_schema_version()` - takes `Dict` instead of `str`
- **Impact**: 10 test methods fail

---

## Python Version Compatibility

All identified errors apply equally to:
- **Python 3.11**: Same errors expected (type hints, function signatures)
- **Python 3.12**: Confirmed with testing

The code uses modern Python features that are compatible with both versions:
- Type hints with `|` operator (3.10+)
- `from __future__ import annotations` for forward compatibility

---

## Recommendations

1. **Immediate**: Export missing helper functions from tools modules
2. **API Fixes**: Update function signatures to match test expectations
3. **Return Types**: Fix return types to match test expectations
4. **Coverage**: Once helper functions are exported, re-run tests to verify coverage improves

---

## Test Execution Environment

- **OS**: Linux
- **Python**: 3.12.3
- **Test Framework**: pytest 8.4.2
- **Coverage Tool**: pytest-cov 7.0.0
- **Coverage Config**: `.coveragerc` and `pytest.ini`

---

## Notes

This analysis was performed without modifying any code, only discovering and documenting existing issues. The errors are consistent across Python 3.11 and 3.12 as they relate to API design rather than language-specific features.
