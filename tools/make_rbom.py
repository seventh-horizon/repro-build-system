#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
from typing import Iterable, Dict, Any, List

CHUNK = 1024 * 1024

def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def collect_artifacts(root: str | os.PathLike[str] = ".", extensions: Iterable[str] | None = None) -> List[Path]:
    """
    Walk `root` and return a list of artifact Paths. If `extensions` is provided,
    only include files whose suffix (without dot) is in that iterable.
    """
    root_p = Path(root)
    allow = None if extensions is None else {e.lower().lstrip(".") for e in extensions}
    out: List[Path] = []
    for dirpath, _, filenames in os.walk(root_p):
        for name in filenames:
            p = Path(dirpath) / name
            if allow is not None:
                suf = p.suffix.lower().lstrip(".")
                if suf not in allow:
                    continue
            if p.is_file():
                out.append(p.relative_to(root_p))
    out.sort()
    return out

def generate_rbom(files: Iterable[Path]) -> Dict[str, Any]:
    """
    Produce: { "files": [ { "name": "...", "sha256": "..." }, ... ] }
    """
    items: List[Dict[str, str]] = []
    for rel in files:
        rel_p = Path(rel)
        items.append({"name": str(rel_p).replace("\\", "/"), "sha256": _sha256_of(Path(".") / rel_p)})
    return {"files": items}

def main(argv: List[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Generate a simple RBOM for a set of files.")
    ap.add_argument("--root", default=".", help="Root directory to scan")
    ap.add_argument("--ext", action="append", default=None, help="File extensions to include (repeatable)")
    ap.add_argument("--out", default="release_bom.json", help="Output JSON file")
    args = ap.parse_args(argv)

    files = collect_artifacts(args.root, args.ext)
    rbom = generate_rbom(files)
    Path(args.out).write_text(json.dumps(rbom, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {args.out} with {len(rbom.get('files', []))} entries")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())