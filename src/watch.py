"""Watch mode: poll the sources, rebuild on change and at midnight."""

import datetime
import os
import sys
import time

import report
from config import ASSETS, BUILDER, CONTENT, EXTRA, THEME

CODE = (str(BUILDER), str(THEME / "types"))


def restarts(moved, code=CODE):
    """Did the code itself change - the generator, or a theme type? The
    process still runs the old code: it must restart to load the new.
    `code`: the path prefixes that are code (a test passes its own)."""
    return any(k.startswith(code) for k in moved)


def snapshot():
    """mtime and size of every source file, the builder included."""
    state = {}
    for base in (CONTENT, THEME, ASSETS, BUILDER, *EXTRA):
        for f in [base] if base.is_file() else base.rglob("*"):
            if f.is_file() and "__pycache__" not in f.parts:
                st = f.stat()
                state[str(f)] = (st.st_mtime_ns, st.st_size)
    return state


def watch(dest, interval, build_into):
    before, day = snapshot(), datetime.date.today()
    while True:
        time.sleep(interval)
        now = snapshot()
        if now == before:
            if datetime.date.today() != day:
                # Midnight: an upcoming event may have become a past one.
                day = datetime.date.today()
                try:
                    build_into(dest)
                except Exception as e:
                    report.report(e)
                    print("build failed, previous output kept", flush=True)
            continue
        moved = {k for k in now.keys() | before.keys() if now.get(k) != before.get(k)}
        before = now
        if restarts(moved):
            # The renderer itself changed: restart to load the new code.
            print("builder/ or theme/types/ changed, restarting", flush=True)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        try:
            build_into(dest)
        except Exception as e:  # keep serving the last good build
            report.report(e)
            print("build failed, previous output kept", flush=True)
