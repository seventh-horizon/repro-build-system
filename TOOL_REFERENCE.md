# Repro Pack Tool Reference

Complete reference documentation for all 23 tools in the Repro Pack system.

---

## Quick Reference Table

| Tool | Category | Purpose | Input | Output |
|------|----------|---------|-------|--------|
| make_snapshot | Build | Capture source state | Source dir | snapshot.json |
| version_stamp | Build | Add version info | Version string | VERSION file |
| make_vel_manifest | Build | Generate provenance | Snapshot + git info | vel_manifest.json |
| det_tar | Build | Create deterministic tar | Source dir | .tar file |
| vel_validator | Validation | Validate manifest | Manifest + artifact | Exit code |
| verify_gzip_header | Validation | Check gzip header | .gz file | check result |
| verify_tar_determinism | Validation | Check tar metadata | .tar file | tar_check.json |
| safe_paths_check | Validation | Validate file paths | Archive | paths_check.json |
| secret_lint | Security | Detect secrets | Source tree | secrets_report.json |
| permissions_lint | Security | Check permissions | File/dir | perms_report.json |
| pins_manifest_check | Security | Verify action pins | .github/workflows | pins_check.json |
| make_rbom | Compliance | Generate RBOM | Artifacts dir | release_bom.json |
| rbom_check | Compliance | Validate RBOM | RBOM + policy | rbom_check.json |
| policy_trace | Compliance | Trace policy checks | All checks | policy_trace.json |
| meta_lint | Compliance | Check metadata | Files | meta_check.json |
| evidence_matrix | Reporting | Generate evidence | All outputs | evidence.json |
| make_ci_summary | Reporting | Create CI summary | Build results | summary.md |
| repro_audit | Reporting | Audit report | Evidence | audit_report.json |
| io_utils | Utility | I/O helpers | - | - |
| config | Utility | Configuration | config.yml | Config object |
| cjson | Utility | Canonical JSON | Dict | Canonical JSON |
| json_canonical_check | Utility | Verify canonical | JSON file | Check result |

---

## Build Tools

### make_snapshot.py

**Purpose**: Captures the exact state of the source tree at build time.

**Usage**:
```bash
python tools/make_snapshot.py <source_dir> --output snapshot.json
```

**Arguments**:
- `source_dir`: Path to source directory to snapshot
- `--output, -o`: Output file path (default: snapshot.json)
- `--ignore`: Patterns to ignore (default: .git, __pycache__, *.pyc)

**Output Format**:
```json
{
  "timestamp": "2025-10-14T12:00:00Z",
  "source_root": "/path/to/source",
  "files": [
    {
      "path": "src/main.py",
      "sha256": "abc123...",
      "size": 1234,
      "mode": "0644"
    }
  ],
  "total_files": 42,
  "total_size": 123456
}
```

**Exit Codes**:
- 0: Success
- 1: Error (missing directory, permission denied)

**Example**:
```bash
# Create snapshot of current directory
python tools/make_snapshot.py . -o build/snapshot.json

# Snapshot with custom ignore patterns
python tools/make_snapshot.py src/ --ignore "*.log" --ignore "temp/*"
```

---

### version_stamp.py

**Purpose**: Stamps version information into the build.

**Usage**:
```bash
python tools/version_stamp.py <version> --output VERSION
```

**Arguments**:
- `version`: Version string (e.g., v1.0.0, 1.2.3-beta)
- `--output, -o`: Output file (default: VERSION)
- `--format`: Format (default: text, options: text, json)

**Output Formats**:

*Text format (default)*:
```
v1.0.0
```

*JSON format*:
```json
{
  "version": "v1.0.0",
  "stamped_at": "2025-10-14T12:00:00Z"
}
```

**Example**:
```bash
# Stamp version from git tag
VERSION=$(git describe --tags)
python tools/version_stamp.py $VERSION

# JSON format
python tools/version_stamp.py v1.0.0 --format json -o version.json
```

---

### make_vel_manifest.py

**Purpose**: Generates a Verifiable Evidence Ledger (VEL) manifest with complete build provenance.

**Usage**:
```bash
python tools/make_vel_manifest.py \
  --snapshot snapshot.json \
  --artifact artifact.tar.gz \
  --output vel_manifest.json
```

