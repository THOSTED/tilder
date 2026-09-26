"""HTML output: blocks, then the whole page inside assets/layout.html."""

import html as H
import os
import re
import struct
import sys

import highlight
import inline
import languages
from config import CFG, CONTENT, STATE, apex, layout, theme_file
from paths import clean_url, relative
from images import image_size
from markdown import front_matter
from report import error
from seo import head_tags, is_landing, page_heading, page_title

def html_meta(items, entry_cls):
    out = []
    for item in items:
        if item.startswith("`") and item.endswith("`"):
            t = item[1:-1]
            cls = "tag tag--next" if "next" in entry_cls else (
                "tag tag--full" if "full" in entry_cls else "tag")
            out.append(f'<span class="{cls}">{H.escape(t)}</span>')
        elif " | " in item:
            iso, human = item.split(" | ", 1)
            out.append(f'<span><time datetime="{H.escape(iso)}">'
                       f"{H.escape(human)}</time></span>")
        else:
            out.append(f"<span>{H.escape(item)}</span>")
    return "".join(out)


def html_list(b, res, ind):
    tag = "ol" if b["ordered"] else "ul"
    attrs = f' start="{b["start"]}"' if b["ordered"] and b["start"] != 1 else ""
    if any(i["task"] is not None for i in b["items"]):
        attrs += ' class="tasks"'
    out = [f"{ind}<{tag}{attrs}>"]
    for i in b["items"]:
        body = inline.to_html(i["text"], res)
        if i["task"] is not None:
            state = "done" if i["task"] else "todo"
            label = H.escape(CFG["labels"][f"task_{state}"])
            body = (f'<span class="task task--{state}" role="img" aria-label="{label}">'
                    f"</span>{body}")
        if i["children"]:
            out.append(f"{ind}\t<li>{body}")
            for child in i["children"]:
                out.extend(html_list(child, res, ind + "\t\t"))
            out.append(f"{ind}\t</li>")
        else:
            out.append(f"{ind}\t<li>{body}</li>")
    out.append(f"{ind}</{tag}>")
    return out


def icon(name):
    """An inline SVG logo from the theme's icons/<name>.svg, drawn in the
    text colour (currentColor), hidden from screen readers. None if the
    theme has no such icon."""
    path = theme_file(f"icons/{name}.svg")
    if not path.is_file():
        return None
    svg = path.read_text()
    box = re.search(r'viewBox="([^"]+)"', svg).group(1)
    d = "".join(f'<path d="{H.escape(m)}"/>' for m in re.findall(r'<path[^>]*\sd="([^"]+)"', svg))
    return (f'<svg class="icon" viewBox="{box}" aria-hidden="true" focusable="false">'
            f"{d}</svg>")


def html_toc(b, ind):
    """[TOC]: the page's sections, linked, in a <nav> named for screen
    readers, folded in a <details>: closed by default, opened without any
    script, from the keyboard too. Sections shown only in the text mirror
    are left out."""
    label = H.escape(CFG["labels"]["toc"])
    out = [f'{ind}<nav class="toc" aria-label="{label}">', f"{ind}\t<details>",
           f'{ind}\t\t<summary class="toc-label">{label}</summary>', f"{ind}\t\t<ol>"]
    for s in b["sections"]:
        if "text" not in s["cls"]:
            out.append(f'{ind}\t\t\t<li><a href="#{s["id"]}">{H.escape(s["title"])}</a></li>')
    out += [f"{ind}\t\t</ol>", f"{ind}\t</details>", f"{ind}</nav>"]
    return out


def html_profiles(b):
    """A row of profile links: the network's logo, its name for screen
    readers. rel="me" lets Mastodon and others verify the link."""
    links = []
    for key, label, url in b["items"]:
        mark = icon(key)
        inner = (f'{mark}<span class="sr-only">{H.escape(label)}</span>' if mark
                 else inline.arrow(H.escape(label + " \u2197")))
        target = ' target="_blank"' if inline.opens_new_tab(url) else ""
        if inline.opens_new_tab(url) and inline.NEW_TAB_LABEL:
            inner += f'<span class="sr-only"> ({H.escape(inline.NEW_TAB_LABEL)})</span>'
        links.append(f'<a href="{H.escape(url)}" rel="me noopener"{target} '
                     f'title="{H.escape(label)}">{inner}</a>')
    return f'<p class="profiles">{" ".join(links)}</p>'


