"""對話框與元件的邏輯測試。

沒有 Textual 時使用 tests/textual_stub.py 的替身(只驗邏輯,不驗畫面);
已安裝 Textual 時整組略過,改由 tests/test_editor_ui.py 做真正的 UI 測試。
"""
import unittest

from tests import textual_stub as stub

USING_STUB = stub.install()

try:
    if USING_STUB:
        from tests.textual_stub import Input, Message, mount, pump
        from textual.widgets import Static
        from tui.editor import model as M
        from tui.editor.dialogs import (
            ChoiceDialog, DangerDialog, JsonDialog, ListDialog, MapDialog, NewItemDialog,
            NumberDialog, NumSpec, Picked, PresetDialog, PresetWheelDialog, QuestDialog, SearchDialog,
            TableDialog, TextDialog, TreeDialog, ValueDialog,
        )
        from tui.editor import tree as TR
        from tui.editor.screen import BulkRow, EditorScreen, FieldRow, ModuleList, ModuleTabs
        from tui.widgets import bars
        from tui.editor.widgets import (
            ActionLabel, PickList, PresetGrid, Row, Wheel, WheelPicker,
        )
        from tui.schema import SCHEMA, defaults
        from tui.store import ConfigStore
finally:
    # 被測模組已綁定替身;移除後其他測試檔的 `import textual` 仍會失敗而略過(匯入失敗時也要移除)
    stub.uninstall()


def click(dialog, command):
    """模擬滑鼠點下對話框上的按鈕。"""
    label = next(w for w in dialog._all
                 if isinstance(w, ActionLabel) and w.command == command)
    label.on_click(Message())
    pump(dialog)


def pick_ok(dialog):
    """分組模式:第一層用方向鍵移到下方的 OK 格,按 Enter。"""
    picker = dialog.query_one(WheelPicker)
    while picker.level != "group":
        picker.action_accept()
    for _ in range(len(picker._targets())):
        picker.action_scroll(1)                          # ↓ 到最下面一列(OK / Cancel)
    while picker.gpos[1] > 0:
        picker.action_column(-1)
    picker.action_accept()
    pump(dialog)


def submit(dialog, widget, text):
    widget.value = text
    dialog.on_input_submitted(Input.Submitted(widget, text))
    pump(dialog)


