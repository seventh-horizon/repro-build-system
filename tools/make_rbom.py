#!/usr/bin/env python3
"""RBOM helpers with the API shape expected by tests."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

__all__ = ["collect_artifacts", "generate_rbom"]


def _sha256_file(p: Path, bufsize: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            chunk = f.read(bufsize)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def collect_artifacts(
    root: str | Path = ".",
    extensions: Iterable[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Walk `root` and return a list of artifact dicts:
      { "name": <relative path>, "path": <absolute path>, "size": <int>, "sha256": <hex> }
    Tests expect dictionaries (not Path objects).
    """
    base = Path(root).resolve()
    artifacts: List[Dict[str, Any]] = []
    allow_ext = set(e.lower() for e in (extensions or []))

    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(base).as_posix()

        if allow_ext:
            ext = p.suffix.lower()
            if ext not in allow_ext:
                continue

        artifacts.append(
            {
                "name": rel,
                "path": str(p),
                "size": p.stat().st_size,
                "sha256": _sha256_file(p),
            }
        )
    return artifacts


def generate_rbom(
    root: str | Path,
    version: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Build an RBOM document with the shape tests assert on:
    {
      "schema_version": "1.0",
      "release_version": "<version>",
      "generated_at": "<iso8601 z>",
      "count": <int>,
      "artifacts": [ {name,path,size,sha256}, ... ],
      "metadata": {...}   # optional
    }
    """
    artifacts = collect_artifacts(root)
    doc: Dict[str, Any] = {
        "schema_version": "1.0",
        "release_version": version,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "count": len(artifacts),
        "artifacts": artifacts,
    }
    if metadata:
        doc["metadata"] = metadata
    return doc


if __name__ == "__main__":
    # tiny CLI for local checks: python tools/make_rbom.py <root> <version> > rbom.json
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    ver = sys.argv[2] if len(sys.argv) > 2 else "v0.0.0"
    print(json.dumps(generate_rbom(root, ver), indent=2))
