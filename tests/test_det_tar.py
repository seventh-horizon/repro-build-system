import tarfile, pathlib
from tools.det_tar import build_tar
def _mkfile(p: pathlib.Path, txt: str): p.write_text(txt, encoding='utf-8')
def test_det_tar_root_and_mtime(tmp_path: pathlib.Path):
    a=tmp_path/'a.txt'; _mkfile(a,'A')
    b=tmp_path/'b.txt'; _mkfile(b,'B')
    out=tmp_path/'t.tar'; build_tar(str(out), [str(b), str(a)])
    with tarfile.open(out, 'r:') as t:
        names=[m.name for m in t.getmembers()]
        assert names==sorted(['a.txt','b.txt'])
        for m in t.getmembers():
            assert m.uid==0 and m.gid==0
            assert (m.uname or 'root')=='root'
            assert (m.gname or 'root')=='root'
            assert int(m.mtime)==0
