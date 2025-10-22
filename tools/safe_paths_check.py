#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, sys
RBOM_CANDIDATES=[pathlib.Path("release_assets/release_bom.json"), pathlib.Path("release_bom.json")]
def load_first():
    for p in RBOM_CANDIDATES:
        if p.exists():
            return p, json.loads(p.read_text(encoding="utf-8"))
    return None, None
def main():
    p, rbom = load_first(); issues=[]
    if rbom is None:
        out={"ok": True, "reason":"rbom_absent"}
    else:
        files=rbom.get("files", [])
        for e in files:
            name=(e or {}).get("name","")
            if not name: issues.append({"issue":"empty_name"}); continue
            if name.startswith("/") or ".." in name or "/" in name or "\\" in name:
                issues.append({"issue":"path_traversal","name":name})
            if name.startswith(".git") or name.startswith(".github"):
                issues.append({"issue":"control_dir","name":name})
        out={"ok": len(issues)==0, "issues":issues, "rbom": str(p)}
    pathlib.Path("safe_paths_report.json").write_text(json.dumps(out, sort_keys=True, separators=(",",":")), encoding="utf-8")
    if not out["ok"]:
        print("Safe paths check: FAIL", file=sys.stderr); sys.exit(2)
    print("Safe paths check: PASS")
if __name__=="__main__": main()