def err_text(dialog):
    return str(dialog.query_one("#err").content)


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class ButtonTests(unittest.TestCase):
    """回歸:ActionLabel.Clicked 的屬性名稱不一致,任何按鈕一點就當機。"""

    def test_every_dialog_cancel_button_dismisses_none(self):
        dialogs = [
            ChoiceDialog("t", "h", [("a", 1)], 1),
            TextDialog(SCHEMA["factory.build_secretary"], 1234),
            ListDialog(SCHEMA["expedition.fleet_2"], ["1"]),
            TableDialog(SCHEMA["combat.node_selects"], []),
            PresetDialog(SCHEMA["combat.fleet_presets"], [], multi=True),
            NumberDialog(SCHEMA["expedition.desire_oil"], "t",
                         [NumSpec("oil", 5, 0, 350000)], as_list=False),
            MapDialog(SCHEMA["combat.sortie_map"], "1-1"),
            QuestDialog(SCHEMA["quest.quests"], [], [M.QuestInfo("Bd1")]),
            JsonDialog("t", "h", {}, want_object=True),
        ]
        for d in dialogs:
            mount(d)
            click(d, "cancel")
            self.assertIsNone(d.dismissed, type(d).__name__)

    def test_text_dialog_ok_with_empty_input_shows_error_not_crash(self):
        d = mount(TextDialog(SCHEMA["factory.build_secretary"], 1234))
        d.query_one("#value").value = ""
        click(d, "ok")
        self.assertEqual(d.dismissed, "UNSET")
        self.assertIn("empty", err_text(d))

    def test_text_dialog_ok_returns_int_or_str(self):
        d = mount(TextDialog(SCHEMA["factory.build_secretary"], 1))
        d.query_one("#value").value = "1234"
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked(1234))
        d = mount(TextDialog(SCHEMA["factory.build_secretary"], 1))
        d.query_one("#value").value = "Akagi"
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked("Akagi"))

    def test_list_dialog_remove_and_ok(self):
        d = mount(ListDialog(SCHEMA["expedition.fleet_2"], ["1", "2", "3"]))
        click(d, "remove")                   # 回歸:Remove 會當機
        self.assertEqual(d.items, ["2", "3"])
        click(d, "remove")
        click(d, "remove")
        click(d, "remove")                   # 清單已空:不可丟例外
        self.assertEqual(d.items, [])
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked([]))

    def test_list_dialog_add_then_empty_enter_accepts(self):
        d = mount(ListDialog(SCHEMA["expedition.fleet_2"], []))
        box = d.query_one("#add")
        submit(d, box, "5 21, A1")
        self.assertEqual(d.items, ["5", "21", "A1"])
        submit(d, box, "")                   # 回歸:空白時 Enter(=OK)會當機
        self.assertEqual(d.dismissed, Picked(["5", "21", "A1"]))

    def test_list_dialog_rejects_bad_item_without_crash(self):
        d = mount(ListDialog(SCHEMA["combat.retreat_points"], []))
        submit(d, d.query_one("#add"), "bad node!")
        self.assertEqual(d.items, [])
        self.assertTrue(err_text(d))

    def test_list_dialog_edit_item_roundtrip(self):
        d = mount(ListDialog(SCHEMA["combat.retreat_points"], ["A", "B"]))
        lst = d.query_one("#items")
        lst.cursor = 1
        lst.action_choose()
        pump(d)
        box = d.query_one("#add")
        self.assertEqual(box.value, "B")
        submit(d, box, "C")
        self.assertEqual(d.items, ["A", "C"])

    def test_list_dialog_lbas_nodes_exactly_two(self):
        d = mount(ListDialog(SCHEMA["combat.lbas_group_1_nodes"], []))
        submit(d, d.query_one("#add"), "A")
        click(d, "ok")
        self.assertEqual(d.dismissed, "UNSET")           # 只有 1 個:不能 OK
        self.assertIn("2", err_text(d))
        submit(d, d.query_one("#add"), "A")
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked(["A", "A"]))

    def test_table_dialog_add_remove_ok(self):
        d = mount(TableDialog(SCHEMA["combat.node_selects"], ["A>B"]))
        cells = [d.query_one("#cell-0"), d.query_one("#cell-1")]
        cells[0].value, cells[1].value = "C", "D"
        submit(d, cells[0], "C")
        self.assertEqual(d.items, ["A>B", "C>D"])
        click(d, "remove")                               # 回歸:Remove 會當機
        self.assertEqual(d.items, ["A>B"])               # 移除目前反白的那列(剛加的)
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked(d.items))

    def test_table_dialog_empty_enter_accepts(self):
        d = mount(TableDialog(SCHEMA["scheduler.rules"], ["time:0230:stop:kcauto"]))
        submit(d, d.query_one("#cell-0"), "")
        self.assertEqual(d.dismissed, Picked(["time:0230:stop:kcauto"]))

    def test_table_dialog_scheduler_row_with_optional_extra(self):
        d = mount(TableDialog(SCHEMA["scheduler.rules"], []))
        for i, v in enumerate(["sorties_run", "15", "stop", "combat", ""]):
            d.query_one(f"#cell-{i}").value = v
        submit(d, d.query_one("#cell-0"), "sorties_run")
        self.assertEqual(d.items, ["sorties_run:15:stop:combat"])

    def test_table_dialog_formation_choice_cell(self):
        d = mount(TableDialog(SCHEMA["combat.node_formations"], []))
        d.query_one("#cell-0").value = "A"
        d.query_one("#cell-1").action_cycle(2)
        submit(d, d.query_one("#cell-0"), "A")
        self.assertEqual(d.items, ["A:diamond"])

    def test_preset_grid_multi_and_ok_button(self):
        d = mount(PresetDialog(SCHEMA["combat.fleet_presets"], [], multi=True))
        grid = d.query_one(PresetGrid)
        grid.cursor = 1
        grid.action_toggle()                             # 選 2
        grid.cursor = 15
        grid.action_toggle()                             # auto
        grid.cursor = 0
        grid.action_toggle()                             # 1
        click(d, "ok")                                   # 回歸:選了 preset 再按 OK 會當機
        self.assertEqual(d.dismissed, Picked([2, "auto", 1]))

    def test_preset_grid_enter_accepts(self):
        d = mount(PresetDialog(SCHEMA["combat.fleet_presets"], [3], multi=True))
        d.query_one(PresetGrid).action_accept()
        pump(d)
        self.assertEqual(d.dismissed, Picked([3]))

    def test_preset_single_choices(self):
        f = SCHEMA["pvp.fleet_preset"]
        for token, expected in (("7", 7), ("auto", "auto"), ("null", None), ("0", 0)):
            d = mount(PresetDialog(f, 0, multi=False))
            grid = d.query_one(PresetGrid)
            grid.cursor = grid.tokens.index(token)
            grid.action_accept()
            pump(d)
            self.assertEqual(d.dismissed, Picked(expected), token)

    def test_preset_tokens_for_lbas(self):
        d = mount(PresetDialog(SCHEMA["combat.lbas_groups"], [1], multi=True,
                               tokens=("1", "2", "3")))
        grid = d.query_one(PresetGrid)
        grid.cursor = 2
        grid.action_toggle()
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked([1, 3]))

    def test_choice_dialog_pick(self):
        d = mount(ChoiceDialog("t", "h", M.int_options(SCHEMA["combat.retreat_limit"]), 4))
        lst = d.query_one(PickList)
        self.assertEqual(lst.cursor, 4)
        lst.cursor = 2
        lst.action_choose()
        pump(d)
        self.assertEqual(d.dismissed, Picked(2))

    def test_choice_dialog_null_option(self):
        f = SCHEMA["expedition.fleet_preset"]
        d = mount(ChoiceDialog("t", "h", M.enum_options(f), None))
        lst = d.query_one(PickList)
        self.assertEqual(lst.cursor, 0)                      # null(disable)排第一
        lst.action_choose()
        pump(d)
        self.assertEqual(d.dismissed, Picked(None))

    def test_json_dialog(self):
        d = mount(JsonDialog("t", "h", {"a": 1}, want_object=True))
        d.query_one("#json").text = "{bad"
        click(d, "ok")
        self.assertEqual(d.dismissed, "UNSET")
        d.query_one("#json").text = '{"x": [1, 2]}'
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked({"x": [1, 2]}))

    def test_danger_dialog_buttons(self):
        f = SCHEMA["combat.push_nodes"]
        d = mount(DangerDialog(f, ["A"]))
        click(d, "yes")
        self.assertIs(d.dismissed, True)
        d = mount(DangerDialog(f, ["A"]))
        click(d, "no")
        self.assertIs(d.dismissed, False)

    def test_search_dialog(self):
        d = mount(SearchDialog(["future.thing"]))
        box = d.query_one("#q")
        d.on_input_changed(Input.Changed(box, "secretary"))
        self.assertTrue(all(k.endswith("secretary") or "secretary" in k for k in d.hits))
        d.on_input_submitted(Input.Submitted(box, "secretary"))
        self.assertTrue(d.dismissed.value.endswith("secretary"))
        d = mount(SearchDialog(["future.thing"]))
        d.on_input_changed(Input.Changed(d.query_one("#q"), "future"))
        self.assertEqual(d.hits, ["future.thing"])


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class WheelTests(unittest.TestCase):
    def number(self, key, value, lo, hi, **kw):
        f = SCHEMA[key]
        d = mount(NumberDialog(f, f.label, [NumSpec("n", value, lo, hi, **kw)], as_list=False))
        return d, d.query_one(WheelPicker)

    def test_digit_wheels_for_big_number(self):
        d, picker = self.number("expedition.desire_oil", 350000, 0, 350000)
        self.assertEqual(picker.values(), list("350000"))
        picker.col = 5
        picker.action_scroll(1)                          # 個位 0 → 1
        pump(d)
        # 350001 超過上限 → 自動收斂回 350000
        self.assertEqual(picker.values(), list("350000"))
        picker.col = 1
        picker.action_scroll(-1)                         # 十萬位旁邊的萬位 5 → 4
        pump(d)
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked(340000))

    def test_clamp_when_digit_exceeds_max(self):
        d, picker = self.number("expedition.desire_oil", 350000, 0, 350000)
        picker.col = 0
        picker.action_scroll(1)                          # 3 → 4:450000 > 350000
        pump(d)
        self.assertEqual(picker.values(), list("350000"))

    def test_wrap_around(self):
        d, picker = self.number("passive_repair.slots_to_reserve", 0, 0, None)
        picker.col = 3
        picker.action_scroll(-1)                         # 0 往下 → 9
        pump(d)
        self.assertEqual(picker.values(), list("0009"))

    def test_signed_wheel(self):
        d, picker = self.number("general.jst_offset", -5, -20, 20)
        self.assertEqual(picker.values(), ["-", "0", "5"])
        picker.col = 0
        picker.action_scroll(1)
        pump(d)
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked(5))

    def test_signed_clamps_to_range(self):
        d, picker = self.number("general.jst_offset", 9, -20, 20)
        picker.col = 1
        picker.action_scroll(1)                          # 十位 0 → 1 = 19
        picker.action_scroll(1)                          # 29 → 收斂 20
        pump(d)
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked(20))

    def test_minutes_two_digits(self):
        d, picker = self.number("combat.repair_timelimit_minutes", 30, 0, 59)
        self.assertEqual(picker.values(), ["3", "0"])
        picker.col = 0
        picker.action_scroll(3)                          # 60 → 收斂 59
        pump(d)
        self.assertEqual(picker.values(), ["5", "9"])

    def test_value_out_of_range_is_clamped_on_open(self):
        d, picker = self.number("combat.repair_timelimit_minutes", 99, 0, 59)
        self.assertEqual(picker.values(), ["5", "9"])

    def test_recipe_four_numbers(self):
        f = SCHEMA["factory.build_recipe"]
        specs = [NumSpec(n, v, 0, None, min_places=3)
                 for n, v in zip(("fuel", "ammo", "steel", "bauxite"), (30, 30, 30, 30))]
        d = mount(NumberDialog(f, f.label, specs, as_list=True))
        picker = d.query_one(WheelPicker)
        self.assertEqual(len(picker.wheels), 16)         # 沒有上限:每個數字 4 位
        self.assertTrue(picker.grouped)
        picker.action_accept()                           # 第一層:進入 fuel
        picker.col = 0
        picker.action_scroll(1)                          # fuel 千位 +1
        pump(d)
        picker.action_accept()                           # 確定,回第一層
        pump(d)
        self.assertEqual(picker.level, "group")
        pick_ok(d)
        self.assertEqual(d.dismissed, Picked([1030, 30, 30, 30]))

    def test_enter_on_picker_accepts(self):
        d, picker = self.number("combat.repair_bucket_threshold", 500, 0, None)
        picker.action_accept()
        pump(d)
        self.assertEqual(d.dismissed, Picked(500))

    def test_picker_click_scrolls_to_item(self):
        d, picker = self.number("expedition.desire_bucket", 2000, 0, 3000)
        picker.col = 3

        class Ev(Message):
            x, y = 0, 0
        ev = Ev()
        ev.x = picker._starts()[3]
        ev.y = 1 + 2 + 1                                 # 標題列 + 中心偏移 2 + 下一項
        picker.on_click(ev)
        pump(d)
        self.assertEqual(picker.values()[3], "1")

    def test_picker_render_shape(self):
        d, picker = self.number("expedition.desire_oil", 350000, 0, 350000)
        lines = str(picker.render()).split("\n")
        self.assertEqual(len(lines), WheelPicker.VISIBLE + 1)     # 標題列 + 5 列

    def test_map_dialog(self):
        d = mount(MapDialog(SCHEMA["combat.sortie_map"], "3-5"))
        picker = d.query_one(WheelPicker)
        self.assertEqual(picker.values(), ["3", "5", "—"])
        picker.col = 0
        picker.action_scroll(-2)                         # 3 → 1:只有 6 張圖
        pump(d)
        self.assertEqual(picker.values(), ["1", "5", "—"])
        self.assertEqual(picker.wheels[1].items, ["1", "2", "3", "4", "5", "6"])
        picker.action_scroll(6)                          # 世界 1 → 7:編號縮到 4
        pump(d)
        self.assertEqual(picker.wheels[0].items[picker.wheels[0].index], "7")
        self.assertEqual(len(picker.wheels[1].items), 4)
        click(d, "ok")
        self.assertEqual(d.dismissed.value, "7-4")

    def test_map_dialog_auto_and_event(self):
        d = mount(MapDialog(SCHEMA["combat.sortie_map"], "auto"))
        picker = d.query_one(WheelPicker)
        self.assertEqual(picker.wheels[1].items, ["—"])
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked("auto"))
        d = mount(MapDialog(SCHEMA["combat.sortie_map"], "E-3"))
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked("E-3"))

    def test_map_dialog_unknown_value_falls_back(self):
        d = mount(MapDialog(SCHEMA["combat.sortie_map"], "weird"))
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked("1-1"))


