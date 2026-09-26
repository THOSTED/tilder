#!/usr/bin/env python3
"""Build the site: content/ + assets/ -> public/.

    python3 builder/build.py                 build once into public/
    python3 builder/build.py --out DIR       build into DIR
    python3 builder/build.py --watch         build, then rebuild on every change
    python3 builder/build.py --debug         show Python tracebacks after error messages

The source is restricted, accented Markdown (builder/docs/markdown.md). Each page
comes out twice: HTML, and pure ASCII for the terminal (AGENTS.md §11).

The builder, one concern per module, all in src/ (../build.py is only the
entry point):

    build.py      this driver: one build, the CLI, the first-build retry
    config.py     paths, content/site.toml, what a build shares (STATE)
    report.py     errors and warnings, one shape
    markdown.py   Markdown -> a tree of nodes (sections, entries, blocks)
    inline.py     inline markup, for both outputs
    page.py       the tree -> HTML, inside assets/layout.html
    text.py       the tree -> the text mirror, 75 columns
    ansify.py     the text mirror -> its coloured twin
    highlight.py  syntax highlighting of code blocks
    contenttypes.py the types (types/, theme/types/), collections, items, lists
    dates.py      dates in words, from [dates]
    seo.py        meta tags, structured data, sitemaps, robots.txt, manifest
    feeds.py      RSS and iCalendar
    paths.py      content paths -> output paths, URLs, relative links
    fold.py       ASCII folding
    watch.py      polling, rebuild on change and at midnight
    icons.sh      assets/logo.svg -> the raster icons (run by hand)

types/ holds the built-in content types, one module each (docs/types.md).

It holds no user-facing text: that lives in content/site.toml.
"""

import datetime
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
# --root DIR: the project to build. Read before config, which resolves paths.
if "--root" in sys.argv:
    os.environ["SITE_ROOT"] = sys.argv[sys.argv.index("--root") + 1]
import ansify as ansify_module
import contenttypes
import inline
import report
from ansify import ansify
from config import (ASSETS, BUILDER, CFG, CONFIG, CONTENT, EXTRA, ROOT, STATE, TEMPLATES,
                    THEME, apex, load_config)
from icons import generated
from fold import to_ascii
from feeds import calendar, events_feed, posts_feed
from markdown import parse, site_path
from page import render_html
from paths import clean_url, rendered, txt_name
from seo import check, manifest, robots, sitemap_xml
from text import plain, render_txt
from watch import snapshot, watch