**Arguments**:
- `--snapshot`: Path to snapshot.json
- `--artifact`: Path to build artifact
- `--output, -o`: Output manifest path
- `--git-sha`: Git commit SHA (auto-detected if not provided)
- `--metadata`: Additional metadata JSON file

**Output Format**:
```json
{
  "provenance": {
    "git_sha": "abc123...",
    "artifact_sha256": "def456...",
    "build_timestamp": "2025-10-14T12:00:00Z",
    "builder": "github-actions"
  },
  "environment": {
    "python_version": "3.11.5",
    "os": "Linux",
    "platform": "x86_64"
  },
  "results_contract": {
    "snapshot_sha256": "789ghi...",
    "file_count": 42,
    "total_size": 123456
  }
}
```

**Exit Codes**:
- 0: Success
- 1: Missing required inputs
- 2: Validation failed

**Example**:
```bash
# Generate manifest with auto-detected git info
python tools/make_vel_manifest.py \
  --snapshot build/snapshot.json \
  --artifact dist/app.tar.gz \
  --output build/vel_manifest.json

# With explicit git SHA and metadata
python tools/make_vel_manifest.py \
  --snapshot build/snapshot.json \
  --artifact dist/app.tar.gz \
  --git-sha $(git rev-parse HEAD) \
  --metadata build_info.json \
  --output build/vel_manifest.json
```

---

### det_tar.py

**Purpose**: Creates deterministic, reproducible tarball archives.

**Usage**:
```bash
python tools/det_tar.py <source_dir> --output archive.tar
```

**Arguments**:
- `source_dir`: Directory to archive
- `--output, -o`: Output tar file path
- `--compression`: Compression method (none, gzip, bzip2)
- `--prefix`: Path prefix for files in archive

**Determinism Features**:
- Files sorted alphabetically
- UID/GID set to 0
- mtime set to 0 (epoch: 1970-01-01)
- uname/gname cleared
- Consistent file modes

**Output**: Bit-for-bit reproducible tarball

**Example**:
```bash
# Create deterministic tar
python tools/det_tar.py src/ --output dist/src.tar

# With gzip compression
python tools/det_tar.py src/ --output dist/src.tar --compression gzip

# With path prefix
python tools/det_tar.py src/ --output dist/release.tar --prefix myapp-1.0/
```

**Verification**:
```bash
# Build twice and compare
python tools/det_tar.py src/ -o build1.tar
python tools/det_tar.py src/ -o build2.tar
sha256sum build1.tar build2.tar
# Hashes should be identical
```

---

## Validation Tools

### vel_validator.py

**Purpose**: Validates VEL manifest against actual artifacts and git repository.

**Usage**:
```bash
python tools/vel_validator.py \
  vel_manifest.json \
  --artifact artifact.tar.gz \
  --schema schema/vel_manifest.schema.json
```

**Arguments**:
- `manifest`: Path to VEL manifest
- `--artifact`: Path to artifact to verify
- `--schema`: JSON schema file for validation
- `--strict-git`: Fail if git SHA cannot be verified

**Validation Checks**:
1. ✅ Schema validation (required fields present)
2. ✅ JSON Schema validation (if provided)
3. ✅ Artifact SHA-256 matches manifest
4. ✅ Git commit exists locally (optional)

**Exit Codes**:
- 0: Validation passed
- 2: Validation failed

**Example**:
```bash
# Basic validation
python tools/vel_validator.py \
  build/vel_manifest.json \
  --artifact dist/app.tar.gz \
  --schema schema/vel_manifest.schema.json

# Strict mode (require git verification)
python tools/vel_validator.py \
  build/vel_manifest.json \
  --artifact dist/app.tar.gz \
  --strict-git
```

**Output**:
```
Checking manifest structure... ✓
Validating against JSON schema... ✓
Verifying artifact SHA-256... ✓
Checking git commit abc123... ✓
Manifest validation PASS
```

---

### verify_gzip_header.py

**Purpose**: Validates gzip headers for reproducibility compliance.

**Usage**:
```bash
python tools/verify_gzip_header.py <file.gz> --output check.json
```

**Arguments**:
- `file`: Path to gzip file
- `--output, -o`: Output JSON report

**Checks**:
- Magic bytes (1f 8b)
- Compression method (deflate = 08)
- mtime = 0 (required for reproducibility)
- OS byte = 3 (Unix/Linux)

