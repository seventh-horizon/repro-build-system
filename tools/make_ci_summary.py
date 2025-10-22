#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, datetime
FILES=["evidence_index.json","pins_report.json","permissions_report.json","tar_check.json","gzip_check.json","reports/repro.md.json"]
def load(p): 
    pp=pathlib.Path(p)
    if not pp.exists(): return None
    try: return json.loads(pp.read_text(encoding="utf-8"))
    except Exception: return None
def mark(obj):
    if obj is None: return "∅"
    if isinstance(obj, dict) and "ok" in obj: return "✅" if obj.get("ok") else "❌"
    if isinstance(obj, dict) and obj.get("overall") in ("PASS","FAIL","ERROR"): return "✅" if obj["overall"]=="PASS" else "❌"
    return "ℹ️"
def main():
    now=datetime.datetime.utcnow().isoformat()+"Z"
    rows=[(f, mark(load(f))) for f in FILES]
    md=["# CI Summary","", f"_Generated: {now}_",""]
    for f,m in rows: md.append(f"- {m} `{f}`")
    pathlib.Path("CI_SUMMARY.md").write_text("\n".join(md)+"\n", encoding="utf-8")
    print("Wrote CI_SUMMARY.md")
if __name__=="__main__": main()
