import contextlib
import io
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests import helpers  # noqa: F401 - sys.path and SITE_ROOT
import languages
import report
from config import BUILDER, CFG, CONTENT, STATE, load_config


class Split(unittest.TestCase):
    def test_suffix(self):
        self.assertEqual(languages.split("about.en"), ("about", "en"))
        self.assertEqual(languages.split("about"), ("about", None))
        self.assertEqual(languages.split("index.pt-br"), ("index", "pt-br"))
        self.assertEqual(languages.split("2026-01-01-hello.fr"), ("2026-01-01-hello", "fr"))
        self.assertEqual(languages.split("v1.2"), ("v1.2", None))          # not a language code
        self.assertEqual(languages.split("notes.final"), ("notes.final", None))


class Setup(unittest.TestCase):
    def setUp(self):
        languages.setup()

    def test_declared_and_default(self):
        self.assertEqual(languages.default(), "en")
        self.assertEqual(languages.declared(), ["en", "fr"])
        self.assertTrue(languages.multilingual())
        self.assertEqual(languages.prefix("en"), "")
        self.assertEqual(languages.prefix("fr"), "fr/")
        self.assertEqual(STATE["lang"], "en")
        self.assertEqual(STATE["prefix"], "")

    def test_configs_per_language(self):
        self.assertEqual(languages.CONFIGS["en"]["site"]["lang"], "en")
        self.assertEqual(languages.CONFIGS["fr"]["site"]["lang"], "fr")
        self.assertEqual(languages.CONFIGS["fr"]["site"]["locale"], "fr_FR")
        self.assertEqual(languages.CONFIGS["fr"]["labels"]["skip"], "aller au contenu")
        self.assertEqual(languages.CONFIGS["fr"]["labels"]["copy"], "copy")        # not translated: inherited
        self.assertEqual(languages.CONFIGS["fr"]["nav"][0]["label"], "accueil")
        self.assertEqual(languages.CONFIGS["fr"]["dates"]["first"], "1er")
        self.assertEqual(languages.CONFIGS["fr"]["collections"]["events"]["upcoming_tag"], "à venir")
        self.assertEqual(languages.CONFIGS["en"]["labels"]["languages"], "Languages")
        self.assertEqual(languages.CONFIGS["fr"]["labels"]["languages"], "Langues")
        self.assertEqual(CFG["site"]["lang"], "en")   # setup leaves the default loaded

    def test_use_switches_the_configuration(self):
        languages.use("fr")
        try:
            self.assertEqual(CFG["site"]["lang"], "fr")
            self.assertEqual(STATE["lang"], "fr")
            self.assertEqual(STATE["prefix"], "fr/")
            self.assertEqual(CFG["site"]["name"], "test site")   # not overridden: inherited
        finally:
            languages.use("en")
        self.assertEqual(STATE["prefix"], "")

    def test_pick_follows_the_fallback_order(self):
        a, b, c, d = (pathlib.Path(x) for x in ("p.fr.md", "p.en.md", "p.md", "p.de.md"))
        self.assertEqual(languages.pick({"fr": a, "en": b, None: c}, "fr"), (a, "fr"))
        self.assertEqual(languages.pick({"en": b, None: c}, "fr"), (b, "en"))
        self.assertEqual(languages.pick({None: c}, "fr"), (c, "en"))            # no suffix: the default's content
        self.assertEqual(languages.pick({"fr": a}, "en"), (a, "fr"))            # only another language has it
        self.assertEqual(languages.pick({}, "en"), (None, None))


def scratch():
    """A copy of the fixture site in a temp dir; (tmp, site) paths."""
    tmp = tempfile.mkdtemp()
    site = pathlib.Path(tmp) / "site"
    shutil.copytree(pathlib.Path(CONTENT).parent, site)
    return tmp, site


def run(site, *args):
    r = subprocess.run([sys.executable, str(BUILDER / "build.py"), "--root", str(site),
                        "--out", str(site / "out"), *args], capture_output=True, text=True,
                       env={"SITE_ROOT": str(site), "BUILD_TODAY": "2026-06-15", "PATH": "/usr/bin:/bin"})
    return r.returncode, r.stderr


class ConfigErrors(unittest.TestCase):
    def setUp(self):
        self.tmp, self.site = scratch()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_undeclared_language_file(self):
        (self.site / "content" / "site.de.toml").write_text('[site]\nlang = "de"\n')
        code, err = run(self.site)
        self.assertEqual(code, 1)
        self.assertIn('error: content/site.de.toml: "de" is not a declared language. '
                      "Declared: en, fr ([site] languages in content/site.toml)", err)

    def test_default_missing_from_languages(self):
        toml = self.site / "content" / "site.toml"
        toml.write_text(toml.read_text().replace('languages = ["en", "fr"]', 'languages = ["fr"]'))
        code, err = run(self.site)
        self.assertEqual(code, 1)
        self.assertIn('error: content/site.toml: [site] languages does not contain the default language "en". '
                      "Add it, or change [site] lang", err)

    def test_language_file_with_another_lang(self):
        fr = self.site / "content" / "site.fr.toml"
        fr.write_text(fr.read_text().replace('lang = "fr"', 'lang = "de"'))
        code, err = run(self.site)
        self.assertEqual(code, 1)
        self.assertIn('error: content/site.fr.toml: [site] lang is "de", not "fr". '
                      "A language's file sets its own lang, or leaves it out", err)

    def test_errors_are_gathered(self):
        (self.site / "content" / "site.de.toml").write_text("")
        fr = self.site / "content" / "site.fr.toml"
        fr.write_text(fr.read_text().replace('lang = "fr"', 'lang = "de"'))
        code, err = run(self.site)
        self.assertEqual(code, 1)
        self.assertEqual(err.count("error: "), 2)

    def test_undeclared_suffix_on_a_page(self):
        (self.site / "content" / "about.de.md").write_text("---\nman: T(1)\ntitle: x\ndescription: d\ntagline: t\nnav: -\n---\n\n## Name\n\nx\n")
        (self.site / "content" / "blog" / "2026-03-01-x.es.md").write_text("---\ntitle: x\ndescription: d\n---\n\n## Name\n\nx\n")
        code, err = run(self.site)
        self.assertEqual(code, 1)
        self.assertIn('error: content/about.de.md: "de" is not a declared language. Declared: en, fr', err)
        self.assertIn('error: content/blog/2026-03-01-x.es.md: "es" is not a declared language', err)
        self.assertEqual(err.count("error: "), 2)

    def test_a_dotted_name_that_is_not_a_language_is_a_page(self):
        (self.site / "content" / "v1.2.md").write_text("---\nman: T(1)\ntitle: v1.2\ndescription: A page whose name has a dot but no language suffix in it.\ntagline: t\nnav: -\n---\n\n## Name\n\nx\n")
        code, err = run(self.site)
        self.assertEqual(code, 0, err)
        self.assertTrue((self.site / "out" / "v1.2.html").is_file())