**Output Format**:
```json
{
  "file": "artifact.tar.gz",
  "is_valid": true,
  "checks": {
    "magic_bytes": "1f8b",
    "compression": "deflate",
    "mtime": 0,
    "os": 3
  },
  "issues": []
}
```

**Exit Codes**:
- 0: Valid gzip header
- 1: Invalid header or mtime != 0

**Example**:
```bash
# Check gzip header
python tools/verify_gzip_header.py dist/app.tar.gz

# Save report
python tools/verify_gzip_header.py dist/app.tar.gz -o build/gzip_check.json
```

---

### verify_tar_determinism.py

**Purpose**: Validates tarball metadata for deterministic builds.

**Usage**:
```bash
python tools/verify_tar_determinism.py <file.tar> --output tar_check.json
```

**Arguments**:
- `file`: Path to tar file
- `--output, -o`: Output JSON report

**Checks**:
- ✅ Files in alphabetical order
- ✅ UID = 0 for all files
- ✅ GID = 0 for all files  
- ✅ mtime = 0 for all files
- ✅ uname = "" for all files
- ✅ gname = "" for all files

**Output Format**:
```json
{
  "file": "artifact.tar",
  "is_deterministic": true,
  "total_files": 42,
  "checks": {
    "file_order": "sorted",
    "all_uid_zero": true,
    "all_gid_zero": true,
    "all_mtime_zero": true
  },
  "issues": []
}
```

**Example**:
```bash
# Check tar determinism
python tools/verify_tar_determinism.py dist/app.tar

# Detailed report
python tools/verify_tar_determinism.py dist/app.tar -o build/tar_check.json
```

---

### safe_paths_check.py

**Purpose**: Validates file paths in archives for security (no path traversal).

**Usage**:
```bash
python tools/safe_paths_check.py <archive> --output paths_check.json
```

**Arguments**:
- `archive`: Path to archive file (.tar, .tar.gz, .zip)
- `--output, -o`: Output JSON report
- `--allow-absolute`: Allow absolute paths (default: false)

**Checks**:
- ❌ No `..` (parent directory references)
- ❌ No absolute paths (unless allowed)
- ❌ No symlinks escaping base directory
- ❌ No null bytes in paths

**Output Format**:
```json
{
  "archive": "artifact.tar.gz",
  "is_safe": true,
  "total_paths": 42,
  "dangerous_paths": [],
  "issues": []
}
```

**Exit Codes**:
- 0: All paths safe
- 1: Dangerous paths found

**Example**:
```bash
# Check archive paths
python tools/safe_paths_check.py dist/release.tar.gz

# Allow absolute paths
python tools/safe_paths_check.py dist/release.tar.gz --allow-absolute
```

---

## Security Tools

### secret_lint.py

**Purpose**: Scans source code for accidentally committed secrets and credentials.

**Usage**:
```bash
python tools/secret_lint.py <path> --output secrets_report.json
```

**Arguments**:
- `path`: File or directory to scan
- `--output, -o`: Output JSON report
- `--config`: Custom patterns config file

**Detection Methods**:
1. **Pattern Matching**: Regex for known secret formats
2. **Entropy Analysis**: High-entropy strings
3. **Context Analysis**: Variable names suggesting secrets

**Detected Patterns**:
- AWS keys (AKIA...)
- GitHub tokens (ghp_..., gho_...)
- API keys (various formats)
- Private keys (BEGIN RSA PRIVATE KEY)
- Database passwords
- JWT tokens
- OAuth secrets

**Output Format**:
```json
{
  "scan_path": "src/",
  "has_secrets": false,
  "findings": [],
  "summary": {
    "files_scanned": 42,
    "secrets_found": 0,
    "high_confidence": 0,
    "medium_confidence": 0
  }
}
```

**Exit Codes**:
- 0: No secrets found
- 1: Secrets detected

**Example**:
```bash
# Scan directory
python tools/secret_lint.py src/

# Scan with custom config
python tools/secret_lint.py src/ --config secret_patterns.yml

# Save report
python tools/secret_lint.py src/ -o build/secrets_report.json
```

---

### permissions_lint.py

**Purpose**: Validates file permissions for security compliance.

