#!/usr/bin/env python3
import argparse, json, glob, pathlib, sys
def is_canonical(text:str)->bool:
    try:
        obj=json.loads(text)
        return text.strip()==json.dumps(obj, sort_keys=True, separators=(",",":"))
    except Exception:
        return True
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out", default="json_check_report.json"); ap.add_argument("globs", nargs="*"); args=ap.parse_args()
    files=set()
    for g in args.globs: files.update(glob.glob(g, recursive=True))
    issues=[]
    for f in sorted(files):
        p=pathlib.Path(f); 
        if not p.exists() or not p.is_file(): continue
        txt=p.read_text(encoding="utf-8", errors="ignore")
        if not is_canonical(txt):
            issues.append({"file": f, "issue":"non_canonical"})
    out={"ok": len(issues)==0, "issues": issues}
    pathlib.Path(args.out).write_text(json.dumps(out, sort_keys=True, separators=(",",":")), encoding="utf-8")
    print("JSON canonical check:", "PASS" if out["ok"] else "FAIL")
    sys.exit(0)
if __name__=="__main__": main()
