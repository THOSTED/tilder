# Collection navigation - design

Date: 2026-09-26. Status: approved in conversation, awaiting review of this
document. Implementation plan to follow. Asked for by a documentation
theme (the project's own website): a sidebar listing the pages of a
collection, previous/next links, and per-language files written by a type
(a search index).

---

## 1. Goal

Three optional, generic additions to the theme and type contracts:

1. `{{ collection_nav }}` - the items of the page's collection, in order,
   optionally grouped, the current one marked.
2. `{{ prev }}` and `{{ next }}` - the page's neighbours in that order.
3. `LOCALIZED_OUTPUTS` - a type attribute: `outputs()` runs once per
   language instead of once.

A theme that uses none of them, and a type that sets neither new
attribute, changes by not one byte: the reference site and the starter are
the regression test.

### Not in this work

- A search index, or any search: that is the theme's, through
  `LOCALIZED_OUTPUTS`.
- Nesting deeper than one level of groups.
- Navigation across collections.

---

## 2. Order and membership

- The order is the one lists already use: the type's `sort_key`, as
  `contenttypes.load_items` returns the items, per language (each language
  pass has its own items, fallback included).
- A page **belongs** to a collection when it is one of its items. The
  collection's own index page (`content/<dir>/index.md`, and its
  translations) is not an item but **shows** the collection's navigation,
  with no current item and no neighbours.
- Any other page: the three placeholders are empty strings.

## 3. Groups

An item may set `group:` in its front matter (a free label, in the page's
language). When at least one item of the collection has one:

- items are gathered by group, groups in the order of their first item;
- items without a group come first, ungrouped.

No item has one: a flat list.

## 4. `{{ collection_nav }}`

```html
<nav class="collection-nav" aria-label="In this section">
  <ul>
    <li><a href="../docs/getting-started">Getting started</a></li>
    <li class="collection-group"><span class="collection-group-label">Reference</span>
      <ul>
        <li><a href="../docs/markdown" aria-current="page">Markdown</a></li>
      </ul>
    </li>
  </ul>
</nav>
```

- The link text is the item's `title`; its `href` is relative, like `nav`.
- `aria-label` is `labels.collection_nav` (`defaults.toml`, default
  `"In this section"`); a collection may override it with its own
  `nav_label` key.
- The group label is not a heading: the page's outline stays the `<h1>`
  wordmark and the sections' `<h2>`.
- Titles and labels are HTML-escaped.

## 5. `{{ prev }}` and `{{ next }}`

```html
<a class="prev" rel="prev" href="../docs/project"><span class="prev-label">previous</span> Project layout</a>
<a class="next" rel="next" href="../docs/collections"><span class="next-label">next</span> Collections</a>
```

- Empty at either end of the order, on a collection's index page, and
  outside collections.
- Labels: `labels.prev` (`"previous"`), `labels.next` (`"next"`).
- The order ignores groups: the last item of one group is followed by the
  first of the next.

### In the text mirror

A type that sets `SEQUENTIAL = True` gets, in the text mirror only, a line
before the footer rule:

```
previous: Project layout                          next: Collections
```

folded to ASCII, 75 columns, the titles truncated with `...` when the two
do not fit; one side only at an end. The line is not linked (the mirror has
no links); the HTML placeholders do not depend on `SEQUENTIAL`. Without
`SEQUENTIAL` (every built-in type), the mirror is unchanged.

## 6. `LOCALIZED_OUTPUTS`

A type attribute, default `False`.

- `False`: `outputs(items, conf)` is called once, in the default language,
  as today.
- `True`: it is called in every language pass, with that language's items;
  every returned path is prefixed with the language's prefix (`""` for the
  default, `"fr/"`...). The type does not prefix itself.

`conf` in each pass is the collection's settings in that language, so a
type's words are translated as any other.

## 7. Contract updates

- `defaults.toml`: `labels.collection_nav`, `labels.prev`, `labels.next`,
  English and neutral, commented.
- `starter/content/site.fr.toml`: their French.
- `docs/theme.md`: the three placeholders (computed, not escaped by the
  layout), the classes `.collection-nav`, `.collection-group`,
  `.collection-group-label`, `.prev`, `.prev-label`, `.next`, `.next-label`.
- `docs/types.md`: `SEQUENTIAL`, `LOCALIZED_OUTPUTS`, `group:` and the
  collection key `nav_label`.
- `starter/theme/style.css` styles the new classes; the starter layout does
  not need to use them (the starter has only a blog), but
  `starter/theme/layout.html` places `{{ prev }}{{ next }}` after the body,
  so the blog shows them.

  *Consequence:* the starter's post pages gain previous/next links. The
  "not one byte" rule applies to a site whose theme does not use the
  placeholders.

## 8. Errors

No new error: a `group:` that is not a string is converted with `str()`.
An unknown placeholder already stops the build; these three are now known.

## 9. Tests

On the fixture site (`tests/`):

- order follows `sort_key`, per language, fallback items included;
- groups: first-appearance order, ungrouped first, flat when none;
- `aria-current` on the current item only; none on the index page;
- prev/next: both ends empty, the index page empty, a page outside
  collections empty, order across groups;
- labels from `labels.*` and the collection's `nav_label`, per language;
- `SEQUENTIAL`: the mirror line, truncation at 75 columns, ASCII fold, and
  no line for a type without it; `ansi/` stripped equals `txt/`;
- `LOCALIZED_OUTPUTS`: one call per language, paths prefixed; without it,
  one call, unprefixed (the calendar test stays green);
- a theme without the placeholders: output identical to before.

## 10. Release

A minor version: `v1.1.0`, the Docker image tagged by CI. The website pins
that tag.