**Usage**:
```bash
python tools/permissions_lint.py <path> --output perms_report.json
```

**Arguments**:
- `path`: File or directory to check
- `--output, -o`: Output JSON report
- `--policy`: Permission policy file

**Rules**:
- Private keys: Must be 0600 or 0400
- Scripts (.sh, .py): Must have execute bit
- Config files: Should not be 0777
- Sensitive files: Should not be world-readable

**Output Format**:
```json
{
  "path": "src/",
  "has_issues": false,
  "issues": [],
  "summary": {
    "files_checked": 42,
    "warnings": 0,
    "errors": 0
  }
}
```

**Exit Codes**:
- 0: No permission issues
- 1: Permission violations found

**Example**:
```bash
# Check directory permissions
python tools/permissions_lint.py src/

# Check single file
python tools/permissions_lint.py config/private.key

# With custom policy
python tools/permissions_lint.py src/ --policy perms_policy.json
```

---

### pins_manifest_check.py

**Purpose**: Validates GitHub Actions are pinned to specific SHA commits (not tags).

**Usage**:
```bash
python tools/pins_manifest_check.py .github/workflows/ --output pins_check.json
```

**Arguments**:
- `workflows_dir`: Path to workflows directory
- `--output, -o`: Output JSON report
- `--allow-tags`: Allow tag references (not recommended)

**Checks**:
- ✅ All actions pinned to SHA (40 hex chars)
- ❌ No tag references (v1, v2, etc.)
- ❌ No branch references (main, master, etc.)

**Why Pin to SHA?**:
- **Security**: Prevent supply chain attacks
- **Reproducibility**: Exact version control
- **Auditability**: Know exact code running

**Output Format**:
```json
{
  "workflows_dir": ".github/workflows/",
  "total_workflows": 3,
  "total_actions": 15,
  "unpinned_actions": [],
  "is_compliant": true
}
```

**Exit Codes**:
- 0: All actions properly pinned
- 1: Unpinned actions found

**Example**:
```bash
# Check GitHub Actions pins
python tools/pins_manifest_check.py .github/workflows/

# Allow tags (not recommended for production)
python tools/pins_manifest_check.py .github/workflows/ --allow-tags
```

---

## Compliance Tools

### make_rbom.py

**Purpose**: Generates Release Bill of Materials (RBOM) listing all release artifacts.

**Usage**:
```bash
python tools/make_rbom.py <artifacts_dir> \
  --version v1.0.0 \
  --output release_bom.json
```

**Arguments**:
- `artifacts_dir`: Directory containing release artifacts
- `--version, -v`: Release version
- `--output, -o`: Output RBOM file
- `--metadata`: Additional metadata JSON

**Output Format**:
```json
{
  "schema_version": "1.0",
  "release_version": "v1.0.0",
  "generated_at": "2025-10-14T12:00:00Z",
  "artifacts": [
    {
      "name": "app.tar.gz",
      "sha256": "abc123...",
      "size": 12345678,
      "type": "archive"
    },
    {
      "name": "checksums.txt",
      "sha256": "def456...",
      "size": 1234,
      "type": "metadata"
    }
  ],
  "metadata": {
    "build_id": "2025-10-14-001",
    "git_sha": "abc123...",
    "builder": "github-actions"
  }
}
```

**Exit Codes**:
- 0: RBOM generated successfully
- 1: Error (missing directory, no artifacts)

**Example**:
```bash
# Generate RBOM
python tools/make_rbom.py dist/ --version v1.0.0

# With metadata
python tools/make_rbom.py dist/ \
  --version v1.0.0 \
  --metadata build_info.json \
  --output build/release_bom.json
```

---

### rbom_check.py

**Purpose**: Validates RBOM against policy constraints.

**Usage**:
```bash
python tools/rbom_check.py release_bom.json \
  --policy schema/rbom_policy.json \
  --output rbom_check.json
```

**Arguments**:
- `rbom`: Path to RBOM file
- `--policy`: Policy file
- `--output, -o`: Output check report

**Policy Checks**:
- Schema version compatibility
- Required artifacts present
- Forbidden file extensions
- Size limits
- Artifact count limits

**Policy Format**:
```json
{
  "schema_version": "1.0",
  "required_artifacts": ["README.md", "LICENSE"],
  "forbidden_extensions": [".exe", ".dll"],
  "max_artifact_size": 1000000000,
  "max_artifact_count": 100
}
```

