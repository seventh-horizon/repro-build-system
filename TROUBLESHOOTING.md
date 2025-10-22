# Troubleshooting Guide - Repro Pack

Common issues and solutions for Repro Pack tools.

---

## Quick Diagnosis

### Issue Checklist

```bash
# Run diagnostic script
python tools/diagnose.py

# Or manually check:
python --version  # Should be 3.11+
git --version     # Should be 2.0+
which gzip        # Should exist
ls -la tools/     # All tools present?
```

---

## Build Issues

### Issue: "FileNotFoundError: snapshot.json"

**Cause**: Snapshot not created before building manifest.

**Solution**:
```bash
# Always create snapshot first
python tools/make_snapshot.py src/ --output dist/snapshot.json
```

### Issue: "Hash mismatch in VEL validation"

**Cause**: Artifact modified after manifest creation.

**Solution**:
```bash
# Regenerate both
python tools/det_tar.py src/ --output dist/artifact.tar
gzip -n dist/artifact.tar
python tools/make_vel_manifest.py \
  --snapshot dist/snapshot.json \
  --artifact dist/artifact.tar.gz \
  --output dist/vel_manifest.json
```

### Issue: "Build not reproducible"

**Causes**:
1. Timestamps in tar (mtime != 0)
2. Different gzip settings
3. File ordering changed
4. UID/GID not zero

**Solution**:
```bash
# Use det_tar.py (handles all these)
python tools/det_tar.py src/ --output dist/artifact.tar

# Use gzip with -n flag (no timestamp)
gzip -n dist/artifact.tar

# Verify
python tools/verify_tar_determinism.py dist/artifact.tar.gz
```

---

## Validation Issues

### Issue: "Git commit not found"

**Cause**: Git SHA in manifest doesn't exist locally.

**Solution**:
```bash
# Fetch all history
git fetch --unshallow

# Or skip git validation
python tools/vel_validator.py manifest.json \
  --artifact artifact.tar.gz
  # Don't use --strict-git
```

### Issue: "JSON Schema validation failed"

**Cause**: Manifest doesn't match schema.

**Solution**:
```bash
# Check schema file exists
ls -la schema/vel_manifest.schema.json

# Validate JSON syntax
python -m json.tool dist/vel_manifest.json

# Regenerate manifest
python tools/make_vel_manifest.py ...
```

### Issue: "Tar file not deterministic: mtime not zero"

**Cause**: Used standard tar instead of det_tar.py.

**Solution**:
```bash
# WRONG
tar czf artifact.tar.gz src/

# CORRECT
python tools/det_tar.py src/ --output dist/artifact.tar
gzip -n dist/artifact.tar
```

---

## Security Issues

### Issue: "Secrets detected but they're false positives"

**Cause**: Pattern matches non-secrets (e.g., test data).

**Solution**:
```bash
# Add to .secretsignore
echo "tests/fixtures/*" >> .secretsignore
echo "docs/examples/*" >> .secretsignore

# Or use custom config
python tools/secret_lint.py src/ --config custom_patterns.yml
```

### Issue: "Permission check fails on executable"

**Cause**: Script missing execute bit.

**Solution**:
```bash
# Add execute permission
chmod +x deploy.sh

# Verify
python tools/permissions_lint.py .
```

### Issue: "GitHub Actions not pinned to SHA"

**Cause**: Using tag reference (v1, v2).

**Solution**:
```yaml
# WRONG
- uses: actions/checkout@v4

# CORRECT
- uses: actions/checkout@692973e3d937129bcbf40652eb9f2f61becf3332 # v4.1.7
```

---

## Compliance Issues

### Issue: "RBOM validation failed: missing required artifacts"

**Cause**: Policy requires specific files.

**Solution**:
```bash
# Check policy
cat schema/rbom_policy.json

# Ensure required files present
ls -la dist/README.md dist/LICENSE

# Add missing files
cp README.md dist/
cp LICENSE dist/
```

### Issue: "Artifact size exceeds limit"

**Cause**: Artifact too large for policy.

**Solution**:
```bash
# Check policy limit
jq '.max_artifact_size' schema/rbom_policy.json

# Reduce artifact size or update policy
# Option 1: Exclude unnecessary files
python tools/det_tar.py src/ --output dist/artifact.tar \
  --exclude "*.log" --exclude "temp/*"

# Option 2: Update policy (if appropriate)
# Edit schema/rbom_policy.json
```

---

## CI/CD Issues

### Issue: "GitHub Actions workflow fails: 'command not found'"

**Cause**: Python tools not in PATH.

**Solution**:
```yaml
# Add python to command
- name: Build
  run: python tools/make_snapshot.py src/
  
# Or add tools to PATH
- name: Setup
  run: echo "${{ github.workspace }}/tools" >> $GITHUB_PATH
```

### Issue: "GitLab CI artifact not found in next stage"

**Cause**: Artifacts not passed between stages.

**Solution**:
```yaml
build:
  artifacts:
    paths:
      - dist/
    expire_in: 1 hour  # Or longer

validate:
  dependencies:
    - build  # Explicitly depend on build job
```

### Issue: "Docker build fails: 'No such file or directory'"

**Cause**: Files not copied to Docker context.

**Solution**:
```dockerfile
# Copy all needed files
COPY tools/ /repro-pack/tools/
COPY schema/ /repro-pack/schema/
COPY requirements.txt /repro-pack/

# Or use .dockerignore properly
```

---

## Performance Issues

### Issue: "Build takes too long (>5 minutes)"

**Causes**:
- Large source tree
- Slow disk I/O
- Inefficient scanning

