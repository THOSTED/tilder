"""Posts: dated articles, newest first, with an RSS feed. The built-in
`post` type, written as any theme type is (docs/types.md)."""

from config import apex
from dates import human_date
from paths import clean_url
from seo import org_ref, page_heading, share_image

NAME = "post"
DATED = True
ARTICLE = True          # Reader mode and read-aloud tools look for one
OG_TYPE = "article"
PAGED = {"posts"}       # {posts} shows per_page cards a page, when the collection sets it
DEFAULTS = {
    "man": "SITE-BLOG(7)",          # items' man-page name, unless they set one
    "nav": "blog/",                 # items' nav entry, and the feed's link
    "empty": "No post yet.",        # a {posts} list with nothing in it
    "feed": "",                     # RSS path, e.g. "blog/feed.xml"; empty for none
    "feed_title": "posts",
    "feed_description": "Posts.",
    "scheduled": True,              # a post dated after the build's date waits for it
}


def defaults(item, conf):
    meta = item["meta"]
    meta.setdefault("man", conf["man"])
    meta.setdefault("nav", conf["nav"])
    meta.setdefault("tagline", human_date(item["date"]))
    meta.setdefault("description", "")


def tags(meta):
    """`tag` (one) and `tags` (several, separated by commas), in that
    order, each once."""
    words = [meta.get("tag", "")] + meta.get("tags", "").split(",")
    return list(dict.fromkeys(w.strip() for w in words if w.strip()))


def entry(item, link, conf):
    """The card: date, author, tag; the description in a list."""
    meta = item["meta"]
    line = [f"{item['date']} | {human_date(item['date'])}"]
    if meta.get("author"):
        line.append(meta["author"])
    line.extend(f"`{t}`" for t in tags(meta))
    blocks = []
    if link and meta.get("description"):
        blocks.append({"k": "para", "text": meta["description"], "cls": []})
    return {"k": "entry", "id": None, "cls": ["link"] if link else [], "meta": line,
            "blocks": blocks, "own": not link,
            "title": f"[{meta['title']}]({item['path'][:-5]})" if link else meta["title"]}


def posts(items, conf):
    """{posts}: every post, newest first."""
    return {"items": [(it, []) for it in reversed(items)], "empty": conf.get("empty", "")}


MARKERS = {"posts": posts}


def json_ld(item, conf):
    meta = item["meta"]
    node = {"@type": "BlogPosting", "headline": page_heading(meta),
            "description": meta["description"], "datePublished": item["date"],
            "dateModified": meta.get("updated", item["date"]),
            "publisher": org_ref(), "image": share_image(meta)[0]}
    if meta.get("author"):
        node["author"] = {"@type": "Person", "name": meta["author"]}
    return node


def meta_tags(item, conf):
    meta, out = item["meta"], []
    if meta.get("author"):
        out.append(("name", "author", meta["author"]))
    out.append(("property", "article:published_time", item["date"]))
    out.extend(("property", "article:tag", t) for t in tags(meta))
    return out


def feed_item(item, conf):
    return {"title": item["meta"]["title"], "link": apex() + clean_url(item["path"]),
            "description": item["meta"]["description"], "date": item["date"]}
