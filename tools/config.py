import yaml, pathlib
from typing import Any, Dict
ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG: Dict[str, Any] = yaml.safe_load((ROOT/'config.yml').read_text(encoding='utf-8'))
def get_path(key: str) -> str:
    return str(ROOT / CONFIG["paths"][key])
