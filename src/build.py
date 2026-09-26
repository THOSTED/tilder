#!/usr/bin/env python3
"""Build the site: content/ + assets/ -> public/.

    python3 builder/build.py                 build once into public/
    python3 builder/build.py --out DIR       build into DIR
    python3 builder/build.py --watch         build, then rebuild on every change
    python3 builder/build.py --debug         show Python tracebacks after error messages
    python3 builder/build.py --version       print the builder version and exit

The source is restricted, accented Markdown (builder/docs/markdown.md). Each page
comes out twice: HTML, and pure ASCII for the terminal (AGENTS.md §4).

The builder, one concern per module, all in src/ (../build.py is only the
entry point):

    build.py         this driver: one build, the CLI, the first-build retry
    config.py        paths, content/site.toml, what a build shares (STATE)
    report.py        errors and warnings, one shape
    markdown.py      Markdown -> a tree of nodes (sections, entries, blocks)
    inline.py        inline markup, for both outputs
    page.py          the tree -> HTML, inside the site's theme/layout.html
    text.py          the tree -> the text mirror, 75 columns
    ansify.py        the text mirror -> its coloured twin
    highlight.py     syntax highlighting of code blocks
    contenttypes.py  the types (types/, theme/types/), collections, items, lists
    dates.py         dates in words, from [dates]
    seo.py           meta tags, structured data, sitemaps, robots.txt, manifest
    feeds.py         RSS and iCalendar
    paths.py         content paths -> output paths, URLs, relative links
    fold.py          ASCII folding
    watch.py         polling, rebuild on change and at midnight
    icons.py         the favicon, app icons and share.png, made at every build
    images.py        an image's width and height, read from the file itself

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
import languages
import report
from ansify import ansify
from config import (ASSETS, BUILDER, CFG, CONFIG, CONTENT, EXTRA, ROOT, STATE,
                    THEME, apex, served)
from icons import generated
from fold import to_ascii
from feeds import feed
from markdown import parse, site_path
from page import render_html
from paths import clean_url, txt_name
from seo import check, manifest, robots, sitemap_xml
from text import plain, render_txt
from watch import snapshot, watch
import watch as watch_module

def build():
    """Every output file, as {relative path: bytes}: one pass per declared
    language, each under its prefix; the sitemap, robots.txt, the manifest,
    the types' own files (the calendar) and the copies once."""
    langs = languages.setup()
    STATE["today"] = os.environ.get("BUILD_TODAY") or datetime.date.today().isoformat()
    out, every, table = {}, [], {}  # every: the pages of every language, for the sitemap
    for lang in langs:
        languages.use(lang)
        inline.EXTERNAL = CFG["labels"]["external"]
        inline.NEW_TAB_LABEL = CFG["labels"]["new_tab"]
        inline.NEW_TAB = CFG["links"]["new_tab"]
        inline.SAME_TAB = tuple(CFG["links"]["same_tab"])
        ansify_module.COMMANDS = CFG["text"]["commands"]
        ansify_module.BOXES = {
            to_ascii(CFG["labels"][kind]): colour for kind, colour in
            (("info", ansify_module.CYAN), ("warning", ansify_module.YELLOW),
             ("error", ansify_module.RED))}
        contenttypes.load()
        colls = contenttypes.collections()
        items = {name: contenttypes.load_items(name, conf) for name, conf in colls.items()}
        by_src = {it["src"]: it for its in items.values() for it in its}
        if lang == langs[0]:
            # The table needs paths.ITEM_FOLDERS, which load_items fills; the
            # folders are the same in every language.
            table = languages.pages()
            head = (f"languages: {langs[0]} (default), {', '.join(langs[1:])}\n"
                    if languages.multilingual() else "")
            STATE["summary"] = head + contenttypes.summary(colls, items)
        prefix, pages = STATE["prefix"], []
        for key in sorted(table):
            src, content_lang = languages.pick(table[key], lang)
            STATE["content_lang"] = content_lang
            try:
                meta, sections, preamble = parse(src)
                it = by_src[src] if src in by_src else contenttypes.page_item(src, meta)
                meta = it["meta"]
                meta["_dir"] = site_path(src)
                pages.append(it)
                contenttypes.fill_lists(sections, src, it["path"], colls, items)
                out[prefix + it["path"]] = render_html(it, sections, preamble, colls)
                if meta.get("text", "yes") != "no":
                    marked = render_txt(meta, sections)
                    out[f"txt/{prefix}{txt_name(it['path'])}.txt"] = plain(marked)
                    out[f"ansi/{prefix}{txt_name(it['path'])}.txt"] = ansify(marked)
            except report.BuildError:
                raise
            except Exception as e:  # a missing `title:`...: name the page, not a traceback
                raise report.error(src, f"cannot be built: {e.__class__.__name__}: {e}",
                                   "Run with --debug for the traceback", exc=e)
        # Feeds per language; the types' own files (an iCalendar) once, in
        # the default language: a calendar has no interface language.
        for name, conf in colls.items():
            if not (CONTENT / conf["dir"]).is_dir():
                continue
            module = contenttypes.TYPES[conf["type"]]
            if conf.get("feed") and module.HAS_FEED:
                out[prefix + conf["feed"]] = feed(items[name], conf)
            if lang == langs[0]:
                out.update(contenttypes.call(CONTENT / conf["dir"], module, "outputs", items[name], conf))
        check(pages)
        every.extend(pages)
        if lang == langs[0]:
            out["robots.txt"] = robots(CFG["robots"], f"{apex()}/sitemap.xml")
            out["txt/robots.txt"] = robots(CFG["robots_man"])  # txt/ is the root of the plain-text host
            out["site.webmanifest"] = manifest()
    languages.use(langs[0])
    indexed = [it for it in every if "noindex" not in it["meta"].get("robots", "")]
    out["sitemap.xml"] = sitemap_xml(indexed)
    out["sitemap.txt"] = "".join(f"{apex()}{clean_url(it['path'], it['lang'])}\n" for it in
                                 sorted(indexed, key=lambda it: clean_url(it["path"], it["lang"])))
    out = {k: v.encode("utf-8") for k, v in out.items()}
    # Files next to the pages (images of a post or an event...) are copied
    # as they are, at the same path. Markdown and site.toml are not.
    for f in sorted(CONTENT.rglob("*")):
        rel = f.relative_to(CONTENT)
        if f.is_file() and f.suffix != ".md" and f != CONFIG \
                and not any(part.startswith("_") for part in rel.parts):
            out[str(rel)] = f.read_bytes()
    # The theme, then the project's assets/, which win over it by name.
    # config.UNSERVED and UNSERVED_DIRS name the files the build reads and never serves.
    for base in (THEME, ASSETS):
        for f in sorted(base.rglob("*")) if base.is_dir() else []:
            rel = str(f.relative_to(base))
            if f.is_file() and served(rel):
                out[rel] = f.read_bytes()
    out.update(generated())  # icons and share.png, from assets/logo.svg
    for f in EXTRA:
        out[f.name] = f.read_bytes()
    return out


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
    if "--version" in args:
        print(os.environ.get("TILDER_VERSION", "dev"))
        return 0
    report.DEBUG = "--debug" in args
    if "--out" in args:
        dest = pathlib.Path(args[args.index("--out") + 1]).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    if "--watch" in args:
        interval = float(os.environ.get("BUILD_INTERVAL", "1"))
        own_code = lambda: {k: v for k, v in snapshot().items()
                            if k.startswith(watch_module.CODE)}
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
                      "(a change in builder/ or theme/types/ restarts)", flush=True)
                time.sleep(interval * 5)
                if own_code() != code:
                    print("builder/ or theme/types/ changed, restarting", flush=True)
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
