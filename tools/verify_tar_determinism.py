#!/usr/bin/env python3
"""Checks a .tar.gz for deterministic tar metadata (owner/group, mtime, sort order)."""
from __future__ import annotations
import argparse, json, pathlib, sys, tarfile

def check_tar(tar_path: str) -> dict:
    p = pathlib.Path(tar_path)
    if not p.exists():
        return {"ok": False, "reason": "missing_tar", "path": str(p)}
    try:
        with tarfile.open(str(p), mode="r:gz") as tgz:
            members = tgz.getmembers()
    except Exception as e:
        return {"ok": False, "reason": f"read_error:{e}"}
    names = [m.name for m in members if m.isfile()]
    sorted_names = sorted(names)
    order_ok = (names == sorted_names)
    meta_ok = True
    bad_meta = []
    for m in members:
        if (m.uid, m.gid, m.uname, m.gname, m.mtime) != (0, 0, "root", "root", 0):
            meta_ok = False
            bad_meta.append({"name": m.name, "uid": m.uid, "gid": m.gid, "uname": m.uname, "gname": m.gname, "mtime": m.mtime})
    ok = order_ok and meta_ok
    return {"ok": ok, "order_ok": order_ok, "meta_ok": meta_ok, "bad_meta": bad_meta, "count": len(members), "path": str(p)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tar", required=True, help="Path to .tar.gz")
    ap.add_argument("--out", default="tar_check.json")
    args = ap.parse_args()
    rep = check_tar(args.tar)
    pathlib.Path(args.out).write_text(json.dumps(rep, sort_keys=True, separators=(",",":")), encoding="utf-8")
    if not rep.get("ok", False):
        print("Tar determinism: FAIL", file=sys.stderr)
        sys.exit(2)
    print("Tar determinism: PASS")

if __name__ == "__main__":
    main()
