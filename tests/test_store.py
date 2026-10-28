import json
import os
import tempfile
import unittest
from pathlib import Path

from tui.schema import SCHEMA, defaults, validate_cross, validate_all
from tui.store import ConfigLoadError, ConfigStore, ConfigValidationError


def levels(issues):
    return sorted(i.level for i in issues)


class CrossFieldRules(unittest.TestCase):
    def base(self, **over):
        values = defaults()
        values.update(over)
        return values

    def test_defaults_have_no_cross_issues(self):
        self.assertEqual(validate_cross(self.base()), [])

    def test_pvp_with_combined_fleet_is_error_when_combat_enabled(self):
        v = self.base(**{"pvp.enabled": True, "combat.fleet_mode": "ctf",
                         "combat.enabled": True})
        self.assertEqual(levels(validate_cross(v)), ["error"])

    def test_pvp_with_combined_fleet_is_warning_when_combat_disabled(self):
        v = self.base(**{"pvp.enabled": True, "combat.fleet_mode": "tcf"})
        self.assertEqual(levels(validate_cross(v)), ["warning"])

    def test_pvp_with_strike_is_fine(self):
        v = self.base(**{"pvp.enabled": True, "combat.fleet_mode": "strike",
                         "combat.enabled": True})
        self.assertEqual(validate_cross(v), [])

    def test_lbas_group_without_nodes_and_nodes_without_group(self):
        v = self.base(**{"combat.lbas_groups": [1]})
        self.assertEqual(levels(validate_cross(v)), ["warning"])
        v = self.base(**{"combat.lbas_group_2_nodes": ["A", "B"]})
        self.assertEqual(levels(validate_cross(v)), ["warning"])
        v = self.base(**{"combat.lbas_groups": ["1", "2"],
                         "combat.lbas_group_1_nodes": ["A", "A"],
                         "combat.lbas_group_2_nodes": ["B", "Z"]})
        self.assertEqual(validate_cross(v), [])

    def test_retreat_and_push_same_node(self):
        v = self.base(**{"combat.retreat_points": ["A", "B"],
                         "combat.push_nodes": ["B"]})
        issues = validate_cross(v)
        self.assertEqual(levels(issues), ["warning"])
        self.assertIn("B", issues[0].message)

    def test_repair_limit_above_retreat_limit(self):
        v = self.base(**{"combat.retreat_limit": 2, "combat.repair_limit": 3})
        self.assertEqual(levels(validate_cross(v)), ["warning"])

    def test_invalid_field_types_do_not_crash_cross_rules(self):
        v = self.base(**{"combat.lbas_groups": "oops", "combat.retreat_limit": None,
                         "combat.retreat_points": 5})
        validate_cross(v)  # 不應丟例外
        validate_all(v)


class StoreCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.cfg = self.dir / "configs" / "config_cui.json"
        self.tpl = self.dir / "config_cui_template.json"

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")


class StoreLoading(StoreCase):
    def test_missing_file_uses_defaults_and_is_dirty(self):
        store = ConfigStore(self.cfg)
        self.assertTrue(store.is_new_file)
        self.assertTrue(store.is_dirty)
        self.assertEqual(store.get("general.chrome_dev_port"), 9222)
        self.assertEqual(len(store.keys()), len(SCHEMA))

    def test_layering_defaults_template_file(self):
        self.write(self.tpl, {"combat.sortie_map": "3-5", "combat.enabled": True})
        self.write(self.cfg, {"combat.sortie_map": "6-4"})
        store = ConfigStore(self.cfg, self.tpl)
        self.assertEqual(store.get("combat.sortie_map"), "6-4")   # 檔案 > 模板
        self.assertTrue(store.get("combat.enabled"))               # 模板 > 預設
        self.assertEqual(store.get("combat.fleet_mode"), "standard")  # 預設
        self.assertFalse(store.is_dirty)

    def test_template_used_when_file_missing(self):
        self.write(self.tpl, {"combat.sortie_map": "3-5"})
        store = ConfigStore(self.cfg, self.tpl)
        self.assertEqual(store.get("combat.sortie_map"), "3-5")
        self.assertTrue(store.is_new_file)

    def test_corrupt_json_raises(self):
        self.cfg.parent.mkdir(parents=True)
        self.cfg.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ConfigLoadError):
            ConfigStore(self.cfg)

    def test_non_object_json_raises(self):
        self.write(self.cfg, [1, 2, 3])
        with self.assertRaises(ConfigLoadError):
            ConfigStore(self.cfg)

    def test_get_returns_copy(self):
        store = ConfigStore(self.cfg)
        store.get("quest.quests").append("Bd1")
        self.assertEqual(store.get("quest.quests"), [])


