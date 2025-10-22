from __future__ import annotations
import hashlib, os
from pathlib import Path
from typing import Union
BufSize = 4 << 20
def sha256_path(path: Union[str, Path]) -> str:
    p=Path(path); h=hashlib.sha256(); buf=bytearray(BufSize); mv=memoryview(buf)
    with p.open('rb', buffering=0) as f:
        while True:
            n=f.readinto(mv)
            if not n: break
            h.update(mv[:n])
    return h.hexdigest()
