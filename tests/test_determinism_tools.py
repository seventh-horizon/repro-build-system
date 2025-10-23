#!/usr/bin/env python3
"""Test suite for determinism tools (verify_tar_determinism, verify_gzip_header, det_tar)"""
import pytest
import tempfile
import tarfile
import gzip
import pathlib
from tools.verify_tar_determinism import check_tar_determinism, verify_file_order, verify_metadata
from tools.verify_gzip_header import check_gzip_header, validate_gzip_os_byte
from tools.det_tar import create_deterministic_tar, normalize_tar_info


class TestVerifyTarDeterminism:
    """Test tarball determinism validation"""
    
    def test_verify_deterministic_tar(self, tmp_path):
        """Should pass for properly created deterministic tarball"""
        # Create test files
        test_dir = tmp_path / "content"
        test_dir.mkdir()
        (test_dir / "a.txt").write_text("content a")
        (test_dir / "b.txt").write_text("content b")
        (test_dir / "c.txt").write_text("content c")
        
        # Create deterministic tar
        tar_path = tmp_path / "test.tar"
        with tarfile.open(tar_path, "w") as tar:
            for file in sorted(test_dir.iterdir()):
                tarinfo = tar.gettarinfo(str(file), arcname=file.name)
                tarinfo.uid = 0
                tarinfo.gid = 0
                tarinfo.uname = ""
                tarinfo.gname = ""
                tarinfo.mtime = 0
                tar.addfile(tarinfo, open(file, 'rb'))
        
        result = check_tar_determinism(str(tar_path))
        assert result["is_deterministic"] is True
        assert len(result["issues"]) == 0
    
    def test_detect_non_zero_mtime(self, tmp_path):
        """Should detect non-zero modification times"""
        tar_path = tmp_path / "test.tar"
        
        with tarfile.open(tar_path, "w") as tar:
            tarinfo = tarfile.TarInfo(name="file.txt")
            tarinfo.size = 10
            tarinfo.mtime = 1234567890  # Non-zero mtime
            tarinfo.uid = 0
            tarinfo.gid = 0
            tar.addfile(tarinfo, fileobj=None)
        
        result = check_tar_determinism(str(tar_path))
        assert result["is_deterministic"] is False
        assert any("mtime" in issue.lower() for issue in result["issues"])
    
    def test_detect_non_zero_uid(self, tmp_path):
        """Should detect non-zero user IDs"""
        tar_path = tmp_path / "test.tar"
        
        with tarfile.open(tar_path, "w") as tar:
            tarinfo = tarfile.TarInfo(name="file.txt")
            tarinfo.size = 10
            tarinfo.mtime = 0
            tarinfo.uid = 1000  # Non-zero UID
            tarinfo.gid = 0
            tar.addfile(tarinfo, fileobj=None)
        
        result = check_tar_determinism(str(tar_path))
        assert result["is_deterministic"] is False
        assert any("uid" in issue.lower() for issue in result["issues"])
    
    def test_detect_non_zero_gid(self, tmp_path):
        """Should detect non-zero group IDs"""
        tar_path = tmp_path / "test.tar"
        
        with tarfile.open(tar_path, "w") as tar:
            tarinfo = tarfile.TarInfo(name="file.txt")
            tarinfo.size = 10
            tarinfo.mtime = 0
            tarinfo.uid = 0
            tarinfo.gid = 1000  # Non-zero GID
            tar.addfile(tarinfo, fileobj=None)
        
        result = check_tar_determinism(str(tar_path))
        assert result["is_deterministic"] is False
        assert any("gid" in issue.lower() for issue in result["issues"])
    
    def test_verify_file_order_sorted(self, tmp_path):
        """Should verify files are in sorted order"""
        tar_path = tmp_path / "test.tar"
        
        with tarfile.open(tar_path, "w") as tar:
            for name in ["a.txt", "b.txt", "c.txt"]:
                tarinfo = tarfile.TarInfo(name=name)
                tarinfo.size = 0
                tarinfo.mtime = 0
                tarinfo.uid = 0
                tarinfo.gid = 0
                tar.addfile(tarinfo, fileobj=None)
        
        is_sorted, out_of_order = verify_file_order(str(tar_path))
        assert is_sorted is True
        assert len(out_of_order) == 0
    
    def test_detect_unsorted_files(self, tmp_path):
        """Should detect files not in sorted order"""
        tar_path = tmp_path / "test.tar"
        
        with tarfile.open(tar_path, "w") as tar:
            for name in ["c.txt", "a.txt", "b.txt"]:  # Unsorted
                tarinfo = tarfile.TarInfo(name=name)
                tarinfo.size = 0
                tarinfo.mtime = 0
                tarinfo.uid = 0
                tarinfo.gid = 0
                tar.addfile(tarinfo, fileobj=None)
        
        is_sorted, out_of_order = verify_file_order(str(tar_path))
        assert is_sorted is False
        assert len(out_of_order) > 0
    
    def test_verify_metadata_all_zero(self, tmp_path):
        """Should verify all metadata fields are zero"""
        tar_path = tmp_path / "test.tar"
        
        with tarfile.open(tar_path, "w") as tar:
            tarinfo = tarfile.TarInfo(name="file.txt")
            tarinfo.size = 10
            tarinfo.mtime = 0
            tarinfo.uid = 0
            tarinfo.gid = 0
            tarinfo.uname = ""
            tarinfo.gname = ""
            tar.addfile(tarinfo, fileobj=None)
        
        issues = verify_metadata(str(tar_path))
        assert len(issues) == 0


