"""編輯器的純邏輯測試(不需要 Textual)。"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from tui.editor import model as M
from tui.schema import SCHEMA, Kind


class FormatTests(unittest.TestCase):
    def test_cell_len_counts_wide_chars(self):
        self.assertEqual(M.cell_len("abc"), 3)
        self.assertEqual(M.cell_len("撤退"), 4)

    def test_pad_and_truncate(self):
        self.assertEqual(M.cell_len(M.pad_cells("撤退損傷", 12)), 12)
        out = M.pad_cells("撤退損傷等級很長", 8)
        self.assertEqual(M.cell_len(out), 8)
        self.assertIn("…", out)
        self.assertEqual(M.pad_cells("x", 0), "")

    def test_gauge_and_int_format(self):
        self.assertEqual(M.gauge(4, 0, 4, 8), "█" * 8)
        self.assertEqual(M.gauge(0, 0, 4, 8), "░" * 8)
        self.assertTrue(M.format_value(SCHEMA["combat.retreat_limit"], 2).endswith(" 2"))
        self.assertEqual(M.format_value(SCHEMA["general.chrome_dev_port"], 9222), "9222")

    def test_every_field_formats_default_and_garbage(self):
        for f in SCHEMA.values():
            M.format_value(f, f.make_default(), 30)
            for junk in (None, object(), "x", 5, [1], {"a": 1}):
                M.format_value(f, junk, 20)           # 不可丟例外
            M.type_label(f)

    def test_bool_and_null(self):
        f = SCHEMA["combat.enabled"]
        self.assertEqual(M.format_value(f, True), "on")
        self.assertEqual(M.format_value(f, False), "off")
        self.assertEqual(M.format_value(SCHEMA["pvp.fleet_preset"], None), "disable")

    def test_list_summary(self):
        f = SCHEMA["combat.retreat_points"]
        self.assertEqual(M.format_value(f, []), "(empty)")
        self.assertEqual(M.format_value(f, ["A", "B"]), "A, B")
        self.assertTrue(M.format_value(f, list("ABCDEFGHIJ"), 12).startswith("10 items"))

    def test_describe_includes_issue_and_modified(self):
        f = SCHEMA["general.jst_offset"]
        issues = []
        from tui.schema import validate_field
        issues = validate_field(f.key, 99)
        lines = M.describe(f, 99, 0, issues, changed=True)
        joined = "\n".join(line.text for line in lines)
        self.assertIn("modified", joined)
        self.assertIn("error", joined)
        self.assertEqual(M.row_flag(issues), "error")
        self.assertEqual(M.row_flag([]), "")


class ModuleTests(unittest.TestCase):
    def test_entries_cover_all_cards_plus_other(self):
        mods = [e.module for e in M.MODULE_ENTRIES]
        self.assertEqual(mods[-1], M.OTHER)
        self.assertEqual(len(mods), 11)
        hotkeys = [e.hotkey for e in M.MODULE_ENTRIES]
        self.assertEqual(len(set(hotkeys)), len(hotkeys))
        # 編輯器自己使用的鍵不可被模組快捷鍵佔用
        for reserved in "dzw":
            self.assertNotIn(reserved, hotkeys)

    def test_all_61_keys_reachable(self):
        values = {k: f.make_default() for k, f in SCHEMA.items()}
        seen = []
        for e in M.MODULE_ENTRIES:
            seen += M.module_keys(e.module, values)
        self.assertEqual(sorted(seen), sorted(SCHEMA))
        self.assertEqual(len(seen), 61)

    def test_unknown_keys(self):
        values = {"combat.enabled": True, "future.thing": 1}
        self.assertEqual(M.module_keys(M.OTHER, values), ["future.thing"])

    def test_every_field_has_an_editor(self):
        for f in SCHEMA.values():
            self.assertIn(M.editor_for(f), {
                "bool", "choice", "choice_int", "wheel", "map", "text", "preset_wheel",
                "tokens", "recipe", "table", "quest", "list", "tree", "json"})
        self.assertEqual(M.editor_for(None), "json")
        self.assertEqual(M.editor_for(SCHEMA["quest.quests"]), "quest")
        self.assertEqual(M.editor_for(SCHEMA["scheduler.rules"]), "table")
        self.assertEqual(M.editor_for(SCHEMA["factory.build_secretary"]), "text")
        self.assertEqual(M.editor_for(SCHEMA["ship_switcher.slots"]), "tree")

    def test_numbers_never_use_the_keyboard(self):
        """數字欄位一律用滾輪 / 選單 / 格子,只有 int|str 的秘書艦保留文字輸入。"""
        text_fields = [k for k, f in SCHEMA.items() if M.editor_for(f) == "text"]
        self.assertEqual(sorted(text_fields),
                         ["factory.build_secretary", "factory.develop_secretary"])
        self.assertEqual(M.editor_for(SCHEMA["combat.sortie_map"]), "map")
        self.assertEqual(M.editor_for(SCHEMA["combat.retreat_limit"]), "choice_int")
        self.assertEqual(M.editor_for(SCHEMA["general.chrome_dev_port"]), "wheel")
        self.assertEqual(M.editor_for(SCHEMA["factory.build_recipe"]), "recipe")
        self.assertEqual(M.editor_for(SCHEMA["combat.lbas_groups"]), "tokens")

    def test_adjustable_fields(self):
        adjustable = {k for k, f in SCHEMA.items() if M.adjustable(f)}
        for key in ("combat.retreat_limit", "combat.repair_limit",
                    "passive_repair.repair_threshold", "event_reset.farm_difficulty",
                    "combat.fleet_mode", "combat.enabled", "expedition.fleet_preset"):
            self.assertIn(key, adjustable)
        for key in ("general.jst_offset", "combat.repair_timelimit_minutes",
                    "expedition.desire_oil", "combat.sortie_map"):
            self.assertNotIn(key, adjustable)

    def test_tables_match_schema_patterns(self):
        for key in M.TABLES:
            self.assertIn(key, SCHEMA)
        self.assertEqual(set(M.TABLES), {
            "combat.node_selects", "combat.node_formations",
            "combat.node_night_battles", "scheduler.rules"})


class SearchTests(unittest.TestCase):
    def test_search_by_key_label_help(self):
        self.assertEqual(M.search_fields("night")[0].key, "combat.node_night_battles")
        self.assertIn("combat.retreat_limit", [f.key for f in M.search_fields("撤退")])
        self.assertTrue(M.search_fields("chrome"))
        self.assertEqual(M.search_fields(""), [])
        self.assertEqual(M.search_fields("zzzzqqq"), [])

    def test_all_terms_must_match(self):
        keys = [f.key for f in M.search_fields("combat retreat")]
        self.assertIn("combat.retreat_limit", keys)
        self.assertNotIn("expedition.fleet_2", keys)

    def test_name_hit_ranks_first(self):
        self.assertEqual(M.search_fields("secretary")[0].name.endswith("secretary"), True)


class DangerTests(unittest.TestCase):
    def test_only_adding_nodes_needs_confirm(self):
        f = SCHEMA["combat.push_nodes"]
        self.assertTrue(M.needs_danger_confirm(f, [], ["A"]))
        self.assertTrue(M.needs_danger_confirm(f, ["A"], ["A", "B"]))
        self.assertFalse(M.needs_danger_confirm(f, ["A", "B"], ["A"]))
        self.assertFalse(M.needs_danger_confirm(f, ["A"], []))
        self.assertFalse(M.needs_danger_confirm(f, ["A"], ["A"]))
        self.assertEqual(M.added_items(["A"], ["A", "B"]), ["B"])

    def test_non_danger_never_confirms(self):
        self.assertFalse(M.needs_danger_confirm(SCHEMA["combat.retreat_points"], [], ["A"]))

    def test_only_push_nodes_is_danger(self):
        self.assertEqual([k for k, f in SCHEMA.items() if f.danger], ["combat.push_nodes"])


class ParseTests(unittest.TestCase):
    def test_int(self):
        f = SCHEMA["combat.retreat_limit"]
        self.assertEqual(M.parse_input(f, " 3 "), 3)
        with self.assertRaises(M.ParseError):
            M.parse_input(f, "abc")
        self.assertTrue(M.check_value(f, 9))
        self.assertIsNone(M.check_value(f, 4))

    def test_int_str(self):
        f = SCHEMA["factory.build_secretary"]
        self.assertEqual(M.parse_input(f, "1234"), 1234)
        self.assertEqual(M.parse_input(f, "Akagi"), "Akagi")
        with self.assertRaises(M.ParseError):
            M.parse_input(f, "  ")

    def test_str(self):
        self.assertEqual(M.parse_input(SCHEMA["combat.sortie_map"], " 3-5 "), "3-5")
        self.assertTrue(M.check_value(SCHEMA["combat.sortie_map"], "bad"))

    def test_step_and_cycle(self):
        f = SCHEMA["combat.retreat_limit"]
        self.assertEqual(M.step_int(f, 3, 1), 4)
        self.assertIsNone(M.step_int(f, 4, 1))
        self.assertIsNone(M.step_int(f, 0, -1))
        self.assertIsNone(M.step_int(f, True, 1))
        self.assertIsNone(M.step_int(SCHEMA["combat.enabled"], 1, 1))
        self.assertEqual(M.cycle_choice(["a", "b", "c"], "c"), "a")
        self.assertEqual(M.cycle_choice(["a", "b", "c"], "a", -1), "c")
        self.assertEqual(M.cycle_choice(["a", "b"], "zzz"), "a")

    def test_enum_options_nullable(self):
        opts = M.enum_options(SCHEMA["expedition.fleet_preset"])
        self.assertEqual([v for _, v in opts], [None, "auto"])      # disable 第一,auto 第二
        self.assertEqual(opts[0][0], "disable")
        self.assertEqual([v for _, v in M.enum_options(SCHEMA["combat.fleet_mode"])][0], "standard")


class ListTests(unittest.TestCase):
    def test_coerce_like_keeps_int_type(self):
        self.assertEqual(M.coerce_like([1, 2], "3"), 3)
        self.assertEqual(M.coerce_like(["1"], "3"), "3")
        self.assertEqual(M.coerce_like([], "3"), "3")
        self.assertEqual(M.coerce_like([1], "auto"), "auto")

    def test_item_error_only_reports_the_new_item(self):
        f = SCHEMA["combat.retreat_points"]
        self.assertIsNone(M.list_item_error(f, ["A"], "B"))
        self.assertIn("節點", M.list_item_error(f, ["A"], "bad node!") or "")

    def test_lbas_nodes_allow_duplicates_and_transient_length(self):
        f = SCHEMA["combat.lbas_group_1_nodes"]
        self.assertIsNone(M.list_item_error(f, ["A"], "A"))      # 一個時尚未滿 2 也不報
        self.assertIsNone(M.list_item_error(f, [], "A"))
        self.assertIsNotNone(M.list_length_error(f, ["A"]))
        self.assertIsNone(M.list_length_error(f, ["A", "A"]))
        self.assertIsNone(M.list_length_error(f, []))


class TableTests(unittest.TestCase):
    def test_parse_and_format_roundtrip(self):
        spec = M.TABLES["combat.node_selects"]
        self.assertEqual(spec.parse("A>B"), ("A", "B"))
        self.assertEqual(spec.format(("A", "B")), "A>B")
        spec = M.TABLES["scheduler.rules"]
        for text in ("time:0230:stop:kcauto", "sorties_run:15:stop:combat",
                     "a:b:c:d:e"):
            self.assertEqual(spec.format(spec.parse(text)), text)

    def test_parse_pads_and_merges_extra(self):
        spec = M.TABLES["combat.node_formations"]
        self.assertEqual(spec.parse("A"), ("A", ""))
        self.assertEqual(spec.parse("A:b:c"), ("A", "b:c"))

    def test_missing_required(self):
        spec = M.TABLES["scheduler.rules"]
        self.assertIn("module", spec.missing(("time", "1", "stop", "", "")))
        self.assertIsNone(spec.missing(("time", "1", "stop", "kcauto", "")))

    def test_check_row(self):
        f = SCHEMA["combat.node_formations"]
        spec = M.TABLES[f.key]
        self.assertIsNone(M.check_table_row(f, spec, ["A", "diamond"], [], None))
        self.assertIsNotNone(M.check_table_row(f, spec, ["A", "nope"], [], None))
        self.assertIsNotNone(M.check_table_row(f, spec, ["", "diamond"], [], None))
        f = SCHEMA["scheduler.rules"]
        spec = M.TABLES[f.key]
        self.assertIsNone(M.check_table_row(f, spec, ["time", "0230", "stop", "kcauto", ""], [], None))
        self.assertIsNotNone(M.check_table_row(f, spec, ["time", "", "stop", "kcauto", ""], [], None))

    def test_night_battle_choices(self):
        col = M.TABLES["combat.node_night_battles"].columns[1]
        self.assertEqual(col.choices, ("True", "False"))
        f = SCHEMA["combat.node_night_battles"]
        self.assertIsNone(M.check_table_row(f, M.TABLES[f.key], ["A", "True"], [], None))

    def test_suggestions(self):
        spec = M.TABLES["scheduler.rules"]
        seen = M.table_suggestions(["time:1:stop:kcauto", "time:2:stop:combat"], spec)
        self.assertEqual(seen[0], ["time"])
        self.assertEqual(seen[3], ["kcauto", "combat"])


class PresetTests(unittest.TestCase):
    def test_tokens(self):
        multi = M.preset_tokens(multi=True, nullable=True)
        self.assertEqual(multi[:2], ["1", "2"])
        self.assertEqual(multi[-1], "auto")
        single = M.preset_tokens(multi=False, nullable=True)
        self.assertEqual(single[-3:], ["auto", "null", "0"])
        self.assertNotIn("null", M.preset_tokens(multi=False, nullable=False))

    def test_selection_and_values(self):
        self.assertEqual(M.preset_selection(None), ["null"])
        self.assertEqual(M.preset_selection(0), ["0"])
        self.assertEqual(M.preset_selection([1, "auto"]), ["1", "auto"])
        self.assertEqual(M.preset_value(["3", "auto", "1"]), [3, "auto", 1])
        self.assertEqual(M.preset_value(["3", "auto"], like=["1"]), ["3", "auto"])
        self.assertEqual(M.preset_value(["3"], like=[1]), [3])
        self.assertIsNone(M.preset_single_value("null"))
        self.assertEqual(M.preset_single_value("auto"), "auto")
        self.assertEqual(M.preset_single_value("7"), 7)

    def test_validator_accepts_results(self):
        f = SCHEMA["combat.fleet_presets"]
        self.assertEqual(f.validate(M.preset_value(["1", "auto", "15"])), [])
        p = SCHEMA["pvp.fleet_preset"]
        for t in M.preset_tokens(multi=False, nullable=True):
            self.assertEqual(p.validate(M.preset_single_value(t)), [], t)

    def test_duplicates(self):
        self.assertTrue(M.has_duplicates([1, "1"]))
        self.assertFalse(M.has_duplicates([1, 2]))


class QuestTests(unittest.TestCase):
    def test_grouping_keeps_file_order(self):
        cat = [M.QuestInfo(i) for i in ("Bd1", "Bd10", "Bd2", "Bw1", "Cd1", "2610B2", "weird")]
        groups = M.group_quests(cat, ["Bd1", "Zzz9"])
        self.assertEqual([g for g, _ in groups], ["Bd", "Bw", "Cd", "2610", "misc", "other"])
        self.assertEqual(dict(groups)["Bd"], ["Bd1", "Bd10", "Bd2"])
        self.assertEqual(dict(groups)["other"], ["Zzz9"])

    def test_merge_keeps_order(self):
        self.assertEqual(M.merge_selection(["Bw1", "Bd1"], ["Bd1", "Bd2", "Bw1"]),
                         ["Bw1", "Bd1", "Bd2"])
        self.assertEqual(M.merge_selection(["A1"], []), [])

    def _write(self, root, rel, data):
        path = Path(root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_catalog_reads_only_quests_json_top_level_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "data/quests/quests.json", {
                "Bd1": {"id": 201, "type": "daily", "recommended_map": ["B-5-3-P"]},
                "2610B2": {"id": 985, "type": "weekly"},
                "Bw1": {"id": 214, "type": "weekly", "map_context": [{"name": "C9"}]},
            })
            self._write(tmp, "data/other/quest_stuff.json", {"Zz9": {}})   # 不讀
            cat = M.load_quest_catalog(tmp)
            self.assertEqual([q.id for q in cat], ["Bd1", "2610B2", "Bw1"])
            self.assertEqual(cat[0].note, "#201 daily")

    def test_catalog_prefers_data_over_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "data/quests/quests.json", {"Bd1": {}})
            self._write(tmp, "template/data/quests/quests.json", {"Cd1": {}})
            self.assertEqual([q.id for q in M.load_quest_catalog(tmp)], ["Bd1"])

    def test_catalog_falls_back_to_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "template/data/quests/quests.json", {"Cd1": {}})
            self.assertEqual([q.id for q in M.load_quest_catalog(tmp)], ["Cd1"])
            self.assertEqual(M.find_quest_file(tmp).name, "quests.json")

    def test_catalog_bad_or_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(M.load_quest_catalog(tmp), [])
            self._write(tmp, "data/quests/quests.json", ["not", "a", "dict"])
            self.assertEqual(M.load_quest_catalog(tmp), [])
            (Path(tmp) / "data/quests/quests.json").write_text("{bad", encoding="utf-8")
            self.assertEqual(M.load_quest_catalog(tmp), [])

    def test_real_quests_file_if_present(self):
        path = os.environ.get("KCAUTO_QUESTS")
        if not path:
            self.skipTest("設 KCAUTO_QUESTS=<quests.json> 可檢查實際檔案")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "data/quests/quests.json"
            target.parent.mkdir(parents=True)
            target.write_bytes(Path(path).read_bytes())
            cat = M.load_quest_catalog(tmp)
            self.assertGreater(len(cat), 50)
            groups = dict(M.group_quests(cat, []))
            self.assertIn("Bd", groups)
            self.assertNotIn("misc", groups)

    def test_group_titles(self):
        self.assertEqual(M.quest_group_title("Bd"), "Bd · sortie daily")
        self.assertEqual(M.quest_group_title("Dm"), "Dm · expedition monthly")
        self.assertEqual(M.quest_group_title("2610"), "2610 · event")
        self.assertEqual(M.quest_group_title("other"), "other (not in quests.json)")


class WheelModelTests(unittest.TestCase):
    def test_layout(self):
        self.assertEqual(M.number_layout(0, 350000, 5), (False, 6))
        self.assertEqual(M.number_layout(-20, 20, 0), (True, 2))
        self.assertEqual(M.number_layout(0, None, 7), (False, 4))
        self.assertEqual(M.number_layout(0, None, 123456), (False, 6))
        self.assertEqual(M.number_layout(0, 59, 0, min_places=3), (False, 3))

    def test_digits_roundtrip(self):
        self.assertEqual(M.digits_of(350000, 6), [3, 5, 0, 0, 0, 0])
        self.assertEqual(M.digits_of(-5, 2), [0, 5])
        self.assertEqual(M.number_from(True, [0, 5]), -5)
        self.assertEqual(M.number_from(False, [3, 0]), 30)
        self.assertEqual(M.clamp_number(99, 0, 59), 59)
        self.assertEqual(M.clamp_number(-3, 0, None), 0)
        self.assertEqual(M.clamp_number(10**9, 0, None), 10**9)

    def test_map_parse_and_build(self):
        self.assertEqual(M.parse_map("3-5"), ("3", 5, ""))
        self.assertEqual(M.parse_map("E-2"), ("E", 2, ""))
        self.assertEqual(M.parse_map("2-2-A"), ("2", 2, "A"))
        self.assertEqual(M.parse_map("auto"), ("auto", None, ""))
        self.assertIsNone(M.parse_map("nonsense"))
        self.assertIsNone(M.parse_map("2-A"))
        self.assertIsNone(M.parse_map(5))
        self.assertEqual(M.build_map("3", "5"), "3-5")
        self.assertEqual(M.build_map("2", "2", "A"), "2-2-A")
        self.assertEqual(M.build_map("2", "2", M.NO_NODE), "2-2")
        self.assertEqual(M.build_map("auto", "—", "A"), "auto")

    def test_node_items(self):
        nodes = {("2", 2): ["A"], ("5", 6): ["G", "R"]}
        self.assertEqual(M.map_node_items(nodes, "2", "2"), ["—", "A"])
        self.assertEqual(M.map_node_items(nodes, "5", "6"), ["—", "G", "R"])
        self.assertEqual(M.map_node_items(nodes, "1", "1"), ["—"])
        self.assertEqual(M.map_node_items(None, "2", "2"), ["—"])
        self.assertEqual(M.map_node_items(nodes, "auto", "—"), ["—"])
        # 目前值不在 noro6 內也保留,不會一打開就被悄悄改掉
        self.assertEqual(M.map_node_items(nodes, "2", "2", "Z"), ["—", "A", "Z"])
        f = SCHEMA["combat.sortie_map"]
        for node in ("A", "G", "Z"):
            self.assertEqual(f.validate(M.build_map("2", "2", node)), [])

    def test_map_items(self):
        self.assertEqual(len(M.map_number_items("1")), 6)
        self.assertEqual(len(M.map_number_items("7")), 4)
        self.assertEqual(len(M.map_number_items("E")), M.EVENT_MAPS)
        self.assertEqual(M.map_number_items("auto"), ["—"])
        self.assertEqual(len(M.map_number_items("2", 8)), 8)       # 既有值超出時延伸
        self.assertIn("E", M.world_items())
        self.assertIn("2610", M.world_items("2610"))

    def test_every_map_value_is_valid_for_the_schema(self):
        f = SCHEMA["combat.sortie_map"]
        for world in M.WORLDS:
            for n in M.map_number_items(world):
                self.assertEqual(f.validate(M.build_map(world, n)), [], (world, n))
                self.assertEqual(f.validate(M.build_map(world, n, "A")), [], (world, n))

    def test_resource_layout(self):
        """配方 2×2:上 fuel/steel,下 ammo/bauxite;設定檔順序仍是 fuel, ammo, steel, bauxite。"""
        names = [r[0] for r in M.RESOURCES]
        self.assertEqual(names, ["fuel", "ammo", "steel", "bauxite"])
        place = {r[0]: (r[2], r[3]) for r in M.RESOURCES}
        self.assertEqual(place["fuel"], (0, 0))
        self.assertEqual(place["steel"], (0, 1))
        self.assertEqual(place["ammo"], (1, 0))
        self.assertEqual(place["bauxite"], (1, 1))
        self.assertEqual(len({r[1] for r in M.RESOURCES}), 4)           # 四種顏色各不相同

    def test_adjust_value(self):
        f = SCHEMA["combat.retreat_limit"]
        self.assertEqual(M.adjust_value(f, 2, 1), 3)
        self.assertEqual(M.adjust_value(f, 4, 1), 4)            # 到頭不循環
        self.assertEqual(M.adjust_value(f, 0, -1), 0)
        self.assertEqual(M.adjust_value(SCHEMA["combat.enabled"], False, 1), True)
        self.assertEqual(M.adjust_value(SCHEMA["combat.enabled"], True, -1), False)
        mode = SCHEMA["combat.fleet_mode"]
        self.assertEqual(M.adjust_value(mode, "standard", -1), mode.choices[-1])
        self.assertEqual(M.int_options(f)[0], ("0", 0))
        self.assertEqual(len(M.int_options(f)), 5)


class AdjustTests(unittest.TestCase):
    def test_enter_style_wrap_on_ints_and_bools(self):
        f = SCHEMA["combat.retreat_limit"]
        self.assertEqual(M.adjust_value(f, 4, 1, wrap=True), 0)       # 到頭繞回
        self.assertEqual(M.adjust_value(f, 0, -1, wrap=True), 4)
        self.assertEqual(M.adjust_value(f, 2, 1, wrap=True), 3)
        self.assertEqual(M.adjust_value(f, 4, 1), 4)                  # ← → 不繞
        b = SCHEMA["combat.enabled"]
        self.assertEqual(M.adjust_value(b, True, 1, wrap=True), False)  # Enter = 反轉
        self.assertEqual(M.adjust_value(b, False, 1, wrap=True), True)
        self.assertEqual(M.adjust_value(b, True, 1), True)            # → 永遠是 on
        self.assertEqual(M.adjust_value(b, True, -1), False)

    def test_wrap_ignores_garbage_values(self):
        f = SCHEMA["combat.retreat_limit"]
        for junk in ("x", None, True, 2.5):
            self.assertEqual(M.adjust_value(f, junk, 1, wrap=True), junk)

    def test_can_adjust(self):
        f = SCHEMA["combat.retreat_limit"]
        self.assertFalse(M.can_adjust(f, 4, 1))
        self.assertTrue(M.can_adjust(f, 4, -1))
        self.assertFalse(M.can_adjust(f, 0, -1))
        b = SCHEMA["combat.enabled"]
        self.assertFalse(M.can_adjust(b, True, 1))
        self.assertTrue(M.can_adjust(b, True, -1))
        self.assertTrue(M.can_adjust(SCHEMA["combat.fleet_mode"], "standard", 1))


class PresetWheelModelTests(unittest.TestCase):
    LIST = SCHEMA["combat.fleet_presets"]
    PVP = SCHEMA["pvp.fleet_preset"]

    def test_disable_first_then_auto(self):
        for f in (self.LIST, self.PVP):
            tokens = M.preset_wheel_tokens(f)
            self.assertEqual(tokens[:2], ["disable", "auto"])
            self.assertEqual(tokens[2:], [str(n) for n in range(1, 16)])
            self.assertEqual(len(tokens), 17)

    def test_current_selection(self):
        self.assertEqual(M.preset_wheel_current(self.LIST, []), "disable")
        self.assertEqual(M.preset_wheel_current(self.LIST, [3]), "3")
        self.assertEqual(M.preset_wheel_current(self.LIST, ["auto"]), "auto")
        self.assertEqual(M.preset_wheel_current(self.LIST, [7, 9]), "7")     # 多個:取第一個
        self.assertEqual(M.preset_wheel_current(self.LIST, "junk"), "disable")
        self.assertEqual(M.preset_wheel_current(self.PVP, None), "disable")
        self.assertEqual(M.preset_wheel_current(self.PVP, 0), "disable")     # 0 也是不使用
        self.assertEqual(M.preset_wheel_current(self.PVP, "auto"), "auto")
        self.assertEqual(M.preset_wheel_current(self.PVP, 99), "disable")    # 對不上 → disable

    def test_list_field_always_gets_exactly_one_element(self):
        for token in M.preset_wheel_tokens(self.LIST):
            value = M.preset_wheel_result(self.LIST, token, [1, 2])
            self.assertLessEqual(len(value), 1, token)
            self.assertEqual(self.LIST.validate(value), [], token)
        self.assertEqual(M.preset_wheel_result(self.LIST, "disable"), [])
        self.assertEqual(M.preset_wheel_result(self.LIST, "auto"), ["auto"])
        self.assertEqual(M.preset_wheel_result(self.LIST, "7", []), [7])
        self.assertEqual(M.preset_wheel_result(self.LIST, "7", ["1"]), ["7"])   # 沿用字串型別

    def test_pvp_results_are_valid(self):
        for token in M.preset_wheel_tokens(self.PVP):
            self.assertEqual(self.PVP.validate(M.preset_wheel_result(self.PVP, token)), [], token)
        self.assertIsNone(M.preset_wheel_result(self.PVP, "disable", None))
        self.assertEqual(M.preset_wheel_result(self.PVP, "disable", 0), 0)    # 原本是 0 就維持 0

    def test_every_disabled_spelling_displays_as_disable(self):
        for f, values in ((self.LIST, [[], None]), (self.PVP, [None, 0]),
                          (SCHEMA["expedition.fleet_preset"], [None])):
            for v in values:
                self.assertEqual(M.format_value(f, v), "disable", (f.key, v))
        self.assertEqual(M.format_value(self.LIST, [7]), "7")
        self.assertEqual(M.format_value(self.PVP, "auto"), "auto")
        self.assertEqual(M.format_value(SCHEMA["combat.retreat_points"], []), "(empty)")  # 其他欄位不受影響

    def test_expedition_preset_is_an_enum_with_disable_first(self):
        f = SCHEMA["expedition.fleet_preset"]
        self.assertEqual(M.editor_for(f), "choice")                 # enum:選取後用 ← → 調整
        self.assertTrue(M.adjustable(f))
        self.assertEqual([v for _, v in M.enum_options(f)], [None, "auto"])


class ExpeditionBulkTests(unittest.TestCase):
    def test_presets_validate_against_fleet_field(self):
        for name, items in M.EXPEDITION_PRESETS:
            for key in M.EXPEDITION_FLEET_KEYS:
                self.assertEqual(SCHEMA[key].validate(items), [], (name, key))
        names = [n for n, _ in M.EXPEDITION_PRESETS]
        self.assertIn("auto", names)
        self.assertIn("overnight", names)

    def test_options(self):
        opts = M.expedition_bulk_options()
        self.assertEqual([v for _, v in opts][-2:], [M.CUSTOM, M.CLEAR])

    def test_common_and_summary(self):
        v = {k: [] for k in M.EXPEDITION_FLEET_KEYS}
        self.assertIsNone(M.expedition_common(v))
        self.assertEqual(M.bulk_summary(v), "all: (none)")
        for k in M.EXPEDITION_FLEET_KEYS:
            v[k] = ["overnight"]
        self.assertEqual(M.expedition_common(v), "overnight")
        v[M.EXPEDITION_FLEET_KEYS[1]] = ["auto"]
        self.assertIsNone(M.expedition_common(v))
        self.assertIn("differs", M.bulk_summary(v))
        self.assertEqual(M.expedition_preset_items("auto"), ["auto"])
        self.assertEqual(M.expedition_preset_items("nope"), [])


class JsonTests(unittest.TestCase):
    def test_roundtrip_and_errors(self):
        value = {"1": {"a": 1}}
        self.assertEqual(M.parse_json(M.dump_json(value), want_object=True), value)
        with self.assertRaises(M.ParseError):
            M.parse_json("{bad")
        with self.assertRaises(M.ParseError):
            M.parse_json("[1]", want_object=True)
        self.assertEqual(M.parse_json("[1]"), [1])

    def test_format_raw(self):
        self.assertEqual(M.format_raw({"a": 1}), '{"a": 1}')
        self.assertEqual(M.format_raw(object(), 200).startswith("<object"), True)


if __name__ == "__main__":
    unittest.main()
