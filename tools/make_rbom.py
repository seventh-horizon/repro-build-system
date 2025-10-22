#!/usr/bin/env python3
"""Build Release Bill of Materials (RBOM) from release artifacts."""
from __future__ import annotations
import argparse, glob, hashlib, json, pathlib, sys

def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(4<<20):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, help="Glob pattern for input files")
    ap.add_argument("--out", required=True, help="Output RBOM JSON file")
    args = ap.parse_args()
    
    files = []
    for pattern in args.inputs.split():
        files.extend(glob.glob(pattern, recursive=True))
    
    artifacts = []
    for fp in sorted(set(files)):
        p = pathlib.Path(fp)
        if not p.is_file():
            continue
        artifacts.append({
            "name": p.name,
            "path": str(p),
            "size": p.stat().st_size,
            "sha256": sha256_file(p)
        })
    
    rbom = {
        "schema_version": "1.0",
        "artifacts": artifacts,
        "count": len(artifacts)
    }
    
    pathlib.Path(args.out).write_text(
        json.dumps(rbom, sort_keys=True, indent=2),
        encoding="utf-8"
    )
    print(f"RBOM created: {args.out} ({len(artifacts)} artifacts)")

if __name__ == "__main__":
    main()