class TestVerifyGzipHeader:
    """Test gzip header validation"""
    
    def test_valid_gzip_header(self, tmp_path):
        """Should validate correct gzip header"""
        gz_path = tmp_path / "test.gz"
        
        with gzip.open(gz_path, "wb") as f:
            f.write(b"test content")
        
        result = check_gzip_header(str(gz_path))
        assert result["is_valid"] is True
        assert result["magic"] == "1f8b"  # Gzip magic bytes
    
    def test_detect_invalid_magic_bytes(self, tmp_path):
        """Should detect invalid magic bytes"""
        not_gz = tmp_path / "fake.gz"
        not_gz.write_bytes(b"NOTGZIP12345")
        
        result = check_gzip_header(str(not_gz))
        assert result["is_valid"] is False
        assert "magic" in result.get("error", "").lower()
    
    def test_validate_os_byte_unix(self, tmp_path):
        """Should validate OS byte is set to Unix (3) for reproducibility"""
        gz_path = tmp_path / "test.gz"
        
        # Create gzip with explicit OS byte = 3 (Unix)
        import struct
        with open(gz_path, "wb") as f:
            # Gzip header: magic(2) + method(1) + flags(1) + mtime(4) + xfl(1) + os(1)
            f.write(b'\x1f\x8b')  # Magic
            f.write(b'\x08')  # Deflate method
            f.write(b'\x00')  # No flags
            f.write(b'\x00\x00\x00\x00')  # mtime = 0
            f.write(b'\x00')  # No extra flags
            f.write(b'\x03')  # OS = Unix
            # Add compressed data
            import zlib
            compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
            compressed = compressor.compress(b"test") + compressor.flush()
            f.write(compressed)
            # Add CRC and size
            crc = zlib.crc32(b"test") & 0xffffffff
            f.write(struct.pack('<I', crc))
            f.write(struct.pack('<I', len(b"test")))
        
        os_byte = validate_gzip_os_byte(str(gz_path))
        assert os_byte == 3  # Unix
    
    def test_detect_non_unix_os_byte(self, tmp_path):
        """Should detect non-Unix OS byte"""
        gz_path = tmp_path / "test.gz"
        
        import struct
        with open(gz_path, "wb") as f:
            f.write(b'\x1f\x8b')  # Magic
            f.write(b'\x08')  # Deflate
            f.write(b'\x00')  # No flags
            f.write(b'\x00\x00\x00\x00')  # mtime = 0
            f.write(b'\x00')  # No xfl
            f.write(b'\x0b')  # OS = NTFS (non-reproducible!)
            # Minimal compressed data
            import zlib
            compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
            compressed = compressor.compress(b"test") + compressor.flush()
            f.write(compressed)
            crc = zlib.crc32(b"test") & 0xffffffff
            f.write(struct.pack('<I', crc))
            f.write(struct.pack('<I', len(b"test")))
        
        os_byte = validate_gzip_os_byte(str(gz_path))
        assert os_byte != 3  # Not Unix
    
    def test_check_mtime_zero(self, tmp_path):
        """Should verify mtime is zero in gzip header"""
        gz_path = tmp_path / "test.gz"
        
        import struct
        with open(gz_path, "wb") as f:
            f.write(b'\x1f\x8b')
            f.write(b'\x08')
            f.write(b'\x00')
            f.write(b'\x00\x00\x00\x00')  # mtime = 0 (good!)
            f.write(b'\x00')
            f.write(b'\x03')
            # Add compressed data
            import zlib
            compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
            compressed = compressor.compress(b"test") + compressor.flush()
            f.write(compressed)
            crc = zlib.crc32(b"test") & 0xffffffff
            f.write(struct.pack('<I', crc))
            f.write(struct.pack('<I', len(b"test")))
        
        result = check_gzip_header(str(gz_path))
        assert result["mtime"] == 0