**Output Format**:
```json
{
  "rbom_file": "release_bom.json",
  "policy_file": "rbom_policy.json",
  "is_compliant": true,
  "violations": [],
  "summary": {
    "checks_performed": 5,
    "checks_passed": 5,
    "checks_failed": 0
  }
}
```

**Exit Codes**:
- 0: RBOM compliant with policy
- 1: Policy violations found

**Example**:
```bash
# Check RBOM against policy
python tools/rbom_check.py build/release_bom.json \
  --policy schema/rbom_policy.json

# Save detailed report
python tools/rbom_check.py build/release_bom.json \
  --policy schema/rbom_policy.json \
  --output build/rbom_check.json
```

---

### policy_trace.py

**Purpose**: Generates complete trace of policy enforcement throughout build.

**Usage**:
```bash
python tools/policy_trace.py build/ --output policy_trace.json
```

**Arguments**:
- `build_dir`: Directory with build outputs
- `--output, -o`: Output trace file

**Traces**:
- Which policies were checked
- When they were enforced
- Results of each check
- Policy versions used

**Output Format**:
```json
{
  "trace_timestamp": "2025-10-14T12:00:00Z",
  "build_dir": "build/",
  "policies_enforced": [
    {
      "policy": "secret_scanning",
      "tool": "secret_lint.py",
      "result": "pass",
      "timestamp": "2025-10-14T12:00:01Z"
    },
    {
      "policy": "rbom_validation",
      "tool": "rbom_check.py",
      "result": "pass",
      "timestamp": "2025-10-14T12:00:05Z"
    }
  ],
  "summary": {
    "total_policies": 8,
    "passed": 8,
    "failed": 0
  }
}
```

**Example**:
```bash
# Generate policy trace
python tools/policy_trace.py build/

# Save trace
python tools/policy_trace.py build/ -o build/policy_trace.json
```

---

### meta_lint.py

**Purpose**: Validates metadata files (JSON, YAML) for correctness.

**Usage**:
```bash
python tools/meta_lint.py <file> --schema <schema.json> --output meta_check.json
```

**Arguments**:
- `file`: Metadata file to check
- `--schema`: JSON Schema for validation
- `--output, -o`: Output report

**Checks**:
- Valid JSON/YAML syntax
- Schema compliance
- Required fields present
- Data type validation

**Example**:
```bash
# Validate metadata
python tools/meta_lint.py config.json \
  --schema schema/config.schema.json

# Check multiple files
for f in *.json; do
  python tools/meta_lint.py "$f" --schema schema/meta.schema.json
done
```

---

## Reporting Tools

### evidence_matrix.py

**Purpose**: Generates complete evidence matrix for auditors.

**Usage**:
```bash
python tools/evidence_matrix.py build/ --output evidence.json
```

**Arguments**:
- `build_dir`: Directory with all build outputs
- `--output, -o`: Output evidence matrix

**Matrix Contents**:
- All validation results
- All security check results
- All compliance check results
- Build provenance
- Timestamps for all steps

**Output Format**:
```json
{
  "evidence_timestamp": "2025-10-14T12:00:00Z",
  "build_dir": "build/",
  "evidence": [
    {
      "type": "snapshot",
      "tool": "make_snapshot.py",
      "status": "success",
      "output_file": "build/snapshot.json",
      "sha256": "abc123..."
    },
    {
      "type": "validation",
      "tool": "vel_validator.py",
      "status": "success",
      "output_file": "build/vel_check.log"
    }
  ],
  "summary": {
    "total_checks": 15,
    "passed": 15,
    "failed": 0,
    "build_reproducible": true
  }
}
```

**Example**:
```bash
# Generate evidence matrix
python tools/evidence_matrix.py build/ -o build/evidence.json

# Include in release
cp build/evidence.json dist/
```

---

### make_ci_summary.py

**Purpose**: Creates human-readable CI build summary.

**Usage**:
```bash
python tools/make_ci_summary.py build/ --output summary.md
```

**Arguments**:
- `build_dir`: Directory with build results
- `--output, -o`: Output summary file (Markdown)
- `--format`: Output format (md, html, json)