def build():
    """Every output file, as {relative path: bytes}."""
    load_config()
    inline.EXTERNAL = CFG["labels"]["external"]
    inline.NEW_TAB_LABEL = CFG["labels"]["new_tab"]
    inline.NEW_TAB = CFG["links"]["new_tab"]
    inline.SAME_TAB = tuple(CFG["links"]["same_tab"])
    ansify_module.COMMANDS = CFG["text"]["commands"]
    ansify_module.BOXES = {
        to_ascii(CFG["labels"][kind]): colour for kind, colour in
        (("info", ansify_module.CYAN), ("warning", ansify_module.YELLOW),
         ("error", ansify_module.RED))}
    STATE["today"] = os.environ.get("BUILD_TODAY") or datetime.date.today().isoformat()
    contenttypes.load()
    colls = contenttypes.collections()
    items = {name: contenttypes.load_items(name, conf) for name, conf in colls.items()}
    by_src = {it["src"]: it for its in items.values() for it in its}
    STATE["summary"] = contenttypes.summary(colls, items)
    out, pages = {}, []  # pages: every item that is an HTML page, for sitemap and SEO checks
    for src in sorted(p for p in CONTENT.rglob("*.md") if rendered(p)):
        meta, sections, preamble = parse(src)
        it = by_src[src] if src in by_src else contenttypes.page_item(src, meta)
        meta = it["meta"]
        meta["_dir"] = site_path(src)
        _compat(it)  # Task 8 removes this
        pages.append(it)
        contenttypes.fill_lists(sections, src, it["path"], colls, items)
        out[it["path"]] = render_html(it, sections, preamble, colls)
        if meta.get("text", "yes") != "no":
            marked = render_txt(meta, sections)
            out[f"txt/{txt_name(it['path'])}.txt"] = plain(marked)
            out[f"ansi/{txt_name(it['path'])}.txt"] = ansify(marked)
    # Feeds and the type's own files, for the collections whose folder exists.
    for name, conf in colls.items():
        if not (CONTENT / conf["dir"]).is_dir():
            continue
        if conf["type"] == "post" and conf.get("feed"):
            out[conf["feed"]] = posts_feed(items[name], conf)
        if conf["type"] == "event":
            if conf.get("feed"):
                out[conf["feed"]] = events_feed(items[name], conf)
            if conf.get("calendar"):
                out[conf["calendar"]] = calendar(items[name])
    a = apex()
    indexed = [it for it in pages if "noindex" not in it["meta"].get("robots", "")]
    out["sitemap.xml"] = sitemap_xml(indexed)
    out["sitemap.txt"] = "".join(f"{a}{clean_url(it['path'])}\n" for it in
                                 sorted(indexed, key=lambda it: clean_url(it["path"])))
    out["robots.txt"] = robots(CFG["robots"], f"{a}/sitemap.xml")
    check(pages)
    # txt/ is the root of the plain-text host: this is its /robots.txt.
    out["txt/robots.txt"] = robots(CFG["robots_man"])
    out["site.webmanifest"] = manifest()
    out = {k: v.encode("utf-8") for k, v in out.items()}
    # Files next to the pages (images of a post or an event...) are copied
    # as they are, at the same path. Markdown and site.toml are not.
    for f in sorted(CONTENT.rglob("*")):
        rel = f.relative_to(CONTENT)
        if f.is_file() and f.suffix != ".md" and f != CONFIG \
                and not any(part.startswith("_") for part in rel.parts):
            out[str(rel)] = f.read_bytes()
    # The theme, then the project's assets/, which win over it by name.
    # Templates (layout.html, share.svg) are read by the build, not served.
    for base in (THEME, ASSETS):
        for f in sorted(base.rglob("*")) if base.is_dir() else []:
            rel = str(f.relative_to(base))
            # Icons are drawn inline in the pages, not served as files.
            if f.is_file() and rel not in TEMPLATES and not rel.startswith("icons/"):
                out[rel] = f.read_bytes()
    out.update(generated())  # icons and share.png, from assets/logo.svg
    for f in EXTRA:
        out[f.name] = f.read_bytes()
    return out


def _compat(it):
    """Until feeds.py asks the type (Tasks 8-9): the old keys it reads."""
    if it["date"]:
        it["iso"] = it["date"]


def write(outputs, dest):
    """Sync dest with outputs: write what changed, delete what is gone.
    Each file is replaced atomically, so the server never reads half of it."""
    changed = []
    for name, data in sorted(outputs.items()):
        target = dest / name
        if target.is_file() and target.read_bytes() == data:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(f".{target.name}.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)
        changed.append(name)
    for f in sorted(dest.rglob("*"), reverse=True):
        rel = str(f.relative_to(dest))
        if f.is_file() and rel not in outputs:
            f.unlink()
            changed.append(f"-{rel}")
        elif f.is_dir() and not any(f.iterdir()):
            f.rmdir()
    return changed


_SAID = False


def build_into(dest):
    global _SAID
    changed = write(build(), dest)
    if not _SAID:
        print(STATE["summary"], flush=True)
        _SAID = True
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] built {dest}: " + (", ".join(changed) or "no change"), flush=True)


def main():
    args = sys.argv[1:]
    dest = ROOT / "public"
    if args[:1] and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    report.DEBUG = "--debug" in args
    if "--out" in args:
        dest = pathlib.Path(args[args.index("--out") + 1]).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    if "--watch" in args:
        interval = float(os.environ.get("BUILD_INTERVAL", "1"))
        own_code = lambda: {k: v for k, v in snapshot().items()
                            if k.startswith(str(BUILDER))}
        code = own_code()
        while True:
            try:
                build_into(dest)
                break
            except Exception as e:
                # Wait for a fix. If it is in builder/, restart to load it:
                # this process still runs the code that failed.
                report.report(e)
                print("build failed: waiting for a change in content/, theme/ or assets/ "
                      "(a change in builder/ restarts)", flush=True)
                time.sleep(interval * 5)
                if own_code() != code:
                    print("builder/ changed, restarting", flush=True)
                    os.execv(sys.executable, [sys.executable] + sys.argv)
        watch(dest, interval, build_into)
    else:
        try:
            build_into(dest)
        except report.BuildError as e:
            report.report(e)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