def html_code(b):
    """A code block, highlighted when its language is known. The language
    label is a data attribute, shown by CSS."""
    code = "\n".join(b["lines"])
    lang = b["lang"]
    body = highlight.highlight(code, lang) if lang else None
    if lang and body is None:
        print(f"warning: unknown code language {lang!r}, left plain", file=sys.stderr)
    if body is None:
        return f'<pre class="code" tabindex="0"><code>{H.escape(code, quote=False)}</code></pre>'
    # The label is the language as written ("caddy", not the internal "conf").
    label = re.sub(r"[^a-z0-9+#-]", "", lang.lower())
    return (f'<pre class="code" data-lang="{label}" tabindex="0"><code class="language-{label}">'
            f"{body}</code></pre>")


def html_image(b, res):
    src = b["src"]
    size = "" if src.startswith("http") else "".join(
        f' width="{w}" height="{h}"' for w, h in [image_size(CONTENT / src) or (0, 0)] if w)
    url = src if src.startswith("http") else res("/" + src)
    caption = (f"<figcaption>{inline.to_html(b['caption'], res)}</figcaption>"
               if b["caption"] else "")
    return (f'<figure class="figure"><img src="{H.escape(url)}" alt="{H.escape(b["alt"])}"'
            f'{size} loading="lazy" decoding="async">{caption}</figure>')


def html_table(b, res, ind):
    """Wrapped so a wide table scrolls on its own instead of the page."""
    label = H.escape(CFG["labels"]["table"])
    out = [f'{ind}<div class="table" tabindex="0" role="region" aria-label="{label}"><table>',
           f"{ind}\t<thead><tr>"]
    for c, a in zip(b["head"], b["align"]):
        style = f' class="{a}"' if a != "left" else ""
        out.append(f'{ind}\t\t<th scope="col"{style}>{inline.to_html(c, res)}</th>')
    out.append(f"{ind}\t</tr></thead>")
    out.append(f"{ind}\t<tbody>")
    for row in b["rows"]:
        tds = "".join(f'<td{f" class=\"{a}\"" if a != "left" else ""}>'
                      f"{inline.to_html(c, res)}</td>" for c, a in zip(row, b["align"]))
        out.append(f"{ind}\t\t<tr>{tds}</tr>")
    out.append(f"{ind}\t</tbody>")
    out.append(f"{ind}</table></div>")
    return out


def html_blocks(blocks, res, entry_cls=(), ind="\t\t"):
    out = []
    for b in blocks:
        if b["k"] == "para":
            cls = f' class="{" ".join(b["cls"])}"' if b["cls"] else ""
            out.append(f"{ind}<p{cls}>{inline.to_html(b['text'], res)}</p>")
        elif b["k"] == "empty":
            out.append(f'{ind}<p class="empty">{inline.to_html(b["text"], res)}</p>')
        elif b["k"] == "list":
            out.extend(html_list(b, res, ind))
        elif b["k"] == "rule":
            out.append(f"{ind}<hr>")
        elif b["k"] == "code":
            out.append(html_code(b))
        elif b["k"] == "inset":
            paras = "".join(f"<p>{inline.to_html(t, res)}</p>" for t in b["paras"])
            if b["kind"]:
                label = H.escape(CFG["labels"][b["kind"]])
                role = "note"  # static content: "alert" is for live changes
                out.append(f'{ind}<div class="callout callout--{b["kind"]}" role="{role}">'
                           f'<p class="callout-label">{label}</p>{paras}</div>')
            else:
                out.append(f'{ind}<div class="inset">{paras}</div>')
        elif b["k"] == "table":
            out.extend(html_table(b, res, ind))
        elif b["k"] == "image":
            out.append(ind + html_image(b, res))
        elif b["k"] == "toc":
            out.extend(html_toc(b, ind))
        elif b["k"] == "profiles":
            out.append(ind + html_profiles(b))
        elif b["k"] == "comment":
            out.extend(ind + l.strip() for l in b["lines"])
        elif b["k"] == "entry":
            cls = "entry" + "".join(f" entry--{c}" for c in b["cls"])
            data = "".join(f' data-{k}="{H.escape(v)}"'
                           for k, v in b.get("data", {}).items())
            out.append(f'{ind}<div class="{cls}"{data}>')
            if not b.get("own"):  # on its own page, the <h1> is the title
                out.append(f"{ind}\t<h3>{inline.to_html(b['title'], res)}</h3>")
            if b["meta"]:
                out.append(f'{ind}\t<p class="meta">'
                           f'{html_meta(b["meta"], b["cls"])}</p>')
            out.extend(html_blocks(b["blocks"], res, b["cls"], ind + "\t"))
            out.append(f"{ind}</div>")
    return out


