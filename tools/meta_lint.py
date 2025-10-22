#!/usr/bin/env python3
from __future__ import annotations
import os, pathlib, stat, json
ROOT=pathlib.Path("."); BAD=[]
def check_exec_headers():
    for p in ROOT.rglob("*.sh"):
        if p.is_file() and not p.read_text(encoding="utf-8", errors="ignore").startswith("#!"):
            BAD.append({"file":str(p),"issue":"missing_shebang"})
    for p in ROOT.rglob("*.py"):
        if p.is_file() and not p.read_text(encoding="utf-8", errors="ignore").startswith("#!"):
            BAD.append({"file":str(p),"issue":"missing_shebang"})
def check_exec_bits():
    for p in ROOT.rglob("tools/*.py"):
        m=p.stat().st_mode
        if not (m & stat.S_IXUSR):
            BAD.append({"file":str(p),"issue":"not_executable"})
def check_case():
    for p in ROOT.rglob("*"):
        if p.is_file():
            name=p.name
            if " " in name or name!=name.strip():
                BAD.append({"file":str(p),"issue":"bad_filename"})
def main():
    check_exec_headers(); check_exec_bits(); check_case()
    out={"ok": not BAD, "issues": BAD}
    pathlib.Path("meta_trace.json").write_text(json.dumps(out, sort_keys=True, separators=(",",":")), encoding="utf-8")
    print(f"Meta-lint complete ({len(BAD)} issues)")
if __name__=="__main__": main()
