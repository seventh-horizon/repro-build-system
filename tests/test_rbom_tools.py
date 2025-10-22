#!/usr/bin/env python3
"""Test suite for RBOM (Release Bill of Materials) tools"""
import pytest
import json
import tempfile
import pathlib
from tools.make_rbom import generate_rbom, collect_artifacts
from tools.rbom_check import validate_rbom, check_schema_version, check_artifact_count


class TestMakeRBOM:
    """Test RBOM generation (make_rbom.py)"""
    
    def test_collect_artifacts_empty_directory(self, tmp_path):
        """Should return empty list for empty directory"""
        artifacts = collect_artifacts(str(tmp_path))
        assert artifacts == []
    
    def test_collect_artifacts_with_files(self, tmp_path):
        """Should collect all artifact files"""
        # Create test artifacts
        (tmp_path / "artifact1.tar.gz").write_bytes(b"content1")
        (tmp_path / "artifact2.zip").write_bytes(b"content2")
        (tmp_path / "artifact3.txt").write_bytes(b"content3")
        
        artifacts = collect_artifacts(str(tmp_path))
        assert len(artifacts) == 3
        
        # Check artifact structure
        names = [a["name"] for a in artifacts]
        assert "artifact1.tar.gz" in names
        assert "artifact2.zip" in names
        assert "artifact3.txt" in names
    
    def test_artifact_includes_sha256(self, tmp_path):
        """Should include SHA-256 hash for each artifact"""
        test_file = tmp_path / "test.bin"
        test_content = b"test content for hashing"
        test_file.write_bytes(test_content)
        
        artifacts = collect_artifacts(str(tmp_path))
        assert len(artifacts) == 1
        
        # Verify SHA-256 is present and valid
        import hashlib
        expected_sha = hashlib.sha256(test_content).hexdigest()
        assert artifacts[0]["sha256"] == expected_sha
    
    def test_artifact_includes_size(self, tmp_path):
        """Should include file size for each artifact"""
        test_file = tmp_path / "test.bin"
        test_content = b"x" * 1024  # 1KB
        test_file.write_bytes(test_content)
        
        artifacts = collect_artifacts(str(tmp_path))
        assert artifacts[0]["size"] == 1024
    
    def test_generate_rbom_structure(self, tmp_path):
        """Should generate valid RBOM structure"""
        # Create test artifacts
        (tmp_path / "artifact.tar.gz").write_bytes(b"content")
        
        rbom = generate_rbom(str(tmp_path), "v1.0.0")
        
        # Check required fields
        assert "schema_version" in rbom
        assert "release_version" in rbom
        assert "artifacts" in rbom
        assert "generated_at" in rbom
        
        assert rbom["release_version"] == "v1.0.0"
        assert isinstance(rbom["artifacts"], list)
    
    def test_generate_rbom_with_metadata(self, tmp_path):
        """Should include metadata in RBOM"""
        (tmp_path / "artifact.tar.gz").write_bytes(b"content")
        
        metadata = {
            "build_id": "12345",
            "git_sha": "abc123"
        }
        rbom = generate_rbom(str(tmp_path), "v1.0.0", metadata=metadata)
        
        assert "metadata" in rbom
        assert rbom["metadata"]["build_id"] == "12345"
        assert rbom["metadata"]["git_sha"] == "abc123"


class TestRBOMCheck:
    """Test RBOM validation (rbom_check.py)"""
    
    def test_valid_rbom_passes(self):
        """Should pass validation for valid RBOM"""
        rbom = {
            "schema_version": "1.0",
            "release_version": "v1.0.0",
            "artifacts": [
                {
                    "name": "artifact.tar.gz",
                    "sha256": "a" * 64,
                    "size": 1024
                }
            ],
            "generated_at": "2025-10-14T00:00:00Z"
        }
        
        is_valid, errors = validate_rbom(rbom)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_missing_schema_version(self):
        """Should fail when schema_version missing"""
        rbom = {
            "release_version": "v1.0.0",
            "artifacts": []
        }
        
        is_valid, errors = validate_rbom(rbom)
        assert is_valid is False
        assert any("schema_version" in e for e in errors)
    
    def test_missing_artifacts(self):
        """Should fail when artifacts missing"""
        rbom = {
            "schema_version": "1.0",
            "release_version": "v1.0.0"
        }
        
        is_valid, errors = validate_rbom(rbom)
        assert is_valid is False
        assert any("artifacts" in e for e in errors)
    
    def test_check_schema_version_valid(self):
        """Should accept valid schema versions"""
        assert check_schema_version("1.0") is True
        assert check_schema_version("1.1") is True
        assert check_schema_version("2.0") is True
    
    def test_check_schema_version_invalid(self):
        """Should reject invalid schema versions"""
        assert check_schema_version("0.9") is False
        assert check_schema_version("invalid") is False
        assert check_schema_version("") is False
    
    def test_check_artifact_count_within_limits(self):
        """Should pass when artifact count is reasonable"""
        rbom = {"artifacts": [{"name": f"artifact{i}"} for i in range(10)]}
        assert check_artifact_count(rbom, max_count=100) is True
    
    def test_check_artifact_count_exceeds_limit(self):
        """Should fail when artifact count exceeds limit"""
        rbom = {"artifacts": [{"name": f"artifact{i}"} for i in range(150)]}
        assert check_artifact_count(rbom, max_count=100) is False
    
    def test_artifact_missing_sha256(self):
        """Should fail when artifact lacks SHA-256"""
        rbom = {
            "schema_version": "1.0",
            "release_version": "v1.0.0",
            "artifacts": [
                {
                    "name": "artifact.tar.gz",
                    "size": 1024
                    # Missing sha256
                }
            ]
        }
        
        is_valid, errors = validate_rbom(rbom)
        assert is_valid is False
        assert any("sha256" in e.lower() for e in errors)
    
    def test_artifact_invalid_sha256_format(self):
        """Should fail when SHA-256 is invalid format"""
        rbom = {
            "schema_version": "1.0",
            "release_version": "v1.0.0",
            "artifacts": [
                {
                    "name": "artifact.tar.gz",
                    "sha256": "invalid_hash",
                    "size": 1024
                }
            ]
        }
        
        is_valid, errors = validate_rbom(rbom)
        assert is_valid is False


