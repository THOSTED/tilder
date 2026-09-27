"""build.py --check: the site's theme against the contract of this tilder.
It builds nothing. Two checks, each ending with a summary line:

  classes   every class the builder writes (contract.CLASSES) has a rule
            in style.css, but those [check] unstyled names
  contrast  each pair of [check] contrast, custom properties of :root in
            style.css, reaches [check] contrast_min in the light scheme
            and in the dark one (:root inside @media (prefers-color-scheme:
            dark)), as a WCAG 2 contrast ratio

[check] is read from defaults.toml, the theme's theme.toml and the site's
site.toml, the last one winning. Problems are printed in the report's
shape, one line each; the exit code is 1 when there is one, else 0.
With --markdown, the contrast table goes to standard output as Markdown,
for a theme's README, and the summary lines to standard error."""

import re
import sys
import tomllib

from config import CONFIG, DEFAULTS, THEME_TOML, _layer, theme_file
from contract import CLASSES
from report import BuildError, error, message, rel, report

COMMENT = re.compile(r"/\*.*?\*/", re.S)
STRING = re.compile(r'"(?:[^"\\\n]|\\.)*"|' + r"'(?:[^'\\\n]|\\.)*'")
TOKEN = re.compile(r"(--[\w-]+)\s*:\s*([^;]*)")
IMPORTANT = re.compile(r"\s*!\s*important\s*$", re.I)
HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")
DARK = re.compile(r"@media\b[^{]*prefers-color-scheme\s*:\s*dark")


def settings():
    """[check] over its defaults: {"unstyled": [...], "contrast": [...],
    "contrast_min": 4.5}."""
    data = {}
    for path in (DEFAULTS, THEME_TOML, CONFIG):
        try:
            _layer(data, path)
        except tomllib.TOMLDecodeError as e:
            raise error(path, f"is not valid TOML: {e}", "Fix it, then check again")
    check = data.get("check", {})
    if not isinstance(check, dict):
        raise error(THEME_TOML, "[check] must be a table",
                    "Write [check] on its own line, then its keys")
    return check


def _strip(css):
    """`css` with its comments removed, then its string literals emptied
    (kept the same length, so positions still line up): a brace or a class
    name inside a string is not code."""
    return STRING.sub(lambda m: m.group(0)[0] * 2, COMMENT.sub("", css))


def missing(css, classes, unstyled=()):
    """The classes that no selector of `css` names, comments and string
    contents aside, but the `unstyled` ones: `.name` counts when no name
    character follows."""
    css = _strip(css)
    return [c for c in classes if c not in unstyled
            and not re.search(r"\." + re.escape(c) + r"(?![\w-])", css)]


def rules(css):
    """[(prelude, body)]: the top-level rules of a stylesheet, comments
    aside, and string literals emptied (content: "}" must not end a rule).
    A statement before a rule (@import ...;) is not part of its prelude."""
    css, out, i = _strip(css), [], 0
    while (j := css.find("{", i)) >= 0:
        depth = 0
        for k in range(j, len(css)):
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            if depth == 0:
                break
        else:
            raise ValueError("a { is never closed")
        out.append((css[i:j].rsplit(";", 1)[-1].strip(), css[j + 1:k]))
        i = k + 1
    return out


def _values(body):
    """{name: value} of the custom properties of a rule's body."""
    return {n: IMPORTANT.sub("", v).strip() for n, v in TOKEN.findall(body)}


def tokens(css):
    """{"light": {name: value}, "dark": {name: value} or None}: the custom
    properties of the top-level :root rules, and those of the :root rules
    inside @media (prefers-color-scheme: dark) over them, as a browser
    would see them. None when the theme has no dark scheme."""
    light, dark = {}, None
    for prelude, body in rules(css):
        if prelude == ":root":
            light.update(_values(body))
        elif DARK.search(prelude):
            for inner, inner_body in rules(body):
                if inner == ":root":
                    dark = dark or {}
                    dark.update(_values(inner_body))
    return {"light": light, "dark": None if dark is None else {**light, **dark}}


