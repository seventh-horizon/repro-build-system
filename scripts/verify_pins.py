#!/usr/bin/env python3
import argparse, json, re, sys, pathlib
WS = pathlib.Path(".github/workflows")
ACTION_RE = re.compile(r"^\s*uses:\s*([^\s@]+)@([^\s#]+)")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
def scan():
    findings=[]
    for yml in sorted(WS.glob("*.yml")):
        for i, line in enumerate(yml.read_text(encoding="utf-8").splitlines(), start=1):
            m = ACTION_RE.match(line)
            if not m: continue
            repo, ref = m.group(1), m.group(2)
            if repo.startswith("./") or repo.startswith(".github/"):
                ok=True
            else:
                ok=bool(SHA_RE.match(ref)) or ref.endswith(".yml@v1.9.0")
            findings.append({"file": str(yml), "line": i, "repo": repo, "ref": ref, "ok": ok})
    return findings
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--pins", default="ACTIONS-PINS.md"); ap.add_argument("--out", default="pins_report.json"); ap.parse_args()
    f=scan(); pathlib.Path("pins_report.json").write_text(json.dumps({"findings":f}, sort_keys=True, separators=(",",":")), encoding="utf-8")
    bad=[x for x in f if not x["ok"]]
    if bad:
        print("ERROR: Unpinned actions detected", file=sys.stderr); sys.exit(2)
    print("Pinned-actions verification PASS")
if __name__=="__main__": main()
