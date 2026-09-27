"""The contract between the builder and a theme, as data: every class the
builder writes, in the order of docs/theme.md's table ("The HTML the
builder writes"), which a test keeps equal to CLASSES. build.py --check
checks a theme's style.css against it (themecheck.py)."""

CLASSES = (
    "sr-only",
    "wordmark", "tilde", "slash", "here", "cursor",
    "nav", "sep",
    "languages",
    "collection-nav", "collection-group", "collection-group-label",
    "collection-section", "collection-section--open", "collection-section-label",
    "prev", "prev-label", "next", "next-label",
    "s", "b",
    "grid", "members", "posts", "upcoming", "past", "next-event",
    "entry", "entry--next", "entry--full", "entry--link",
    "meta", "tag", "tag--next", "tag--full",
    "small", "muted", "faint", "mono", "warn", "empty",
    "inset", "callout", "callout--info", "callout--warning", "callout--error", "callout-label",
    "code", "hl-k", "hl-s", "hl-c", "hl-b", "hl-n", "hl-v", "hl-p", "hl-t", "hl-gi", "hl-gd", "hl-gh",
    "table", "center", "right",
    "tasks", "task", "task--done", "task--todo",
    "figure",
    "toc", "toc-label",
    "profiles", "icon",
    "u",
)
