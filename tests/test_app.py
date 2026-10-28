"""儀表板的 UI 測試(Textual pilot)。未安裝 Textual 時整組略過。

這組測試在開發沙盒中無法執行(沒有 Textual),請在實際環境跑:
    python -m unittest tests.test_app -v
"""
import json
import tempfile
import unittest
from pathlib import Path

try:
    import textual  # noqa: F401
except ImportError:  # pragma: no cover
    textual = None

from tui.modules import CARDS
from tui.store import ConfigStore

BIG = (120, 70)      # 夠高,所有方框都在畫面內


@unittest.skipIf(textual is None, "未安裝 textual")
class DashboardTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "configs" / "config_cui.json"
        self.store = ConfigStore(self.path)

    def tearDown(self):
        self._tmp.cleanup()

    def make_app(self):
        from tui.app import KcautoCui
        return KcautoCui(self.store)

    async def test_all_cards_exist_and_first_is_focused(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.pause()
            for spec in CARDS:
                app.query_one(f"#{spec.card_id}")
            self.assertEqual(app.focused.id, "card-combat")

    async def test_hotkeys_focus_each_card(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            for spec in CARDS:
                await pilot.press(spec.hotkey)
                self.assertEqual(app.focused.id, spec.card_id, spec.hotkey)

    async def test_arrow_keys_navigate_the_grid(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("right")
            self.assertEqual(app.focused.id, "card-expedition")
            await pilot.press("down")
            self.assertEqual(app.focused.id, "card-quest")
            await pilot.press("left")
            self.assertEqual(app.focused.id, "card-pvp")
            await pilot.press("up")
            self.assertEqual(app.focused.id, "card-combat")
            await pilot.press("up")           # 上緣:不動
            self.assertEqual(app.focused.id, "card-combat")

    async def test_space_toggles_enabled_and_dims_card(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("c")
            card = app.query_one("#card-combat")
            self.assertTrue(card.has_class("off"))          # 預設 combat.enabled=False
            await pilot.press("space")
            self.assertTrue(self.store.get("combat.enabled"))
            self.assertFalse(card.has_class("off"))
            await pilot.press("space")
            self.assertFalse(self.store.get("combat.enabled"))
            self.assertTrue(card.has_class("off"))

    async def test_space_on_general_does_nothing(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            before = self.store.as_dict()
            await pilot.press("g", "space")
            self.assertEqual(self.store.as_dict(), before)

    async def test_click_on_toggle_zone_toggles(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.pause()
            card = app.query_one("#card-pvp")
            await pilot.click("#card-pvp",
                              offset=(card.size.width - 4, card.size.height - 1))
            self.assertTrue(self.store.get("pvp.enabled"))

    async def test_click_on_body_focuses_without_toggling(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.pause()
            await pilot.click("#card-pvp", offset=(3, 1))
            self.assertEqual(app.focused.id, "card-pvp")
            self.assertFalse(self.store.get("pvp.enabled"))

    async def test_save_key_writes_file(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("c", "space", "w")
            await pilot.pause()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIs(data["combat.enabled"], True)

    async def test_save_blocked_by_errors(self):
        self.store.set("general.jst_offset", 99)
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("w")
            await pilot.pause()
        self.assertFalse(self.path.exists())

    async def test_quit_clean_does_not_prompt(self):
        from tui.app import ConfirmQuit
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("q")
            await pilot.pause()
            self.assertNotIsInstance(app.screen, ConfirmQuit)

    async def test_quit_dirty_prompts_and_cancel_returns(self):
        from tui.app import ConfirmQuit
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("c", "space", "q")
            await pilot.pause()
            self.assertIsInstance(app.screen, ConfirmQuit)
            await pilot.press("escape")
            await pilot.pause()
            self.assertNotIsInstance(app.screen, ConfirmQuit)
            self.assertTrue(self.store.get("combat.enabled"))   # 沒被丟掉

    async def test_modal_blocks_dashboard_keys(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("c", "space", "q")
            await pilot.pause()
            await pilot.press("e", "space")        # 對話框開著,不應生效
            self.assertTrue(self.store.get("combat.enabled"))
            self.assertIs(self.store.get("expedition.enabled"), True)  # 預設值,未被切換

    async def test_quit_dirty_discard_leaves_file_untouched(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("c", "space", "q")
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause()
        self.assertFalse(self.path.exists())

    # ------------------------------------------------------------------ #
    # 響應式版面
    # ------------------------------------------------------------------ #
    async def layout_of(self, size):
        app = self.make_app()
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            main = app.query_one("#main")
            return (
                next(c for c in main.classes if c.startswith("cols-")),
                next(c for c in main.classes if c.startswith("log-")),
            )

    async def test_wide_terminals_use_more_columns_with_log_on_the_right(self):
        self.assertEqual(await self.layout_of((120, 60)), ("cols-2", "log-right"))
        self.assertEqual(await self.layout_of((150, 60)), ("cols-3", "log-right"))
        self.assertEqual(await self.layout_of((180, 60)), ("cols-4", "log-right"))

    async def test_narrow_but_tall_puts_log_below(self):
        self.assertEqual(await self.layout_of((80, 60)), ("cols-2", "log-bottom"))

    async def test_narrow_and_short_hides_log(self):
        self.assertEqual(await self.layout_of((80, 24)), ("cols-2", "log-hidden"))

    async def test_log_box_position_matches_plan(self):
        app = self.make_app()
        async with app.run_test(size=(150, 60)) as pilot:
            await pilot.pause()
            cards, log = app.query_one("#cards"), app.query_one("#log-box")
            self.assertGreaterEqual(log.region.x, cards.region.right)   # 在右側
        app = self.make_app()
        async with app.run_test(size=(80, 60)) as pilot:
            await pilot.pause()
            cards, log = app.query_one("#cards"), app.query_one("#log-box")
            self.assertGreaterEqual(log.region.y, cards.region.bottom)  # 在下方
            self.assertTrue(log.display)
        app = self.make_app()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            self.assertFalse(app.query_one("#log-box").display)

    async def test_arrow_keys_follow_the_actual_column_count(self):
        app = self.make_app()
        async with app.run_test(size=(150, 60)) as pilot:    # 3 欄
            await pilot.pause()
            await pilot.press("right", "right")
            self.assertEqual(app.focused.id, "card-pvp")
            await pilot.press("down")
            self.assertEqual(app.focused.id, "card-factory")
            await pilot.press("right")                        # 右緣:不動
            self.assertEqual(app.focused.id, "card-factory")

    async def test_layout_updates_when_terminal_is_resized(self):
        app = self.make_app()
        async with app.run_test(size=(180, 60)) as pilot:
            await pilot.pause()
            main = app.query_one("#main")
            self.assertTrue(main.has_class("cols-4"))
            await pilot.resize_terminal(80, 60)
            await pilot.pause()
            self.assertTrue(main.has_class("log-bottom"))
            self.assertFalse(main.has_class("log-right"))
            self.assertFalse(main.has_class("cols-4"))


if __name__ == "__main__":
    unittest.main()