**Output** (Markdown):
```markdown
# Build Summary

## Build Information
- **Version**: v1.0.0
- **Git SHA**: abc123...
- **Build Time**: 2025-10-14 12:00:00 UTC
- **Duration**: 45 seconds

## Validation Results
✅ VEL Manifest Validation: PASS
✅ Tar Determinism Check: PASS
✅ Gzip Header Check: PASS

## Security Checks
✅ Secret Scanning: PASS (0 secrets found)
✅ Permission Check: PASS (0 issues)
✅ Actions Pins: PASS (all pinned)

## Compliance
✅ RBOM Generated: release_bom.json
✅ RBOM Validation: PASS
✅ Policy Enforcement: PASS (8/8 policies)

## Artifacts
- app.tar.gz (12.3 MB, sha256: abc123...)
- checksums.txt (1.2 KB, sha256: def456...)

**Status**: ✅ BUILD SUCCESS
```

**Example**:
```bash
# Generate CI summary
python tools/make_ci_summary.py build/ -o build/summary.md

# HTML format
python tools/make_ci_summary.py build/ --format html -o build/summary.html

# Post to GitHub
cat build/summary.md >> $GITHUB_STEP_SUMMARY
```

---

### repro_audit.py

**Purpose**: Generates comprehensive audit report for compliance/security review.

**Usage**:
```bash
python tools/repro_audit.py build/ --output audit_report.json
```

**Arguments**:
- `build_dir`: Directory with evidence
- `--output, -o`: Output audit report
- `--include-evidence`: Include full evidence files

**Report Sections**:
1. Executive Summary
2. Build Provenance
3. Security Assessment
4. Compliance Status
5. Recommendations

**Output Format**:
```json
{
  "audit_timestamp": "2025-10-14T12:00:00Z",
  "report_version": "1.0",
  "executive_summary": {
    "build_reproducible": true,
    "security_issues": 0,
    "compliance_status": "pass",
    "recommendation": "APPROVE FOR RELEASE"
  },
  "provenance": {
    "git_sha": "abc123...",
    "build_timestamp": "2025-10-14T12:00:00Z",
    "builder": "github-actions",
    "reproducibility_verified": true
  },
  "security_assessment": {
    "secrets_found": 0,
    "permission_issues": 0,
    "vulnerability_scan": "pass"
  },
  "compliance_status": {
    "slsa_level": 3,
    "policies_enforced": 8,
    "policies_passed": 8
  }
}
```

**Example**:
```bash
# Generate audit report
python tools/repro_audit.py build/ -o build/audit_report.json

# Include full evidence
python tools/repro_audit.py build/ \
  --include-evidence \
  --output build/complete_audit.json
```

---

## Utility Tools

### io_utils.py

**Purpose**: Provides common I/O utilities for other tools.

**Functions**:

```python
def read_json(path: str) -> dict:
    """Read and parse JSON file"""

def write_json(path: str, data: dict, canonical: bool = False):
    """Write JSON file (optionally canonical)"""

def sha256_file(path: str) -> str:
    """Compute SHA-256 hash of file"""

def sha256_path(path: str) -> str:
    """Compute SHA-256 hash (alias for sha256_file)"""

def ensure_dir(path: str):
    """Create directory if it doesn't exist"""
```

**Usage**:
```python
from tools.io_utils import read_json, write_json, sha256_file

# Read JSON
data = read_json("config.json")

# Write JSON
write_json("output.json", {"key": "value"})

# Compute hash
hash = sha256_file("artifact.tar.gz")
```

---

### config.py

**Purpose**: Loads and manages configuration from config.yml.

**Functions**:

```python
def load_config(path: str = "config.yml") -> dict:
    """Load configuration from YAML file"""

def get_config(key: str, default=None):
    """Get configuration value by key"""
```

**Usage**:
```python
from tools.config import load_config, get_config

# Load config
config = load_config("config.yml")

# Get value
output_dir = get_config("build.output_dir", default="dist/")
```

---

### cjson.py

**Purpose**: Canonical JSON serialization (RFC 8785).

**Functions**:

```python
def canonical_json(obj: dict) -> str:
    """Serialize object to canonical JSON"""

def canonical_json_bytes(obj: dict) -> bytes:
    """Serialize object to canonical JSON bytes"""
```

