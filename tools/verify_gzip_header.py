#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, pathlib, struct, sys
def parse_hdr(path):
    with open(path,"rb") as f: data=f.read(16)
    if len(data)<10: return {"ok":False,"issue":"short_header"}
    id1,id2,cm,flg,mtime,xfl,os_=struct.unpack("<BBBBIBB", data[:10])
    if id1!=0x1F or id2!=0x8B or cm!=8: return {"ok":False,"issue":"not_gzip"}
    return {"ok":True,"mtime":mtime,"os":os_,"xfl":xfl,"flg":flg}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--gz", required=True); ap.add_argument("--out", default="gzip_check.json"); args=ap.parse_args()
    hdr=parse_hdr(args.gz); issues=[]
    if not hdr.get("ok"): issues.append({"issue": hdr.get("issue","unknown")})
    else:
        if hdr["mtime"]!=0: issues.append({"issue":"mtime_nonzero","value":hdr["mtime"]})
        if hdr["os"] not in (3,255): issues.append({"issue":"os_code_unexpected","value":hdr["os"]})
    out={"ok": len(issues)==0, "issues": issues, "header": {k:v for k,v in hdr.items() if k!="ok"}}
    pathlib.Path(args.out).write_text(json.dumps(out, sort_keys=True, separators=(",",":")), encoding="utf-8")
    if issues: print("Gzip header determinism: FAIL", file=sys.stderr); sys.exit(2)
    print("Gzip header determinism: PASS")
if __name__=="__main__": main()
