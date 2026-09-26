"""The test suite: `python3 -m unittest discover -s tests -t . -v` from
the repository root. With `-t .` the modules import as tests.<name>, so
this file always runs first. Every test builds the fixture site in
tests/site/, with a fixed date, and looks at the files the build returns."""

import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
os.environ["SITE_ROOT"] = str(HERE / "site")
os.environ["BUILD_TODAY"] = "2026-06-15"
# src/ first, so `import build` is src/build.py, not the entry point at the root.
sys.path.insert(0, str(HERE.parent / "src"))