NODES = {("2", 2): ["A"], ("5", 6): ["G", "R", "N", "Z"], ("7", 2): ["G", "M"]}


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class MapNodeTests(unittest.TestCase):
    def open(self, value):
        return mount(MapDialog(SCHEMA["combat.sortie_map"], value, NODES))

    def test_node_wheel_offers_noro6_nodes(self):
        d = self.open("2-2")
        picker = d.query_one(WheelPicker)
        self.assertEqual(picker.wheels[2].items, ["—", "A"])
        picker.col = 2
        picker.action_scroll(1)
        pump(d)
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked("2-2-A"))

    def test_existing_node_value_is_selected(self):
        d = self.open("7-2-M")
        picker = d.query_one(WheelPicker)
        self.assertEqual(picker.values(), ["7", "2", "M"])
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked("7-2-M"))

    def test_node_options_follow_world_and_map(self):
        d = self.open("2-2-A")
        picker = d.query_one(WheelPicker)
        picker.col = 1
        picker.action_scroll(1)                          # 2-3:沒有節點預設
        pump(d)
        self.assertEqual(picker.wheels[2].items, ["—"])
        self.assertEqual(picker.values()[2], "—")
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked("2-3"))

    def test_five_six_has_four_nodes(self):
        d = self.open("5-6")
        self.assertEqual(d.query_one(WheelPicker).wheels[2].items, ["—", "G", "R", "N", "Z"])

    def test_node_missing_from_noro6_is_kept(self):
        d = self.open("2-2-Q")
        picker = d.query_one(WheelPicker)
        self.assertEqual(picker.values(), ["2", "2", "Q"])

    def test_no_noro6_means_no_node_options(self):
        d = mount(MapDialog(SCHEMA["combat.sortie_map"], "2-2", None))
        self.assertEqual(d.query_one(WheelPicker).wheels[2].items, ["—"])
        self.assertIn("No node-specific", str(d.query_one("#note").content))

    def test_note_lists_nodes(self):
        d = self.open("5-6")
        self.assertIn("G, R, N, Z", str(d.query_one("#note").content))

    def test_auto_has_no_node(self):
        d = self.open("auto")
        self.assertEqual(d.query_one(WheelPicker).values(), ["auto", "—", "—"])
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked("auto"))


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class WheelDirectionTests(unittest.TestCase):
    def test_up_is_previous_and_down_is_next(self):
        from tui.editor.widgets import WheelPicker as W
        bindings = {b.key: b.action for b in W.BINDINGS}
        self.assertEqual(bindings["up"], "scroll(-1)")
        self.assertEqual(bindings["down"], "scroll(1)")
        self.assertEqual(bindings["pageup"], "scroll(-5)")
        self.assertEqual(bindings["pagedown"], "scroll(5)")

    def test_mouse_wheel_up_is_previous(self):
        picker = WheelPicker([Wheel([str(n) for n in range(10)], 5)])

        class Ev(Message):
            x, y = 1, 2
            def prevent_default(self): pass
        picker.on_mouse_scroll_up(Ev())
        self.assertEqual(picker.values(), ["4"])
        picker.on_mouse_scroll_down(Ev())
        picker.on_mouse_scroll_down(Ev())
        self.assertEqual(picker.values(), ["6"])

    def test_displayed_order_is_ascending_downward(self):
        picker = WheelPicker([Wheel([str(n) for n in range(10)], 5, wrap=False)])
        lines = [ln.strip() for ln in str(picker.render()).split("\n")]
        self.assertEqual(lines, ["3", "4", "5", "6", "7"])


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class RecipeLayoutTests(unittest.TestCase):
    def open(self, values=(30, 31, 32, 33)):
        f = SCHEMA["factory.build_recipe"]
        specs = [NumSpec(n, v, 0, None, min_places=3, color=c, row=r, col=k)
                 for (n, c, r, k), v in zip(M.RESOURCES, values)]
        return mount(NumberDialog(f, f.label, specs, as_list=True))

    def goto(self, picker, label):
        """第一層:把游標移到指定資源。"""
        for r, row in enumerate(picker._targets()):
            for c, (kind, value) in enumerate(row):
                if kind == "group" and picker.wheels[value].label == label:
                    picker.gpos = (r, c)
                    return
        raise AssertionError(label)

    def test_two_by_two_layout_and_order(self):
        d = self.open()
        picker = d.query_one(WheelPicker)
        rows = picker._block_rows()
        self.assertEqual(len(rows), 2)
        labels = [[picker.wheels[i].label for i in r if picker.wheels[i].label] for r in rows]
        self.assertEqual(labels, [["fuel", "steel"], ["ammo", "bauxite"]])
        colors = {w.label: w.color for w in picker.wheels if w.label}
        self.assertEqual(colors, {n: c for n, c, _, _ in M.RESOURCES})

    def test_saved_order_is_still_fuel_ammo_steel_bauxite(self):
        d = self.open((10, 20, 30, 40))
        pick_ok(d)
        self.assertEqual(d.dismissed, Picked([10, 20, 30, 40]))

    # --- 第一層:選資源 ---------------------------------------------------- #
    def test_level_one_arrows_move_between_resources(self):
        d = self.open()
        picker = d.query_one(WheelPicker)
        self.assertEqual(picker.level, "group")

        def at():
            kind, value = picker._current_target()
            return picker.wheels[value].label if kind == "group" else value
        self.assertEqual(at(), "fuel")
        picker.action_column(1)
        self.assertEqual(at(), "steel")                   # 同一排:右邊是 steel
        picker.action_scroll(1)
        self.assertEqual(at(), "bauxite")                 # 下一排同一欄
        picker.action_column(-1)
        self.assertEqual(at(), "ammo")
        picker.action_scroll(-1)
        self.assertEqual(at(), "fuel")
        picker.action_scroll(-1)                          # 到頂不動
        picker.action_column(-1)                          # 到左邊不動
        self.assertEqual(at(), "fuel")

    def test_level_one_down_reaches_ok_and_cancel(self):
        d = self.open()
        picker = d.query_one(WheelPicker)
        picker.action_scroll(1)
        picker.action_scroll(1)
        self.assertEqual(picker._current_target(), ("action", "OK"))
        picker.action_column(1)
        self.assertEqual(picker._current_target(), ("action", "Cancel"))
        picker.action_column(1)                           # 到底不動
        self.assertEqual(picker._current_target(), ("action", "Cancel"))
        picker.action_accept()
        pump(d)
        self.assertIsNone(d.dismissed)

    def test_level_one_ignores_scrolling_keys_so_nothing_changes_by_accident(self):
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        picker.action_scroll(5)
        picker.action_scroll(-5)
        pump(d)
        self.assertEqual([picker.values()[i] for i in (0, 1, 2, 3)], list("0010"))
        pick_ok(d)
        self.assertEqual(d.dismissed, Picked([10, 20, 30, 40]))

    def test_tab_walks_resources_then_buttons_in_reading_order(self):
        d = self.open()
        picker = d.query_one(WheelPicker)
        seen = []
        for _ in range(6):
            kind, value = picker._current_target()
            seen.append(picker.wheels[value].label if kind == "group" else value)
            picker.action_group(1)
        self.assertEqual(seen, ["fuel", "steel", "ammo", "bauxite", "OK", "Cancel"])
        picker.action_group(1)
        self.assertEqual(picker._current_target(), ("action", "Cancel"))
        picker.action_group(-1)
        self.assertEqual(picker._current_target(), ("action", "OK"))

    # --- 第二層:調數字 ---------------------------------------------------- #
    def test_enter_goes_into_the_resource_and_back_out(self):
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        self.goto(picker, "steel")
        picker.action_accept()
        pump(d)
        self.assertEqual(picker.level, "digit")
        self.assertEqual(picker.wheels[picker.col].label, "steel")        # 停在 steel 的第一位
        self.assertIn("confirm", str(d.query_one("#hint").content))
        picker.action_column(3)
        picker.action_scroll(1)                                           # 個位 +1
        pump(d)
        picker.action_accept()                                            # 確定 → 回第一層
        pump(d)
        self.assertEqual(picker.level, "group")
        self.assertIn("choose", str(d.query_one("#hint").content))
        pick_ok(d)
        self.assertEqual(d.dismissed, Picked([10, 20, 31, 40]))

    def test_digit_level_left_right_stay_inside_the_resource(self):
        d = self.open()
        picker = d.query_one(WheelPicker)
        self.goto(picker, "steel")
        picker.action_accept()
        start = picker.col
        picker.action_column(-1)                          # 不會跑到 fuel
        self.assertEqual(picker.col, start)
        for _ in range(10):
            picker.action_column(1)
        self.assertEqual(picker.col, start + 3)           # 4 位數的最後一位,不會跑到 ammo
        self.assertEqual(picker.wheels[picker.col].label, "")

    def test_digit_level_up_down_scroll_and_do_not_leave(self):
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        picker.action_accept()                            # fuel
        picker.action_column(3)
        picker.action_scroll(-1)                          # ↑ = 上一個值
        pump(d)
        picker.action_scroll(-1)
        pump(d)
        self.assertEqual(picker.level, "digit")
        self.assertEqual(picker.values()[3], "8")         # 0 → 9 → 8(個位數會繞回)

    def test_escape_in_digit_level_undoes_only_that_resource_and_returns(self):
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        self.goto(picker, "fuel")
        picker.action_accept()
        picker.action_column(3)
        picker.action_scroll(2)
        pump(d)
        picker.action_accept()                            # fuel 確定 = 12
        self.goto(picker, "ammo")
        picker.action_accept()
        picker.action_column(3)
        picker.action_scroll(5)
        pump(d)
        d.action_cancel()                                 # Esc:ammo 還原並回第一層
        pump(d)
        self.assertEqual(picker.level, "group")
        self.assertEqual(d.dismissed, "UNSET")            # 對話框還在
        self.assertIn("choose", str(d.query_one("#hint").content))
        pick_ok(d)
        self.assertEqual(d.dismissed, Picked([12, 20, 30, 40]))

    def test_escape_on_level_one_cancels_the_dialog(self):
        d = self.open()
        d.action_cancel()
        self.assertIsNone(d.dismissed)

    def test_clamping_still_works_inside_a_resource(self):
        f = SCHEMA["factory.build_recipe"]
        specs = [NumSpec(n, v, 0, 300, min_places=3, row=r, col=k)
                 for (n, c, r, k), v in zip(M.RESOURCES, (299, 0, 0, 0))]
        d = mount(NumberDialog(f, f.label, specs, as_list=True))
        picker = d.query_one(WheelPicker)
        picker.action_accept()
        picker.action_scroll(1)                           # 百位 2 → 3:399 → 收斂 300
        pump(d)
        self.assertEqual("".join(picker.values()[:3]), "300")

    # --- 滑鼠 ------------------------------------------------------------- #
    def test_clicking_a_digit_enters_that_resource_and_scrolls(self):
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        ammo = next(i for i, w in enumerate(picker.wheels) if w.label == "ammo")
        x = picker._starts()[ammo] + 6                    # ammo 的個位數
        y = 7 + 1 + 2 + 1                                 # 第二排:標題列 7、中心 10、下一項 11
        picker.on_click(MouseEvent(x, y))
        pump(d)
        self.assertEqual(picker.level, "digit")
        self.assertEqual(picker.col, ammo + 3)
        self.assertEqual(picker.values()[ammo + 3], "1")  # 個位 0 → 1

    def test_clicking_another_resource_confirms_the_first_and_switches(self):
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        fuel = 0
        steel = next(i for i, w in enumerate(picker.wheels) if w.label == "steel")
        picker.on_click(MouseEvent(picker._starts()[fuel] + 6, 1 + 2 + 1))      # fuel 個位 +1
        pump(d)
        picker.on_click(MouseEvent(picker._starts()[steel] + 6, 1 + 2))         # steel 個位(中心列)
        pump(d)
        self.assertEqual(picker.wheels[picker.col].label, "")
        self.assertEqual(picker._group_of(picker.col), steel)
        pick_ok(d)
        self.assertEqual(d.dismissed, Picked([11, 20, 30, 40]))

    def test_clicking_ok_and_cancel_cells(self):
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        y = picker._action_line()
        (_, ok0, _), (_, c0, _) = picker._action_cells()
        picker.on_click(MouseEvent(c0 + 1, y))
        pump(d)
        self.assertIsNone(d.dismissed)
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        picker.on_click(MouseEvent(ok0 + 1, y))
        pump(d)
        self.assertEqual(d.dismissed, Picked([10, 20, 30, 40]))

    def test_mouse_wheel_needs_the_resource_to_be_entered_first(self):
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        picker.on_mouse_scroll_down(MouseEvent(picker._starts()[0] + 6, 3))
        pump(d)
        self.assertEqual(picker.values()[3], "0")         # 第一層:滑鼠滾輪不動作
        picker.action_accept()
        picker.on_mouse_scroll_down(MouseEvent(picker._starts()[0] + 6, 3))
        pump(d)
        self.assertEqual(picker.values()[3], "1")

    # --- 排版 ------------------------------------------------------------- #
    def test_render_height_and_click_hits_right_block(self):
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        text = str(picker.render()).split("\n")
        self.assertEqual(len(text), 2 * (5 + 1) + 1 + 2)           # 兩排 + 分隔線 + 規線 + OK 列
        self.assertEqual(picker.styles.height, 15)
        starts = picker._starts()
        ammo = next(i for i, w in enumerate(picker.wheels) if w.label == "ammo")
        idx, offset = picker._locate(starts[ammo], 7 + 1 + 2 + 1)
        self.assertEqual((idx, offset), (ammo, 1))
        self.assertEqual(picker._locate(0, 6), (-1, 0))          # 兩排之間的空行
        self.assertIn("[ OK ]", text[-1])
        self.assertIn("[ Cancel ]", text[-1])
        self.assertEqual(set(text[-2]), {"─"})

    def test_short_terminal_shrinks_to_three_rows(self):
        from types import SimpleNamespace
        d = self.open()
        picker = d.query_one(WheelPicker)
        d.on_resize(SimpleNamespace(size=SimpleNamespace(width=120, height=24)))
        self.assertEqual(picker.rows_shown, 3)
        self.assertEqual(picker.styles.height, 11)
        d.on_resize(SimpleNamespace(size=SimpleNamespace(width=120, height=50)))
        self.assertEqual(picker.rows_shown, 5)
        self.assertEqual(len(str(picker.render()).split("\n")), 15)

    def test_no_separate_button_row_in_grouped_mode(self):
        d = self.open()
        self.assertFalse([w for w in d._all if isinstance(w, ActionLabel)])

    def test_single_number_dialogs_keep_the_button_row(self):
        d = mount(NumberDialog(SCHEMA["general.chrome_dev_port"], "port",
                               [NumSpec("port", 9222, 0, 65535)], as_list=False))
        picker = d.query_one(WheelPicker)
        self.assertFalse(picker.grouped)
        self.assertTrue([w for w in d._all if isinstance(w, ActionLabel)])


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class FitTests(unittest.TestCase):
    def test_lists_shrink_on_short_terminals(self):
        from types import SimpleNamespace
        cat = [M.QuestInfo(f"Bd{i}") for i in range(1, 40)]
        d = mount(QuestDialog(SCHEMA["quest.quests"], [], cat))
        lst = d.query_one(PickList)
        d.on_resize(SimpleNamespace(size=SimpleNamespace(width=120, height=20)))
        self.assertEqual(lst.max_visible, 6)
        d.on_resize(SimpleNamespace(size=SimpleNamespace(width=120, height=10)))
        self.assertEqual(lst.max_visible, 3)                 # 至少 3 列
        d.on_resize(SimpleNamespace(size=SimpleNamespace(width=120, height=80)))
        self.assertEqual(lst.max_visible, 14)                # 不超過預設


