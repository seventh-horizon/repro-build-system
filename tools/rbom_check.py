#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Dict, Iterable

def check_schema_version(doc: Dict[str, Any], allowed: Iterable[str] = ("1.0", "1.1")) -> bool:
    ver = str(doc.get("schemaVersion", "")).strip()
    return ver in set(allowed)

def check_artifact_count(doc: Dict[str, Any], *, min_count: int = 1, max_count: int | None = None) -> bool:
    files = doc.get("files") or doc.get("artifacts") or []
    n = len(files)
    if n < min_count:
        return False
    if max_count is not None and n > max_count:
        return False
    return True

def validate_rbom(doc: Dict[str, Any]) -> bool:
    return check_schema_version(doc) and check_artifact_count(doc)

__all__ = ["validate_rbom", "check_schema_version", "check_artifact_count"]
