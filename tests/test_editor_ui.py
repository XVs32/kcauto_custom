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
            target = next(r for r in screen._field_rows() if r.key == "combat.retreat_limit")
            target.focus()
            await pilot.press("plus")
            self.assertEqual(self.store.get("combat.retreat_limit"), 3)
            await pilot.press("z")
            self.assertEqual(self.store.get("combat.retreat_limit"), 2)
            await pilot.press("d")
            self.assertEqual(self.store.get("combat.retreat_limit"), 4)

    async def test_text_dialog_for_secretary_accepts_int_and_str(self):
        from tui.editor.dialogs import TextDialog
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "f")
            next(r for r in screen._field_rows() if r.key == "factory.build_secretary").focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, TextDialog)
            for _ in range(6):
                await pilot.press("backspace")
            await pilot.press("enter")                       # 空白:不可當機,只顯示錯誤
            await pilot.pause()
            self.assertIsInstance(app.screen, TextDialog)
            await pilot.press("A", "k", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("factory.build_secretary"), "Ak")

    async def test_ok_button_click_works_in_dialogs(self):
        """回歸:點 OK / Remove / Cancel 按鈕會當機。"""
        from tui.editor.widgets import ActionLabel
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "e")
            next(r for r in screen._field_rows() if r.key == "expedition.fleet_2").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("5", "enter")
            await pilot.pause()
            labels = {w.command: w for w in app.screen.query(ActionLabel)}
            for command in ("remove", "ok"):                     # 依序用滑鼠點 Remove、OK
                region = labels[command].region
                await pilot.click(offset=(region.x + 1, region.y))
                await pilot.pause()
            self.assertEqual(self.store.get("expedition.fleet_2"), [])

    async def test_escape_cancels_dialog_without_change(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            target = next(r for r in screen._field_rows() if r.key == "combat.sortie_map")
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
            next(r for r in screen._field_rows() if r.key == "combat.retreat_points").focus()
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
            next(r for r in screen._field_rows() if r.key == "combat.push_nodes").focus()
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
            next(r for r in screen._field_rows() if r.key == "combat.push_nodes").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("a", "enter", "enter")
            await pilot.pause()
            await pilot.press("y")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.push_nodes"), ["a"])

    async def test_recipe_wheels(self):
        from tui.editor.dialogs import NumberDialog
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "f")
            next(r for r in screen._field_rows() if r.key == "factory.build_recipe").focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, NumberDialog)
            await pilot.press("right", "right", "down")      # 燃料 0030 → 十位 +1(↓ = 下一個值)
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(self.store.get("factory.build_recipe"), [40, 30, 30, 30])

    async def test_sortie_map_wheel(self):
        from tui.editor.dialogs import MapDialog
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(r for r in screen._field_rows() if r.key == "combat.sortie_map").focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, MapDialog)
            await pilot.press("down", "down", "right", "down", "down")   # 世界 1→3,海域 1→3
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.sortie_map"), "3-3")

    async def test_arrows_move_rows_even_when_pane_must_scroll(self):
        """回歸:面板高度不夠(出現捲動)時,↑↓ 要換列,不是捲動整個面板。"""
        app = self.make_app()
        async with app.run_test(size=(100, 16)) as pilot:
            screen = await self.open_editor(pilot)
            rows = screen._field_rows()
            self.assertGreater(len(rows), 12)
            for i in range(1, 13):
                await pilot.press("down")
                self.assertIs(screen.focused, rows[i])
            for i in range(12, 6, -1):
                await pilot.press("up")
                self.assertIs(screen.focused, rows[i - 1])
            await pilot.press("end")
            self.assertIs(screen.focused, rows[-1])
            await pilot.press("home")
            self.assertIs(screen.focused, rows[0])

    async def test_node_wheel_uses_noro6_presets(self):
        import json, os, tempfile
        from pathlib import Path
        from tests.lz_compress import compress_utf16
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "configs" / "noro6" / "noro6"
        path.parent.mkdir(parents=True)
        leaf = lambda n: {"name": n, "isDirectory": False}
        tree = {"savedata": {"name": "r", "isDirectory": True,
                             "childItems": [leaf("B-2-2"), leaf("B-2-2-A")]}}
        path.write_text(compress_utf16(json.dumps(tree)), encoding="utf-8")
        old = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, old)
        self.store.set("combat.sortie_map", "2-2")
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(r for r in screen._field_rows() if r.key == "combat.sortie_map").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("right", "right", "down", "enter")     # 節點 — → A
            await pilot.pause()
            self.assertEqual(self.store.get("combat.sortie_map"), "2-2-A")

    async def test_recipe_dialog_is_two_by_two(self):
        from tui.editor.dialogs import NumberDialog
        from tui.editor.widgets import WheelPicker
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "f")
            next(r for r in screen._field_rows() if r.key == "factory.build_recipe").focus()
            await pilot.press("enter")
            await pilot.pause()
            picker = app.screen.query_one(WheelPicker)
            labels = [[picker.wheels[i].label for i in row if picker.wheels[i].label]
                      for row in picker._block_rows()]
            self.assertEqual(labels, [["fuel", "steel"], ["ammo", "bauxite"]])

    async def test_int_wheel_clamps_to_range(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "g")
            next(r for r in screen._field_rows() if r.key == "general.jst_offset").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("right", "down", "down", "down", "enter")   # 十位 0→3:收斂為 20
            await pilot.pause()
            self.assertEqual(self.store.get("general.jst_offset"), 20)

    async def test_left_right_adjust_level_fields(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(r for r in screen._field_rows() if r.key == "combat.retreat_limit").focus()
            await pilot.press("left")
            self.assertEqual(self.store.get("combat.retreat_limit"), 3)
            await pilot.press("right", "right")
            self.assertEqual(self.store.get("combat.retreat_limit"), 4)     # 到頭不循環
            next(r for r in screen._field_rows() if r.key == "combat.enabled").focus()
            await pilot.press("right")
            self.assertTrue(self.store.get("combat.enabled"))
            await pilot.press("left")
            self.assertFalse(self.store.get("combat.enabled"))

    async def test_left_on_wide_field_goes_to_module_list(self):
        from tui.editor.screen import ModuleList
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(r for r in screen._field_rows() if r.key == "combat.sortie_map").focus()
            await pilot.press("left")
            self.assertIsInstance(screen.focused, ModuleList)

    async def test_expedition_bulk_row(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "e")
            bulk = next(r for r in screen._field_rows() if r.key == "@expedition.all_fleets")
            bulk.focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("down", "enter")               # overnight
            await pilot.pause()
            for key in ("expedition.fleet_2", "expedition.fleet_3", "expedition.fleet_4"):
                self.assertEqual(self.store.get(key), ["overnight"])
            await pilot.press("d")                           # 還原三個艦隊的預設
            self.assertEqual(self.store.get("expedition.fleet_3"), [])

    async def test_quest_dialog_lists_only_catalog(self):
        import json, os, tempfile
        from pathlib import Path
        from tui.editor.dialogs import QuestDialog
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        qdir = Path(tmp.name) / "data" / "quests"
        qdir.mkdir(parents=True)
        (qdir / "quests.json").write_text(json.dumps(
            {"Bd1": {"id": 201, "type": "daily"}, "Cd1": {"id": 303, "type": "daily"}}))
        old = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, old)
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "u")
            next(r for r in screen._field_rows() if r.key == "quest.quests").focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, QuestDialog)
            self.assertEqual([g for g, _ in app.screen.groups], ["Bd", "Cd"])
            await pilot.press("down", "space", "enter")      # 勾 Bd1
            await pilot.pause()
            self.assertEqual(self.store.get("quest.quests"), ["Bd1"])

    async def test_preset_grid_multi_keeps_pick_order(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(r for r in screen._field_rows() if r.key == "combat.fleet_presets").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("right", "space", "left", "space", "enter")   # 先 2 再 1
            await pilot.pause()
            self.assertEqual(self.store.get("combat.fleet_presets"), [2, 1])

    async def test_table_dialog_adds_node_select(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(r for r in screen._field_rows() if r.key == "combat.node_selects").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("a", "tab", "b", "enter", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.node_selects"), ["a>b"])

    async def test_scheduler_rule_row(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "s")
            next(r for r in screen._field_rows() if r.key == "scheduler.rules").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("t", "tab", "1", "tab", "s", "tab", "k", "enter", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("scheduler.rules"), ["t:1:s:k"])

    async def test_json_dialog_edits_ship_switcher(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "h")
            next(r for r in screen._field_rows() if r.key == "ship_switcher.slots").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("ctrl+s")
            await pilot.pause()
            self.assertEqual(self.store.get("ship_switcher.slots"), {})

    async def test_tree_editor_builds_slots(self):
        from tui.editor.dialogs import TreeDialog
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "h")
            next(r for r in screen._field_rows() if r.key == "ship_switcher.slots").focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, TreeDialog)
            await pilot.press("a")                                   # 新增 object
            await pilot.pause()
            await pilot.press("s", "1", "enter")                     # key = s1,跳到型別清單
            await pilot.press("down", "down", "down", "down", "down", "enter")   # object
            await pilot.pause()
            await pilot.press("a")                                   # 在 s1 底下新增 int
            await pilot.pause()
            await pilot.press("n", "enter", "down", "enter")         # key = n,型別 int → 開滾輪
            await pilot.pause()
            await pilot.press("right", "right", "down", "down", "enter")   # 滾到 0..0 之後 + 2
            await pilot.pause()
            await pilot.press("ctrl+s")
            await pilot.pause()
            value = self.store.get("ship_switcher.slots")
            self.assertEqual(list(value), ["s1"])
            self.assertEqual(list(value["s1"]), ["n"])
            self.assertIsInstance(value["s1"]["n"], int)

    async def test_tree_editor_edits_existing_slots_and_cancel_keeps_original(self):
        self.store.set("ship_switcher.slots", {"1": {"ship": 5, "name": "x"}})
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "h")
            next(r for r in screen._field_rows() if r.key == "ship_switcher.slots").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("down", "x")                           # 刪掉 ship
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(self.store.get("ship_switcher.slots"), {"1": {"ship": 5, "name": "x"}})

    async def test_compact_layout_on_a_narrow_terminal(self):
        from tui.editor.screen import ModuleTabs
        app = self.make_app()
        async with app.run_test(size=(44, 28)) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.pause()
            self.assertTrue(screen.has_class("narrow"))
            self.assertTrue(screen.has_class("compact"))
            row = screen._field_rows()[0]
            self.assertEqual(row.size.height, 2)
            tabs = screen.query_one(ModuleTabs)
            self.assertTrue(tabs.display)
            self.assertFalse(screen.query_one("#ed-left").display)
            before = screen.entry.module
            await pilot.click(ModuleTabs, offset=(tabs.size.width - 2, 0))
            await pilot.pause()
            self.assertNotEqual(screen.entry.module, before)
            await pilot.click(ModuleTabs, offset=(1, 0))
            await pilot.pause()
            self.assertEqual(screen.entry.module, before)

    async def test_rows_are_one_line_again_when_the_terminal_grows(self):
        app = self.make_app()
        async with app.run_test(size=(44, 28)) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.pause()
            self.assertEqual(screen._field_rows()[0].size.height, 2)
            await pilot.resize_terminal(120, 40)
            await pilot.pause()
            self.assertFalse(screen.has_class("compact"))
            self.assertFalse(screen.has_class("narrow"))
            self.assertEqual(screen._field_rows()[0].size.height, 1)

    async def test_arrows_still_move_rows_in_compact_mode(self):
        app = self.make_app()
        async with app.run_test(size=(44, 20)) as pilot:
            screen = await self.open_editor(pilot)
            rows = screen._field_rows()
            for i in range(1, 8):
                await pilot.press("down")
                self.assertIs(screen.focused, rows[i])

    async def test_dialogs_work_on_a_narrow_terminal(self):
        app = self.make_app()
        async with app.run_test(size=(50, 30)) as pilot:
            screen = await self.open_editor(pilot, "s")
            next(r for r in screen._field_rows() if r.key == "scheduler.rules").focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertTrue(app.screen.has_class("narrow"))
            await pilot.press("t", "tab", "1", "tab", "s", "tab", "k", "enter", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("scheduler.rules"), ["t:1:s:k"])

    async def test_dashboard_survives_very_small_terminals(self):
        from tui.widgets.bars import StatusBar
        app = self.make_app()
        for size in ((30, 12), (36, 20), (60, 14)):
            async with app.run_test(size=size) as pilot:
                await pilot.pause()
                app.query_one(StatusBar).refresh_from(self.store)
                app = self.make_app()

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
            screen = await self.open_editor(pilot)
            await pilot.press("o")                       # 「o」是編輯器內的快捷鍵,儀表板沒有
            self.assertEqual(screen.entry.module, "other")
            self.assertEqual([r.key for r in screen._field_rows()], ["future.thing"])

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
            # 焦點在「開關」上時 → 會調整開關;要在不可調整的欄位上 → 才是切換模組
            next(r for r in screen._field_rows() if r.key == "combat.sortie_map").focus()
            await pilot.press("right")
            self.assertEqual(screen.entry.module, "expedition")


if __name__ == "__main__":
    unittest.main()
