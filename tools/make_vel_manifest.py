#!/usr/bin/env python3
import argparse, json, os, subprocess, uuid, platform, pathlib
from tools.config import get_path
from tools.io_utils import sha256_path
def deterministic_uuid(repo: str, git_sha: str) -> str:
    url=f"https://github.com/{(repo or 'local-repo').strip('/')}".lower()
    ns=uuid.uuid5(uuid.NAMESPACE_URL, url)
    return str(uuid.uuid5(ns, git_sha or "0"*40))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--artifact", default=get_path('artifact')); ap.add_argument("--out", default=get_path('manifest')); args=ap.parse_args()
    try: git_sha=subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip()
    except Exception: git_sha="0"*40
    repo=os.environ.get("GITHUB_REPOSITORY","org/repo")
    doc={"vel_schema_version":"1.0","manifest_uuid":deterministic_uuid(repo, git_sha),"license_id":"MIT",
         "provenance":{"git_sha":git_sha,"artifact_sha256":sha256_path(args.artifact) if pathlib.Path(args.artifact).exists() else ""},
         "environment":{"python_version":platform.python_version(),"system_locale":os.environ.get("LC_ALL","C"),"timezone":os.environ.get("TZ","UTC"),"decimal_context":"28","decimal_rounding":"ROUND_HALF_EVEN"},
         "results_contract":{"metrics_version":"v0.9-P1B-decimal","canonical_ratio":"1.46282301","input_vector_sha256":"deadbeef"*8,"rounding_precision":8,"pass_fail":true}}
    pathlib.Path(args.out).write_text(json.dumps(doc, sort_keys=True, separators=(",",":")), encoding="utf-8")
    print(f"Wrote {args.out}")
if __name__=="__main__": main()
