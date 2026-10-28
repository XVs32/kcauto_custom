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
            NumberDialog, NumSpec, Picked, PresetDialog, QuestDialog, SearchDialog,
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
        self.assertEqual(lst.cursor, 0)
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
        picker.col = 4                                   # ammo 第 1 位(每個數字 4 位)
        picker.action_scroll(1)
        pump(d)
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked([30, 1030, 30, 30]))

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
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked([10, 20, 30, 40]))

    def test_scrolling_the_right_resource(self):
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        starts = {picker.wheels[i].label: i for i in range(len(picker.wheels))
                  if picker.wheels[i].label}
        picker.col = starts["steel"] + 3                 # 鋼材最後一位(每個數字 4 位)
        picker.action_scroll(1)
        pump(d)
        picker.col = starts["bauxite"] + 3
        picker.action_scroll(-1)
        pump(d)
        click(d, "ok")
        self.assertEqual(d.dismissed, Picked([10, 20, 31, 49]))

    def test_tab_jumps_between_resources(self):
        d = self.open()
        picker = d.query_one(WheelPicker)
        order = []
        for _ in range(4):
            order.append(picker.wheels[picker._group_starts()[
                max(i for i, s in enumerate(picker._group_starts()) if s <= picker.col)]].label)
            picker.action_group(1)
        self.assertEqual(order, ["fuel", "steel", "ammo", "bauxite"])
        picker.action_group(1)                           # 到底不再前進
        self.assertEqual(picker.wheels[picker.col].label, "bauxite")
        picker.action_group(-1)
        self.assertEqual(picker.wheels[picker.col].label, "ammo")

    def test_render_height_and_click_hits_right_block(self):
        d = self.open((10, 20, 30, 40))
        picker = d.query_one(WheelPicker)
        text = str(picker.render()).split("\n")
        self.assertEqual(len(text), 2 * (5 + 1) + 1)
        self.assertEqual(picker.styles.height, 13)
        starts = picker._starts()
        ammo = next(i for i, w in enumerate(picker.wheels) if w.label == "ammo")
        # 第二排:標題列在 y=7,中心列 y=7+1+2=10;點中心下一列 → 該滾輪 +1
        idx, offset = picker._locate(starts[ammo] + 3 * 0, 7 + 1 + 2 + 1)
        self.assertEqual((idx, offset), (ammo, 1))
        self.assertEqual(picker._locate(0, 6), (-1, 0))          # 兩排之間的空行

    def test_short_terminal_shrinks_to_three_rows(self):
        from types import SimpleNamespace
        d = self.open()
        picker = d.query_one(WheelPicker)
        d.on_resize(SimpleNamespace(size=SimpleNamespace(width=120, height=24)))
        self.assertEqual(picker.rows_shown, 3)
        self.assertEqual(picker.styles.height, 9)
        d.on_resize(SimpleNamespace(size=SimpleNamespace(width=120, height=50)))
        self.assertEqual(picker.rows_shown, 5)
        self.assertEqual(len(str(picker.render()).split("\n")), 13)


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
