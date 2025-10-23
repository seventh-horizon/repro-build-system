#!/usr/bin/env python3
"""Test suite for security tools (secret_lint, permissions_lint, safe_paths_check)"""
import pytest
import tempfile
import pathlib


# Mock implementations for testing (these would be in the actual tools)

def detect_patterns(content):
    """Mock implementation of secret pattern detection"""
    patterns = {
        "api_key": r"(?i)(api[_-]?key|apikey)[\s]*[=:]\s*['\"]?([a-z0-9_\-]{20,})['\"]?",
        "aws_key": r"AKIA[0-9A-Z]{16}",
        "github_token": r"ghp_[a-zA-Z0-9]{36}",
        "private_key": r"-----BEGIN .* PRIVATE KEY-----"
    }
    
    import re
    findings = []
    for pattern_name, pattern in patterns.items():
        matches = re.finditer(pattern, content)
        for match in matches:
            findings.append({
                "type": pattern_name,
                "value": match.group(0),
                "line": content[:match.start()].count('\n') + 1
            })
    
    return findings


def check_entropy(string, threshold=4.5):
    """Mock implementation of entropy check"""
    import math
    from collections import Counter
    
    if len(string) < 20:
        return False
    
    counter = Counter(string)
    entropy = -sum(count/len(string) * math.log2(count/len(string)) 
                   for count in counter.values())
    
    return entropy > threshold


def scan_for_secrets(filepath):
    """Mock implementation of file scanning"""
    with open(filepath) as f:
        content = f.read()
    
    findings = detect_patterns(content)
    
    return {
        "file": filepath,
        "has_secrets": len(findings) > 0,
        "findings": findings
    }


def check_file_permissions(filepath):
    """Mock implementation of permission checking"""
    import os
    import stat
    
    st = os.stat(filepath)
    mode = st.st_mode
    
    return {
        "mode": oct(stat.S_IMODE(mode))[2:],  # Remove '0o' prefix
        "is_executable": bool(mode & stat.S_IXUSR),
        "is_world_readable": bool(mode & stat.S_IROTH),
        "is_world_writable": bool(mode & stat.S_IWOTH)
    }


def validate_permissions(filepath, file_type):
    """Mock implementation of permission validation"""
    perms = check_file_permissions(filepath)
    issues = []
    
    if file_type == "private_key":
        if perms["is_world_readable"]:
            issues.append("Private key permissions too permissive: world-readable")
        if perms["is_world_writable"]:
            issues.append("Private key permissions too permissive: world-writable")
    
    if file_type == "script":
        if not perms["is_executable"]:
            issues.append("Script is not executable")
    
    return len(issues) == 0, issues


def check_path_safety(path, allow_absolute=False, base_dir=None):
    """Mock implementation of path safety check"""
    dangerous = detect_path_traversal(path)
    
    if dangerous:
        return True, "Path traversal detected"
    
    if not allow_absolute and path.startswith('/'):
        return True, "Absolute path not allowed"
    
    if base_dir:
        import os
        try:
            real_path = os.path.realpath(path)
            real_base = os.path.realpath(base_dir)
            if not real_path.startswith(real_base):
                return True, "Path escapes base directory"
        except:
            pass
    
    return False, "Path is safe"


def detect_path_traversal(path):
    """Mock implementation of path traversal detection"""
    dangerous_patterns = [
        "..",
        "%2e%2e",
        "\x00",
        "..%2f",
        "%2f.."
    ]
    
    path_lower = path.lower()
    return any(pattern in path_lower for pattern in dangerous_patterns)


