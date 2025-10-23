#!/usr/bin/env python3
"""Checks a .tar.gz for deterministic tar metadata (owner/group, mtime, sort order)."""
from __future__ import annotations
import argparse, json, pathlib, sys, tarfile
from typing import Iterable

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
            bad_meta.append({
                "name": m.name,
                "uid": m.uid,
                "gid": m.gid,
                "uname": m.uname,
                "gname": m.gname,
                "mtime": m.mtime
            })
    ok = order_ok and meta_ok
    return {
        "ok": ok,
        "order_ok": order_ok,
        "meta_ok": meta_ok,
        "bad_meta": bad_meta,
        "count": len(members),
        "path": str(p)
    }

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

# --- Determinism helpers expected by tests ---

def verify_file_order(members: Iterable[tarfile.TarInfo]) -> bool:
    """True if member names are sorted and unique."""
    names = [m.name for m in members]
    return names == sorted(names) and len(names) == len(set(names))

def verify_metadata(member: tarfile.TarInfo) -> bool:
    """Ensure deterministic metadata for each member."""
    uid_ok = getattr(member, "uid", 0) == 0
    gid_ok = getattr(member, "gid", 0) == 0
    uname_ok = getattr(member, "uname", "") == "root"
    gname_ok = getattr(member, "gname", "") == "root"
    mtime_ok = getattr(member, "mtime", 0) == 0
    mode = getattr(member, "mode", 0)
    perms_ok = (mode & 0o002) == 0  # Not world-writable
    return uid_ok and gid_ok and uname_ok and gname_ok and mtime_ok and perms_ok

def check_tar_determinism(tar_path: str) -> dict:
    """
    Check if tar is deterministic and return dict with detailed results.
    Expected by tests to return a dict with 'is_deterministic' key.
    """
    p = pathlib.Path(tar_path)
    if not p.exists():
        return {"is_deterministic": False, "issues": ["Tar file does not exist"]}
    
    try:
        with tarfile.open(str(p), "r:*") as tf:
            members = [m for m in tf.getmembers() if m.name != "./"]
    except Exception as e:
        return {"is_deterministic": False, "issues": [f"Failed to read tar: {e}"]}
    
    issues = []
    
    # Check file order
    if not verify_file_order(members):
        issues.append("Files are not in sorted order")
    
    # Check metadata for each member
    for m in members:
        if not verify_metadata(m):
            if m.uid != 0:
                issues.append(f"{m.name}: uid is {m.uid}, not 0")
            if m.gid != 0:
                issues.append(f"{m.name}: gid is {m.gid}, not 0")
            uname = getattr(m, "uname", "") or "root"
            gname = getattr(m, "gname", "") or "root"
            if uname != "root":
                issues.append(f"{m.name}: uname is '{uname}', not 'root'")
            if gname != "root":
                issues.append(f"{m.name}: gname is '{gname}', not 'root'")
            if m.mtime != 0:
                issues.append(f"{m.name}: mtime is {m.mtime}, not 0")
            mode = getattr(m, "mode", 0)
            if (mode & 0o002) != 0:
                issues.append(f"{m.name}: mode has world-writable bit set")
    
    return {
        "is_deterministic": len(issues) == 0,
        "issues": issues
    }

if __name__ == "__main__":
    main()
