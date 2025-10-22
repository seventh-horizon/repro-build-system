# tools/det_tar.py
import tarfile, pathlib, os
from typing import Iterable, List
def _add_file(t: tarfile.TarFile, src: pathlib.Path, arcname: str) -> None:
    info = t.gettarinfo(str(src), arcname)
    info.uid = info.gid = 0; info.uname = info.gname = "root"; info.mtime = 0
    with src.open("rb") as fh: t.addfile(info, fh)
def build_tar(out_base: str, files: Iterable[str]) -> None:
    out = pathlib.Path(out_base); out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out, mode="w") as t:
        for fp in sorted(files):
            p = pathlib.Path(fp)
            if not p.exists():
                if os.getenv("HORIZON_DEBUG","0")=="1":
                    print(f"HDEBUG skip_missing path={p}")
                continue
            _add_file(t, p, p.name)
