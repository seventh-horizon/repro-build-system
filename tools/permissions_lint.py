#!/usr/bin/env python3
from __future__ import annotations
import os
from pathlib import Path
from typing import Iterable, Tuple

def check_file_permissions(path: os.PathLike[str] | str, *, forbid_world_writable: bool = True,
                           max_exec_dirs: bool = True) -> bool:
    st = os.stat(path)
    mode = st.st_mode & 0o777
    if forbid_world_writable and (mode & 0o002):
        return False
    return True

def validate_permissions(paths: Iterable[str | os.PathLike[str]]) -> Tuple[bool, list[str]]:
    failures: list[str] = []
    for p in paths:
        if not check_file_permissions(p):
            failures.append(str(p))
    return (len(failures) == 0, failures)

__all__ = ["check_file_permissions", "validate_permissions"]
