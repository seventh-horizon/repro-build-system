#!/usr/bin/env python3
import argparse, json, hashlib, os, platform, re, locale
from pathlib import Path
def g(d,*p,default="MISSING"):
    cur=d
    for k in p:
        if not isinstance(cur,dict) or k not in cur: return default
        cur=cur[k]
    return str(cur)
def sha256sum(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b""): h.update(chunk)
    return h.hexdigest()
def verify_artifact(m: dict, art: Path):
    exp=g(m,"provenance","artifact_sha256")
    if not art.exists(): return "ERROR","missing"
    got=sha256sum(art); 
    return ("PASS" if got.lower()==exp.lower() else "FAIL", got)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--manifest", required=True); ap.add_argument("--artifact", required=True); ap.add_argument("--stdout", action="store_true"); ap.add_argument("--json", action="store_true"); ap.add_argument("-o","--out", default="reports/repro.md"); args=ap.parse_args()
    m=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    status, got = verify_artifact(m, Path(args.artifact))
    overall = "PASS" if status=="PASS" else "FAIL"
    rep=f"# Repro Audit\n\nOverall: **{overall}**\n"
    if args.stdout: print(rep)
    else:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(rep, encoding="utf-8")
    if args.json:
        Path(args.out).with_suffix(".json").write_text(json.dumps({"overall":overall, "artifact_sha_actual":got}, sort_keys=True, separators=(",",":")), encoding="utf-8")
    print("Audit", overall)
if __name__=="__main__": main()