class TestRBOMPolicy:
    """Test RBOM policy enforcement"""
    
    def test_forbidden_patterns_detection(self):
        """Should detect forbidden file patterns"""
        rbom = {
            "schema_version": "1.0",
            "release_version": "v1.0.0",
            "artifacts": [
                {"name": "artifact.exe", "sha256": "a" * 64, "size": 1024}
            ]
        }
        
        policy = {
            "forbidden_extensions": [".exe", ".dll"]
        }
        
        violations = check_policy(rbom, policy)
        assert len(violations) > 0
        assert any(".exe" in v for v in violations)
    
    def test_required_artifacts_present(self):
        """Should verify required artifacts are present"""
        rbom = {
            "schema_version": "1.0",
            "release_version": "v1.0.0",
            "artifacts": [
                {"name": "README.md", "sha256": "a" * 64, "size": 100},
                {"name": "LICENSE", "sha256": "b" * 64, "size": 200}
            ]
        }
        
        policy = {
            "required_artifacts": ["README.md", "LICENSE"]
        }
        
        violations = check_policy(rbom, policy)
        assert len(violations) == 0
    
    def test_required_artifacts_missing(self):
        """Should detect missing required artifacts"""
        rbom = {
            "schema_version": "1.0",
            "release_version": "v1.0.0",
            "artifacts": [
                {"name": "README.md", "sha256": "a" * 64, "size": 100}
            ]
        }
        
        policy = {
            "required_artifacts": ["README.md", "LICENSE"]
        }
        
        violations = check_policy(rbom, policy)
        assert len(violations) > 0
        assert any("LICENSE" in v for v in violations)
    
    def test_size_limits_enforced(self):
        """Should enforce artifact size limits"""
        rbom = {
            "schema_version": "1.0",
            "release_version": "v1.0.0",
            "artifacts": [
                {"name": "huge.bin", "sha256": "a" * 64, "size": 2000000000}  # 2GB
            ]
        }
        
        policy = {
            "max_artifact_size": 1000000000  # 1GB
        }
        
        violations = check_policy(rbom, policy)
        assert len(violations) > 0
        assert any("size" in v.lower() for v in violations)


class TestRBOMIntegration:
    """Integration tests for complete RBOM workflow"""
    
    def test_generate_and_validate_rbom(self, tmp_path):
        """Should generate and successfully validate RBOM"""
        # Create test artifacts
        (tmp_path / "app.tar.gz").write_bytes(b"application")
        (tmp_path / "README.md").write_bytes(b"readme content")
        (tmp_path / "LICENSE").write_bytes(b"license text")
        
        # Generate RBOM
        rbom = generate_rbom(str(tmp_path), "v1.0.0")
        
        # Validate RBOM
        is_valid, errors = validate_rbom(rbom)
        assert is_valid is True
        assert len(errors) == 0
        
        # Check all artifacts present
        assert len(rbom["artifacts"]) == 3
    
    def test_rbom_file_persistence(self, tmp_path):
        """Should save and load RBOM from file"""
        # Create artifacts
        (tmp_path / "artifact.tar.gz").write_bytes(b"content")
        
        # Generate RBOM
        rbom = generate_rbom(str(tmp_path), "v1.0.0")
        
        # Save to file
        rbom_file = tmp_path / "release_bom.json"
        rbom_file.write_text(json.dumps(rbom, indent=2))
        
        # Load and validate
        loaded_rbom = json.loads(rbom_file.read_text())
        is_valid, errors = validate_rbom(loaded_rbom)
        assert is_valid is True


# Mock implementation of check_policy for testing
def check_policy(rbom, policy):
    """Check RBOM against policy constraints"""
    violations = []
    
    # Check forbidden extensions
    if "forbidden_extensions" in policy:
        for artifact in rbom.get("artifacts", []):
            for forbidden_ext in policy["forbidden_extensions"]:
                if artifact["name"].endswith(forbidden_ext):
                    violations.append(f"Forbidden extension {forbidden_ext} in {artifact['name']}")
    
    # Check required artifacts
    if "required_artifacts" in policy:
        present_artifacts = {a["name"] for a in rbom.get("artifacts", [])}
        for required in policy["required_artifacts"]:
            if required not in present_artifacts:
                violations.append(f"Required artifact missing: {required}")
    
    # Check size limits
    if "max_artifact_size" in policy:
        for artifact in rbom.get("artifacts", []):
            if artifact.get("size", 0) > policy["max_artifact_size"]:
                violations.append(f"Artifact {artifact['name']} exceeds size limit")
    
    return violations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
