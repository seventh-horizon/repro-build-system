# tests/conftest.py
import sys
import pathlib

# ensure the repo root (parent of tests/) is on sys.path so `import tools` works
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
