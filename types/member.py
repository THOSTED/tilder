"""Members: one page each, a searchable grid, a profile card with the
person's public links. The built-in `member` type (docs/types.md)."""

from config import CFG
from fold import to_ascii
from seo import org_ref, page_heading, page_title

NAME = "member"
SCRIPT = "members.js"   # search and filter on a {members} page, if the theme ships it
DEFAULTS = {
    "man": "SITE-MEMBERS(7)",
    "nav": "members",
    "categories": ["admin", "member"],   # display and sort order
    "default_category": "member",
    "empty": "No member listed yet.",
    "search_label": "search",
    "search_placeholder": "first or last name",
    "all": "all",
    "one": "entry",
    "many": "entries",
    "none": "No entry matches.",
    "full": "full",                      # a mentor at capacity, said in words
}

# Profiles a member may list, in display order: front-matter key, and the
# name read by screen readers and shown in the text mirror. `website` is
# named by labels.website.
NETWORKS = (("linkedin", "LinkedIn"), ("github", "GitHub"), ("gitlab", "GitLab"),
            ("mastodon", "Mastodon"), ("bluesky", "Bluesky"), ("website", None))


def defaults(item, conf):
    meta = item["meta"]
    meta.setdefault("man", conf["man"])
    meta.setdefault("nav", conf["nav"])
    meta.setdefault("description", "")


def member_name(meta):
    """The name shown: the chosen name if given, else first and last."""
    return meta.get("display_name") or " ".join(
        n for n in (meta.get("first_name", ""), meta.get("last_name", "")) if n)


def profiles(meta):
    """[(key, label, url)] of the member's public profiles. A key may hold
    several URLs, separated by spaces (a personal and a company GitHub):
    each is then named with its handle, "GitHub (ada)"."""
    out = []
    for key, label in NETWORKS:
        urls = meta.get(key, "").split()
        name = label or CFG["labels"]["website"]
        for url in urls:
            handle = url.rstrip("/").rsplit("/", 1)[-1]
            out.append((key, f"{name} ({handle})" if len(urls) > 1 else name, url))
    return out


def sort_key(item, conf):
    """Category order, then last name (ASCII, lower), then slug."""
    meta, order = item["meta"], conf["categories"]
    category = meta.get("category", conf["default_category"])
    rank = (order.index(category) if category in order else len(order), category)
    return (rank, to_ascii(meta.get("last_name", "")).lower(), item["slug"])


def entry(item, link, conf):
    """The card: name, pronouns, affiliation, capacity, category tag, the
    profile links; and the words members.js searches."""
    meta = item["meta"]
    name = member_name(meta)
    line = [meta[k] for k in ("pronouns", "affiliation", "capacity") if meta.get(k)]
    category = meta.get("category", conf["default_category"])
    if meta.get("full") == "yes":
        line.append(conf["full"])  # said in words, not only by the tag's colour
    line.append(f"`{category}`")
    names = [name, meta.get("first_name", ""), meta.get("last_name", "")]
    links = profiles(meta)
    return {
        "k": "entry", "id": None, "own": not link,
        "blocks": [{"k": "profiles", "items": links}] if links else [],
        "meta": line,
        "title": f"[{name}]({item['path'][:-5]})" if link else name,
        "cls": ["full"] if meta.get("full") == "yes" else [],
        "data": {"category": category,
                 "search": " ".join(dict.fromkeys(to_ascii(" ".join(names)).lower().split()))},
    }


def grid(items, conf):
    """{members}: every member, in load order, as a grid."""
    return {"items": [(it, []) for it in items], "empty": conf.get("empty", ""), "cls": ["grid"]}


MARKERS = {"members": grid}


def list_data(conf):
    """The search's wording, for members.js: it holds no text itself."""
    return {k: conf[k] for k in ("search_label", "search_placeholder", "all", "one", "many", "none")}


def json_ld(item, conf):
    meta = item["meta"]
    person = {"@type": "Person", "name": page_heading(meta), "memberOf": org_ref()}
    same = [url for key, _ in NETWORKS for url in meta.get(key, "").split()]
    if same:
        person["sameAs"] = same  # links the profiles to the person
    if meta.get("affiliation"):
        person["affiliation"] = {"@type": "Organization", "name": meta["affiliation"]}
    return {"@type": "ProfilePage", "name": page_title(meta), "mainEntity": person}
