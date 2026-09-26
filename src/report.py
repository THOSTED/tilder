"""Errors and warnings, one shape.

    error: <file>[:<line>]: <what is wrong>. <what to do>

A problem the build cannot work around is a BuildError; it may hold several
messages, so one run shows every problem of a phase, not the first. The
Python traceback is shown only with --debug: the message is meant to be
enough.
"""

import sys
import traceback

from config import BUILDER, ROOT

DEBUG = False  # --debug: tracebacks after the messages


class BuildError(Exception):
    """One or more problems: items is [(message, cause or None)]."""

    def __init__(self, items):
        self.items = [(m, None) if isinstance(m, str) else tuple(m) for m in items]
        super().__init__("\n".join(m for m, _ in self.items))


def rel(path):
    """A path as the user knows it: relative to the site root when under
    it, else to the generator's root (types/post.py, in Docker too), else
    as given."""
    for base in (ROOT, BUILDER):
        try:
            return str(path.relative_to(base))
        except (AttributeError, ValueError):
            pass
    return str(path)


def message(path, what, hint="", line=None):
    where = rel(path) if path else ""
    if where and line:
        where += f":{line}"
    text = f"{where}: {what}" if where else what
    return f"{text}. {hint}" if hint else text


def error(path, what, hint="", line=None, exc=None):
    """A BuildError with one item. Build it, then raise it or gather it."""
    return BuildError([(message(path, what, hint, line), exc)])


def fail(errors):
    """Raise every gathered error at once."""
    raise BuildError([item for e in errors for item in e.items])


def warning(path, what, hint=""):
    print(f"warning: {message(path, what, hint)}", file=sys.stderr, flush=True)


def report(exc):
    """Print an exception the way the build reports errors."""
    if isinstance(exc, BuildError):
        for text, cause in exc.items:
            print(f"error: {text}", file=sys.stderr, flush=True)
            if DEBUG and cause is not None:
                traceback.print_exception(cause, file=sys.stderr)
    else:
        print(f"error: {exc.__class__.__name__}: {exc}", file=sys.stderr, flush=True)
        if DEBUG:
            traceback.print_exception(exc, file=sys.stderr)