PLACEHOLDER = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def fill(template, computed, meta, path):
    """Replace {{ name }} in the layout. `computed` values are HTML built
    here and go in as-is; `page.*` (front matter) and `section.key` (from
    site.toml) are escaped. An unknown name stops the build; `path` names
    the layout file in that error."""
    def value(m):
        name = m.group(1)
        if name in computed:
            return computed[name]
        if name.startswith("page."):
            return H.escape(meta.get(name[5:], ""))
        node = CFG
        for part in name.split("."):
            if not isinstance(node, dict) or part not in node:
                raise error(path, f"unknown placeholder {{{{ {name} }}}}",
                            "The placeholders are listed in docs/theme.md")
            node = node[part]
        return H.escape(str(node))
    return PLACEHOLDER.sub(value, template)


def has_code(nodes):
    return any(n["k"] == "code" or has_code(n.get("blocks", [])) for n in nodes)


def switcher(item, res):
    """{{ languages }}: every declared language, linking to this page's
    sibling; the current one marked. Empty in a monolingual site."""
    if not languages.multilingual():
        return ""
    names = languages.CONFIGS[languages.default()].get("languages", {})
    links = []
    for L in languages.declared():
        current = ' aria-current="page"' if L == STATE["lang"] else ""
        href = res("/" + clean_url(item["path"], L).lstrip("/"))
        links.append(f'\t<a href="{href}" hreflang="{L}" lang="{L}"{current}>{H.escape(names.get(L, L))}</a>')
    label = H.escape(CFG["labels"]["languages"])
    return f'<nav class="languages" aria-label="{label}">\n' + "\n".join(links) + "\n</nav>"


