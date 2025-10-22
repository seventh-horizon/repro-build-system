from __future__ import annotations
import json
from pathlib import Path
from typing import Any
def write_canonical_json(obj: Any, path: str | Path) -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, sort_keys=True, separators=(",",":")), encoding="utf-8")
