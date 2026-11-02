"""Multi-language: language file completeness, switching, fallback, extension. Pure Python, no Textual needed."""

import ast
import importlib.util
import json
import os
import string
import tempfile
import unittest
from pathlib import Path

from tui import i18n
from tui.editor import model as M
from tui.editor import narrow as N
from tui.schema import SCHEMA

ROOT = Path(__file__).resolve().parent.parent / "tui"
LANGS = ("zh_TW", "ja")
# proper nouns: spelled the same in every language, no language file entry needed
SAME_EVERYWHERE = {
    "Production ID",
    "Production ID…",
    "production ID",
    "Language / 言語 / 語言",
}


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def load(code: str) -> dict:
    return json.loads((i18n.LOCALE_DIR / f"{code}.json").read_text(encoding="utf-8"))


class Base(unittest.TestCase):
    def setUp(self):
        self._saved = (
            i18n.language(),
            i18n.LOCALE_DIR,
            dict(i18n._cache),
            os.environ.get(i18n.ENV_VAR),
        )
        i18n.set_language("en")

    def tearDown(self):
        lang, directory, cache, env = self._saved
        i18n.LOCALE_DIR = directory
        i18n._cache.clear()
        i18n._cache.update(cache)
        i18n.set_language(lang)
        if env is None:
            os.environ.pop(i18n.ENV_VAR, None)
        else:
            os.environ[i18n.ENV_VAR] = env


class Core(Base):
    def test_available_languages(self):
        codes = [c for c, _ in i18n.available()]
        self.assertEqual(codes[0], "en")
        self.assertTrue({"en", "zh_TW", "ja"} <= set(codes))
        names = dict(i18n.available())
        self.assertEqual(names["ja"], "日本語")
        self.assertEqual(names["zh_TW"], "繁體中文")

    def test_default_is_english(self):
        self.assertEqual(i18n.language(), "en")
        self.assertEqual(SCHEMA["combat.enabled"].label, "Enable combat")
        self.assertEqual(i18n.t("{n} selected", n=3), "3 selected")

    def test_normalize_aliases(self):
        for raw, want in [
            ("zh-TW", "zh_TW"),
            ("zh_tw", "zh_TW"),
            ("zh", "zh_TW"),
            ("ja_JP", "ja"),
            ("JA", "ja"),
            ("en_US.UTF-8", "en"),
            ("en", "en"),
        ]:
            self.assertEqual(i18n.normalize(raw), want, raw)
        for bad in (None, "", "xx", 5):
            self.assertIsNone(i18n.normalize(bad))

    def test_unknown_language_keeps_current(self):
        i18n.set_language("ja")
        self.assertFalse(i18n.set_language("klingon"))
        self.assertEqual(i18n.language(), "ja")

    def test_missing_translation_falls_back_to_english(self):
        i18n.set_language("ja")
        self.assertEqual(
            i18n.t("never translated sentence"), "never translated sentence"
        )
        self.assertEqual(i18n.t("never {x}", x=1), "never 1")

    def test_broken_placeholder_in_translation_does_not_crash(self):
        i18n._cache["zz"] = {"messages": {"{n} selected": "{oops} chosen"}}
        i18n._current = "zz"
        try:
            self.assertEqual(i18n.t("{n} selected", n=3), "3 selected")
        finally:
            i18n._current = "en"

    def test_switching_changes_field_text_and_error_messages(self):
        f = SCHEMA["combat.sortie_map"]
        en = (f.label, f.help, f.validate(5)[0])
        i18n.set_language("zh_TW")
        self.assertEqual(f.label, "出擊海域")
        self.assertNotEqual((f.label, f.help, f.validate(5)[0]), en)
        i18n.set_language("ja")
        self.assertEqual(f.label, "出撃海域")
        self.assertEqual(f.validate(5), ["文字列である必要があります"])
        i18n.set_language("en")
        self.assertEqual((f.label, f.help, f.validate(5)[0]), en)

    def test_ship_codes_stay_english_names_are_translated(self):
        self.assertEqual(M.SHIP_TYPE_CODES[:3], ("DE", "DD", "CL"))
        i18n.set_language("ja")
        self.assertEqual(i18n.t("Destroyer"), "駆逐艦")
        self.assertEqual(
            M.SHIP_TYPE_CODES[:3], ("DE", "DD", "CL")
        )  # codes are not translated

    def test_group_titles_are_translated(self):
        self.assertEqual(M.group_title("routing"), "Routing")
        i18n.set_language("zh_TW")
        self.assertEqual(M.group_title("routing"), "路線")

    def test_search_matches_english_and_current_language(self):
        i18n.set_language("zh_TW")
        self.assertIn("combat.retreat_limit", [f.key for f in M.search_fields("撤退")])
        self.assertIn(
            "combat.retreat_limit", [f.key for f in M.search_fields("retreat")]
        )

    def test_list_item_error_prefix_works_in_every_language(self):
        f = SCHEMA["combat.retreat_points"]
        for lang in ("en", "zh_TW", "ja"):
            i18n.set_language(lang)
            self.assertIsNone(M.list_item_error(f, ["A"], "B"), lang)
            self.assertIsNotNone(M.list_item_error(f, ["A"], "bad node!"), lang)