**Features**:
- Sorted keys
- No whitespace
- Consistent number formatting
- UTF-8 encoding

**Usage**:
```python
from tools.cjson import canonical_json

data = {"b": 2, "a": 1}
canonical = canonical_json(data)
# Output: '{"a":1,"b":2}'
```

---

### json_canonical_check.py

**Purpose**: Verifies JSON files are in canonical form.

**Usage**:
```bash
python tools/json_canonical_check.py <file.json>
```

**Checks**:
- Keys sorted alphabetically
- No unnecessary whitespace
- Consistent formatting

**Exit Codes**:
- 0: File is canonical
- 1: File is not canonical

**Example**:
```bash
# Check if JSON is canonical
python tools/json_canonical_check.py manifest.json

# Check all JSON files
find . -name "*.json" -exec python tools/json_canonical_check.py {} \;
```

---

## Common Patterns

### Pattern 1: Complete Build Pipeline
```bash
# Step 1: Capture source
python tools/make_snapshot.py src/ -o build/snapshot.json

# Step 2: Create artifact
python tools/det_tar.py src/ -o build/artifact.tar
gzip -n build/artifact.tar  # -n for no timestamp

# Step 3: Generate manifest
python tools/make_vel_manifest.py \
  --snapshot build/snapshot.json \
  --artifact build/artifact.tar.gz \
  --output build/vel_manifest.json

# Step 4: Validate
python tools/vel_validator.py build/vel_manifest.json \
  --artifact build/artifact.tar.gz

# Step 5: Security checks
python tools/secret_lint.py src/
python tools/permissions_lint.py src/

# Step 6: Generate RBOM
python tools/make_rbom.py build/ --version v1.0.0

# Step 7: Compliance
python tools/rbom_check.py build/release_bom.json \
  --policy schema/rbom_policy.json

# Step 8: Evidence
python tools/evidence_matrix.py build/ -o build/evidence.json
```

### Pattern 2: CI/CD Integration
```yaml
- name: Build
  run: |
    python tools/make_snapshot.py src/ -o build/snapshot.json
    python tools/det_tar.py src/ -o build/artifact.tar
    gzip -n build/artifact.tar

- name: Validate
  run: |
    python tools/vel_validator.py build/vel_manifest.json \
      --artifact build/artifact.tar.gz

- name: Security
  run: |
    python tools/secret_lint.py src/
    python tools/permissions_lint.py src/
    
- name: Compliance
  run: |
    python tools/make_rbom.py build/ --version ${{ github.ref_name }}
    python tools/rbom_check.py build/release_bom.json \
      --policy schema/rbom_policy.json
```

### Pattern 3: Makefile Integration
```makefile
.PHONY: build validate security compliance

build:
	python tools/make_snapshot.py src/ -o build/snapshot.json
	python tools/det_tar.py src/ -o build/artifact.tar
	gzip -n build/artifact.tar
	python tools/make_vel_manifest.py \
		--snapshot build/snapshot.json \
		--artifact build/artifact.tar.gz \
		--output build/vel_manifest.json

validate:
	python tools/vel_validator.py build/vel_manifest.json \
		--artifact build/artifact.tar.gz
	python tools/verify_tar_determinism.py build/artifact.tar.gz
	python tools/verify_gzip_header.py build/artifact.tar.gz

security:
	python tools/secret_lint.py src/
	python tools/permissions_lint.py src/
	python tools/pins_manifest_check.py .github/workflows/

compliance:
	python tools/make_rbom.py build/ --version v1.0.0
	python tools/rbom_check.py build/release_bom.json \
		--policy schema/rbom_policy.json
	python tools/evidence_matrix.py build/ -o build/evidence.json
```

---

## Troubleshooting

### Common Issues

**Issue**: "FileNotFoundError: snapshot.json"  
**Solution**: Run make_snapshot.py first to create snapshot

**Issue**: "ValidationError: artifact hash mismatch"  
**Solution**: Ensure artifact hasn't been modified after manifest creation

**Issue**: "PermissionError: Cannot read file"  
**Solution**: Check file permissions, run with appropriate user

**Issue**: "JSONDecodeError: Invalid JSON"  
**Solution**: Validate JSON syntax, ensure proper encoding

---

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - CI/CD integration
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Detailed troubleshooting

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-14  
**Tool Count**: 23 tools documented
