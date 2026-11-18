"""Colour the text mirror with ANSI escape sequences.

The input is the marked text from text.py: the plain text plus invisible
marks the build placed where it knew the markup - around inline `code`
(CODE_ON / CODE_OFF), around a list item's marker (LIST_ON / LIST_OFF), at
the start of each code-block line (CODE_BLOCK, or HL_BLOCK when its
language is highlighted) and of its rules (FRAME), and around each token of
a highlighted block (HL[kind] / HL_OFF, the kinds of highlight.py). Colour
follows those marks exactly, across line breaks; it is not guessed from the
words.

txt/ is the same text with the marks removed and no escape at all: it is
what the plain-text host serves, and it must survive `curl > file`.

The rest is layout, recognised line by line: the header and footer rules
dim, section headings bold, the first section's name bold, callout boxes in
the colour of their kind, URLs and [ tags ] in the one accent. Eight ANSI
colours, or a 256-colour accent the site chose ([text] accent); never a
background: it reads on light and dark terminals.
"""

import re

from highlight import KINDS

RESET, BOLD, DIM, UNDER = "\033[0m", "\033[1m", "\033[2m", "\033[4m"
RED, GREEN, YELLOW, MAGENTA = "\033[31m", "\033[32m", "\033[33m", "\033[35m"
# The eight colours, in the order of their SGR codes: 30 black ... 37 white.
COLOURS = ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")
CODE_ON, CODE_OFF, CODE_BLOCK, LIST_ON, LIST_OFF = "\x02", "\x03", "\x04", "\x05", "\x06"
FRAME = "\x07"
HL_BLOCK, HL_OFF = "\x01", "\x08"
HL = {kind: chr(0x0e + n) for n, kind in enumerate(KINDS)}  # as in text.py


def sgr(value):
    """The escape of a colour: a colour name -> ESC[3Nm, its bright twin
    ("bright-cyan") -> ESC[9Nm, "dim" -> ESC[2m, an index from 16 to 255 ->
    ESC[38;5;Nm (0-15 are the eight colours and their bright twins, which
    a terminal's theme redefines: name them instead). None for anything
    else."""
    if isinstance(value, str) and value in COLOURS:
        return f"\033[3{COLOURS.index(value)}m"
    if isinstance(value, str) and value.startswith("bright-") and value[7:] in COLOURS:
        return f"\033[9{COLOURS.index(value[7:])}m"
    if value == "dim":
        return DIM
    if type(value) is int and 16 <= value <= 255:
        return f"\033[38;5;{value}m"
    return None


# Set by the build from site.toml, per language: the accent ([text] accent),
# callout labels and their colour (INFO in the accent), and the words that
# start a command line in a code block.
ACCENT = sgr("cyan")
# [text] link: URLs and internal paths, quieter than what the accent puts
# forward; [text] muted: the rules, the code frames, the cards' frames.
LINK = ACCENT
MUTED = DIM
BOXES = {"INFO": ACCENT, "WARNING": YELLOW, "ERROR": RED}
COMMANDS = ["curl"]

HEADING = re.compile(r"^[A-Z][A-Z0-9()' -]*$")
URL = re.compile(r"https?://[^\s\x01-\x08\x0e-\x1a]+")
# An internal link's path, as text.py writes it: "label (/events)".
LOCAL = re.compile(r"(?<=\()/[^\s()\x01-\x08\x0e-\x1a]*(?=\))")
# A card's frame, and its URL line under the title (text.sidebar).
CARD = re.compile(r"^(\s*)([,|'])(?= |$)")
CARD_URL = re.compile(r"^(\s*\| )(/\S*)$")
TAG = re.compile(r"\[ [^\]]+ \]")
BOX_SIDE = re.compile(r"^(\s*)\|(.*)\|$")
BOX_BOTTOM = re.compile(r"^\s*\+-+\+$")


def _box_top(line):
    labels = "|".join(map(re.escape, BOXES))
    return re.match(rf"^(\s*)\+- ({labels}) (-+\+)$", line) if BOXES else None


CLOSERS = {")": "(", "]": "[", "}": "{"}


def trim(s):
    """s without the punctuation that closes the sentence around it: a
    trailing . , ; : ! ?, a quote left unpaired, a bracket left unopened.
    `(see https://x.org/a_(b)).` -> the URL is https://x.org/a_(b)."""
    while s:
        c = s[-1]
        if not (c in ".,;:!?" or (c in "\"'" and s.count(c) % 2)
                or (c in CLOSERS and s.count(c) > s.count(CLOSERS[c]))):
            break
        s = s[:-1]
    return s


def _accent(s, also=""):
    """s in the accent (and `also`: UNDER), its closing punctuation left as
    it is."""
    kept = trim(s)
    return ACCENT + also + kept + RESET + s[len(kept):] if kept else s


def _link(s):
    """s in the link colour, underlined, its closing punctuation left out."""
    kept = trim(s)
    return LINK + UNDER + kept + RESET + s[len(kept):] if kept else s


def _split_tags(s):
    """A card title's line -> (the title, the [ tags ] after it, spaces
    included)."""
    m = re.search(r"\s+(\[ [^\]]+ \]\s*)+$", s)
    return (s[:m.start()], s[m.start():]) if m else (s, "")