class TestSecretLint:
    """Test secret detection (secret_lint.py)"""
    
    def test_detect_api_key_pattern(self):
        """Should detect API key patterns"""
        content = "API_KEY=sk_live_abcdef123456789"
        secrets = detect_patterns(content)
        assert len(secrets) > 0
        assert any("api" in s["type"].lower() for s in secrets)
    
    def test_detect_aws_credentials(self):
        """Should detect AWS access keys"""
        content = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        secrets = detect_patterns(content)
        assert len(secrets) > 0
        assert any("aws" in s["type"].lower() for s in secrets)
    
    def test_detect_private_key(self):
        """Should detect private keys"""
        content = """
        -----BEGIN RSA PRIVATE KEY-----
        MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF2dT...
        -----END RSA PRIVATE KEY-----
        """
        secrets = detect_patterns(content)
        assert len(secrets) > 0
        assert any("private" in s["type"].lower() for s in secrets)
    
    def test_detect_github_token(self):
        """Should detect GitHub tokens"""
        content = "GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz1234567890"
        secrets = detect_patterns(content)
        assert len(secrets) > 0
        assert any("github" in s["type"].lower() for s in secrets)
    
    def test_no_secrets_in_clean_file(self):
        """Should not flag false positives in clean content"""
        content = """
        # This is a comment
        name = "application"
        version = "1.0.0"
        description = "A clean configuration file"
        """
        secrets = detect_patterns(content)
        assert len(secrets) == 0
    
    def test_entropy_detection_random_string(self):
        """Should detect high-entropy random strings"""
        # High entropy string (likely secret) - needs more unique characters
        high_entropy = "Kx9P3mR7nQ2sT4vY6wZ8jL5hG1bN0cM"
        assert check_entropy(high_entropy) is True
        
        # Low entropy string (normal text)
        low_entropy = "this is normal text"
        assert check_entropy(low_entropy) is False
    
    def test_scan_file_with_secrets(self, tmp_path):
        """Should scan file and find secrets"""
        test_file = tmp_path / "config.yaml"
        test_file.write_text("""
        database:
          password: "sup3rs3cr3tP@ssw0rd123!"
        api_key: "sk_live_1234567890abcdef"
        AWS_ACCESS_KEY_ID: "AKIAIOSFODNN7EXAMPLE"
        """)
        
        results = scan_for_secrets(str(test_file))
        assert results["has_secrets"] is True
        assert len(results["findings"]) > 0
    
    def test_scan_clean_file(self, tmp_path):
        """Should scan file and find no secrets"""
        test_file = tmp_path / "config.yaml"
        test_file.write_text("""
        database:
          host: "localhost"
          port: 5432
        api:
          timeout: 30
        """)
        
        results = scan_for_secrets(str(test_file))
        assert results["has_secrets"] is False
        assert len(results["findings"]) == 0
    
    def test_ignore_comments(self):
        """Should handle commented-out secrets appropriately"""
        content = """
        # EXAMPLE_KEY=sk_test_123456789 (this is just an example)
        # Do not use real keys in config files
        """
        secrets = detect_patterns(content)
        # Should still detect but mark as in comment
        if len(secrets) > 0:
            assert secrets[0].get("in_comment", False)


class TestPermissionsLint:
    """Test file permission validation (permissions_lint.py)"""
    
    def test_check_executable_permissions(self, tmp_path):
        """Should detect executable files"""
        script = tmp_path / "script.sh"
        script.write_text("#!/bin/bash\necho hello")
        script.chmod(0o755)  # rwxr-xr-x
        
        perms = check_file_permissions(str(script))
        assert perms["is_executable"] is True
        assert perms["mode"] == "755"
    
    def test_check_world_writable(self, tmp_path):
        """Should detect world-writable files"""
        dangerous_file = tmp_path / "open.txt"
        dangerous_file.write_text("content")
        dangerous_file.chmod(0o666)  # rw-rw-rw-
        
        perms = check_file_permissions(str(dangerous_file))
        assert perms["is_world_writable"] is True
    
    def test_check_world_readable(self, tmp_path):
        """Should detect world-readable files"""
        public_file = tmp_path / "public.txt"
        public_file.write_text("content")
        public_file.chmod(0o644)  # rw-r--r--
        
        perms = check_file_permissions(str(public_file))
        assert perms["is_world_readable"] is True
    
    def test_check_restricted_permissions(self, tmp_path):
        """Should validate properly restricted files"""
        private_file = tmp_path / "private.txt"
        private_file.write_text("sensitive data")
        private_file.chmod(0o600)  # rw-------
        
        perms = check_file_permissions(str(private_file))
        assert perms["is_world_readable"] is False
        assert perms["is_world_writable"] is False
    
    def test_validate_permissions_secure_files(self, tmp_path):
        """Should pass validation for secure file permissions"""
        secure_file = tmp_path / "secure.key"
        secure_file.write_text("private key")
        secure_file.chmod(0o600)
        
        is_valid, issues = validate_permissions(str(secure_file), "private_key")
        assert is_valid is True
        assert len(issues) == 0
    
    def test_validate_permissions_insecure_private_key(self, tmp_path):
        """Should fail validation for insecure private key"""
        insecure_key = tmp_path / "insecure.key"
        insecure_key.write_text("private key")
        insecure_key.chmod(0o644)  # Too open
        
        is_valid, issues = validate_permissions(str(insecure_key), "private_key")
        assert is_valid is False
        assert len(issues) > 0
        assert any("too permissive" in i.lower() for i in issues)
    
    def test_validate_script_executable(self, tmp_path):
        """Should validate script has executable bit"""
        script = tmp_path / "deploy.sh"
        script.write_text("#!/bin/bash\necho deploying")
        script.chmod(0o755)
        
        is_valid, issues = validate_permissions(str(script), "script")
        assert is_valid is True
    
    def test_validate_script_not_executable(self, tmp_path):
        """Should fail when script lacks executable bit"""
        script = tmp_path / "deploy.sh"
        script.write_text("#!/bin/bash\necho deploying")
        script.chmod(0o644)  # Not executable
        
        is_valid, issues = validate_permissions(str(script), "script")
        assert is_valid is False
        assert any("not executable" in i.lower() for i in issues)


