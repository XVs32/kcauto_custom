import json
import os
import unittest
from pathlib import Path

from tui.schema import (
    SCHEMA, MODULES, defaults, fields_of, groups_of, validate_field, parse_rule,
)

# Wiki Ch5 列出的全部欄位(依文件順序)。漏掉任何一個,測試就會失敗。
CH5_KEYS = """
general.interaction_mode general.jst_offset general.chrome_dev_port
general.poi_api_port general.poi_control_port general.paused
combat.enabled combat.sortie_map combat.fleet_mode combat.fleet_presets
combat.check_fatigue combat.check_lbas_fatigue combat.clear_stop
combat.port_check combat.reserve_repair_dock combat.retreat_limit
combat.repair_limit combat.repair_bucket_threshold
combat.repair_timelimit_hours combat.repair_timelimit_minutes
combat.retreat_points combat.push_nodes combat.node_selects
combat.node_formations combat.node_night_battles combat.node_smoke
combat.lbas_groups combat.lbas_group_1_nodes combat.lbas_group_2_nodes
combat.lbas_group_3_nodes combat.override
expedition.enabled expedition.fleet_2 expedition.fleet_3 expedition.fleet_4
expedition.fleet_preset expedition.desire_oil expedition.desire_ammo
expedition.desire_steel expedition.desire_bauxite expedition.desire_bucket
pvp.enabled pvp.fleet_preset
quest.enabled quest.quests
factory.enabled factory.build_recipe factory.build_secretary
factory.develop_recipe factory.develop_secretary
scheduler.enabled scheduler.rules
passive_repair.enabled passive_repair.repair_threshold
passive_repair.slots_to_reserve
ship_switcher.enabled ship_switcher.slots
event_reset.enabled event_reset.farm_difficulty
event_reset.reset_difficulty event_reset.frequency
""".split()


class SchemaCompleteness(unittest.TestCase):
    def test_covers_exactly_the_ch5_keys(self):
        self.assertEqual(len(CH5_KEYS), 61)
        self.assertEqual(set(SCHEMA), set(CH5_KEYS))

    def test_schema_order_follows_ch5(self):
        self.assertEqual(list(SCHEMA), CH5_KEYS)

    def test_every_module_has_fields(self):
        for module in MODULES:
            self.assertTrue(fields_of(module), module)

    def test_every_field_has_label_and_help(self):
        for field in SCHEMA.values():
            self.assertTrue(field.label.strip(), field.key)
            self.assertTrue(field.help.strip(), field.key)

    def test_groups_are_stable(self):
        self.assertEqual(groups_of("combat"),
                         ["basic", "fatigue", "repair", "routing", "lbas"])

    def test_template_is_covered_when_available(self):
        """設定 KCAUTO_TEMPLATE 指向 config_cui_template.json 即可檢查實際模板。"""
        path = os.environ.get("KCAUTO_TEMPLATE")
        if not path or not Path(path).is_file():
            self.skipTest("未設定 KCAUTO_TEMPLATE")
        with open(path, encoding="utf-8") as fh:
            template = json.load(fh)
        self.assertEqual(sorted(set(template) - set(SCHEMA)), [])


class DefaultsAreValid(unittest.TestCase):
    def test_all_defaults_pass_validation(self):
        for key, value in defaults().items():
            self.assertEqual(validate_field(key, value), [], key)

    def test_defaults_match_ch5(self):
        d = defaults()
        self.assertEqual(d["general.interaction_mode"], "chrome_driver")
        self.assertEqual(d["general.chrome_dev_port"], 9222)
        self.assertEqual(d["combat.sortie_map"], "1-1")
        self.assertEqual(d["combat.retreat_limit"], 4)
        self.assertEqual(d["combat.repair_limit"], 3)
        self.assertEqual(d["expedition.desire_bucket"], 3000)
        self.assertEqual(d["factory.build_recipe"], [30, 30, 30, 30])
        self.assertEqual(d["factory.develop_recipe"], [10, 10, 10, 10])
        self.assertIsNone(d["expedition.fleet_preset"])

    def test_make_default_returns_independent_copies(self):
        a = SCHEMA["quest.quests"].make_default()
        a.append("Bd1")
        self.assertEqual(SCHEMA["quest.quests"].make_default(), [])