def text_part(s):
    """Outside code: URLs and internal paths in the link colour, [ tags ]
    and list markers in the accent."""
    s = URL.sub(lambda m: _link(m.group(0)), s)
    s = LOCAL.sub(lambda m: LINK + UNDER + m.group(0) + RESET, s)
    s = TAG.sub(lambda m: BOLD + ACCENT + m.group(0) + RESET, s)
    return s.replace(LIST_ON, ACCENT).replace(LIST_OFF, RESET)


def marked(line, inside):
    """Colour one line's marks. `inside` says whether a code span is still
    open from the line before; returns (line, inside after it)."""
    out = [ACCENT] if inside else []
    for part in re.split(f"([{CODE_ON}{CODE_OFF}])", line):
        if part == CODE_ON:
            out.append(ACCENT)
            inside = True
        elif part == CODE_OFF:
            out.append(RESET)
            inside = False
        elif inside:
            out.append(part.replace(LIST_ON, "").replace(LIST_OFF, ""))
        else:
            out.append(text_part(part))
    if inside:
        out.append(RESET)  # closed at the line's end, reopened on the next
    return "".join(out), inside


def code_line(line):
    """A code-block line: a command line - a known command, possibly after
    a `$ ` prompt - in the accent; anything else as it is."""
    words = "|".join(map(re.escape, COMMANDS))
    m = re.match(rf"^(\s*(?:[$#] )?)((?:{words})\b.*)$", line)
    return m.group(1) + _accent(m.group(2)) if m else line


def token_colours():
    """The colour of each kind of token in a highlighted code block, in
    the accent of the current pass."""
    return {"k": BOLD + ACCENT, "x": BOLD + ACCENT,   # keyword, shell command
            "b": ACCENT, "o": ACCENT,                  # builtin or type, option
            "s": GREEN, "c": DIM, "p": DIM,            # string, comment, prompt
            "n": MAGENTA, "v": MAGENTA,                # number, variable
            "t": BOLD, "gh": BOLD,                     # tag or key, diff hunk
            "gi": GREEN, "gd": RED}                    # diff: inserted, deleted


def highlighted(line):
    """A line of a highlighted code block: each token in its kind's colour."""
    colours = token_colours()
    for kind, mark in HL.items():
        line = line.replace(mark, colours[kind])
    return line.replace(HL_OFF, RESET)


def ansify(text):
    lines = text.split("\n")
    footer = max(i for i, l in enumerate(lines) if l.strip())
    first_heading = next((i for i, l in enumerate(lines) if i and HEADING.match(l)), None)
    box, inside, out = None, False, []
    for i, line in enumerate(lines):
        if line.startswith(CODE_BLOCK):
            out.append(code_line(line[1:]))
            continue
        if line.startswith(HL_BLOCK):
            out.append(highlighted(line[1:]))
            continue
        if line.startswith(FRAME):  # a code block's rules: muted
            body = line[1:]
            indent = body[: len(body) - len(body.lstrip())]
            out.append(indent + MUTED + body.lstrip() + RESET)
            continue
        top = _box_top(line)
        if top:
            box = BOXES[top.group(2)]
            out.append(top.group(1) + box + "+- " + BOLD + top.group(2) + RESET
                       + box + " " + top.group(3) + RESET)
            continue
        if box and BOX_BOTTOM.match(line):
            out.append(box + line + RESET)
            box = None
            continue
        side = BOX_SIDE.match(line) if box else None
        if side:
            body, inside = marked(side.group(2), inside)
            out.append(side.group(1) + box + "|" + RESET + body + box + "|" + RESET)
            continue
        if not line.strip():
            out.append(line)
        elif i in (0, footer):
            out.append(MUTED + line + RESET)
        elif CARD.match(line):
            # A card's line: its frame muted, its URL line in the link colour.
            url = CARD_URL.match(line)
            if url:
                bar = url.group(1).rstrip()
                out.append(bar[:-1] + MUTED + "|" + RESET + " " + LINK + UNDER + url.group(2) + RESET)
                continue
            m = CARD.match(line)
            rest = line[m.end():]
            if lines[i - 1].strip() == ",":
                # The card's title, the line after its top: bold, its tags
                # in the accent at the right edge.
                gap = rest[:len(rest) - len(rest.lstrip(" "))]
                title, tags = _split_tags(rest.lstrip(" "))
                out.append(m.group(1) + MUTED + m.group(2) + RESET + gap
                           + BOLD + title + RESET + text_part(tags))
                continue
            body, inside = marked(rest, inside)
            out.append(m.group(1) + MUTED + m.group(2) + RESET + body)
        elif HEADING.match(line):
            out.append(BOLD + line + RESET)
        elif i == (first_heading or -1) + 1 and " - " in line:
            # The first section's first line: "name - what it is".
            indent = line[: len(line) - len(line.lstrip())]
            name, rest = line.lstrip().split(" - ", 1)
            body, inside = marked(rest, inside)
            out.append(indent + BOLD + name + RESET + " - " + body)
        else:
            body, inside = marked(line, inside)
            out.append(body)
    return "\n".join(out)
