# Quick Error Reference

## 6 Missing Functions (Import Errors)

### tools/verify_gzip_header.py
```python
def check_gzip_header(gz_path: str) -> dict:
    """Should return: {"is_valid": bool, "magic": str, "mtime": int}"""

def validate_gzip_os_byte(gz_path: str) -> int:
    """Should return: OS byte value (3 for Unix)"""
```

### tools/det_tar.py
```python
def create_deterministic_tar(source_dir: str, tar_path: str) -> None:
    """Create a deterministic tarball from source directory"""

def normalize_tar_info(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
    """Normalize tar metadata: uid=0, gid=0, uname="", gname="", mtime=0"""
```

### tools/safe_paths_check.py
```python
def check_path_safety(path: str, allow_absolute: bool = False, 
                      base_dir: str | None = None) -> tuple[bool, str]:
    """Should return: (is_dangerous, reason)"""

def detect_path_traversal(path: str) -> bool:
    """Detect path traversal attempts like ../ or encoded variants"""
```

## 4 Wrong Function Signatures (API Errors)

### tools/make_rbom.py

**Current:**
```python
def collect_artifacts(root: str | os.PathLike[str] = ".", 
                     extensions: Iterable[str] | None = None) -> List[Path]:
```

**Expected:**
```python
def collect_artifacts(root: str | os.PathLike[str] = ".", 
                     extensions: Iterable[str] | None = None) -> List[Dict[str, Any]]:
    # Should return: [{"name": "...", "sha256": "...", "size": 123}, ...]
```

---

**Current:**
```python
def generate_rbom(files: Iterable[Path]) -> Dict[str, Any]:
    # Returns: {"files": [...]}
```

**Expected:**
```python
def generate_rbom(root: str, version: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    # Should return: {
    #   "schema_version": "1.0",
    #   "release_version": "v1.0.0",
    #   "artifacts": [...],
    #   "generated_at": "...",
    #   "metadata": {...}
    # }
```

### tools/rbom_check.py

**Current:**
```python
def validate_rbom(doc: Dict[str, Any]) -> bool:
```

**Expected:**
```python
def validate_rbom(doc: Dict[str, Any]) -> tuple[bool, list[str]]:
    # Should return: (is_valid, error_messages)
```

---

**Current:**
```python
def check_schema_version(doc: Dict[str, Any], 
                        allowed: Iterable[str] = ("1.0", "1.1")) -> bool:
```

**Expected:**
```python
def check_schema_version(version: str, 
                        allowed: Iterable[str] = ("1.0", "1.1")) -> bool:
    # Should take a string version, not a dict
```

## Test Failure Count by File

- ❌ `test_determinism_tools.py` - Cannot import (4 missing functions)
- ❌ `test_security_tools.py` - Cannot import (2 missing functions)  
- ⚠️ `test_rbom_tools.py` - 14 tests fail (API mismatches)
- ✅ `test_cjson_canonical.py` - 2 tests pass
- ✅ `test_det_tar.py` - 1 test pass
- ✅ `test_safe_paths.py` - 1 test pass
- ✅ `test_vel_validator.py` - 20 tests pass

## Total: 20 Errors

- 6 Import errors
- 14 API/signature errors

## Python 3.11 & 3.12

All errors apply to both versions (no version-specific issues).