def luminance(colour):
    """The relative luminance of #rgb or #rrggbb (WCAG 2)."""
    h = colour[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)

    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def ratio(a, b):
    """The WCAG 2 contrast ratio of two colours, 1 to 21."""
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def contrast(css, pairs):
    """([(scheme, fg, bg, ratio)], [(what, hint)]): each pair in each
    scheme; a token missing or not a hex colour is a problem, once, and its
    pairs have no row."""
    rows, problems, schemes = [], [], tokens(css)
    for scheme in ("light", "dark"):
        values = schemes[scheme]
        if values is None:
            continue
        for fg, bg in pairs:
            bad = False
            for name in (fg, bg):
                value = values.get(name)
                if value is None:
                    problems.append((f"{scheme}: {name} is not set in :root",
                                     "Set it, or leave its pairs out of [check] contrast"))
                    bad = True
                elif not HEX.fullmatch(value):
                    problems.append((f"{scheme}: {name} is {value}, not a hex colour",
                                     "Write it #rrggbb, or leave its pairs out of [check] contrast"))
                    bad = True
            if not bad:
                rows.append((scheme, fg, bg, ratio(values[fg], values[bg])))
    return rows, list(dict.fromkeys(problems))


def markdown(rows, minimum):
    """The contrast table, as Markdown."""
    lines = ["| scheme | foreground | background | ratio | minimum |",
             "|---|---|---|---:|---:|"]
    lines += [f"| {s} | `{fg}` | `{bg}` | {r:.2f} | {minimum:g} |" for s, fg, bg, r in rows]
    return "\n".join(lines)


def _pairs(value):
    """[check] contrast as [(fg, bg)], or None when it is malformed."""
    if not isinstance(value, list):
        return None
    ok = all(isinstance(p, list) and len(p) == 2
             and all(isinstance(t, str) and t.startswith("--") for t in p) for p in value)
    return [tuple(p) for p in value] if ok else None


def run(markdown_table=False, out=sys.stdout, err=sys.stderr):
    """Both checks; the exit code."""
    problems = []

    def problem(path, what, hint=""):
        problems.append(f"error: {message(path, what, hint)}")

    try:
        conf = settings()
    except BuildError as e:
        report(e)
        return 1
    unstyled = conf.get("unstyled", [])
    pairs = _pairs(conf.get("contrast", []))
    minimum = conf.get("contrast_min", 4.5)
    where = rel(THEME_TOML)
    if not (isinstance(unstyled, list) and all(isinstance(c, str) for c in unstyled)):
        problem(THEME_TOML, "[check] unstyled must be a list of class names", 'Write unstyled = ["icon"]')
        unstyled = []
    if pairs is None:
        problem(THEME_TOML, "[check] contrast must be a list of pairs of custom properties",
                'Write contrast = [["--text", "--bg"]]')
        pairs = []
    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
        problem(THEME_TOML, "[check] contrast_min must be a number", "Write contrast_min = 4.5")
        minimum = 4.5
    unstyled = {c.lstrip(".") for c in unstyled}
    path = theme_file("style.css")
    css = path.read_text(encoding="utf-8") if path.is_file() else None
    lines = []

    if css is None:
        lines.append(f"classes: skipped, no {rel(path)}")
    else:
        gone = missing(css, CLASSES, unstyled)
        for c in gone:
            problem(path, f"no rule for .{c}",
                    f"Style it, or name it in [check] unstyled ({where})")
        checked = len([c for c in CLASSES if c not in unstyled])
        lines.append(f"classes: {len(gone)} of {checked} not styled" if gone
                     else f"classes: {checked} of the contract, all styled")

    rows = []
    if not pairs:
        lines.append(f"contrast: skipped, no [check] contrast in {where}")
    elif css is None:
        problem(path, "is missing, and [check] contrast names colours of it",
                f"Add the stylesheet, or remove [check] contrast ({where})")
    else:
        try:
            rows, bad = contrast(css, pairs)
        except ValueError as e:
            rows, bad = [], [(f"cannot be read: {e}", "")]
        for what, hint in bad:
            problem(path, what, hint)
        low = [r for r in rows if r[3] < minimum]
        for s, fg, bg, r in low:
            problem(path, f"{s}: {fg} on {bg} is {r:.2f}:1, below {minimum:g}:1",
                    "Darken or lighten one of them")
        schemes = ", ".join(dict.fromkeys(r[0] for r in rows))
        if bad:
            lines.append(f"contrast: {len(low)} of {len(rows)} pairs below {minimum:g}:1, "
                         f"{len(bad)} unreadable")
        elif low:
            lines.append(f"contrast: {len(low)} of {len(rows)} pairs below {minimum:g}:1")
        else:
            lines.append(f"contrast: {len(rows)} pairs ({schemes}), all at or above {minimum:g}:1")

    for p in problems:
        print(p, file=err)
    if markdown_table:
        if rows:
            print(markdown(rows, minimum), file=out)
    for line in lines:
        print(line, file=err if markdown_table else out)
    return 1 if problems else 0