class FieldValidation(unittest.TestCase):
    def ok(self, key, value):
        self.assertEqual(validate_field(key, value), [], f"{key}={value!r}")

    def bad(self, key, value):
        issues = validate_field(key, value)
        self.assertTrue(any(i.level == "error" for i in issues), f"{key}={value!r}")

    def test_bool_rejects_ints(self):
        self.ok("combat.enabled", True)
        self.bad("combat.enabled", 1)
        self.bad("combat.enabled", "true")

    def test_int_rejects_bool_and_range(self):
        self.ok("general.jst_offset", -20)
        self.ok("general.jst_offset", 20)
        self.bad("general.jst_offset", 21)
        self.bad("general.jst_offset", True)
        self.bad("general.jst_offset", 1.5)
        self.bad("combat.repair_timelimit_minutes", 60)
        self.bad("expedition.desire_oil", 350001)
        self.bad("general.chrome_dev_port", 65536)

    def test_enum(self):
        self.ok("general.interaction_mode", "poi")
        self.bad("general.interaction_mode", "selenium")
        self.ok("expedition.fleet_preset", None)
        self.ok("expedition.fleet_preset", "auto")
        self.bad("expedition.fleet_preset", "manual")
        self.bad("combat.fleet_mode", None)

    def test_sortie_map(self):
        for value in ("1-1", "6-4", "E-1", "auto"):
            self.ok("combat.sortie_map", value)
        for value in ("", "11", "1-", "1 -1"):
            self.bad("combat.sortie_map", value)

    def test_fleet_presets(self):
        self.ok("combat.fleet_presets", [1, 2, 15])
        self.ok("combat.fleet_presets", ["auto"])
        self.bad("combat.fleet_presets", [0])
        self.bad("combat.fleet_presets", [16])
        self.bad("combat.fleet_presets", ["x"])

    def test_pvp_preset(self):
        for value in (None, "auto", 0, 1, 15):
            self.ok("pvp.fleet_preset", value)
        for value in (16, -1, "7", True):
            self.bad("pvp.fleet_preset", value)

    def test_node_formats(self):
        self.ok("combat.node_selects", ["A>B", "C>D"])
        self.bad("combat.node_selects", ["A-B"])
        self.ok("combat.node_formations", ["A:line_ahead", "Z:combined_fleet_4"])
        self.bad("combat.node_formations", ["A:zigzag"])
        self.ok("combat.node_night_battles", ["X:True", "A:False"])
        self.bad("combat.node_night_battles", ["X:true"])

    def test_lbas_nodes_need_zero_or_two(self):
        self.ok("combat.lbas_group_1_nodes", [])
        self.ok("combat.lbas_group_1_nodes", ["A", "A"])
        self.bad("combat.lbas_group_1_nodes", ["A"])
        self.bad("combat.lbas_group_1_nodes", ["A", "B", "C"])
        self.ok("combat.lbas_groups", [1, "2"])
        self.bad("combat.lbas_groups", [4])

    def test_list_items_reject_bad_types(self):
        self.bad("quest.quests", [None])
        self.bad("quest.quests", [True])
        self.bad("quest.quests", "Bd1")

    def test_expedition_fleets_accept_int_and_str(self):
        self.ok("expedition.fleet_2", [2, 4, 5])
        self.ok("expedition.fleet_2", ["2", "3"])
        self.ok("expedition.fleet_2", ["auto"])
        self.ok("expedition.fleet_2", ["active"])
        self.bad("expedition.fleet_2", ["a b"])

    def test_recipe(self):
        self.ok("factory.build_recipe", [30, 30, 30, 30])
        self.bad("factory.build_recipe", [30, 30, 30])
        self.bad("factory.build_recipe", [30, 30, 30, "x"])
        self.bad("factory.build_recipe", [-1, 30, 30, 30])

    def test_object(self):
        self.ok("ship_switcher.slots", {})
        self.ok("ship_switcher.slots", {"1": {"x": 1}})
        self.bad("ship_switcher.slots", [])

    def test_damage_levels(self):
        self.ok("combat.retreat_limit", 0)
        self.bad("combat.retreat_limit", 5)
        self.bad("passive_repair.repair_threshold", 0)
        self.ok("passive_repair.repair_threshold", 4)

    def test_unknown_key_is_ignored(self):
        self.assertEqual(validate_field("future.setting", object()), [])

    def test_push_nodes_raises_danger_only_when_used(self):
        self.assertEqual(validate_field("combat.push_nodes", []), [])
        issues = validate_field("combat.push_nodes", ["D"])
        self.assertEqual([i.level for i in issues], ["danger"])


class SchedulerRules(unittest.TestCase):
    def test_parse_roundtrip(self):
        for text in ("time:0230:stop:kcauto", "sorties_run:15:stop:combat",
                     "a:b:c:d:e"):
            self.assertEqual(parse_rule(text).format(), text)

    def test_field_accepts_examples(self):
        issues = validate_field("scheduler.rules",
                                ["time:0230:stop:kcauto", "sorties_run:15:stop:combat"])
        self.assertEqual(issues, [])

    def test_bad_rules(self):
        for text in ("time:0230:stop", "a:b:c:d:e:f", "time::stop:kcauto", ""):
            with self.assertRaises(ValueError, msg=text):
                parse_rule(text)
        self.assertTrue(validate_field("scheduler.rules", ["time:0230"]))


if __name__ == "__main__":
    unittest.main()
