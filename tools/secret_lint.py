#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, re
ROOT=pathlib.Path(".")
SKIP={".git","out","release_assets","wheelhouse","field",".github"}
TEXT={".py",".sh",".md",".yml",".yaml",".json",".toml",".cfg",".ini",".txt",".lock",".Makefile","Makefile"}
PATS=[re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|PGP) PRIVATE KEY-----"), re.compile(r"AKIA[0-9A-Z]{16}"), re.compile(r"(?i)secret[_-]?key\s*[:=]\s*[A-Za-z0-9/+]{16,}"), re.compile(r"(?i)api[_-]?key\s*[:=]\s*[A-Za-z0-9_\-]{16,}"), re.compile(r"(?i)token\s*[:=]\s*[A-Za-z0-9_\-]{16,}")]
def is_text(p: pathlib.Path)->bool:
    if p.name in TEXT or p.suffix in TEXT: return True
    try: raw=p.read_bytes()[:2048]; return b"\x00" not in raw
    except Exception: return False
def scan():
    finds=[]
    for p in ROOT.rglob("*"):
        if not p.is_file(): continue
        if any(part in SKIP for part in p.parts): continue
        if not is_text(p): continue
        try: txt=p.read_text(encoding="utf-8", errors="ignore")
        except Exception: continue
        for i,line in enumerate(txt.splitlines(), start=1):
            if any(pat.search(line) for pat in PATS):
                finds.append({"file": str(p), "line": i}); break
    return finds
def main():
    out={"findings": scan()}
    pathlib.Path("secret_scan.json").write_text(json.dumps(out, sort_keys=True, separators=(",",":")), encoding="utf-8")
    print(f"Secret lint complete. Findings: {len(out['findings'])}")
if __name__=="__main__": main()
