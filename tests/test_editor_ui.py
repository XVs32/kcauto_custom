"""編輯器的 UI 測試(Textual pilot)。未安裝 Textual 時整組略過。

沙盒沒有 Textual,這組測試尚未實際執行過,請在實際環境跑:
    python -m unittest tests.test_editor_ui -v
"""
import unittest

try:
    import textual  # noqa: F401
except ImportError:  # pragma: no cover
    textual = None

from tests.test_app import BIG, _AppTestBase


@unittest.skipIf(textual is None, "未安裝 textual")
class EditorTests(_AppTestBase):

    async def open_editor(self, pilot, hotkey="c"):
        from tui.editor.screen import EditorScreen
        await pilot.press(hotkey, "enter")
        await pilot.pause()
        self.assertIsInstance(pilot.app.screen, EditorScreen)
        return pilot.app.screen

    async def test_enter_opens_editor_on_that_module_and_esc_returns(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "e")
            self.assertEqual(screen.entry.module, "expedition")
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 1)
            self.assertEqual(app.focused.id, "card-expedition")

    async def test_dashboard_keys_are_inert_while_editing(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.open_editor(pilot)
            await pilot.press("q")
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 2)       # q 不會離開程式

    async def test_space_toggles_bool_and_dashboard_follows(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.pause()
            self.assertEqual(screen.focused.key, "combat.enabled")
            await pilot.press("space")
            self.assertTrue(self.store.get("combat.enabled"))
            await pilot.press("space")
            self.assertFalse(self.store.get("combat.enabled"))

    async def test_module_hotkeys_and_brackets(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.press("f")
            self.assertEqual(screen.entry.module, "factory")
            await pilot.press("right_square_bracket")
            self.assertEqual(screen.entry.module, "passive_repair")
            await pilot.press("left_square_bracket", "left_square_bracket")
            self.assertEqual(screen.entry.module, "scheduler")
            await pilot.press("o")
            self.assertEqual(screen.entry.module, "other")

    async def test_arrows_move_between_rows(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            first = screen.focused.key
            await pilot.press("down")
            self.assertNotEqual(screen.focused.key, first)
            await pilot.press("up")
            self.assertEqual(screen.focused.key, first)

    async def test_plus_minus_adjust_int(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "g")
            await pilot.press("down", "plus")                # jst_offset
            self.assertEqual(self.store.get("general.jst_offset"), 1)
            await pilot.press("minus", "minus")
            self.assertEqual(self.store.get("general.jst_offset"), -1)

    async def test_default_and_undo_keys(self):
        self.store.set("combat.retreat_limit", 2)
        self.store.save()
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            screen.query_one("#pane-combat").query("FieldRow")  # 已建立
            target = next(r for r in screen._rows() if r.key == "combat.retreat_limit")
            target.focus()
            await pilot.press("plus")
            self.assertEqual(self.store.get("combat.retreat_limit"), 3)
            await pilot.press("z")
            self.assertEqual(self.store.get("combat.retreat_limit"), 2)
            await pilot.press("d")
            self.assertEqual(self.store.get("combat.retreat_limit"), 4)

    async def test_text_dialog_sets_value_and_rejects_bad_input(self):
        from tui.editor.dialogs import TextDialog
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "g")
            target = next(r for r in screen._rows() if r.key == "general.jst_offset")
            target.focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, TextDialog)
            for _ in range(4):
                await pilot.press("backspace")
            await pilot.press("9", "9", "enter")             # 超出範圍
            await pilot.pause()
            self.assertIsInstance(app.screen, TextDialog)
            self.assertEqual(self.store.get("general.jst_offset"), 0)
            for _ in range(4):
                await pilot.press("backspace")
            await pilot.press("8", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("general.jst_offset"), 8)

    async def test_escape_cancels_dialog_without_change(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            target = next(r for r in screen._rows() if r.key == "combat.sortie_map")
            target.focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("x", "escape")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.sortie_map"), "1-1")

    async def test_list_dialog_adds_items(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(r for r in screen._rows() if r.key == "combat.retreat_points").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("a", "enter", "b", "enter", "enter")   # 加 A、B,空白 Enter = OK
            await pilot.pause()
            self.assertEqual(self.store.get("combat.retreat_points"), ["a", "b"])

    async def test_push_nodes_requires_confirmation(self):
        from tui.editor.dialogs import DangerDialog
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(r for r in screen._rows() if r.key == "combat.push_nodes").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("a", "enter", "enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, DangerDialog)
            self.assertEqual(self.store.get("combat.push_nodes"), [])
            await pilot.press("n")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.push_nodes"), [])
            # 再來一次,這次確認
            next(r for r in screen._rows() if r.key == "combat.push_nodes").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("a", "enter", "enter")
            await pilot.pause()
            await pilot.press("y")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.push_nodes"), ["a"])

    async def test_recipe_dialog(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "f")
            next(r for r in screen._rows() if r.key == "factory.build_recipe").focus()
            await pilot.press("enter")
            await pilot.pause()
            for _ in range(3):
                await pilot.press("backspace")
            await pilot.press("5", "0", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("factory.build_recipe"), [50, 30, 30, 30])

    async def test_preset_grid_multi_keeps_pick_order(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(r for r in screen._rows() if r.key == "combat.fleet_presets").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("right", "space", "left", "space", "enter")   # 先 2 再 1
            await pilot.pause()
            self.assertEqual(self.store.get("combat.fleet_presets"), [2, 1])

    async def test_table_dialog_adds_node_select(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(r for r in screen._rows() if r.key == "combat.node_selects").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("a", "tab", "b", "enter", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.node_selects"), ["a>b"])

    async def test_scheduler_rule_row(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "s")
            next(r for r in screen._rows() if r.key == "scheduler.rules").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("t", "tab", "1", "tab", "s", "tab", "k", "enter", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("scheduler.rules"), ["t:1:s:k"])

    async def test_json_dialog_edits_ship_switcher(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "h")
            next(r for r in screen._rows() if r.key == "ship_switcher.slots").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("ctrl+s")
            await pilot.pause()
            self.assertEqual(self.store.get("ship_switcher.slots"), {})

    async def test_search_jumps_to_field(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.press("slash")
            await pilot.pause()
            for ch in "secretary":
                await pilot.press(ch)
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(screen.entry.module, "factory")
            self.assertTrue(screen.focused.key.endswith("secretary"))

    async def test_unknown_keys_appear_under_other(self):
        self.store.set("future.thing", 5)
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "o")
            self.assertEqual([r.key for r in screen._rows()], ["future.thing"])

    async def test_save_from_editor_writes_file(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.open_editor(pilot)
            await pilot.press("space", "w")
            await pilot.pause()
        self.assertTrue(self.path.exists())

    async def test_logs_still_arrive_while_editor_is_open(self):
        from tui.runner import LOG_OUTPUT
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.open_editor(pilot)
            self.runner.on_log(LOG_OUTPUT, "hello from kcauto")
            await pilot.pause()
            log = app._dash.query_one("LogBox")
            self.assertTrue(any("hello from kcauto" in t.plain for t in log.history))

    async def test_narrow_terminal_hides_module_list(self):
        app = self.make_app()
        async with app.run_test(size=(60, 30)) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.pause()
            self.assertTrue(screen.has_class("narrow"))
            await pilot.press("right")
            self.assertEqual(screen.entry.module, "expedition")


if __name__ == "__main__":
    unittest.main()