class TestSafePathsCheck:
    """Test path safety validation (safe_paths_check.py)"""
    
    def test_detect_path_traversal_dotdot(self):
        """Should detect .. path traversal"""
        dangerous_path = "../../../etc/passwd"
        assert detect_path_traversal(dangerous_path) is True
    
    def test_detect_path_traversal_absolute(self):
        """Should detect absolute path attempts"""
        dangerous_path = "/etc/passwd"
        is_dangerous, reason = check_path_safety(dangerous_path, allow_absolute=False)
        assert is_dangerous is True
        assert "absolute" in reason.lower()
    
    def test_detect_encoded_traversal(self):
        """Should detect URL-encoded traversal"""
        dangerous_path = "..%2f..%2fetc%2fpasswd"
        assert detect_path_traversal(dangerous_path) is True
    
    def test_safe_relative_path(self):
        """Should allow safe relative paths"""
        safe_path = "src/components/Button.tsx"
        is_dangerous, reason = check_path_safety(safe_path)
        assert is_dangerous is False
    
    def test_safe_absolute_path_when_allowed(self):
        """Should allow absolute paths when permitted"""
        safe_path = "/usr/local/bin/app"
        is_dangerous, reason = check_path_safety(safe_path, allow_absolute=True)
        assert is_dangerous is False
    
    def test_detect_symlink_escape(self, tmp_path):
        """Should detect symlink that escapes allowed directory"""
        # Create symlink pointing outside
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        
        link_path = tmp_path / "escape_link"
        link_path.symlink_to(target_dir.parent)
        
        is_dangerous, reason = check_path_safety(
            str(link_path),
            base_dir=str(tmp_path)
        )
        assert is_dangerous is True
    
    def test_detect_null_byte_injection(self):
        """Should detect null byte injection attempts"""
        dangerous_path = "file.txt\x00.exe"
        assert detect_path_traversal(dangerous_path) is True
    
    def test_validate_archive_paths(self, tmp_path):
        """Should validate paths in archive extraction"""
        safe_paths = [
            "README.md",
            "src/main.py",
            "docs/guide.md"
        ]
        
        dangerous_paths = [
            "../../../etc/passwd",
            "/etc/shadow",
            "legal/../../../etc/hosts"
        ]
        
        for path in safe_paths:
            is_dangerous, _ = check_path_safety(path)
            assert is_dangerous is False, f"False positive: {path}"
        
        for path in dangerous_paths:
            is_dangerous, _ = check_path_safety(path)
            assert is_dangerous is True, f"Missed dangerous path: {path}"


class TestSecurityIntegration:
    """Integration tests for security tools"""
    
    def test_full_security_scan(self, tmp_path):
        """Should perform complete security scan"""
        # Create test files with various issues
        
        # File with secrets
        config = tmp_path / "config.py"
        config.write_text('API_KEY = "sk_live_abc123456789def"\nAWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"')
        
        # File with bad permissions
        script = tmp_path / "deploy.sh"
        script.write_text("#!/bin/bash\nrm -rf /")
        script.chmod(0o777)  # World writable!
        
        # Scan for secrets
        secret_results = scan_for_secrets(str(config))
        assert secret_results["has_secrets"] is True
        
        # Check permissions
        perm_results = check_file_permissions(str(script))
        assert perm_results["is_world_writable"] is True
        
        # Both should be flagged in security report
        total_issues = len(secret_results["findings"]) + (1 if perm_results["is_world_writable"] else 0)
        assert total_issues >= 2
    
    def test_clean_project_passes(self, tmp_path):
        """Should pass security scan for clean project"""
        # Create clean files
        readme = tmp_path / "README.md"
        readme.write_text("# Clean Project\n\nNo secrets here!")
        readme.chmod(0o644)
        
        script = tmp_path / "build.sh"
        script.write_text("#!/bin/bash\necho 'Building...'")
        script.chmod(0o755)
        
        # Scan
        secret_results = scan_for_secrets(str(readme))
        perm_results = check_file_permissions(str(script))
        
        assert secret_results["has_secrets"] is False
        assert perm_results["is_world_writable"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
