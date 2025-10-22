#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, subprocess
def _git(args):
    try: return subprocess.check_output(["git"]+args, text=True).strip()
    except Exception: return None
def main():
    repo=os.environ.get("GITHUB_REPOSITORY","org/repo")
    sha=_git(["rev-parse","HEAD"]) or "0"*40
    tag=_git(["describe","--tags","--always","--dirty=-dirty"]) or "0.0.0"
    dirty=bool(tag.endswith("-dirty")) or bool(_git(["status","--porcelain"]))
    out={"repository":repo,"git_sha":sha,"git_tag": (tag.replace("-dirty","") if tag else "0.0.0"), "dirty": dirty, "run_id": os.environ.get("GITHUB_RUN_ID","unknown")}
    pathlib.Path("version.json").write_text(json.dumps(out, sort_keys=True, separators=(",",":")), encoding="utf-8")
    print("Wrote version.json")
if __name__=="__main__": main()
