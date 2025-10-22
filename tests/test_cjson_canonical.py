import json, pathlib
from tools.cjson import write_canonical_json
def test_cjson_is_canonical(tmp_path: pathlib.Path):
    p=tmp_path/'x.json'; obj={"b":2,"a":1,"nested":{"y":2,"x":1}}
    write_canonical_json(obj, p)
    assert p.read_text(encoding='utf-8')==json.dumps(obj, sort_keys=True, separators=(",",":"))
def test_cjson_stable_across_writes(tmp_path: pathlib.Path):
    p=tmp_path/'y.json'; obj={"z":[3,2,1],"a":"t"}
    write_canonical_json(obj, p); first=p.read_text(encoding='utf-8')
    write_canonical_json(obj, p); second=p.read_text(encoding='utf-8')
    assert first==second
