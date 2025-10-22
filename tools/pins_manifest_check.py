#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, re, sys
WF=pathlib.Path(".github/workflows")
PINS=pathlib.Path("ACTIONS-PINS.md")
USE_RE=re.compile(r"^\s*uses:\s*([^\s@]+)@([0-9a-f]{40}|[^\s#]+)", re.M)
PIN_RE=re.compile(r"^\s*-\s*([^\s@]+)@([0-9a-f]{40}|[^\s#]+)\s*$")
def list_actions():
    used={}
    for y in sorted(WF.glob("*.yml")):
        txt=y.read_text(encoding='utf-8')
        for m in USE_RE.finditer(txt):
            repo, ref=m.group(1), m.group(2)
            if repo.startswith("./") or repo.startswith(".github/"): continue
            used.setdefault(repo, set()).add(ref)
    return {k: sorted(v) for k,v in used.items()}
def list_pins():
    pins={}
    if not PINS.exists(): return pins
    for line in PINS.read_text(encoding='utf-8').splitlines():
        m=PIN_RE.match(line.strip())
        if m: pins[m.group(1)]=m.group(2)
    return pins
def main():
    used=list_actions(); pins=list_pins()
    missing=[]; mismatched=[]
    for repo, refs in used.items():
        if repo not in pins:
            missing.append({"repo": repo, "used_refs": refs})
        else:
            pin=pins[repo]
            if not any(ref==pin for ref in refs):
                mismatched.append({"repo": repo, "manifest_pin": pin, "used_refs": refs})
    report={"ok": not (missing or mismatched), "missing": missing, "mismatched": mismatched}
    pathlib.Path("pins_manifest_report.json").write_text(json.dumps(report, sort_keys=True, separators=(",",":")), encoding="utf-8")
    if report["ok"]: print("Pins manifest check: PASS")
    else: print("Pins manifest check: FAIL", file=sys.stderr); sys.exit(2)
if __name__=="__main__": main()
