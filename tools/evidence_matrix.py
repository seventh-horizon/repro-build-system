#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, datetime
ROOT=pathlib.Path(".")
FILES={"env_snapshot":"env_snapshot.json","pins_report":"pins_report.json","permissions_report":"permissions_report.json","json_check":"json_check_report.json","tar_check":"tar_check.json","gzip_check":"gzip_check.json","meta_trace":"meta_trace.json","policy_index":"schema/policy_index.json","repro_json":"reports/repro.md.json"}
POLICY={"env_snapshot":"Deterministic env","pins_report":"SHA-pinned actions","permissions_report":"Least-privilege","json_check":"Canonical JSON","tar_check":"Deterministic tar","gzip_check":"Gzip header","meta_trace":"Repo hygiene","policy_index":"Policy index","repro_json":"Repro audit"}
def load_json(p): 
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return None
def status(obj):
    if obj is None: return "absent"
    if isinstance(obj, dict) and "ok" in obj: return "pass" if obj.get("ok") else "fail"
    if isinstance(obj, dict) and obj.get("overall") in ("PASS","FAIL","ERROR"): return "pass" if obj["overall"]=="PASS" else "fail"
    return "info"
def main():
    now=datetime.datetime.utcnow().isoformat()+"Z"; rows={}
    for k,rel in FILES.items():
        p=ROOT/rel; o=load_json(p) if p.exists() else None; st=status(o)
        rows[k]={"file":rel,"exists":p.exists(),"status":st}
    out={"generated":now,"entries":rows,"policy_map":POLICY}
    pathlib.Path("evidence_index.json").write_text(json.dumps(out, sort_keys=True, separators=(",",":")), encoding="utf-8")
    md=["# Evidence Matrix","","_Generated: "+now+"_", ""]
    for k in sorted(rows.keys()):
        r=rows[k]; mark={"pass":"✅","fail":"❌","warn":"⚠️","info":"ℹ️","absent":"∅"}.get(r["status"],"ℹ️")
        md.append(f"- {mark} **{k}** → `{r['file']}` — {POLICY.get(k,'')}")
    pathlib.Path("EVIDENCE_MATRIX.md").write_text("\n".join(md)+"\n", encoding="utf-8")
    print("Wrote evidence_index.json and EVIDENCE_MATRIX.md")
if __name__=="__main__": main()
