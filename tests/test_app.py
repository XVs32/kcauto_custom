"""UI tests for the dashboard (Textual pilot). The whole group is skipped when Textual is not installed.

These tests cannot run in the development sandbox (no Textual); run them in a real environment:
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

from tests.fakes import FakeRunner
from tui.modules import CARDS
from tui.runner import LOG_OUTPUT, LOG_SYSTEM, RunState
from tui.store import ConfigStore

BIG = (120, 70)  # tall enough that all boxes are on screen


class _AppTestBase(unittest.IsolatedAsyncioTestCase):
    """Shared: temporary config file, FakeRunner, waiting helpers."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "configs" / "config_cui.json"
        self.store = ConfigStore(self.path)

    def tearDown(self):
        self._tmp.cleanup()

    def make_app(self):
        from tui.app import KcautoCui

        self.runner = FakeRunner()
        return KcautoCui(self.store, runner=self.runner)

    async def until(self, pilot, predicate, tries=60):
        """Wait for the worker / redraw to finish (about 3 seconds at most)."""
        for _ in range(tries):
            if predicate():
                return True
            await pilot.pause(0.05)
        return predicate()


@unittest.skipIf(textual is None, "textual is not installed")
class DashboardTests(_AppTestBase):
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
            await pilot.press("up")  # top edge: does not move
            self.assertEqual(app.focused.id, "card-combat")

    async def test_x_toggles_enabled_and_dims_card(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("c")
            card = app.query_one("#card-combat")
            self.assertTrue(card.has_class("off"))  # default combat.enabled=False
            await pilot.press("x")
            self.assertTrue(self.store.get("combat.enabled"))
            self.assertFalse(card.has_class("off"))
            await pilot.press("x")
            self.assertFalse(self.store.get("combat.enabled"))
            self.assertTrue(card.has_class("off"))

    async def test_arrow_right_from_the_last_column_enters_the_log_and_left_leaves(
        self,
    ):
        from tui.widgets.logbox import LogBox

        app = self.make_app()
        async with app.run_test(size=(150, 40)) as pilot:
            await pilot.pause()
            self.assertEqual(app.layout_plan.log, "right")
            await pilot.press("right")  # combat → expedition (column 2)
            self.assertEqual(app.focused.id, "card-expedition")
            await pilot.press("right")  # right again at the last column → log
            self.assertIsInstance(app.focused, LogBox)
            await pilot.press("left")  # ← back to the box we came from
            self.assertEqual(app.focused.id, "card-expedition")

    async def test_log_gets_the_spare_width_instead_of_more_card_columns(self):
        app = self.make_app()
        async with app.run_test(size=(200, 40)) as pilot:
            await pilot.pause()
            self.assertEqual(app.layout_plan.columns, 2)
            cards = app.query_one("#cards")
            log = app.query_one("#log-box")
            self.assertGreater(log.size.width, cards.size.width)

    async def test_arrow_down_from_the_last_row_enters_a_bottom_log_and_up_at_top_leaves(
        self,
    ):
        from tui.widgets.logbox import LogBox

        app = self.make_app()
        async with app.run_test(size=(80, 60)) as pilot:
            await pilot.pause()
            self.assertEqual(app.layout_plan.log, "bottom")
            await pilot.press("g")  # general: the last box
            await pilot.press("down")
            self.assertIsInstance(app.focused, LogBox)
            await pilot.press(
                "up"
            )  # the log is not scrolled → at the top → back to the boxes
            self.assertEqual(app.focused.id, "card-general")

    async def test_down_does_not_enter_a_hidden_log(self):
        from tui.widgets.logbox import LogBox

        app = self.make_app()
        async with app.run_test(size=(60, 12)) as pilot:
            await pilot.pause()
            self.assertEqual(app.layout_plan.log, "hidden")
            await pilot.press("g", "down", "right")
            self.assertNotIsInstance(app.focused, LogBox)

    async def test_language_dialog_switches_language_without_touching_the_dashboard(
        self,
    ):
        from tui import i18n
        from tui.editor.dialogs import ChoiceDialog

        saved = []
        original = i18n.save_pref
        i18n.save_pref = lambda code, root=".": (
            saved.append(code) or True
        )  # do not write into the project directory
        i18n.set_language("en")
        try:
            app = self.make_app()
            async with app.run_test(size=BIG) as pilot:
                await pilot.press("t")
                await pilot.pause()
                self.assertIsInstance(app.screen, ChoiceDialog)
                codes = [value for _, value in app.screen.options]
                self.assertEqual(codes, [c for c, _ in i18n.available()])
                await pilot.press("down", "enter")  # en → next
                await pilot.pause()
                self.assertEqual(i18n.language(), codes[1])
                self.assertEqual(saved, [codes[1]])
                self.assertEqual(len(app.screen_stack), 1)
                await pilot.press("t")  # a dialog does not open twice
                await pilot.press("escape")
                await pilot.pause()
                self.assertEqual(len(app.screen_stack), 1)
        finally:
            i18n.save_pref = original
            i18n.set_language("en")

    async def test_editor_opens_in_the_selected_language(self):
        from tui import i18n

        i18n.set_language("zh_TW")
        try:
            app = self.make_app()
            async with app.run_test(size=BIG) as pilot:
                await pilot.press("c", "enter")
                await pilot.pause()
                rows = list(app.screen.query("FieldRow"))
                self.assertTrue(rows)
                self.assertEqual(rows[0].field.label, "啟用出擊")
        finally:
            i18n.set_language("en")

    async def test_x_on_general_does_nothing(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            before = self.store.as_dict()
            await pilot.press("g", "x")
            self.assertEqual(self.store.as_dict(), before)

    async def test_click_on_toggle_zone_toggles(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.pause()
            card = app.query_one("#card-pvp")
            await pilot.click(
                "#card-pvp", offset=(card.size.width - 4, card.size.height - 1)
            )
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
            await pilot.press("c", "x", "w")
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
            await pilot.press("c", "x", "q")
            await pilot.pause()
            self.assertIsInstance(app.screen, ConfirmQuit)
            await pilot.press("escape")
            await pilot.pause()
            self.assertNotIsInstance(app.screen, ConfirmQuit)
            self.assertTrue(self.store.get("combat.enabled"))  # was not dropped

    async def test_modal_blocks_dashboard_keys(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("c", "x", "q")
            await pilot.pause()
            await pilot.press("e", "x")  # a dialog is open, so it must have no effect
            self.assertTrue(self.store.get("combat.enabled"))
            self.assertIs(
                self.store.get("expedition.enabled"), True
            )  # default value, not toggled

    async def test_quit_dirty_discard_leaves_file_untouched(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("c", "x", "q")
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause()
        self.assertFalse(self.path.exists())

    # ------------------------------------------------------------------ #
    # responsive layout
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
            self.assertGreaterEqual(log.region.x, cards.region.right)  # on the right
        app = self.make_app()
        async with app.run_test(size=(80, 60)) as pilot:
            await pilot.pause()
            cards, log = app.query_one("#cards"), app.query_one("#log-box")
            self.assertGreaterEqual(log.region.y, cards.region.bottom)  # below
            self.assertTrue(log.display)
        app = self.make_app()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            self.assertFalse(app.query_one("#log-box").display)

    async def test_arrow_keys_follow_the_actual_column_count(self):
        app = self.make_app()
        async with app.run_test(size=(150, 60)) as pilot:  # 3 columns
            await pilot.pause()
            await pilot.press("right", "right")
            self.assertEqual(app.focused.id, "card-pvp")
            await pilot.press("down")
            self.assertEqual(app.focused.id, "card-factory")
            await pilot.press("right")  # right edge: does not move
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


@unittest.skipIf(textual is None, "textual is not installed")
class RunnerIntegrationTests(_AppTestBase):
    async def test_apply_saves_then_restarts(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("c", "x", "a")
            self.assertTrue(
                await self.until(pilot, lambda: "restart" in self.runner.calls)
            )
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIs(data["combat.enabled"], True)

    async def test_apply_is_blocked_by_errors(self):
        self.store.set("general.jst_offset", 99)
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("a")
            await pilot.pause(0.2)
            self.assertNotIn("restart", self.runner.calls)
        self.assertFalse(self.path.exists())

    async def test_apply_with_nothing_changed_still_restarts(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{}", encoding="utf-8")
        self.store.load()
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("a")
            self.assertTrue(
                await self.until(pilot, lambda: "restart" in self.runner.calls)
            )

    async def test_b_toggles_pause_only_when_running(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("space")  # not running: no action
            self.assertEqual(self.runner.calls, [])
            await self.runner.start()
            await pilot.press("space")
            self.assertIn("pause", self.runner.calls)
            await pilot.press("space")
            self.assertIn("resume", self.runner.calls)

    async def test_k_no_longer_stops_kcauto(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.runner.start()
            await pilot.press("k")
            await pilot.pause(0.1)
            self.assertNotIn("stop", self.runner.calls)
            self.assertNotIn("k", [b.key for b in app.BINDINGS])

    async def test_space_pauses_from_a_card_and_from_the_log_without_toggling_modules(
        self,
    ):
        from tui.widgets.logbox import LogBox

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.runner.start()
            before = self.store.as_dict()
            await pilot.press("space")  # focus on a box
            self.assertEqual(self.runner.calls.count("pause"), 1)
            await pilot.press("l")
            await pilot.pause()
            self.assertIsInstance(app.focused, LogBox)
            await pilot.press("space")  # focus on the log
            self.assertEqual(self.runner.calls.count("pause"), 2)
            self.assertEqual(self.store.as_dict(), before)

    async def test_enter_on_the_log_applies_config_like_a(self):
        from tui.widgets.logbox import LogBox

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("c", "x")  # change something so there is a save
            await pilot.press("l")
            await pilot.pause()
            self.assertIsInstance(app.focused, LogBox)
            self.assertFalse(self.runner.waiting_enter)
            await pilot.press("enter")
            self.assertTrue(
                await self.until(pilot, lambda: "restart" in self.runner.calls)
            )
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIs(data["combat.enabled"], True)

    async def test_enter_on_the_log_still_answers_a_waiting_prompt(self):
        from tui.widgets.logbox import LogBox

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.runner.start()
            self.runner.set_waiting(True)
            self.assertTrue(
                await self.until(pilot, lambda: isinstance(app.focused, LogBox))
            )
            await pilot.press("enter")
            self.assertTrue(
                await self.until(pilot, lambda: "send_enter" in self.runner.calls)
            )
            self.assertNotIn("restart", self.runner.calls)

    async def test_log_lines_are_colored_and_recorded(self):
        from tui.widgets.logbox import LogBox

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.pause()
            self.runner.emit(LOG_OUTPUT, "\x1b[92mhello\x1b[0m world")
            self.runner.emit(LOG_SYSTEM, "kcauto paused")
            log = app.query_one(LogBox)
            lines = log.plain_lines()
            self.assertEqual(lines[-2], "hello world")
            self.assertTrue(lines[-1].endswith("kcauto paused"))
            styles = {span.style for span in log.history[-2].spans}
            self.assertTrue(any("98c379" in str(st) for st in styles))

    async def test_history_is_kept_while_log_is_hidden(self):
        from tui.widgets.logbox import BUFFER_LINES, LogBox

        app = self.make_app()
        async with app.run_test(size=(80, 24)) as pilot:  # the log is hidden
            await pilot.pause()
            for i in range(BUFFER_LINES + 50):
                self.runner.emit(LOG_OUTPUT, f"line {i}")
            log = app.query_one(LogBox)
            self.assertEqual(len(log.history), BUFFER_LINES)  # has a limit
            self.assertEqual(log.plain_lines()[-1], f"line {BUFFER_LINES + 49}")

    async def test_waiting_enter_focuses_log_and_enter_is_sent(self):
        from tui.widgets.logbox import LogBox

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.runner.start()
            self.runner.set_waiting(True)
            self.assertTrue(
                await self.until(pilot, lambda: isinstance(app.focused, LogBox))
            )
            await pilot.press("enter")
            self.assertTrue(
                await self.until(pilot, lambda: "send_enter" in self.runner.calls)
            )

    async def test_enter_on_log_without_waiting_does_not_send_enter(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.runner.start()
            await pilot.press("l", "enter")
            await pilot.pause(0.1)
            self.assertNotIn("send_enter", self.runner.calls)  # applies config instead

    async def test_hidden_log_goes_fullscreen_and_escape_returns(self):
        from tui.widgets.logbox import LogBox

        app = self.make_app()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            main = app.query_one("#main")
            self.assertFalse(app.query_one("#log-box").display)
            await pilot.press("l")
            self.assertTrue(await self.until(pilot, lambda: main.has_class("log-full")))
            self.assertTrue(
                await self.until(pilot, lambda: app.query_one("#log-box").display)
            )
            self.assertTrue(
                await self.until(pilot, lambda: isinstance(app.focused, LogBox))
            )
            await pilot.press("escape")
            self.assertTrue(
                await self.until(pilot, lambda: not main.has_class("log-full"))
            )
            self.assertFalse(app.query_one("#log-box").display)

    async def test_escape_leaves_log_focus_back_to_last_card(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.press("e", "l")
            await pilot.pause()
            await pilot.press("escape")
            self.assertTrue(
                await self.until(
                    pilot,
                    lambda: (
                        app.focused is not None and app.focused.id == "card-expedition"
                    ),
                )
            )

    async def test_status_bar_follows_runner_state(self):
        from tui.widgets.bars import StatusBar

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            bar = app.query_one(StatusBar)
            self.assertEqual(bar.run_state, "stopped")
            await self.runner.start()
            self.assertEqual(bar.run_state, "running")
            self.runner.pause()
            self.assertEqual(bar.run_state, "paused")
            self.runner.set_waiting(True)
            self.assertTrue(bar.waiting_enter)
            await self.runner.stop()
            self.assertEqual(bar.run_state, "stopped")
            self.assertIsNone(bar.sample)

    async def test_status_bar_shows_process_sample(self):
        from tui.widgets.bars import StatusBar

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.runner.start()
            self.runner.sample_value = FakeRunner.make_sample()
            bar = app.query_one(StatusBar)
            self.assertTrue(await self.until(pilot, lambda: bar.sample is not None, 80))
            self.assertEqual(bar.sample.pid, 1234)

    async def test_quit_while_running_asks_and_stops_kcauto(self):
        from tui.app import ConfirmQuit

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.runner.start()
            await pilot.press("q")
            await pilot.pause()
            self.assertIsInstance(app.screen, ConfirmQuit)
            self.assertFalse(app.screen.dirty)
            self.assertTrue(app.screen.running)
            await pilot.press("s")  # no unsaved changes: s must not take effect
            await pilot.pause(0.1)
            self.assertIsInstance(app.screen, ConfirmQuit)
            await pilot.press("d")
            self.assertTrue(
                await self.until(pilot, lambda: "stop" in self.runner.calls)
            )

    async def test_quit_cancel_keeps_kcauto_running(self):
        from tui.app import ConfirmQuit

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.runner.start()
            await pilot.press("q", "escape")
            await pilot.pause(0.1)
            self.assertNotIsInstance(app.screen, ConfirmQuit)
            self.assertEqual(self.runner.state, RunState.RUNNING)

    async def test_leaving_the_app_always_kills_the_child(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await pilot.pause()
        self.assertIn("kill_now", self.runner.calls)

    async def test_autostart_starts_kcauto(self):
        from tui.app import KcautoCui

        self.runner = FakeRunner()
        app = KcautoCui(self.store, runner=self.runner, autostart=True)
        async with app.run_test(size=BIG) as pilot:
            self.assertTrue(
                await self.until(pilot, lambda: "restart" in self.runner.calls)
            )


if __name__ == "__main__":
    unittest.main()
