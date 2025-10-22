import json, pathlib
def test_rules(tmp_path, monkeypatch):
    good={'rbom_version':'1.0','generated_at':'2025-01-01T00:00:00Z','files':[{'name':'VEL_MANIFEST.json','sha256':'0'*64}]}
    p=tmp_path/'release_bom.json'; p.write_text(json.dumps(good, sort_keys=True, separators=(",",":")), encoding='utf-8')
    from tools import safe_paths_check
    safe_paths_check.RBOM_CANDIDATES=[p]
    safe_paths_check.main()
    bad={'rbom_version':'1.0','generated_at':'2025-01-01T00:00:00Z','files':[{'name':'../evil','sha256':'0'*64}]}
    p2=tmp_path/'release_bom2.json'; p2.write_text(json.dumps(bad, sort_keys=True, separators=(",",":")), encoding='utf-8')
    safe_paths_check.RBOM_CANDIDATES=[p2]
    try:
        safe_paths_check.main(); assert False
    except SystemExit as e:
        assert int(e.code)==2
