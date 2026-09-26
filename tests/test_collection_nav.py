import json
import pathlib
import shutil
import tempfile
import textwrap
import unittest

from tests.helpers import build_site, rebuild
import contenttypes
from config import CONTENT, load_config


class Flags(unittest.TestCase):
    def test_defaults_and_theme_values(self):
        load_config()
        types = contenttypes.load()
        for name in ("page", "post", "event", "member", "talk"):
            self.assertFalse(types[name].SEQUENTIAL, name)
            self.assertFalse(types[name].LOCALIZED_OUTPUTS, name)
        self.assertTrue(types["guide"].SEQUENTIAL)
        self.assertTrue(types["guide"].LOCALIZED_OUTPUTS)

    def test_flag_kind_is_checked(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            (tmp / "odd.py").write_text(textwrap.dedent('''
                NAME = "odd"
                SEQUENTIAL = "yes"
                def entry(item, link, conf):
                    return None
            '''))
            load_config()
            contenttypes.load([contenttypes.BUILTIN, tmp])
            messages = [str(e) for e in contenttypes.ERRORS]
        finally:
            shutil.rmtree(tmp)
        self.assertTrue(any("SEQUENTIAL must be a bool, not a str" in m for m in messages), messages)
        self.assertNotIn("odd", contenttypes.TYPES)


class LocalizedOutputs(unittest.TestCase):
    def test_one_file_per_language(self):
        out = build_site()
        self.assertEqual(json.loads(out["guides/index.json"]),
                         ["Introduction", "Setup", "Deployment", "Tuning"])
        self.assertEqual(json.loads(out["fr/guides/index.json"]),
                         ["Introduction", "Installation", "Deployment", "Tuning"])

    def test_other_outputs_stay_once(self):
        out = build_site()
        self.assertIn("events.ics", out)
        self.assertNotIn("fr/events.ics", out)


SETUP_NAV = "\n".join([
    '<nav class="collection-nav" aria-label="Guide contents">',
    "<ul>",
    '\t<li><a href="intro">Introduction</a></li>',
    '\t<li class="collection-group"><span class="collection-group-label">Basics</span>',
    "\t<ul>",
    '\t\t<li><a href="setup" aria-current="page">Setup</a></li>',
    '\t\t<li><a href="tuning">Tuning</a></li>',
    "\t</ul>",
    "\t</li>",
    '\t<li class="collection-group"><span class="collection-group-label">Advanced</span>',
    "\t<ul>",
    '\t\t<li><a href="deploy">Deployment</a></li>',
    "\t</ul>",
    "\t</li>",
    "</ul>",
    "</nav>"])


class Placeholders(unittest.TestCase):
    def test_sidebar_on_an_item(self):
        page = build_site()["guides/setup.html"]
        self.assertIn(SETUP_NAV, page)
        self.assertEqual(SETUP_NAV.count("aria-current"), 1)

    def test_neighbours_ignore_groups(self):
        out = build_site()
        deploy = out["guides/deploy.html"]
        self.assertIn('<a class="prev" rel="prev" href="setup"><span class="prev-label">previous</span> Setup</a>', deploy)
        self.assertIn('<a class="next" rel="next" href="tuning"><span class="next-label">next</span> Tuning</a>', deploy)
        self.assertNotIn('rel="prev"', out["guides/intro.html"])
        self.assertNotIn('rel="next"', out["guides/tuning.html"])

    def test_collection_page_shows_the_sidebar_only(self):
        index = build_site()["guides/index.html"]
        self.assertIn('<nav class="collection-nav" aria-label="Guide contents">', index)
        nav = index[index.index('<nav class="collection-nav"'):]
        nav = nav[:nav.index("</nav>")]
        self.assertNotIn("aria-current", nav)
        self.assertNotIn('rel="prev"', index)
        self.assertNotIn('rel="next"', index)

    def test_french_pass_uses_served_titles(self):
        deploy = build_site()["fr/guides/deploy.html"]
        self.assertIn('<nav class="collection-nav" aria-label="Sommaire du guide">', deploy)
        self.assertIn('<a href="setup">Installation</a>', deploy)
        self.assertIn('<a class="prev" rel="prev" href="setup"><span class="prev-label">précédent</span> Installation</a>', deploy)
        self.assertIn('<span class="next-label">suivant</span> Tuning</a>', deploy)

    def test_outside_collections_is_empty(self):
        page = CONTENT / "loose.md"
        page.write_text("---\nman: TEST(1)\ntitle: loose\ndescription: A page of the fixture outside every collection, with the guide layout.\n"
                        "tagline: t\nnav: -\nlayout: guide\n---\n\n## Name\n\nloose {mono}\n")
        try:
            out = rebuild()
        finally:
            page.unlink()
        self.assertIn('<body class="layout-guide page">', out["loose.html"])
        self.assertNotIn("collection-nav", out["loose.html"])
        self.assertNotIn('rel="prev"', out["loose.html"])

    def test_layouts_without_the_placeholders_are_unchanged(self):
        post = build_site()["blog/2026-01-01-hello.html"]
        self.assertNotIn("collection-nav", post)
        self.assertNotIn('rel="prev"', post)
        self.assertNotIn('rel="next"', post)
