#!/usr/bin/env python3
"""Test suite for vel_validator.py - Manifest validation tool"""
import pytest
import json
import tempfile
import pathlib
import subprocess
from unittest.mock import patch, MagicMock
from tools.vel_validator import (
    read_json, validate_schema_builtin, validate_schema_jsonschema,
    check_git_sha_exists_locally, check_artifact_sha
)


class TestReadJson:
    """Test JSON file reading"""
    
    def test_read_valid_json(self, tmp_path):
        """Should read valid JSON file"""
        test_file = tmp_path / "test.json"
        test_data = {"key": "value", "number": 42}
        test_file.write_text(json.dumps(test_data))
        
        result = read_json(str(test_file))
        assert result == test_data
    
    def test_read_nonexistent_file(self):
        """Should raise FileNotFoundError for missing file"""
        with pytest.raises(FileNotFoundError):
            read_json("/nonexistent/path.json")
    
    def test_read_invalid_json(self, tmp_path):
        """Should raise JSONDecodeError for invalid JSON"""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{invalid json}")
        
        with pytest.raises(json.JSONDecodeError):
            read_json(str(test_file))


class TestValidateSchemaBuiltin:
    """Test built-in schema validation"""
    
    def test_valid_manifest_structure(self):
        """Should pass for manifest with required sections"""
        doc = {
            "provenance": {},
            "environment": {},
            "results_contract": {}
        }
        assert validate_schema_builtin(doc) is True
    
    def test_missing_provenance(self, capsys):
        """Should fail and warn when provenance missing"""
        doc = {"environment": {}, "results_contract": {}}
        result = validate_schema_builtin(doc)
        assert result is False
        captured = capsys.readouterr()
        assert "missing core sections" in captured.err
    
    def test_missing_environment(self):
        """Should fail when environment missing"""
        doc = {"provenance": {}, "results_contract": {}}
        assert validate_schema_builtin(doc) is False
    
    def test_missing_results_contract(self):
        """Should fail when results_contract missing"""
        doc = {"provenance": {}, "environment": {}}
        assert validate_schema_builtin(doc) is False
    
    def test_empty_document(self):
        """Should fail for empty document"""
        assert validate_schema_builtin({}) is False


class TestValidateSchemaJsonschema:
    """Test JSON Schema validation"""
    
    def test_valid_against_schema(self, tmp_path):
        """Should pass when document matches schema"""
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}}
        }
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps(schema))
        
        doc = {"name": "test"}
        result = validate_schema_jsonschema(doc, str(schema_file))
        assert result is True
    
    def test_invalid_against_schema(self, tmp_path, capsys):
        """Should fail when document doesn't match schema"""
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}}
        }
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps(schema))
        
        doc = {"name": 123}  # Wrong type
        result = validate_schema_jsonschema(doc, str(schema_file))
        assert result is False
        captured = capsys.readouterr()
        assert "validation failed" in captured.err
    
    def test_missing_schema_file(self, capsys):
        """Should warn but pass when schema file missing"""
        doc = {"any": "data"}
        result = validate_schema_jsonschema(doc, "/nonexistent/schema.json")
        assert result is True
        captured = capsys.readouterr()
        assert "schema not found" in captured.err


class TestCheckGitShaExistsLocally:
    """Test git commit verification"""
    
    @patch('subprocess.check_call')
    def test_commit_exists(self, mock_check_call):
        """Should return True when git commit exists"""
        mock_check_call.return_value = None
        exists, reason = check_git_sha_exists_locally("abc123")
        assert exists is True
        assert reason == "present"
        mock_check_call.assert_called_once()
    
    @patch('subprocess.check_call')
    def test_commit_not_found(self, mock_check_call):
        """Should return False when git commit not found"""
        mock_check_call.side_effect = subprocess.CalledProcessError(1, 'git')
        exists, reason = check_git_sha_exists_locally("missing123")
        assert exists is False
        assert reason == "not_found"
    
    @patch('subprocess.check_call')
    def test_git_not_installed(self, mock_check_call):
        """Should return False when git command missing"""
        mock_check_call.side_effect = FileNotFoundError()
        exists, reason = check_git_sha_exists_locally("abc123")
        assert exists is False
        assert reason == "git_missing"


class TestCheckArtifactSha:
    """Test artifact hash verification"""
    
    def test_matching_sha(self, tmp_path):
        """Should return True when SHA matches"""
        artifact = tmp_path / "artifact.txt"
        artifact.write_bytes(b"test content")
        
        # Calculate expected SHA256
        import hashlib
        expected_sha = hashlib.sha256(b"test content").hexdigest()
        
        result = check_artifact_sha(expected_sha, str(artifact))
        assert result is True
    
    def test_mismatching_sha(self, tmp_path):
        """Should return False when SHA doesn't match"""
        artifact = tmp_path / "artifact.txt"
        artifact.write_bytes(b"test content")
        
        result = check_artifact_sha("wrongsha256hash", str(artifact))
        assert result is False
    
    def test_case_insensitive_sha(self, tmp_path):
        """Should handle case-insensitive SHA comparison"""
        artifact = tmp_path / "artifact.txt"
        artifact.write_bytes(b"test content")
        
        import hashlib
        expected_sha = hashlib.sha256(b"test content").hexdigest()
        
        result = check_artifact_sha(expected_sha.upper(), str(artifact))
        assert result is True
    
    def test_nonexistent_artifact(self, capsys):
        """Should return False for missing artifact"""
        result = check_artifact_sha("anysha", "/nonexistent/artifact")
        assert result is False
        captured = capsys.readouterr()
        assert "failed to hash artifact" in captured.err


class TestIntegrationValidation:
    """Integration tests for complete validation workflow"""
    
    def test_complete_valid_manifest(self, tmp_path):
        """Should validate complete valid manifest"""
        # Create artifact
        artifact = tmp_path / "artifact.tar.gz"
        artifact.write_bytes(b"artifact content")
        
        # Calculate artifact SHA
        import hashlib
        artifact_sha = hashlib.sha256(b"artifact content").hexdigest()
        
        # Create manifest
        manifest = {
            "provenance": {
                "artifact_sha256": artifact_sha,
                "git_sha": "abc123"
            },
            "environment": {"python_version": "3.11"},
            "results_contract": {"status": "success"}
        }
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))
        
        # Validate
        doc = read_json(str(manifest_file))
        assert validate_schema_builtin(doc) is True
        assert check_artifact_sha(artifact_sha, str(artifact)) is True
    
    def test_manifest_with_wrong_artifact_hash(self, tmp_path):
        """Should detect artifact hash mismatch"""
        artifact = tmp_path / "artifact.tar.gz"
        artifact.write_bytes(b"artifact content")
        
        manifest = {
            "provenance": {
                "artifact_sha256": "wronghash",
                "git_sha": "abc123"
            },
            "environment": {},
            "results_contract": {}
        }
        manifest_file = tmp_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest))
        
        doc = read_json(str(manifest_file))
        assert validate_schema_builtin(doc) is True
        assert check_artifact_sha("wronghash", str(artifact)) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