**Solutions**:
```bash
# 1. Exclude unnecessary files
python tools/make_snapshot.py src/ \
  --ignore "node_modules" \
  --ignore "*.log" \
  --ignore "temp/*"

# 2. Use SSD for build directory
export REPRO_OUTPUT_DIR=/tmp/fast-disk/dist

# 3. Run scans in parallel
python tools/secret_lint.py src/ &
python tools/permissions_lint.py src/ &
wait
```

### Issue: "Secret scanning is slow"

**Cause**: Scanning large files or many files.

**Solutions**:
```bash
# 1. Exclude large/binary files
python tools/secret_lint.py src/ \
  --exclude "*.bin" \
  --exclude "*.jpg"

# 2. Increase regex efficiency (custom config)
# Edit patterns to be more specific

# 3. Scan only changed files in CI
git diff --name-only HEAD^ | \
  xargs python tools/secret_lint.py
```

---

## Common Errors

### Error: "JSONDecodeError: Expecting value"

**Cause**: Invalid JSON file.

**Solution**:
```bash
# Validate JSON
python -m json.tool file.json

# Or use jq
jq . file.json

# Fix syntax errors and retry
```

### Error: "PermissionError: [Errno 13] Permission denied"

**Cause**: No permission to read/write file.

**Solution**:
```bash
# Check permissions
ls -la file.txt

# Fix permissions
chmod 644 file.txt  # For regular files
chmod 755 script.sh  # For scripts

# Or run with sudo (not recommended)
sudo python tools/...
```

### Error: "UnicodeDecodeError: 'utf-8' codec can't decode"

**Cause**: Non-UTF-8 file encoding.

**Solution**:
```bash
# Detect encoding
file -i file.txt

# Convert to UTF-8
iconv -f ISO-8859-1 -t UTF-8 file.txt > file_utf8.txt

# Or exclude binary files
python tools/make_snapshot.py src/ --ignore "*.bin"
```

### Error: "Git command not found"

**Cause**: Git not installed.

**Solution**:
```bash
# Install Git
# Ubuntu/Debian:
sudo apt-get install git

# macOS:
brew install git

# Verify
git --version
```

---

## Environment Issues

### Issue: "Tool works locally but fails in CI"

**Causes**:
- Different Python version
- Missing dependencies
- Different environment variables

**Solutions**:
```bash
# 1. Match Python versions
python --version  # Check local
# Update CI to use same version

# 2. Freeze dependencies
pip freeze > requirements.lock
# Use requirements.lock in CI

# 3. Check environment
env | grep REPRO_
# Set same variables in CI
```

### Issue: "Tests pass but build fails"

**Cause**: Test mocks don't match real behavior.

**Solution**:
```bash
# Run integration tests
pytest tests/ -m integration

# Test with real tools
python tools/make_snapshot.py test-data/

# Don't over-mock in tests
```

---

## Debugging Tips

### Enable Verbose Mode

```bash
# Set debug level
export REPRO_DEBUG=1

# Or per-tool
python tools/vel_validator.py --verbose manifest.json
```

### Check Tool Versions

```bash
# Python
python --version

# Git
git --version

# Gzip
gzip --version

# All dependencies
pip list
```

### Verify File Hashes

```bash
# Compute SHA-256
sha256sum file.tar.gz

# Compare with manifest
jq '.provenance.artifact_sha256' dist/vel_manifest.json

# Should match exactly
```

### Inspect Tar Contents

```bash
# List contents
tar -tzf artifact.tar.gz

# Check metadata
tar -tvzf artifact.tar.gz | head -20

# Extract single file
tar -xzf artifact.tar.gz path/to/file
```

### Test Reproducibility Manually

```bash
# Build 1
python tools/det_tar.py src/ --output build1.tar
gzip -n build1.tar

# Wait a moment
sleep 5

# Build 2
python tools/det_tar.py src/ --output build2.tar
gzip -n build2.tar

# Compare
sha256sum build1.tar.gz build2.tar.gz
diff <(xxd build1.tar.gz) <(xxd build2.tar.gz)
```

---

## Getting Help

### Self-Help Resources

1. Check this troubleshooting guide
2. Review tool documentation (TOOL_REFERENCE.md)
3. Check architecture guide (ARCHITECTURE.md)
4. Search GitHub issues

### Reporting Issues

When reporting issues, include:

```bash
# 1. Environment info
python --version
git --version
uname -a

# 2. Tool version
git describe --tags

# 3. Exact command
# (copy/paste the command you ran)

# 4. Error output
# (full error message)

# 5. Relevant files
ls -la dist/
cat dist/vel_manifest.json
```

### Debug Script

```bash
#!/bin/bash
# debug.sh - Collect debug information

echo "=== Environment ==="
python --version
git --version
gzip --version

echo ""
echo "=== Repro Pack ==="
git describe --tags
ls -la tools/

echo ""
echo "=== Python Packages ==="
pip list | grep -E "pytest|json"

echo ""
echo "=== Build Directory ==="
ls -lah dist/

echo ""
echo "=== Test Run ==="
python tools/make_snapshot.py src/ --output /tmp/test-snapshot.json
cat /tmp/test-snapshot.json
```

---

## Prevention Tips

### Before Every Build

- [ ] Clean build directory (`make clean`)
- [ ] Verify Git status (`git status`)
- [ ] Check for uncommitted changes
- [ ] Pull latest changes
- [ ] Update dependencies

### Before Every Release

- [ ] Run full test suite
- [ ] Verify reproducibility
- [ ] Check all security scans
- [ ] Review compliance reports
- [ ] Test in clean environment

### CI/CD Best Practices

- [ ] Pin all dependencies
- [ ] Use caching wisely
- [ ] Validate on every PR
- [ ] Archive evidence bundles
- [ ] Monitor build times

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-15  
**Status**: Complete