class StoreEditing(StoreCase):
    def setUp(self):
        super().setUp()
        self.write(self.cfg, {"combat.sortie_map": "1-1"})
        self.store = ConfigStore(self.cfg)

    def test_set_marks_dirty_and_changed(self):
        self.assertFalse(self.store.is_dirty)
        self.store.set("combat.sortie_map", "3-5")
        self.assertTrue(self.store.is_dirty)
        self.assertEqual(self.store.changed_keys(), ["combat.sortie_map"])
        self.assertTrue(self.store.is_changed("combat.sortie_map"))

    def test_setting_back_to_original_is_not_dirty(self):
        self.store.set("combat.sortie_map", "3-5")
        self.store.set("combat.sortie_map", "1-1")
        self.assertFalse(self.store.is_dirty)

    def test_set_returns_issues_but_keeps_value(self):
        issues = self.store.set("general.jst_offset", 99)
        self.assertEqual([i.level for i in issues], ["error"])
        self.assertEqual(self.store.get("general.jst_offset"), 99)
        self.assertTrue(self.store.has_errors())

    def test_set_returns_cross_field_issue(self):
        self.store.set("combat.enabled", True)
        self.store.set("combat.fleet_mode", "ctf")
        issues = self.store.set("pvp.enabled", True)
        self.assertEqual([i.level for i in issues], ["error"])

    def test_reset_and_revert(self):
        self.store.set("combat.sortie_map", "3-5")
        self.store.revert_key("combat.sortie_map")
        self.assertEqual(self.store.get("combat.sortie_map"), "1-1")
        self.store.set("general.jst_offset", 5)
        self.store.reset_key("general.jst_offset")
        self.assertEqual(self.store.get("general.jst_offset"), 0)
        self.store.set("combat.enabled", True)
        self.store.revert_all()
        self.assertFalse(self.store.is_dirty)

    def test_listeners(self):
        seen = []
        self.store.subscribe(seen.append)
        self.store.set("combat.enabled", True)
        self.store.revert_all()
        self.assertEqual(seen, ["combat.enabled", None])


class StoreSaving(StoreCase):
    def test_save_roundtrip_and_clean_state(self):
        store = ConfigStore(self.cfg)
        store.set("combat.enabled", True)
        store.set("combat.fleet_presets", [1, 2])
        store.save()
        self.assertFalse(store.is_dirty)
        reloaded = ConfigStore(self.cfg)
        self.assertTrue(reloaded.get("combat.enabled"))
        self.assertEqual(reloaded.get("combat.fleet_presets"), [1, 2])
        self.assertFalse(reloaded.is_new_file)

    def test_unknown_keys_are_preserved_and_written_after_known_ones(self):
        self.write(self.cfg, {"future.thing": {"a": 1}, "combat.enabled": True})
        store = ConfigStore(self.cfg)
        store.set("combat.sortie_map", "2-3")
        store.set("another.unknown", [1])
        store.save()
        data = json.loads(self.cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["future.thing"], {"a": 1})
        self.assertEqual(data["another.unknown"], [1])
        keys = list(data)
        self.assertEqual(keys[:len(SCHEMA)], list(SCHEMA))
        self.assertEqual(keys[len(SCHEMA):], ["future.thing", "another.unknown"])

    def test_save_refuses_errors_unless_forced(self):
        store = ConfigStore(self.cfg)
        store.set("general.jst_offset", 99)
        with self.assertRaises(ConfigValidationError) as ctx:
            store.save()
        self.assertEqual(len(ctx.exception.issues), 1)
        self.assertFalse(self.cfg.exists())
        store.save(force=True)
        self.assertTrue(self.cfg.exists())

    def test_warnings_do_not_block_save(self):
        store = ConfigStore(self.cfg)
        store.set("combat.lbas_groups", [1])   # warning: 沒有目標節點
        store.save()
        self.assertTrue(self.cfg.exists())

    def test_backup_written_before_overwrite(self):
        self.write(self.cfg, {"combat.sortie_map": "1-1"})
        store = ConfigStore(self.cfg)
        store.set("combat.sortie_map", "3-5")
        store.save()
        backup = json.loads(store.backup_path.read_text(encoding="utf-8"))
        self.assertEqual(backup, {"combat.sortie_map": "1-1"})

    def test_no_backup_for_new_file_and_none_when_disabled(self):
        store = ConfigStore(self.cfg)
        store.save()
        self.assertFalse(store.backup_path.exists())
        store.set("combat.enabled", True)
        store.save(backup=False)
        self.assertFalse(store.backup_path.exists())

    def test_no_temp_files_left_behind(self):
        store = ConfigStore(self.cfg)
        store.save()
        store.set("combat.enabled", True)
        store.save()
        leftovers = [p.name for p in self.cfg.parent.iterdir() if p.suffix == ".tmp"]
        self.assertEqual(leftovers, [])

    def test_failed_write_keeps_original_file(self):
        self.write(self.cfg, {"combat.sortie_map": "1-1"})
        store = ConfigStore(self.cfg)
        store.set("combat.sortie_map", "3-5")
        real_replace = os.replace

        def boom(*_a, **_k):
            raise OSError("disk full")

        os.replace = boom
        try:
            with self.assertRaises(OSError):
                store.save()
        finally:
            os.replace = real_replace
        data = json.loads(self.cfg.read_text(encoding="utf-8"))
        self.assertEqual(data, {"combat.sortie_map": "1-1"})
        self.assertTrue(store.is_dirty)  # 沒存成功,仍是 dirty
        leftovers = [p.name for p in self.cfg.parent.iterdir() if p.suffix == ".tmp"]
        self.assertEqual(leftovers, [])

    def test_output_is_utf8_pretty_json(self):
        store = ConfigStore(self.cfg)
        store.set("combat.node_selects", ["A>B"])
        store.save()
        text = self.cfg.read_text(encoding="utf-8")
        self.assertTrue(text.endswith("}\n"))
        self.assertIn('    "combat.node_selects": [', text)


if __name__ == "__main__":
    unittest.main()
