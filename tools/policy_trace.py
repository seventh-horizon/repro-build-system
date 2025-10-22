#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, hashlib, datetime
SCHEMA = pathlib.Path("schema")
def sha256sum(p: pathlib.Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    entries=[]
    for path in sorted(SCHEMA.glob("*.json")):
        meta={"file": str(path), "sha256": sha256sum(path), "size": path.stat().st_size, "mtime": datetime.datetime.utcfromtimestamp(path.stat().st_mtime).isoformat()+"Z"}
        try:
            data=json.loads(path.read_text(encoding="utf-8")); meta["policy_version"]=data.get("version","unknown"); meta["required_fields"]=data.get("required_fields",[])
        except Exception as e:
            meta["error"]=str(e)
        entries.append(meta)
    out={"generated": datetime.datetime.utcnow().isoformat()+"Z","policies": entries}
    pathlib.Path("schema/policy_index.json").write_text(json.dumps(out, sort_keys=True, separators=(",",":")), encoding="utf-8")
    print(f"Wrote schema/policy_index.json ({len(entries)} policies)")
if __name__=="__main__": main()