class FakeApp:
    """收集 push_screen 的對話框,讓測試手動回覆結果。"""

    def __init__(self):
        self.pushed = []

    def push_screen(self, screen, callback=None):
        self.pushed.append((screen, callback))

    def notify(self, *a, **k):
        pass

    def reply(self, value):
        screen, callback = self.pushed.pop()
        if callback is not None:
            callback(None if value is None else Picked(value))
        return screen


SLOTS = {"1": {"ship": 123, "rules": ["a", True], "name": "x"}, "2": {}}


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class TreeDialogTests(unittest.TestCase):
    def open(self, value=None, field=None):
        d = TreeDialog("slots", "help", SLOTS if value is None else value,
                       field=field or SCHEMA["ship_switcher.slots"])
        d.app = FakeApp()
        mount(d)
        return d

    def paths(self, d):
        return [r.path for r in d.flat]

    def select(self, d, path):
        d.query_one("#tree").cursor = self.paths(d).index(path)
        d._update_crumb()

    def test_starts_expanded_and_shows_rows(self):
        d = self.open()
        self.assertEqual(len(d.flat), 7)
        self.assertIn("▾ 1", d.query_one("#tree").rows[0].text)

    def test_buttons_do_not_crash(self):
        d = self.open()
        for command in ("add", "remove", "cancel"):
            d = self.open()
            click(d, command)
        d = self.open()
        click(d, "ok")
        self.assertEqual(d.dismissed.value, SLOTS)

    def test_original_value_is_not_modified(self):
        d = self.open()
        self.select(d, ("1", "ship"))
        d.action_remove()
        self.assertIn("ship", SLOTS["1"])
        self.assertNotIn("ship", d.doc["1"])

    def test_collapse_and_expand_with_keys(self):
        d = self.open()
        self.select(d, ("1",))
        d.action_close_node()
        self.assertEqual(self.paths(d), [("1",), ("2",)])
        d.action_open_node()
        self.assertEqual(len(d.flat), 7)
        self.select(d, ("1", "rules", 0))
        d.action_close_node()                            # 非容器:回到上一層
        self.assertEqual(d._selected().path, ("1", "rules"))

    def test_enter_on_container_toggles_and_space_flips_bool(self):
        d = self.open()
        lst = d.query_one("#tree")
        self.select(d, ("2",))
        lst.action_choose()
        pump(d)
        self.assertNotIn(("2",), d.expanded)             # 空的容器:收合
        self.select(d, ("1", "rules", 1))
        lst.action_toggle()
        pump(d)
        self.assertIs(d.doc["1"]["rules"][1], False)

    def test_edit_int_opens_number_wheel_and_applies(self):
        d = self.open()
        self.select(d, ("1", "ship"))
        d.query_one("#tree").action_choose()
        pump(d)
        dialog = d.app.reply(124)
        self.assertIsInstance(dialog, NumberDialog)
        self.assertEqual(d.doc["1"]["ship"], 124)
        self.assertEqual(d._selected().path, ("1", "ship"))

    def test_big_ids_get_enough_wheels(self):
        d = self.open({"1": {"id": 12345678}})
        self.select(d, ("1", "id"))
        d.query_one("#tree").action_choose()
        pump(d)
        dialog, _ = d.app.pushed[-1]
        mount(dialog)
        self.assertEqual("".join(dialog.query_one(WheelPicker).values()[1:]), "12345678")

    def test_edit_string(self):
        d = self.open()
        self.select(d, ("1", "name"))
        d.query_one("#tree").action_choose()
        pump(d)
        dialog = d.app.reply("renamed")
        self.assertIsInstance(dialog, ValueDialog)
        self.assertEqual(d.doc["1"]["name"], "renamed")

    def test_edit_float_validates(self):
        d = self.open({"1": {"ratio": 0.5}})
        self.select(d, ("1", "ratio"))
        d.query_one("#tree").action_choose()
        pump(d)
        dialog, _ = d.app.pushed[-1]
        mount(dialog)
        dialog.query_one("#value").value = "abc"
        click(dialog, "ok")
        self.assertEqual(dialog.dismissed, "UNSET")
        dialog.query_one("#value").value = "2.5"
        click(dialog, "ok")
        self.assertEqual(dialog.dismissed, Picked(2.5))

    def test_add_child_to_object_then_edit_it(self):
        d = self.open()
        self.select(d, ("2",))
        d.action_add()
        dialog = d.app.reply(("limit", "int"))
        self.assertIsInstance(dialog, NewItemDialog)
        self.assertEqual(d.doc["2"], {"limit": 0})
        self.assertIn(("2",), d.expanded)
        self.assertEqual(d._selected().path, ("2", "limit"))
        self.assertIsInstance(d.app.pushed[-1][0], NumberDialog)    # 新增完直接輸入內容

    def test_add_to_list_and_nested_container(self):
        d = self.open()
        self.select(d, ("1", "rules"))
        d.action_add()
        d.app.reply((None, "object"))
        self.assertEqual(d.doc["1"]["rules"][-1], {})
        self.assertIn(("1", "rules", 2), d.expanded)
        self.assertFalse(d.app.pushed)                               # object 不跳編輯器

    def test_add_next_to_a_scalar_goes_to_its_parent(self):
        d = self.open()
        self.select(d, ("1", "ship"))
        d.action_add()
        d.app.reply(("extra", "bool"))
        self.assertIs(d.doc["1"]["extra"], False)

    def test_add_at_root_when_empty(self):
        d = self.open({})
        self.assertEqual(d.flat, [])
        d.action_add()
        screen, _ = d.app.pushed[-1]
        self.assertTrue(screen.needs_key)
        d.app.reply(("first", "str"))
        self.assertIn("first", d.doc)

    def test_remove_selected_and_cleanup_expanded(self):
        d = self.open()
        self.select(d, ("1",))
        d.action_remove()
        self.assertNotIn("1", d.doc)
        self.assertTrue(all(p[:1] != ("1",) for p in d.expanded))
        d.action_remove()
        d.action_remove()                                # 已空:不可丟例外
        self.assertEqual(d.doc, {})

    def test_rename_key(self):
        d = self.open()
        self.select(d, ("1",))
        d.action_rename()
        d.app.reply("A")
        self.assertEqual(list(d.doc), ["A", "2"])
        self.assertIn(("A", "rules"), d.expanded)
        self.assertEqual(d._selected().path, ("A",))

    def test_rename_rejects_existing_key_and_list_items(self):
        d = self.open()
        self.select(d, ("1",))
        d.action_rename()
        dialog, _ = d.app.pushed[-1]
        mount(dialog)
        dialog.query_one("#value").value = "2"
        click(dialog, "ok")
        self.assertEqual(dialog.dismissed, "UNSET")
        self.assertIn("exists", err_text(dialog))
        d.app.pushed.clear()
        self.select(d, ("1", "rules", 0))
        d.action_rename()
        self.assertFalse(d.app.pushed)                   # list 項目沒有 key

    def test_change_type(self):
        d = self.open({"a": "12", "b": "x"})
        self.select(d, ("a",))
        d.action_retype()
        d.app.reply("int")
        self.assertEqual(d.doc["a"], 12)
        self.select(d, ("b",))
        d.action_retype()
        d.app.reply("list")
        self.assertEqual(d.doc["b"], [])

    def test_null_row_opens_type_chooser(self):
        d = self.open({"a": None})
        self.select(d, ("a",))
        d.query_one("#tree").action_choose()
        pump(d)
        self.assertIsInstance(d.app.pushed[-1][0], ChoiceDialog)

    def test_raw_json_replaces_tree(self):
        d = self.open()
        d.action_raw_json()
        dialog = d.app.reply({"z": 1})
        self.assertIsInstance(dialog, JsonDialog)
        self.assertEqual(d.doc, {"z": 1})
        self.assertEqual([r.path for r in d.flat], [("z",)])

    def test_apply_validates_against_schema_and_root_type(self):
        d = self.open({"a": 1})
        d.doc = [1]
        d.action_apply()
        self.assertEqual(d.dismissed, "UNSET")
        self.assertIn("object", err_text(d))
        d = self.open({"a": 1})
        d.action_apply()
        self.assertEqual(d.dismissed, Picked({"a": 1}))

    def test_unknown_key_list_root(self):
        d = TreeDialog("future.list", "help", [1, "x"])
        d.app = FakeApp()
        mount(d)
        self.assertEqual(len(d.flat), 2)
        d.action_add()
        screen, _ = d.app.pushed[-1]
        self.assertFalse(screen.needs_key)
        d.app.reply((None, "str"))
        self.assertEqual(len(d.doc), 3)
        click(d, "ok")
        self.assertEqual(d.dismissed.value[:2], [1, "x"])

    def test_moving_cursor_updates_breadcrumb(self):
        d = self.open()
        lst = d.query_one("#tree")
        lst.action_move(1)
        pump(d)
        self.assertEqual(str(d.query_one("#crumb").content), TR.path_text(d._selected().path))


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class NewItemDialogTests(unittest.TestCase):
    def test_key_then_kind(self):
        d = mount(NewItemDialog(True, ["a"]))
        d.query_one("#key").value = "b"
        d.on_input_submitted(Input.Submitted(d.query_one("#key"), "b"))
        lst = d.query_one("#kinds")
        lst.cursor = TR.KINDS.index("bool")
        lst.action_choose()
        pump(d)
        self.assertEqual(d.dismissed, Picked(("b", "bool")))

    def test_duplicate_or_empty_key_is_rejected(self):
        d = mount(NewItemDialog(True, ["a"]))
        for bad in ("", "a"):
            d.query_one("#key").value = bad
            d.query_one("#kinds").action_choose()
            pump(d)
            self.assertEqual(d.dismissed, "UNSET")
            self.assertTrue(err_text(d))

    def test_list_parent_needs_no_key(self):
        d = mount(NewItemDialog(False, []))
        d.query_one("#kinds").action_choose()
        pump(d)
        self.assertEqual(d.dismissed, Picked((None, "str")))

    def test_cancel_button(self):
        d = mount(NewItemDialog(True, []))
        click(d, "cancel")
        self.assertIsNone(d.dismissed)


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class QuestDialogTests(unittest.TestCase):
    CATALOG = [M.QuestInfo(q, n) for q, n in (
        ("Bd1", "#201 daily"), ("Bd2", "#216 daily"), ("Bw1", "#214 weekly"),
        ("2610B2", "#985 weekly"))] if USING_STUB else []

    def test_groups_and_toggle(self):
        d = mount(QuestDialog(SCHEMA["quest.quests"], ["Bd1", "Old9"], self.CATALOG))
        titles = [g for g, _ in d.groups]
        self.assertEqual(titles, ["Bd", "Bw", "2610", "other"])
        lst = d.query_one(PickList)
        self.assertEqual(lst.rows[1].text.split()[0], "Bd1")
        lst.cursor = 2                                   # Bd2
        lst.action_toggle()
        pump(d)
        lst.cursor = 0                                   # Bd 標題 → 整組(已全選就取消)
        lst.action_toggle()
        pump(d)
        lst.action_toggle()                              # 再按一次 → 整組全選
        pump(d)
        click(d, "ok")
        self.assertEqual(d.dismissed.value, ["Bd1", "Old9", "Bd2"])

    def test_group_keys(self):
        d = mount(QuestDialog(SCHEMA["quest.quests"], [], self.CATALOG))
        lst = d.query_one(PickList)
        lst.cursor = 1
        d.action_group(1)
        self.assertEqual(d.chosen, {"Bd1", "Bd2"})
        d.action_group(0)
        self.assertEqual(d.chosen, set())

    def test_titles(self):
        self.assertEqual(M.quest_group_title("Bd"), "Bd · sortie daily")
        self.assertEqual(M.quest_group_title("Dm"), "Dm · expedition monthly")
        self.assertEqual(M.quest_group_title("2610"), "2610 · event")


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class RenderTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self._tmp = tempfile.TemporaryDirectory()
        self.store = ConfigStore(Path(self._tmp.name) / "c.json")
        self.store.set("future.thing", {"a": 1})

    def tearDown(self):
        self._tmp.cleanup()

    def test_every_row_renders(self):
        for key in list(SCHEMA) + ["future.thing"]:
            row = FieldRow(self.store, key)
            row.size.width = 60
            self.assertTrue(str(row.render()).strip(), key)
            row.size.width = 20                           # 很窄也不能丟例外
            row.render()

    def test_rows_render_with_garbage_values(self):
        for key, f in SCHEMA.items():
            for junk in (None, "x", 5, [1], {"a": 1}, True):
                self.store.set(key, junk)
                FieldRow(self.store, key).render()

    def test_bulk_row_and_module_list(self):
        bulk = BulkRow(self.store)
        self.assertIn("none", str(bulk.render()))
        self.store.set(M.EXPEDITION_FLEET_KEYS[0], ["1"])
        self.assertIn("differs", str(bulk.render()))
        for k in M.EXPEDITION_FLEET_KEYS:
            self.store.set(k, ["auto"])
        self.assertIn("all: auto", str(BulkRow(self.store).render()))
        text = str(ModuleList(self.store).render())
        self.assertEqual(len(text.split("\n")), 11)

    def test_widgets_render(self):
        lst = PickList([Row("a", checked=True), Row("b", selectable=False), Row("c")])
        self.assertEqual(len(str(lst.render()).split("\n")), 3)
        grid = PresetGrid(M.preset_tokens(multi=True, nullable=False), ["1"], multi=True)
        self.assertEqual(len(str(grid.render()).split("\n")), 4)
        PickList([]).render()


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class NarrowLayoutTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self._tmp = tempfile.TemporaryDirectory()
        self.store = ConfigStore(Path(self._tmp.name) / "config_cui.json")

    def tearDown(self):
        self._tmp.cleanup()

    # --- 欄位列 --------------------------------------------------------- #
    def test_row_is_two_lines_when_compact(self):
        row = FieldRow(self.store, "combat.sortie_map")
        row.size.width, row.size.height = 40, 2
        lines = str(row.render()).split("\n")
        self.assertEqual(len(lines), 2)
        self.assertIn(SCHEMA["combat.sortie_map"].label, lines[0])
        self.assertIn("1-1", lines[1])
        self.assertTrue(lines[1].startswith("   "))

    def test_row_is_one_line_when_wide(self):
        row = FieldRow(self.store, "combat.sortie_map")
        row.size.width, row.size.height = 80, 1
        text = str(row.render())
        self.assertNotIn("\n", text)
        self.assertIn("1-1", text)

    def test_compact_rows_never_overflow(self):
        for width in (24, 30, 40, 49):
            for key in list(SCHEMA):
                row = FieldRow(self.store, key)
                row.size.width, row.size.height = width, 2
                for line in str(row.render()).split("\n"):
                    self.assertLessEqual(M.cell_len(line), width, (key, width, line))

    def test_bulk_row_compact(self):
        row = BulkRow(self.store)
        row.size.width, row.size.height = 40, 2
        self.assertEqual(len(str(row.render()).split("\n")), 2)

    # --- 模組切換列 ----------------------------------------------------- #
    def test_tabs_render_and_click(self):
        tabs = ModuleTabs()
        tabs.size.width = 60
        tabs.index = 3
        self.assertIn("[ quests ]", str(tabs.render()))
        self.assertIn("pvp", str(tabs.render()))

        class Ev(Message):
            x = 0
        ev = Ev()
        tabs.on_click(ev)
        self.assertEqual(tabs.posted[-1].delta, -1)
        ev.x = 59
        tabs.on_click(ev)
        self.assertEqual(tabs.posted[-1].delta, 1)
        n = len(tabs.posted)
        ev.x = 30
        tabs.on_click(ev)
        self.assertEqual(len(tabs.posted), n)             # 中間不動作

    def test_tabs_render_at_every_width(self):
        tabs = ModuleTabs()
        for index in range(len(M.MODULE_ENTRIES)):
            tabs.index = index
            for width in (20, 33, 50, 71):
                tabs.size.width = width
                self.assertLessEqual(M.cell_len(str(tabs.render())), width)

    # --- 提示列 / 上方資訊列 -------------------------------------------- #
    def test_editor_hints_shrink_but_keep_essentials(self):
        wide = str(EditorScreen._hints(200))
        self.assertIn("move", wide)
        self.assertIn("module", wide)
        mid = str(EditorScreen._hints(46))
        for essential in ("edit", "search", "save", "back"):
            self.assertIn(essential, mid)
        self.assertNotIn("module", mid)
        self.assertLessEqual(M.cell_len(mid.rstrip()), 46)
        narrow = str(EditorScreen._hints(34))
        for essential in ("edit", "save", "back"):
            self.assertIn(essential, narrow)
        self.assertLessEqual(M.cell_len(narrow.rstrip()), 34)
        tiny = str(EditorScreen._hints(20))
        self.assertIn("save", tiny)
        self.assertIn("back", tiny)
        self.assertLessEqual(M.cell_len(tiny.rstrip()), 20)

    def test_dashboard_hints_shrink_but_keep_essentials(self):
        self.assertIn("toggle", str(bars.hint_text(200)))
        narrow = str(bars.hint_text(30))
        for essential in ("save", "quit"):
            self.assertIn(essential, narrow)
        self.assertNotIn("toggle", narrow)

    def test_editor_top_bar_keeps_file_and_counts(self):
        screen = EditorScreen(self.store, "combat")
        screen.size.width = 80
        top = Static()
        screen._by_id["ed-top"] = top
        self.store.set("combat.sortie_map", "2-2")
        self.store.set("combat.retreat_limit", 99)          # 製造 error
        screen._refresh_top()
        text = str(top.content)
        self.assertIn("Editor", text)
        self.assertIn("config_cui.json", text)
        screen.size.width = 36
        screen._refresh_top()
        text = str(top.content)
        self.assertNotIn("Editor", text)                    # 徽章先丟
        self.assertIn("modified*", text)
        self.assertIn("✖", text)

    # --- 儀表板狀態列 --------------------------------------------------- #
    def test_status_bar_keeps_file_and_issue_counts_when_narrow(self):
        bar = bars.StatusBar()
        bar.set_run("running", False)
        self.store.set("combat.sortie_map", "2-2")
        self.store.set("combat.retreat_limit", 99)
        bar.size.width = 120
        bar.refresh_from(self.store)
        wide = str(bar.content)
        self.assertIn("kcauto_custom", wide)
        self.assertIn("JST", wide)
        bar.size.width = 34
        bar.refresh_from(self.store)
        narrow = str(bar.content)
        self.assertNotIn("kcauto_custom", narrow)
        self.assertNotIn("JST", narrow)
        self.assertIn("RUNNING", narrow)
        self.assertIn("config_cui.json*", narrow)
        self.assertIn("✖", narrow)

    def test_status_bar_redraws_on_resize(self):
        bar = bars.StatusBar()
        bar.size.width = 120
        bar.refresh_from(self.store)
        bar.size.width = 30
        bar.on_resize(Message())
        self.assertNotIn("kcauto_custom", str(bar.content))

    def test_status_bar_resize_before_first_refresh_is_safe(self):
        bars.StatusBar().on_resize(Message())

    # --- 對話框窄版 ------------------------------------------------------- #
    def test_dialog_switches_to_narrow_class(self):
        from types import SimpleNamespace
        classes = []
        d = mount(TableDialog(SCHEMA["scheduler.rules"], []))
        d.set_class = lambda on, name: classes.append((name, on))
        d.on_resize(SimpleNamespace(size=SimpleNamespace(width=60, height=30)))
        d.on_resize(SimpleNamespace(size=SimpleNamespace(width=100, height=30)))
        self.assertEqual(classes, [("narrow", True), ("narrow", False)])

    def test_number_and_map_dialogs_also_get_the_class(self):
        from types import SimpleNamespace
        for d in (mount(NumberDialog(SCHEMA["expedition.desire_oil"], "t",
                                     [NumSpec("o", 5, 0, 350000)], as_list=False)),
                  mount(MapDialog(SCHEMA["combat.sortie_map"], "1-1"))):
            seen = []
            d.set_class = lambda on, name, seen=seen: seen.append(on)
            d.on_resize(SimpleNamespace(size=SimpleNamespace(width=50, height=30)))
            self.assertEqual(seen, [True])


