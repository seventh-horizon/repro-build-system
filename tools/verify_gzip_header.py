#!/usr/bin/env python3
"""GZIP header helpers used by tests."""

from __future__ import annotations
from typing import Dict

__all__ = ["check_gzip_header", "validate_gzip_os_byte"]


def _read_first_10_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read(10)


def check_gzip_header(gz_path: str) -> Dict[str, object]:
    """
    Returns:
        {
            "is_valid": bool,
            "magic": str,   # hex, e.g. "1f8b"
            "mtime": int,   # header mtime (seconds)
            "error": str | None
        }
    """
    try:
        hdr = _read_first_10_bytes(gz_path)
        if len(hdr) < 10:
            return {"is_valid": False, "magic": "", "mtime": 0, "error": "short_header"}
        id1, id2 = hdr[0], hdr[1]
        magic = f"{id1:02x}{id2:02x}"
        if (id1, id2) != (0x1F, 0x8B):
            return {"is_valid": False, "magic": magic, "mtime": 0, "error": "bad_magic"}
        # MTIME occupies bytes 4..7 (little-endian)
        mtime = int.from_bytes(hdr[4:8], "little", signed=False)
        return {"is_valid": True, "magic": magic, "mtime": mtime, "error": None}
    except Exception as e:
        return {"is_valid": False, "magic": "", "mtime": 0, "error": f"{e}"}


def validate_gzip_os_byte(gz_path: str) -> int:
    """
    Returns the OS byte value from GZIP header (byte 9).
    Tests typically expect 3 (Unix) for reproducibility.
    """
    hdr = _read_first_10_bytes(gz_path)
    if len(hdr) < 10:
        raise ValueError("short_header")
    return hdr[9]
