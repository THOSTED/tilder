#!/usr/bin/env python3
"""Build a man-page site. The code is in src/; its map is at the top of
src/build.py. `python3 builder/build.py --help` for the options."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from build import main  # noqa: E402  (src/build.py, found through the path above)

if __name__ == "__main__":
    sys.exit(main())
