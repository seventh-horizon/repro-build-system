#!/usr/bin/env python3
"""RBOM policy/shape checks used by tests."""
from __future__ import annotations
from typing import Iterable, Tuple, List, Dict, Any
import argparse, json, pathlib, sys, re
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")

def check_schema_version(version: str, allowed: Iterable[str] = ("1.0", "1.1")) -> bool:
    """Return True if schema version string is allowed."""
    return str(version) in set(map(str, allowed))

def _required_artifact_fields_ok(art: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    for f in ("name", "path", "size", "sha256"):
        if f not in art:
            errs.append(f"missing_field:{f}")
    if "sha256" in art and not HEX64.match(str(art.get("sha256", ""))):
        errs.append("invalid_sha256")
    return errs

def validate_rbom(doc: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Return (ok, errors). Tests expect a tuple, not just a bool.
    Rules (kept simple to match tests):
      - doc["schema_version"] must be allowed
      - doc["count"] must equal len(doc["artifacts"])
      - each artifact has name/path/size/sha256 and sha256 is 64 hex chars
    """
    errors: List[str] = []

    # schema version
    ver = doc.get("schema_version")
    if ver is None or not check_schema_version(str(ver)):
        errors.append("schema_version_mismatch")

    # artifacts/count
    artifacts = doc.get("artifacts", [])
    if not isinstance(artifacts, list):
        errors.append("artifacts_not_list")
    count = int(doc.get("count", -1))
    if count != len(artifacts):
        errors.append(f"count_mismatch:{count}!={len(artifacts)}")

    # per-artifact checks
    for i, art in enumerate(artifacts):
        if not isinstance(art, dict):
            errors.append(f"artifact[{i}].not_object")
            continue
        for e in _required_artifact_fields_ok(art):
            errors.append(f"artifact[{i}].{e}")

    return (len(errors) == 0, errors)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rbom", required=True, help="RBOM JSON file")
    ap.add_argument("--out", required=False, help="Write validation report JSON")
    args = ap.parse_args()

    rbom = json.loads(pathlib.Path(args.rbom).read_text(encoding="utf-8"))
    ok, errs = validate_rbom(rbom)
    rep = {"ok": ok, "errors": errs}
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("RBOM check:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 2)

if __name__ == "__main__":
    main()
