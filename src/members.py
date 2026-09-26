"""Members: one file each, the {members} grid, a card on each page."""

import pathlib

from config import CFG, CONTENT
from fold import to_ascii
from markdown import front_matter
from paths import rendered

MEMBERS = CONTENT / "members"


def member_name(meta):
    """The name shown: the chosen name if given, else first and last."""
    return meta.get("display_name") or " ".join(
        n for n in (meta.get("first_name", ""), meta.get("last_name", "")) if n)


# Profiles a member may list, in display order: front-matter key, and the
# name read by screen readers and shown in the text mirror.
NETWORKS = (("linkedin", "LinkedIn"), ("github", "GitHub"), ("gitlab", "GitLab"),
            ("mastodon", "Mastodon"), ("bluesky", "Bluesky"), ("website", None))


def profiles(meta):
    """[(key, label, url)] of the member's public profiles. A key may hold
    several URLs, separated by spaces (a personal and a company GitHub):
    each is then named with its handle, "GitHub (ttrova)". `website` is
    named by labels.website."""
    out = []
    for key, label in NETWORKS:
        urls = meta.get(key, "").split()
        name = label or CFG["labels"]["website"]
        for url in urls:
            handle = url.rstrip("/").rsplit("/", 1)[-1]
            out.append((key, f"{name} ({handle})" if len(urls) > 1 else name, url))
    return out


def member_entry(slug, meta, link):
    """One member as an entry node: title, meta line, search data."""
    name = member_name(meta)
    items = [meta[k] for k in ("pronouns", "affiliation", "capacity") if meta.get(k)]
    category = meta.get("category", CFG["members"]["default_category"])
    if meta.get("full") == "yes":
        # Said in words, not only by the tag's colour.
        items.append(CFG["members"]["full"])
    items.append(f"`{category}`")
    names = [name, meta.get("first_name", ""), meta.get("last_name", "")]
    blocks = [{"k": "profiles", "items": profiles(meta)}] if profiles(meta) else []
    return {
        "k": "entry", "id": None, "blocks": blocks, "meta": items, "own": not link,
        "title": f"[{name}](members/{slug})" if link else name,
        "cls": ["full"] if meta.get("full") == "yes" else [],
        "data": {
            "category": category,
            "search": " ".join(dict.fromkeys(
                to_ascii(" ".join(names)).lower().split())),
        },
    }


def load_members():
    """(slug, front matter) for every member page, category order then
    last name. Files starting with _ (the template) are skipped."""
    out = []
    for f in sorted(MEMBERS.glob("*.md")) if MEMBERS.is_dir() else []:
        if rendered(f):
            meta, _ = front_matter(f.read_text())
            out.append((f.stem, meta))
    order = CFG["members"]["categories"]
    rank = lambda c: (order.index(c) if c in order else len(order), c)
    default = CFG["members"]["default_category"]
    return sorted(out, key=lambda m: (rank(m[1].get("category", default)),
                                      to_ascii(m[1].get("last_name", "")).lower(),
                                      m[0]))


def fill_members(sections, members, path):
    """Fill every {members} section with one card per member, and put the
    member's own card at the top of their page."""
    for s in sections:
        if "members" in s["cls"]:
            s["cls"].append("grid")
            cards = [member_entry(slug, m, True) for slug, m in members]
            s["blocks"] = cards + s["blocks"] if cards else [
                {"k": "empty", "text": CFG["members"]["empty"]}] + s["blocks"]
    slug = pathlib.PurePath(path).stem
    if path.startswith("members/") and sections:
        for s_slug, m in members:
            if s_slug == slug:
                sections[0]["blocks"].append(member_entry(slug, m, False))
