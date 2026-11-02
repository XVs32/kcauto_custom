import unittest

from tui import akashi
from tui.store import ConfigStore


class AkashiTests(unittest.TestCase):
    def test_slots_match_reference(self):
        self.assertEqual(sorted(akashi.AKASHI_SLOTS), ["1", "2", "3", "4", "5", "6"])
        self.assertEqual(
            akashi.AKASHI_SLOTS["1"], "morale:!=:0|ship:187:>=:1:>=:0:!=:0::"
        )
        rule = akashi.AKASHI_SLOTS["2"]
        self.assertTrue(
            rule.startswith("damage:==:0,damage:>=:3|class:1:!=:1:==:1:!=:0::,")
        )
        self.assertTrue(rule.endswith("class:22:!=:1:==:2:!=:0::"))
        self.assertEqual(rule.count("class:"), 40)  # 20 ship classes × 2
        self.assertNotIn("class:12:", rule)
        self.assertNotIn("class:15:", rule)
        for i in "3456":
            self.assertEqual(akashi.AKASHI_SLOTS[i], rule)
        self.assertEqual(len(rule), 1045)

    def test_slots_for(self):
        self.assertEqual(akashi.slots_for(False, {"1": "x"}), {})
        self.assertEqual(akashi.slots_for(True, {}), akashi.AKASHI_SLOTS)
        self.assertEqual(akashi.slots_for(True, {"1": "x"}), {"1": "x"})

    def test_returns_copies(self):
        a = akashi.akashi_slots()
        a["1"] = "changed"
        self.assertNotEqual(akashi.AKASHI_SLOTS["1"], "changed")


class StoreLinkTests(unittest.TestCase):
    def make(self, tmp):
        return ConfigStore(tmp + "/config.json")

    def test_enable_fills_slots_and_disable_clears(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = self.make(tmp)
            store.set("ship_switcher.enabled", True)
            self.assertEqual(store.get("ship_switcher.slots"), akashi.AKASHI_SLOTS)
            self.assertEqual(akashi.state(store.as_dict()), "akashi")
            store.set("ship_switcher.enabled", False)
            self.assertEqual(store.get("ship_switcher.slots"), {})
            self.assertEqual(akashi.state(store.as_dict()), "off")

    def test_reset_and_revert_keep_both_keys_consistent(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = self.make(tmp)
            store.set("ship_switcher.enabled", True)
            store.reset_key("ship_switcher.enabled")
            self.assertEqual(store.get("ship_switcher.slots"), {})
            store.set("ship_switcher.enabled", True)
            store.revert_key("ship_switcher.enabled")
            self.assertFalse(store.get("ship_switcher.enabled"))
            self.assertEqual(store.get("ship_switcher.slots"), {})


class CombatExclusionTests(unittest.TestCase):
    def make(self, tmp, values=None):
        import json

        path = tmp + "/config.json"
        if values is not None:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(values, fh)
        return ConfigStore(path)

    def test_enabling_combat_turns_akashi_off(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = self.make(tmp)
            store.set("ship_switcher.enabled", True)
            self.assertEqual(store.pop_forced(), [])
            store.set("combat.enabled", True)
            self.assertFalse(store.get("ship_switcher.enabled"))
            self.assertEqual(store.get("ship_switcher.slots"), {})
            self.assertEqual(store.pop_forced(), ["akashi"])
            self.assertEqual(store.pop_forced(), [])  # reading clears it

    def test_akashi_cannot_be_enabled_while_combat_is_enabled(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = self.make(tmp)
            store.set("combat.enabled", True)
            store.set("ship_switcher.enabled", True)
            self.assertFalse(store.get("ship_switcher.enabled"))
            self.assertEqual(store.get("ship_switcher.slots"), {})
            self.assertEqual(store.pop_forced(), ["akashi"])
            store.set(
                "combat.enabled", False
            )  # turning combat off turns Akashi repair on
            self.assertTrue(store.get("ship_switcher.enabled"))
            self.assertEqual(store.get("ship_switcher.slots"), akashi.AKASHI_SLOTS)
            self.assertEqual(store.pop_forced(), ["combat_off"])

    def test_inconsistent_file_is_corrected_on_load_and_shows_as_modified(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = self.make(
                tmp,
                {
                    "combat.enabled": True,
                    "ship_switcher.enabled": True,
                    "ship_switcher.slots": akashi.akashi_slots(),
                },
            )
            self.assertFalse(store.get("ship_switcher.enabled"))
            self.assertIn("ship_switcher.enabled", store.changed_keys())
            self.assertEqual(store.pop_forced(), ["akashi"])

    def test_revert_cannot_restore_a_conflicting_state(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = self.make(
                tmp,
                {
                    "ship_switcher.enabled": True,
                    "ship_switcher.slots": akashi.akashi_slots(),
                },
            )
            store.set("combat.enabled", True)
            store.revert_key("ship_switcher.enabled")
            self.assertFalse(store.get("ship_switcher.enabled"))
            store.revert_all()
            self.assertTrue(
                store.get("ship_switcher.enabled")
            )  # the two did not conflict at save time anyway

    def test_disabling_combat_turns_on_akashi_and_passive_repair(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = self.make(tmp, {"combat.enabled": True})
            self.assertFalse(store.get("passive_repair.enabled"))
            self.assertFalse(store.get("ship_switcher.enabled"))
            store.pop_forced()
            store.set("combat.enabled", False)
            self.assertTrue(store.get("ship_switcher.enabled"))
            self.assertEqual(store.get("ship_switcher.slots"), akashi.AKASHI_SLOTS)
            self.assertTrue(store.get("passive_repair.enabled"))
            self.assertEqual(store.pop_forced(), ["combat_off"])

    def test_enabling_combat_does_not_touch_passive_repair(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = self.make(tmp)
            store.set("passive_repair.enabled", True)
            store.set("combat.enabled", True)
            self.assertTrue(store.get("passive_repair.enabled"))  # no reverse reaction
            self.assertEqual(store.pop_forced(), [])

    def test_only_a_real_toggle_triggers_it(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = self.make(tmp)  # combat is already off
            store.set("combat.enabled", False)  # off → off is not a toggle
            self.assertFalse(store.get("passive_repair.enabled"))
            store.set("combat.enabled", True)
            store.revert_key("combat.enabled")  # revert is an undo, not a toggle
            self.assertFalse(store.get("passive_repair.enabled"))
            self.assertFalse(store.get("ship_switcher.enabled"))

    def test_reset_to_default_counts_as_turning_combat_off(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = self.make(tmp)
            store.set("combat.enabled", True)
            store.reset_key("combat.enabled")
            self.assertTrue(store.get("passive_repair.enabled"))

    def test_other_modules_are_not_affected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = self.make(tmp)
            store.set("expedition.enabled", True)
            store.set("ship_switcher.enabled", True)
            self.assertTrue(store.get("ship_switcher.enabled"))


if __name__ == "__main__":
    unittest.main()
