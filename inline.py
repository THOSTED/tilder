"""Inline rendering: the Markdown subset shared by the HTML and text outputs.

`[text](url)`, `` `code` ``, `**bold**`, `*italic*` or `_italic_`,
`~~struck~~`, `++underlined++`. Nothing else: every addition here is paid twice, once per
output.
"""

import html
import re
from urllib.parse import urlparse

TOKEN = re.compile(
    r"\[(?P<lt>[^\]]+)\]\((?P<lu>[^)]+)\)"
    r"|`(?P<c>[^`]+)`"
    r"|\*\*(?P<b>[^*]+)\*\*"
    r"|~~(?P<s>[^~]+)~~"
    # ++underlined++: not after a letter or inside a space, so "C++" and
    # "1 ++ 2" stay text.
    r"|(?<![\w+])\+\+(?P<ul>[^+\s](?:[^+]*[^+\s])?)\+\+(?![\w+])"
    # *italic*: not touching a space inside, so "2 * 3 * 4" stays text.
    r"|(?<![*\w])\*(?P<i>[^*\s](?:[^*]*[^*\s])?)\*(?![*\w])"
    # _italic_: only at word boundaries, so snake_case stays text.
    r"|(?<![\w_])_(?P<u>[^_\s](?:[^_]*[^_\s])?)_(?![\w_])"
)


def tokens(text):
    """Split a line into (kind, content, url), kind in text, link, code,
    bold, strike, italic. Single pass, no nesting."""
    pos = 0
    for m in TOKEN.finditer(text):
        if m.start() > pos:
            yield ("text", text[pos:m.start()], None)
        if m.group("lt") is not None:
            yield ("link", m.group("lt"), m.group("lu"))
        elif m.group("c") is not None:
            yield ("code", m.group("c"), None)
        elif m.group("b") is not None:
            yield ("bold", m.group("b"), None)
        elif m.group("s") is not None:
            yield ("strike", m.group("s"), None)
        elif m.group("ul") is not None:
            yield ("underline", m.group("ul"), None)
        else:
            yield ("italic", m.group("i") or m.group("u"), None)
        pos = m.end()
    if pos < len(text):
        yield ("text", text[pos:], None)


# Set by the build from site.toml. EXTERNAL is said by screen readers after
# an external link, instead of the arrow (read as "north-east arrow");
# NEW_TAB_LABEL when the link opens a new tab. [links] new_tab and same_tab
# decide which external links open one.
EXTERNAL = ""
NEW_TAB_LABEL = ""
NEW_TAB = False
SAME_TAB = ()
ARROW = "\u2197"


def opens_new_tab(url):
    """True for an external link that [links] sends to a new tab."""
    if not NEW_TAB or not url.startswith(("http://", "https://")):
        return False
    host = urlparse(url).hostname or ""
    return not any(host == h or host.endswith("." + h) for h in SAME_TAB)


def link_attrs(url):
    """target and rel for a link, from [links]."""
    return ' target="_blank" rel="noopener"' if opens_new_tab(url) else ""


def arrow(escaped, new_tab=False):
    """The external-link arrow: hidden from screen readers, which hear
    EXTERNAL instead - and NEW_TAB_LABEL when the link opens a new tab
    (WCAG G201: say it before it happens)."""
    said = [s for s, on in ((EXTERNAL, ARROW in escaped), (NEW_TAB_LABEL, new_tab)) if s and on]
    note = f'<span class="sr-only"> ({", ".join(said)})</span>' if said else ""
    if ARROW in escaped:
        return escaped.replace(ARROW, f'<span aria-hidden="true">{ARROW}</span>') + note
    return escaped + note


def to_html(text, resolve=lambda u: u):
    out = []
    for kind, content, url in tokens(text):
        e = html.escape(content, quote=False)
        if kind == "link":
            out.append(f'<a href="{html.escape(resolve(url))}"{link_attrs(url)}>'
                       f"{arrow(e, opens_new_tab(url))}</a>")
        elif kind == "code":
            out.append(f"<code>{e}</code>")
        elif kind == "bold":
            out.append(f"<b>{e}</b>")
        elif kind == "italic":
            out.append(f"<em>{e}</em>")
        elif kind == "strike":
            out.append(f"<del>{e}</del>")
        elif kind == "underline":
            out.append(f'<u class="u">{e}</u>')
        else:
            out.append(e)
    return "".join(out)


# Invisible marks around `code` in the text mirror: the plain text drops
# them, the coloured one turns them into colour (text.py, ansify.py). Control
# characters never found in content.
CODE_ON, CODE_OFF = "\x02", "\x03"


def to_text(text, marks=False):
    """Text keeps the label; the URL follows only when absolute - an internal
    path is visited with curl, not copied by hand. Italic is plain text;
    struck text keeps its ~~ marks, since dropping them changes the sense.
    With marks, `code` is wrapped in CODE_ON / CODE_OFF."""
    out = []
    for kind, content, url in tokens(text):
        if kind == "link":
            out.append(f"{content} ({url})" if url.startswith("http") else content)
        elif kind == "strike":
            out.append(f"~~{content}~~")
        elif kind == "code" and marks:
            out.append(CODE_ON + content + CODE_OFF)
        else:
            out.append(content)
    return "".join(out)
