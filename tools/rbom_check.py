#!/usr/bin/env python3
"""Check RBOM against policy constraints."""
from __future__ import annotations
import argparse, json, pathlib, sys

def validate_rbom(rbom: dict, policy: dict) -> list[str]:
    errors = []
    
    # Check schema version
    if rbom.get("schema_version") != policy.get("required_schema_version", "1.0"):
        errors.append("schema_version_mismatch")
    
    # Check minimum artifacts
    min_artifacts = policy.get("min_artifacts", 0)
    if rbom.get("count", 0) < min_artifacts:
        errors.append(f"too_few_artifacts: {rbom.get('count')} < {min_artifacts}")
    
    # Check maximum artifacts
    max_artifacts = policy.get("max_artifacts", 1000)
    if rbom.get("count", 0) > max_artifacts:
        errors.append(f"too_many_artifacts: {rbom.get('count')} > {max_artifacts}")
    
    # Validate each artifact
    artifacts = rbom.get("artifacts", [])
    for i, art in enumerate(artifacts):
        # Check required fields
        for field in ["name", "path", "size", "sha256"]:
            if field not in art:
                errors.append(f"artifact[{i}].missing_field:{field}")
        
        # Validate SHA256 format
        if "sha256" in art and len(art["sha256"]) != 64:
            errors.append(f"artifact[{i}].invalid_sha256_length")
        
        # Check for forbidden patterns in names
        forbidden = policy.get("forbidden_name_patterns", [])
        name = art.get("name", "")
        for pattern in forbidden:
            if pattern in name:
                errors.append(f"artifact[{i}].forbidden_pattern:{pattern}")
    
    return errors

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True, help="Policy JSON file")
    ap.add_argument("--rbom", required=True, help="RBOM JSON file to check")
    ap.add_argument("--out", required=True, help="Output report file")
    args = ap.parse_args()
    
    policy = json.loads(pathlib.Path(args.policy).read_text(encoding="utf-8"))
    rbom = json.loads(pathlib.Path(args.rbom).read_text(encoding="utf-8"))
    
    errors = validate_rbom(rbom, policy)
    
    report = {
        "ok": len(errors) == 0,
        "errors": errors,
        "rbom_artifact_count": rbom.get("count", 0)
    }
    
    pathlib.Path(args.out).write_text(
        json.dumps(report, sort_keys=True, separators=(",",":")),
        encoding="utf-8"
    )
    
    if errors:
        print(f"RBOM policy check: FAIL ({len(errors)} errors)", file=sys.stderr)
        sys.exit(2)
    print("RBOM policy check: PASS")

if __name__ == "__main__":
    main()
