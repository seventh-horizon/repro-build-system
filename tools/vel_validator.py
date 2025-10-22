#!/usr/bin/env python3
import argparse, json, subprocess, sys, pathlib
from typing import Tuple, Any, Dict
from tools.io_utils import sha256_path
def read_json(path: str) -> Dict[str, Any]:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
def validate_schema_builtin(doc: dict) -> bool:
    req=["provenance","environment","results_contract"]
    ok=all(k in doc for k in req)
    if not ok: print("WARN: manifest missing core sections; consider JSON Schema.", file=sys.stderr)
    return ok
def validate_schema_jsonschema(doc: dict, schema_path: str) -> bool:
    try:
        import jsonschema, json as _j
        schema=_j.loads(pathlib.Path(schema_path).read_text(encoding="utf-8"))
        jsonschema.validate(instance=doc, schema=schema); return True
    except FileNotFoundError:
        print("WARN: schema not found; skipping jsonschema.", file=sys.stderr); return True
    except Exception as e:
        print(f"ERROR: jsonschema validation failed: {e}", file=sys.stderr); return False
def check_git_sha_exists_locally(expected_sha: str) -> Tuple[bool,str]:
    try:
        subprocess.check_call(["git","cat-file","-e",f"{expected_sha}^{{commit}}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return True,"present"
    except subprocess.CalledProcessError: return False,"not_found"
    except FileNotFoundError: return False,"git_missing"
def check_artifact_sha(expected_sha: str, artifact_path: str) -> bool:
    try: return sha256_path(artifact_path).lower()==expected_sha.lower()
    except Exception as e: print(f"ERROR: failed to hash artifact: {e}", file=sys.stderr); return False
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--artifact", required=True); ap.add_argument("--schema", required=True); ap.add_argument("manifest"); ap.add_argument("--strict-git", action="store_true"); args=ap.parse_args()
    doc=read_json(args.manifest); ok=True
    if not (validate_schema_builtin(doc) and validate_schema_jsonschema(doc, args.schema)): ok=False
    exp=doc.get("provenance",{}).get("artifact_sha256","")
    if not exp or not check_artifact_sha(exp, args.artifact):
        print("ERROR: artifact sha256 mismatch.", file=sys.stderr); ok=False
    git_sha=doc.get("provenance",{}).get("git_sha","")
    if git_sha:
        present, reason = check_git_sha_exists_locally(git_sha)
        if not present:
            msg=f"WARN: local git cannot confirm commit: {git_sha} ({reason})."
            if args.strict-git: print("ERROR: "+msg, file=sys.stderr); ok=False
            else: print(msg, file=sys.stderr)
    print("Manifest validation PASS" if ok else "Manifest validation FAIL")
    sys.exit(0 if ok else 2)
if __name__=="__main__": main()