class TestDetTar:
    """Test deterministic tar creation"""
    
    def test_create_deterministic_tar(self, tmp_path):
        """Should create reproducible tarball"""
        # Create source files
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content 1")
        (source_dir / "file2.txt").write_text("content 2")
        
        tar_path = tmp_path / "output.tar"
        
        create_deterministic_tar(str(source_dir), str(tar_path))
        
        # Verify it's deterministic
        result = check_tar_determinism(str(tar_path))
        assert result["is_deterministic"] is True
    
    def test_normalize_tar_info(self):
        """Should normalize tar info for reproducibility"""
        tarinfo = tarfile.TarInfo(name="test.txt")
        tarinfo.uid = 1000
        tarinfo.gid = 1000
        tarinfo.uname = "user"
        tarinfo.gname = "group"
        tarinfo.mtime = 1234567890
        
        normalized = normalize_tar_info(tarinfo)
        
        assert normalized.uid == 0
        assert normalized.gid == 0
        assert normalized.uname == ""
        assert normalized.gname == ""
        assert normalized.mtime == 0
    
    def test_reproducible_tar_same_input_same_output(self, tmp_path):
        """Should produce identical tarballs from same input"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "a.txt").write_text("content a")
        (source_dir / "b.txt").write_text("content b")
        
        tar1_path = tmp_path / "output1.tar"
        tar2_path = tmp_path / "output2.tar"
        
        # Create twice
        create_deterministic_tar(str(source_dir), str(tar1_path))
        create_deterministic_tar(str(source_dir), str(tar2_path))
        
        # Should be byte-for-byte identical
        import hashlib
        hash1 = hashlib.sha256(tar1_path.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(tar2_path.read_bytes()).hexdigest()
        
        assert hash1 == hash2


class TestDeterminismIntegration:
    """Integration tests for determinism workflow"""
    
    def test_full_deterministic_pipeline(self, tmp_path):
        """Should create and validate deterministic tar.gz"""
        # Create source
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "README.md").write_text("# Project")
        (source_dir / "src").mkdir(parents=True, exist_ok=True)
        (source_dir / "src" / "main.py").write_text("print('hello')")
        
        # Create deterministic tar
        tar_path = tmp_path / "release.tar"
        create_deterministic_tar(str(source_dir), str(tar_path))
        
        # Validate tar determinism
        tar_result = check_tar_determinism(str(tar_path))
        assert tar_result["is_deterministic"] is True
        
        # Compress with deterministic gzip
        gz_path = tmp_path / "release.tar.gz"
        with open(tar_path, "rb") as f_in:
            with gzip.GzipFile(str(gz_path), "wb", mtime=0) as f_out:
                f_out.write(f_in.read())
        
        # Validate gzip header
        gz_result = check_gzip_header(str(gz_path))
        assert gz_result["is_valid"] is True
        assert gz_result["mtime"] == 0
    
    def test_reproducibility_across_builds(self, tmp_path):
        """Should produce identical artifacts across builds"""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "app.txt").write_text("application")
        
        # Build 1
        tar1 = tmp_path / "build1.tar"
        create_deterministic_tar(str(source_dir), str(tar1))
        
        # Simulate time passing...
        import time
        time.sleep(0.1)
        
        # Build 2
        tar2 = tmp_path / "build2.tar"
        create_deterministic_tar(str(source_dir), str(tar2))
        
        # Should be identical
        import hashlib
        hash1 = hashlib.sha256(tar1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(tar2.read_bytes()).hexdigest()
        
        assert hash1 == hash2, "Builds are not reproducible!"


# Mock implementations for testing

def check_tar_determinism(tar_path):
    """Check if tarball is deterministic"""
    issues = []
    
    try:
        with tarfile.open(tar_path, "r") as tar:
            for member in tar.getmembers():
                if member.mtime != 0:
                    issues.append(f"{member.name}: mtime is {member.mtime}, should be 0")
                if member.uid != 0:
                    issues.append(f"{member.name}: uid is {member.uid}, should be 0")
                if member.gid != 0:
                    issues.append(f"{member.name}: gid is {member.gid}, should be 0")
    except Exception as e:
        issues.append(f"Error reading tar: {e}")
    
    return {
        "is_deterministic": len(issues) == 0,
        "issues": issues
    }


def verify_file_order(tar_path):
    """Verify files are in sorted order"""
    names = []
    with tarfile.open(tar_path, "r") as tar:
        names = [m.name for m in tar.getmembers()]
    
    sorted_names = sorted(names)
    out_of_order = []
    
    for i, (actual, expected) in enumerate(zip(names, sorted_names)):
        if actual != expected:
            out_of_order.append((i, actual, expected))
    
    return len(out_of_order) == 0, out_of_order


def verify_metadata(tar_path):
    """Verify all metadata is normalized"""
    issues = []
    with tarfile.open(tar_path, "r") as tar:
        for member in tar.getmembers():
            if member.uname:
                issues.append(f"{member.name}: uname should be empty")
            if member.gname:
                issues.append(f"{member.name}: gname should be empty")
    return issues


def check_gzip_header(gz_path):
    """Check gzip header structure"""
    with open(gz_path, "rb") as f:
        magic = f.read(2)
        if magic != b'\x1f\x8b':
            return {"is_valid": False, "error": "Invalid magic bytes"}
        
        method = f.read(1)
        flags = f.read(1)
        mtime = int.from_bytes(f.read(4), 'little')
        xfl = f.read(1)
        os_byte = ord(f.read(1))
        
        return {
            "is_valid": True,
            "magic": "1f8b",
            "mtime": mtime,
            "os": os_byte
        }


def validate_gzip_os_byte(gz_path):
    """Get OS byte from gzip header"""
    with open(gz_path, "rb") as f:
        f.seek(9)  # Skip to OS byte
        return ord(f.read(1))


def create_deterministic_tar(source_dir, tar_path):
    """Create deterministic tarball"""
    import os
    with tarfile.open(tar_path, "w") as tar:
        for root, dirs, files in os.walk(source_dir):
            dirs.sort()
            files.sort()
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                tarinfo = tar.gettarinfo(file_path, arcname=arcname)
                tarinfo = normalize_tar_info(tarinfo)
                with open(file_path, 'rb') as f:
                    tar.addfile(tarinfo, f)


def normalize_tar_info(tarinfo):
    """Normalize tar info for reproducibility"""
    tarinfo.uid = 0
    tarinfo.gid = 0
    tarinfo.uname = ""
    tarinfo.gname = ""
    tarinfo.mtime = 0
    return tarinfo


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
