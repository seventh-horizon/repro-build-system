#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, re, sys
WORKFLOWS=pathlib.Path(".github/workflows")
def scan_yml(path: pathlib.Path):
    txt=path.read_text(encoding="utf-8"); issues=[]
    if "permissions: {}" not in txt:
        issues.append({"file": str(path), "issue":"toplevel_default_deny_missing"})
    jobs=re.findall(r"(?m)^\s{2,}[a-zA-Z0-9_-]+:\n\s{4,}runs-on:", txt)
    if jobs:
        has=re.findall(r"(?m)^\s{4,}permissions\s*:\s*(\{|$)", txt)
        if len(has) < len(jobs):
            issues.append({"file": str(path), "issue":"job_permissions_missing"})
    return issues
def main():
    all_issues=[]
    for y in sorted(WORKFLOWS.glob("*.yml")): all_issues.extend(scan_yml(y))
    report={"ok": len(all_issues)==0, "issues": all_issues}
    pathlib.Path("permissions_report.json").write_text(json.dumps(report, sort_keys=True, separators=(",",":")), encoding="utf-8")
    if all_issues:
        for i in all_issues: print(f"- {i}", file=sys.stderr)
        sys.exit(2)
    print("Permissions lint: PASS")
if __name__=="__main__": main()