def render_html(item, sections, preamble=(), colls=None):
    meta, path, module = item["meta"], item["path"], item["type"]
    d = os.path.dirname(path)
    res = lambda u: relative(d, u)

    nav = []
    for n in CFG["nav"]:
        current = ' aria-current="page"' if meta.get("nav", "") == n["href"] else ""
        href = n["href"]
        nav.append(f'\t<a href="{res(href)}"{current}{inline.link_attrs(href)}>'
                   f'{inline.arrow(H.escape(n["label"]), inline.opens_new_tab(href))}</a>')
    navhtml = '<span class="sep" aria-hidden="true">·</span>\n'.join(nav)

    feeds = ""
    # `feed:` names a collection, or `all`: its RSS in <link rel="alternate">.
    # A feed is the one file written under the language's prefix: its link
    # stays in the language (page=True).
    for name, c in (colls or {}).items():
        if c.get("feed") and meta.get("feed", "") in (name, "all"):
            title = H.escape(c["feed_title"])
            feeds += (f'\n<link rel="alternate" type="application/rss+xml" '
                      f'title="{title}" href="{relative(d, c["feed"], page=True)}">')

    # Scripts, each loaded where it serves and only if the theme ships the
    # file: the ones the listed types name, then code.js on pages with
    # code. The page is complete without them (AGENTS.md §6).
    named = []
    for s in sections:
        sc = s.get("script")
        if sc and sc not in named and theme_file(sc).is_file():
            named.append(sc)
    script = "".join(f'<script src="{res("/" + sc)}" defer></script>\n' for sc in named)
    if has_code(list(preamble) + sections) and theme_file("code.js").is_file():
        labels = CFG["labels"]
        script += (f'<script src="{res("/code.js")}" defer'
                   f' data-copy="{H.escape(labels["copy"])}"'
                   f' data-copied="{H.escape(labels["copied"])}"></script>\n')

    body = html_blocks(list(preamble), res, ind="")
    for s in sections:
        if "text" in s["cls"]:
            continue
        ident = f' id="{s["id"]}"' if s["id"] else ""
        # A marker naming a collection ({upcoming:meetups}) is a class without
        # its name.
        extra = [c.partition(":")[0] for c in s["cls"] if c not in ("html", "text")]
        bcls = " ".join(["b"] + extra)
        data = "".join(f' data-{k}="{H.escape(str(v))}"' for k, v in s.get("data", {}).items())
        body.append(f'<section class="s"{ident}>')
        body.append(f"\t<h2>{H.escape(s['title'])}</h2>")
        body.append(f'\t<div class="{bcls}"{data}>')
        body.extend(html_blocks(s["blocks"], res))
        body.append("\t</div>")
        body.append("</section>\n")

    # The <h1> is the wordmark, as a path: ~/<site> on the landing page,
    # ~/<site>/<title> elsewhere, the site's name linking to the site root.
    # Screen readers hear "<site>, <title>": the ~/ and the / are decoration.
    name = H.escape(CFG["site"]["name"])
    cursor = '<span class="cursor" aria-hidden="true"></span>'
    tilde = '<span class="tilde" aria-hidden="true">~/</span>'
    slash = '<span class="slash" aria-hidden="true">/</span><span class="sr-only">, </span>'
    if is_landing(meta):
        brand = f'<h1 class="wordmark">{tilde}{name}{cursor}</h1>'
    else:
        # Each folder of the page's URL is a segment too, linking to its
        # index: ~/<site>/blog/<title>, ~/<site>/events/<title>.
        parents = ""
        if STATE["prefix"]:
            parents += f'{slash}<a href="{res("")}">{H.escape(STATE["lang"])}</a>'
        # A folder's own page (blog/index.html) is that folder: not a parent.
        folders = d.split("/") if d else []
        if path.endswith("/index.html"):
            folders = folders[:-1]
        table = STATE["pages"] or languages.pages()
        for i, part in enumerate(folders):
            target = "/".join(d.split("/")[:i + 1])
            # The folder's index in any language makes the link blog/;
            # else the page beside the folder, if any: blog.
            candidates = table.get(target + "/index.md")
            index = target + "/" if candidates else target
            # The segment is named like the page it links to, in the language
            # of the pass, so the path reads the same everywhere: that page's
            # `name:`, else its title (what its own <h1> shows), else the
            # folder's name.
            src, _ = languages.pick(candidates or table.get(target + ".md") or {}, STATE["lang"])
            parent = front_matter(src.read_text())[0] if src else {}
            shown = page_heading(parent) if parent.get("title") else None
            parents += f'{slash}<a href="{res(index)}">{H.escape(shown or part)}</a>'
        # The site's name links to the site root; the language's segment to
        # the language's landing page.
        brand = (f'<h1 class="wordmark"><a href="{res("/")}">{tilde}{name}</a>{parents}'
                 f'{slash}<span class="here">{H.escape(page_heading(meta))}</span>{cursor}</h1>')

    if meta.get("layout"):
        lay_path, template = layout(meta["layout"], asked_by=item["src"])
    else:
        lay_path, template = layout(module.LAYOUT)
    return fill(template, {
        "title": H.escape(page_title(meta)),
        "type": module.NAME,
        "root": res("/"),   # the site root: style.css, icons, the manifest
        "home": res(""),    # the language's landing page
        "canonical": apex() + clean_url(path),
        "feeds": feeds,
        "head": head_tags(item),
        "brand": brand,
        "nav": navhtml,
        "languages": switcher(item, res),
        "content_lang": STATE["content_lang"],
        # Posts and events are articles: Reader mode and read-aloud tools
        # look for one.
        "body": ("<article>\n" + "\n".join(body) + "</article>\n"
                 if module.ARTICLE else "\n".join(body)),
        "script": script,
    }, meta, lay_path)