class Completeness(Base):
    def test_every_field_has_label_and_help_in_every_language(self):
        for code in LANGS:
            fields = load(code)["fields"]
            self.assertEqual(set(fields), set(SCHEMA), code)
            for key, entry in fields.items():
                self.assertTrue(entry.get("label"), (code, key))
                self.assertTrue(entry.get("help"), (code, key))

    def test_field_placeholders_are_not_used(self):
        for code in LANGS:
            for key, entry in load(code)["fields"].items():
                self.assertFalse(
                    placeholders(entry["label"]) | placeholders(entry["help"]),
                    (code, key),
                )

    def _source_keys(self) -> set[str]:
        """Strings written directly in t("…") calls in the code, plus constants translated indirectly through variables."""
        used: set[str] = set()
        for path in ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "t"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    used.add(node.args[0].value)
                # class / module constants: HINT*, _KIND_HELP
                if isinstance(node, ast.Assign) and isinstance(
                    node.targets[0], ast.Name
                ):
                    name = node.targets[0].id
                    if name.startswith("HINT") and path.name == "dialogs.py":
                        used.add(ast.literal_eval(node.value))
                    if name == "_KIND_HELP":
                        used.update(ast.literal_eval(node.value).values())
        used.update(name for _, name in M.SHIP_TYPES)
        used.update(M.GROUP_TITLES.values())
        used.update(M._CATEGORY.values())
        used.update(M._PERIOD.values())
        used.update(desc for _, desc in (*N.EDITOR_HINTS, *N.EDIT_HINTS))
        used.update(spec.note for spec in M.TABLES.values() if spec.note)
        used.update({"error", "warning", "danger"})
        used.update(f.pattern_hint for f in SCHEMA.values() if f.pattern_hint)
        used.update(
            {"Node names: letters, digits and underscores only", "format mismatch"}
        )
        return used

    def test_every_translatable_string_exists_in_every_language(self):
        keys = self._source_keys()
        self.assertGreater(len(keys), 100)
        for code in LANGS:
            messages = load(code)["messages"]
            missing = sorted(
                k for k in keys if k not in messages and k not in SAME_EVERYWHERE
            )
            self.assertEqual(missing, [], code)

    def test_placeholders_match_the_english_source(self):
        for code in LANGS:
            for source, translated in load(code)["messages"].items():
                self.assertEqual(
                    placeholders(source), placeholders(translated), (code, source)
                )

    def test_translations_are_not_empty_and_actually_translated(self):
        for code in LANGS:
            messages = load(code)["messages"]
            self.assertTrue(
                all(isinstance(v, str) and v for v in messages.values()), code
            )
            # the vast majority of strings differ from the English source (only proper nouns such as Production ID may be the same)
            same = [k for k, v in messages.items() if k == v]
            self.assertLess(len(same), 8, (code, same))

    def test_english_file_has_no_overrides_needed(self):
        data = load("en")
        self.assertEqual(data.get("messages"), {})
        self.assertEqual(data.get("fields"), {})

    @unittest.skipUnless(
        importlib.util.find_spec("rich"),
        "needs rich (available when Textual is installed)",
    )
    def test_dashboard_stays_english(self):
        from tui.widgets import bars

        i18n.set_language("ja")
        text = bars.hint_text().plain
        self.assertIn("quit", text)
        self.assertIn("save", text)


class Preferences(Base):
    def test_pref_roundtrip_and_precedence(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(i18n.load_pref(root))
            self.assertTrue(i18n.save_pref("ja", root))
            self.assertEqual(i18n.load_pref(root), "ja")
            os.environ.pop(i18n.ENV_VAR, None)
            self.assertEqual(i18n.init(None, root), "ja")  # preference file
            os.environ[i18n.ENV_VAR] = "zh-TW"
            self.assertEqual(
                i18n.init(None, root), "zh_TW"
            )  # the environment variable takes priority over the preference file
            self.assertEqual(
                i18n.init("en", root), "en"
            )  # --lang has the highest priority
            os.environ.pop(i18n.ENV_VAR)
            i18n.save_pref("xx", root)  # a bad value is ignored
            self.assertEqual(i18n.init(None, root), "en")

    def test_pref_keeps_other_keys_and_survives_broken_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / i18n.PREF_FILE
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"other": 1}), encoding="utf-8")
            i18n.save_pref("ja", root)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")), {"other": 1, "lang": "ja"}
            )
            path.write_text("{broken", encoding="utf-8")
            self.assertIsNone(i18n.load_pref(root))
            self.assertTrue(i18n.save_pref("zh_TW", root))
            self.assertEqual(i18n.load_pref(root), "zh_TW")


class Extensibility(Base):
    def test_dropping_a_json_file_adds_a_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "ko.json").write_text(
                json.dumps(
                    {
                        "_name": "한국어",
                        "fields": {
                            "combat.enabled": {"label": "출격 활성화", "help": "x"}
                        },
                        "messages": {"{n} selected": "{n}개 선택됨"},
                    }
                ),
                encoding="utf-8",
            )
            Path(tmp, "en.json").write_text(
                json.dumps({"_name": "English"}), encoding="utf-8"
            )
            i18n.LOCALE_DIR = Path(tmp)
            i18n._cache.clear()
            self.assertEqual(dict(i18n.available()), {"en": "English", "ko": "한국어"})
            self.assertTrue(i18n.set_language("ko"))
            self.assertEqual(SCHEMA["combat.enabled"].label, "출격 활성화")
            self.assertEqual(
                SCHEMA["combat.fleet_mode"].label, "Fleet mode"
            )  # the untranslated part uses English
            self.assertEqual(i18n.t("{n} selected", n=2), "2개 선택됨")
            self.assertEqual(i18n.t("untranslated"), "untranslated")

    def test_locale_dir_is_packaged_next_to_the_code(self):
        self.assertTrue((i18n.LOCALE_DIR / "en.json").is_file())
        self.assertTrue((i18n.LOCALE_DIR / "zh_TW.json").is_file())
        self.assertTrue((i18n.LOCALE_DIR / "ja.json").is_file())


if __name__ == "__main__":
    unittest.main()