class MouseEvent(Message if USING_STUB else object):
    """測試用的滑鼠事件(只有座標)。"""
    def __init__(self, x=0, y=0):
        super().__init__()
        self.x, self.y = x, y

    def prevent_default(self):
        pass


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class ArrowRowTests(unittest.TestCase):
    """調整型欄位:Enter 進入編輯後才顯示 ‹ ›;第一次點擊只選取,再點一次才進入編輯。"""

    def setUp(self):
        import tempfile
        from pathlib import Path
        self._tmp = tempfile.TemporaryDirectory()
        self.store = ConfigStore(Path(self._tmp.name) / "c.json")
        self.store.set("combat.retreat_limit", 2)

    def tearDown(self):
        self._tmp.cleanup()

    def row(self, key="combat.retreat_limit", editing=False, focused=False, width=80, height=1):
        row = FieldRow(self.store, key)
        row.size.width, row.size.height = width, height
        row.in_edit = editing
        row.has_focus = focused
        return row

    def line0(self, row):
        return str(row.render()).split("\n")[0]

    def test_arrows_only_while_editing(self):
        self.assertNotIn("‹", self.line0(self.row(focused=True)))          # 只是選取:沒有箭頭
        text = self.line0(self.row(editing=True, focused=True))
        self.assertIn("‹", text)
        self.assertIn("›", text)

    def test_value_does_not_jump_when_editing_starts(self):
        a = self.line0(self.row(focused=True))
        b = self.line0(self.row(editing=True, focused=True))
        self.assertEqual(a.index("2"), b.index("2"))

    def test_not_adjustable_rows_never_show_arrows(self):
        for key in ("combat.sortie_map", "general.jst_offset", "combat.fleet_presets"):
            self.assertNotIn("‹", self.line0(self.row(key, editing=True, focused=True)))

    def test_every_adjustable_field_shows_arrows_when_editing_and_fits(self):
        for key, f in SCHEMA.items():
            if M.adjustable(f):
                for width, height in ((80, 1), (40, 2)):
                    row = self.row(key, editing=True, focused=True, width=width, height=height)
                    for line in str(row.render()).split("\n"):
                        self.assertLessEqual(M.cell_len(line), width, key)
                    self.assertIn("‹", str(row.render()), key)

    def test_arrow_zones_match_the_drawn_glyphs(self):
        for height, width in ((1, 80), (2, 40)):
            row = self.row(editing=True, focused=True, width=width, height=height)
            lines = str(row.render()).split("\n")
            y = height - 1
            line = lines[y]
            left_x = M.cell_len(line[:line.index("‹")])
            right_x = M.cell_len(line[:line.index("›")])
            line_no, (l0, l1), (r0, r1) = row._zones
            self.assertEqual(line_no, y)
            self.assertTrue(l0 <= left_x <= l1, (left_x, l0, l1))
            self.assertTrue(r0 <= right_x <= r1, (right_x, r0, r1))

    def click(self, row, x, y=0):
        row.posted.clear()
        row.on_mouse_down(MouseEvent(x, y))
        row.on_click(MouseEvent(x, y))
        return [type(m).__name__ for m in row.posted
                if type(m).__name__ in ("Adjust", "Activated", "EnterEdit")], \
               [getattr(m, "delta", None) for m in row.posted if type(m).__name__ == "Adjust"]

    def test_first_click_only_selects(self):
        row = self.row(focused=False)
        row.render()                                      # 還沒選取
        row.has_focus = True                              # 按下時焦點已經先設好了
        names, _ = self.click(row, 40)
        self.assertEqual(names, [])
        self.assertIs(stub.STATE.focused, row)

    def test_clicking_a_selected_row_enters_editing(self):
        row = self.row(focused=True)
        row.render()                                      # 已經以選取的樣子畫在畫面上
        names, _ = self.click(row, 40)
        self.assertEqual(names, ["EnterEdit"])

    def test_clicking_arrows_only_works_while_editing(self):
        row = self.row(editing=True, focused=True)
        row.render()
        _, (l0, l1), (r0, r1) = row._zones
        self.assertEqual(self.click(row, r0 + 1)[1], [1])
        self.assertEqual(self.click(row, l0 + 1)[1], [-1])

    def test_clicking_the_value_or_label_while_editing_changes_nothing(self):
        row = self.row(editing=True, focused=True)
        row.render()
        _, (l0, l1), (r0, r1) = row._zones
        for x, y in (((l1 + r0) // 2, 0), (5, 0), (r0 + 1, 1)):
            self.assertEqual(self.click(row, x)[0] if y == 0 else self.click(row, x, y)[0], [])

    def test_arrow_position_is_inert_when_the_arrows_were_not_visible(self):
        row = self.row(editing=True, focused=True)
        row.render()
        _, _, (r0, _) = row._zones
        row._arrows_drawn = False                         # 按下當時畫面上沒有箭頭
        row.on_mouse_down(MouseEvent(r0 + 1, 0))
        row.on_click(MouseEvent(r0 + 1, 0))
        self.assertEqual([m for m in row.posted if type(m).__name__ == "Adjust"], [])

    def test_clicking_a_non_adjustable_row_opens_its_editor(self):
        row = self.row("combat.sortie_map", focused=True)
        self.assertEqual(self.click(row, 40)[0], ["Activated"])

    def test_compact_rows_use_the_second_line(self):
        row = self.row(editing=True, focused=True, width=40, height=2)
        row.render()
        _, (l0, l1), (r0, r1) = row._zones
        self.assertEqual(self.click(row, r0 + 1, y=0)[1], [])         # 標籤那一列不算
        self.assertEqual(self.click(row, r0 + 1, y=1)[1], [1])


class FakeScreenApp(FakeApp if USING_STUB else object):
    def __init__(self):
        super().__init__()
        self.popped = 0

    def pop_screen(self):
        self.popped += 1


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class EditModeTests(unittest.TestCase):
    """兩層操作:列表(↑↓ 在欄位間跳)→ Enter 進入 → ← → 改值 → Enter 確定回列表。"""

    def setUp(self):
        import tempfile
        from pathlib import Path
        self._tmp = tempfile.TemporaryDirectory()
        self.store = ConfigStore(Path(self._tmp.name) / "c.json")
        self.saved = []
        self.screen = EditorScreen(self.store, "combat", save=lambda: self.saved.append(1) or True)
        self.screen.app = FakeScreenApp()
        self.hints = Static()
        self.screen._by_id["ed-hints"] = self.hints
        self.screen._by_id["ed-top"] = Static()
        self.screen._by_id["ed-help"] = Static()
        self.row = FieldRow(self.store, "combat.retreat_limit")
        self.store.set("combat.retreat_limit", 2)
        self.store.save()

    def tearDown(self):
        self._tmp.cleanup()

    def enter_on(self, key):
        row = FieldRow(self.store, key)
        self.screen._open_editor(row)
        return row

    def hint_text(self):
        return str(self.hints.content)

    # --- 進入 / 確定 / 取消 ------------------------------------------------ #
    def test_enter_starts_editing_without_changing_anything(self):
        row = self.enter_on("combat.retreat_limit")
        self.assertIs(self.screen._edit_row.key, row.key) if False else None
        self.assertEqual(self.screen._edit_row.key, "combat.retreat_limit")
        self.assertTrue(self.screen._edit_row.in_edit)
        self.assertEqual(self.store.get("combat.retreat_limit"), 2)
        self.assertEqual(self.screen.app.pushed, [])                 # 沒有任何對話框

    def test_left_right_change_the_value_only_while_editing(self):
        self.screen.action_adjust(1)                                 # 沒在編輯:不動
        self.assertEqual(self.store.get("combat.retreat_limit"), 2)
        self.enter_on("combat.retreat_limit")
        self.screen.action_horizontal(1)
        self.screen.action_horizontal(1)
        self.assertEqual(self.store.get("combat.retreat_limit"), 4)
        self.screen.action_horizontal(1)                             # 到頭不繞回
        self.assertEqual(self.store.get("combat.retreat_limit"), 4)
        self.screen.action_horizontal(-1)
        self.assertEqual(self.store.get("combat.retreat_limit"), 3)

    def test_enter_confirms_and_returns_to_the_list(self):
        self.enter_on("combat.retreat_limit")
        self.screen.action_horizontal(-1)
        self.screen.action_edit()
        self.assertIsNone(self.screen._edit_row)
        self.assertEqual(self.store.get("combat.retreat_limit"), 1)
        self.assertEqual(self.screen.app.popped, 0)                  # 沒有離開編輯器

    def test_escape_restores_the_value_and_returns_to_the_list(self):
        self.enter_on("combat.retreat_limit")
        self.screen.action_horizontal(1)
        self.screen.action_horizontal(1)
        self.assertEqual(self.store.get("combat.retreat_limit"), 4)
        self.screen.action_close()
        self.assertEqual(self.store.get("combat.retreat_limit"), 2)
        self.assertIsNone(self.screen._edit_row)
        self.assertEqual(self.screen.app.popped, 0)                  # Esc 只是回到列表

    def test_escape_on_the_list_closes_the_editor(self):
        self.screen.action_close()
        self.assertEqual(self.screen.app.popped, 1)

    def test_a_full_edit_cycle_for_each_kind(self):
        for key, steps, expect in (("combat.enabled", [1], True),
                                   ("combat.fleet_mode", [1], None),
                                   ("expedition.fleet_preset", [1], "auto")):
            before = self.store.get(key)
            self.enter_on(key)
            for d in steps:
                self.screen.action_horizontal(d)
            self.screen.action_edit()
            after = self.store.get(key)
            if expect is not None:
                self.assertEqual(after, expect, key)
            else:
                self.assertNotEqual(after, before, key)
            self.assertIsNone(self.screen._edit_row)

    def test_bool_arrows_set_off_and_on(self):
        self.enter_on("combat.enabled")
        self.screen.action_horizontal(1)
        self.assertIs(self.store.get("combat.enabled"), True)
        self.screen.action_horizontal(-1)
        self.assertIs(self.store.get("combat.enabled"), False)

    def test_disable_comes_first_for_the_expedition_preset(self):
        self.store.set("expedition.fleet_preset", None)
        self.enter_on("expedition.fleet_preset")
        self.screen.action_horizontal(1)
        self.assertEqual(self.store.get("expedition.fleet_preset"), "auto")
        self.screen.action_horizontal(1)
        self.assertIsNone(self.store.get("expedition.fleet_preset"))         # 循環回 disable

    def test_space_inside_editing_cycles_with_wrap(self):
        self.store.set("combat.retreat_limit", 4)
        self.enter_on("combat.retreat_limit")
        self.screen.action_quick()
        self.assertEqual(self.store.get("combat.retreat_limit"), 0)

    def test_space_on_the_list_enters_like_enter(self):
        stub.STATE.focused = FieldRow(self.store, "combat.enabled")
        self.screen.action_quick()
        self.assertEqual(self.screen._edit_row.key, "combat.enabled")
        self.assertEqual(self.store.get("combat.enabled"), False)            # 進入不會改值

    # --- 編輯中其他按鍵暫時失效 -------------------------------------------- #
    def test_other_keys_are_ignored_while_editing(self):
        self.enter_on("combat.retreat_limit")
        stub.STATE.focused = self.screen._edit_row
        self.screen.action_row(1)                                    # ↑↓ 不移動
        self.screen.action_goto_module("expedition")                 # 模組快捷鍵
        self.screen.action_module(1)
        self.screen.action_reset_default()
        self.screen.action_undo()
        self.screen.action_save()
        self.screen.action_search()
        self.assertEqual(self.screen.index, 0)
        self.assertEqual(self.saved, [])
        self.assertEqual(self.screen.app.pushed, [])
        self.assertEqual(self.store.get("combat.retreat_limit"), 2)
        self.assertIsNotNone(self.screen._edit_row)

    def test_keys_work_again_after_confirming(self):
        self.enter_on("combat.retreat_limit")
        self.screen.action_edit()
        stub.STATE.focused = FieldRow(self.store, "combat.retreat_limit")
        self.store.set("combat.retreat_limit", 4)
        self.screen.action_reset_default()
        self.assertEqual(self.store.get("combat.retreat_limit"), 4)          # 預設值就是 4
        self.screen.action_save()
        self.assertEqual(self.saved, [1])

    def test_left_and_right_navigate_again_on_the_list(self):
        """第一層:← → 回到模組導覽(窄視窗切換模組),不會改值。"""
        self.store.set("combat.retreat_limit", 2)
        stub.STATE.focused = FieldRow(self.store, "combat.retreat_limit")
        moved = []
        self.screen.has_class = lambda name: True
        self.screen.action_module = lambda d: moved.append(d)
        self.screen.action_horizontal(1)
        self.assertEqual(moved, [1])
        self.assertEqual(self.store.get("combat.retreat_limit"), 2)

    def test_moving_focus_elsewhere_confirms_the_edit(self):
        self.enter_on("combat.retreat_limit")
        self.screen.action_horizontal(1)
        self.screen._focus_changed(Msg(widget=FieldRow(self.store, "combat.fleet_mode")))
        self.assertIsNone(self.screen._edit_row)
        self.assertEqual(self.store.get("combat.retreat_limit"), 3)          # 保留

    def test_focus_events_from_the_edited_row_itself_keep_editing(self):
        self.enter_on("combat.retreat_limit")
        self.screen._focus_changed(Msg(widget=self.screen._edit_row))
        self.assertIsNotNone(self.screen._edit_row)

    def test_clicking_a_selected_row_enters_editing(self):
        row = FieldRow(self.store, "combat.retreat_limit")
        self.screen._row_enter_edit(FieldRow.EnterEdit(row))
        self.assertIs(self.screen._edit_row, row)
        self.screen._row_enter_edit(FieldRow.EnterEdit(FieldRow(self.store, "combat.enabled")))
        self.assertIs(self.screen._edit_row, row)                            # 編輯中不被搶走

    def test_arrow_clicks_adjust_the_edited_row(self):
        row = self.enter_on("combat.retreat_limit")
        edited = self.screen._edit_row
        self.screen._row_adjust(FieldRow.Adjust(edited, 1))
        self.assertEqual(self.store.get("combat.retreat_limit"), 3)

    def test_non_adjustable_and_bulk_rows_do_not_enter_editing(self):
        for key in ("general.jst_offset", "combat.sortie_map"):
            self.screen._begin_edit(FieldRow(self.store, key))
            self.assertIsNone(self.screen._edit_row)
        self.screen._begin_edit(BulkRow(self.store))
        self.assertIsNone(self.screen._edit_row)

    def test_non_adjustable_rows_still_open_their_editors_on_enter(self):
        for key, kind in (("combat.sortie_map", MapDialog), ("combat.fleet_presets", PresetWheelDialog),
                          ("pvp.fleet_preset", PresetWheelDialog), ("general.jst_offset", NumberDialog)):
            self.screen.app.pushed.clear()
            self.enter_on(key)
            self.assertIsInstance(self.screen.app.pushed[-1][0], kind, key)
            self.assertIsNone(self.screen._edit_row)

    # --- 提示列 ------------------------------------------------------------ #
    def test_hints_follow_the_level(self):
        self.screen._refresh_hints()
        self.assertIn("move", self.hint_text())
        self.enter_on("combat.retreat_limit")
        text = self.hint_text()
        for word in ("change", "confirm", "cancel"):
            self.assertIn(word, text)
        self.assertNotIn("move", text)
        self.screen.action_edit()
        self.assertIn("move", self.hint_text())

    def test_edit_hints_fit_narrow_terminals(self):
        text = str(EditorScreen._hints(30, True))
        self.assertLessEqual(M.cell_len(text.rstrip()), 30)
        self.assertIn("confirm", text)


class Msg(Message if USING_STUB else object):
    def __init__(self, **kw):
        super().__init__()
        self.__dict__.update(kw)


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class PresetWheelDialogTests(unittest.TestCase):
    LIST = SCHEMA["combat.fleet_presets"]
    PVP = SCHEMA["pvp.fleet_preset"]

    def open(self, field, value):
        d = mount(PresetWheelDialog(field, value))
        return d, d.query_one(WheelPicker)

    def test_disable_is_first_auto_is_second(self):
        d, picker = self.open(self.LIST, [3])
        self.assertEqual(picker.wheels[0].items[:3], ["disable", "auto", "1"])
        self.assertEqual(picker.values(), ["3"])

    def test_empty_list_starts_on_disable(self):
        d, picker = self.open(self.LIST, [])
        self.assertEqual(picker.values(), ["disable"])
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked([]))

    def test_writes_exactly_one_element(self):
        d, picker = self.open(self.LIST, [3])
        picker.action_scroll(4)                                   # 3 → 7
        pump(d)
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked([7]))

    def test_auto_is_one_step_below_disable(self):
        d, picker = self.open(self.LIST, [])
        picker.action_scroll(1)
        pump(d)
        self.assertEqual(picker.values(), ["auto"])
        picker.action_accept()
        pump(d)
        self.assertEqual(d.dismissed, Picked(["auto"]))

    def test_stops_at_both_ends(self):
        d, picker = self.open(self.LIST, [15])
        picker.action_scroll(1)
        pump(d)
        self.assertEqual(picker.values(), ["15"])                 # 最後一項,不繞回
        picker.action_scroll(-99)
        pump(d)
        self.assertEqual(picker.values(), ["disable"])

    def test_existing_multiple_values_are_flagged(self):
        d, picker = self.open(self.LIST, [3, 5])
        self.assertEqual(picker.values(), ["3"])
        self.assertIn("only one", str(d.query_one("#note").content))
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked([3]))                # 截成一個

    def test_preview_follows_the_wheel(self):
        d, picker = self.open(self.LIST, [3])
        picker.action_scroll(1)
        pump(d)
        self.assertIn("4", str(d.query_one("#preview").content))
        picker.action_scroll(-99)
        pump(d)
        self.assertIn("disable", str(d.query_one("#preview").content))

    def test_pvp_values(self):
        for value, token, expected in ((None, "disable", None), (0, "disable", 0),
                                       ("auto", "auto", "auto"), (7, "7", 7)):
            d, picker = self.open(self.PVP, value)
            self.assertEqual(picker.values(), [token])
            click(d, "ok")
            self.assertEqual(d.dismissed, Picked(expected), value)

    def test_cancel(self):
        d, _ = self.open(self.LIST, [3])
        click(d, "cancel")
        self.assertIsNone(d.dismissed)

    def test_short_terminal_shrinks_the_wheel(self):
        from types import SimpleNamespace
        d, picker = self.open(self.LIST, [3])
        d.on_resize(SimpleNamespace(size=SimpleNamespace(width=120, height=18)))
        self.assertEqual(picker.rows_shown, 3)
        d.on_resize(SimpleNamespace(size=SimpleNamespace(width=120, height=40)))
        self.assertEqual(picker.rows_shown, 5)


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class TightWheelLayoutTests(unittest.TestCase):
    def recipe(self):
        f = SCHEMA["factory.build_recipe"]
        specs = [NumSpec(n, v, 0, None, min_places=3, color=c, row=r, col=k)
                 for (n, c, r, k), v in zip(M.RESOURCES, (30, 31, 32, 33))]
        d = mount(NumberDialog(f, f.label, specs, as_list=True))
        return d, d.query_one(WheelPicker)

    def test_digits_are_narrow_and_adjacent(self):
        d, picker = self.recipe()
        widths = picker._widths()
        self.assertTrue(all(w == 2 for w in widths))
        starts = picker._starts()
        first_group = [i for i, w in enumerate(picker.wheels) if w.row == 0][:4]
        self.assertEqual([starts[i] for i in first_group], [0, 2, 4, 6])

    def test_whole_picker_is_much_narrower_than_before(self):
        d, picker = self.recipe()
        widest = max(M.cell_len(line) for line in str(picker.render()).split("\n"))
        self.assertLessEqual(widest, 22)                           # 原本約 32 欄

    def test_groups_are_separated_by_a_divider_and_rows_by_a_rule(self):
        d, picker = self.recipe()
        lines = str(picker.render()).split("\n")
        self.assertEqual(len(lines), 15)                          # 含下方分隔線與 OK / Cancel 列
        for i in (0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12):
            self.assertIn("│", lines[i], i)                       # 每一列(含標題)左右組之間都有分隔線
        self.assertEqual(set(lines[6]), {"─"})                    # 兩排之間整行分隔線
        self.assertGreaterEqual(len(lines[6]), 20)

    def test_divider_sits_between_the_two_groups(self):
        d, picker = self.recipe()
        line = str(picker.render()).split("\n")[3]
        left, right = line.split("│")
        self.assertEqual(left.replace(" ", "")[-3:], "030")        # 燃料 0030 的最後三位
        self.assertTrue(right.replace(" ", "").startswith("0032"))  # 鋼材 0032

    def test_labels_are_centered_over_their_own_group(self):
        d, picker = self.recipe()
        label = str(picker.render()).split("\n")[0]
        left, right = label.split("│")
        self.assertIn("fuel", left)
        self.assertIn("steel", right)
        self.assertNotIn("steel", left)

    def test_click_still_hits_the_right_digit(self):
        d, picker = self.recipe()
        steel_first = next(i for i, w in enumerate(picker.wheels) if w.label == "steel")
        x = picker._starts()[steel_first] + 1
        idx, offset = picker._locate(x, 1 + 2 + 1)                # 第一排中心的下一列
        self.assertEqual((idx, offset), (steel_first, 1))
        self.assertEqual(picker._locate(picker._starts()[steel_first] - 2, 3)[0], -1)   # 分隔線上

    def test_single_number_dialogs_are_tight_too(self):
        d = mount(NumberDialog(SCHEMA["general.chrome_dev_port"], "port",
                               [NumSpec("port", 9222, 0, 65535)], as_list=False))
        picker = d.query_one(WheelPicker)
        self.assertTrue(all(w.tight and (w.gap == 0 or i == 0)
                            for i, w in enumerate(picker.wheels)))

    def test_signed_numbers_keep_working(self):
        d = mount(NumberDialog(SCHEMA["general.jst_offset"], "jst",
                               [NumSpec("jst", -5, -20, 20)], as_list=False))
        picker = d.query_one(WheelPicker)
        self.assertEqual(picker.values(), ["-", "0", "5"])
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked(-5))

    def test_map_dialog_keeps_wider_wheels(self):
        d = mount(MapDialog(SCHEMA["combat.sortie_map"], "2-2"))
        picker = d.query_one(WheelPicker)
        self.assertFalse(any(w.tight for w in picker.wheels))
        self.assertEqual([w.gap for w in picker.wheels[1:]], [2, 2])


@unittest.skipUnless(USING_STUB, "已安裝 textual:改跑 test_editor_ui")
class PickListTests(unittest.TestCase):
    def test_cursor_skips_headers_and_reports_edges(self):
        lst = PickList([Row("h", selectable=False), Row("a"), Row("b")])
        self.assertEqual(lst.cursor, 1)
        lst.action_move(1)
        self.assertEqual(lst.cursor, 2)
        lst.action_move(1)                               # 已在最下面:送 Edge
        self.assertEqual(lst.posted[-1].direction, 1)
        lst.action_move(-1)
        lst.action_move(-1)
        self.assertEqual(lst.posted[-1].direction, -1)

    def test_click_toggle_vs_choose(self):
        lst = PickList([Row("a", checked=False, toggle=True), Row("b")])

        class Ev(Message):
            x, y = 0, 0
        ev = Ev()
        ev.y = 0
        lst.on_click(ev)
        self.assertEqual(type(lst.posted[-1]).__name__, "Toggled")
        ev.y = 1
        lst.on_click(ev)
        self.assertEqual(type(lst.posted[-1]).__name__, "Chosen")


if __name__ == "__main__":
    unittest.main()
