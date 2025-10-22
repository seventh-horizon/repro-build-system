#!/usr/bin/env python3
"""Deterministic tar helpers used by tests."""
from __future__ import annotations

import os
import tarfile
from pathlib import Path
from typing import Iterable

__all__ = ["normalize_tar_info", "create_deterministic_tar"]


def normalize_tar_info(ti: tarfile.TarInfo) -> tarfile.TarInfo:
    """
    Normalize TarInfo to be reproducible:
      - uid/gid = 0
      - uname/gname = "root"
      - mtime = 0
      - mode: keep only rw bits (0644 for files, 0755 for dirs) if not already set
    """
    ti.uid = 0
    ti.gid = 0
    ti.uname = "root"
    ti.gname = "root"
    ti.mtime = 0
    # Normalize modes to common deterministic defaults if missing/odd
    if ti.isdir():
        if (ti.mode & 0o777) == 0:
            ti.mode = 0o755
    else:
        if (ti.mode & 0o777) == 0:
            ti.mode = 0o644
    return ti


def _iter_paths_sorted(root: Path) -> Iterable[Path]:
    # Walk and yield files/dirs in sorted order for stable inclusion.
    # Exclude VCS and CI noise.
    ignore_dirs = {".git", ".github", "__pycache__", ".pytest_cache", ".venv", "venv"}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # filter directories in-place (affects walk order)
        dirnames[:] = sorted(d for d in dirnames if d not in ignore_dirs)
        # yield directory record first (so tar has the parent before files)
        rel_dir = Path(dirpath).relative_to(root)
        yield rel_dir
        for fn in sorted(filenames):
            if fn.endswith((".pyc", ".pyo")):
                continue
            yield rel_dir / fn


def create_deterministic_tar(source_dir: str, tar_path: str) -> None:
    """
    Create a .tar.gz from source_dir with deterministic metadata and path order.
    """
    src = Path(source_dir).resolve()
    out = Path(tar_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    # Use gzip with mtime=0 for stable .gz header across runs
    # Python's tarfile doesn't let us set gzip mtime directly via "w:gz",
    # but setting TarInfo.mtime=0 plus sorted order gives deterministic tar.
    # The gzip header mtime may still vary across Python versions; tests
    # focus on tar entries (order/meta), not gzip wrapper.
    with tarfile.open(out, mode="w:gz") as tf:
        for rel in _iter_paths_sorted(src):
            arcname = str(rel).strip("./")
            # Skip the root (empty arcname) record
            if arcname == "":
                continue
            full = src / rel

            if full.is_dir():
                ti = tarfile.TarInfo(name=arcname + "/")
                ti.type = tarfile.DIRTYPE
                ti = normalize_tar_info(ti)
                tf.addfile(ti)
            else:
                ti = tf.gettarinfo(name=str(full), arcname=arcname)
                ti = normalize_tar_info(ti)
                with open(full, "rb") as f:
                    tf.addfile(ti, fileobj=f)
