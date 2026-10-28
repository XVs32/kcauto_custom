import unittest

from tui.modules import CARDS, CARD_BY_MODULE, GRID_COLUMNS, hotkey_markup, move_index
from tui.schema import MODULES, defaults
from tui.summaries import fmt_amount, meter, summarize


class CardMetadata(unittest.TestCase):
    def test_every_module_has_exactly_one_card(self):
        self.assertEqual(sorted(c.module for c in CARDS), sorted(MODULES))

    def test_hotkeys_unique_and_in_label(self):
        keys = [c.hotkey for c in CARDS]
        self.assertEqual(len(keys), len(set(keys)))
        for card in CARDS:
            self.assertIn(card.hotkey, card.label.lower())

    def test_hotkeys_do_not_clash_with_app_keys(self):
        reserved = set("qwabkl?")  # quit, save, apply, pause(break), stop(kill), log, help
        self.assertFalse(reserved & {c.hotkey for c in CARDS})

    def test_only_general_is_not_toggleable(self):
        self.assertEqual([c.module for c in CARDS if not c.toggleable], ["general"])
        self.assertEqual(CARD_BY_MODULE["combat"].enabled_key, "combat.enabled")

    def test_hotkey_markup(self):
        self.assertEqual(hotkey_markup("combat", "c", "b"), "[b]c[/]ombat")
        self.assertEqual(hotkey_markup("quests", "u", "b"), "q[b]u[/]ests")
        self.assertEqual(hotkey_markup("ship switcher", "h", "b"), "s[b]h[/]ip switcher")
        with self.assertRaises(ValueError):
            hotkey_markup("combat", "z")


class GridNavigation(unittest.TestCase):
    def test_moves_inside_grid(self):
        self.assertEqual(move_index(0, 1, 0), 1)
        self.assertEqual(move_index(0, 0, 1), GRID_COLUMNS)
        self.assertEqual(move_index(3, -1, 0), 2)
        self.assertEqual(move_index(3, 0, -1), 1)

    def test_edges_stay_put(self):
        self.assertEqual(move_index(0, -1, 0), 0)
        self.assertEqual(move_index(0, 0, -1), 0)
        self.assertEqual(move_index(1, 1, 0), 1)
        last = len(CARDS) - 1
        self.assertEqual(move_index(last, 0, 1), last)

    def test_odd_count_last_row(self):
        # 5 個方框:最後一格(index 4)的右邊、下面都不存在
        self.assertEqual(move_index(4, 1, 0, count=5), 4)
        self.assertEqual(move_index(3, 0, 1, count=5), 3)
        self.assertEqual(move_index(2, 1, 0, count=5), 3)


class Formatting(unittest.TestCase):
    def test_fmt_amount(self):
        self.assertEqual(fmt_amount(350000), "350k")
        self.assertEqual(fmt_amount(1500), "1.5k")
        self.assertEqual(fmt_amount(300), "300")
        self.assertEqual(fmt_amount(0), "0")
        self.assertEqual(fmt_amount("x"), "x")

    def test_meter(self):
        self.assertEqual(meter(350000, 350000), "█" * 8)
        self.assertEqual(meter(0, 350000), "░" * 8)
        self.assertEqual(meter(175000, 350000), "████░░░░")
        self.assertEqual(meter(10**9, 350000), "█" * 8)
        self.assertEqual(meter(-5, 350000), "░" * 8)
        self.assertEqual(meter("x", 350000), "░" * 8)
        self.assertEqual(meter(True, 350000), "░" * 8)
        self.assertEqual(meter(5, 0), "░" * 8)


class Summaries(unittest.TestCase):
    def values(self, **over):
        v = defaults()
        v.update(over)
        return v

    def text(self, module, **over):
        return "\n".join(t for t, _ in summarize(module, self.values(**over)))

    def test_every_module_summarizes_defaults(self):
        for module in MODULES:
            lines = summarize(module, defaults())
            self.assertTrue(lines, module)
            for text, style in lines:
                self.assertIsInstance(text, str)
                self.assertIsInstance(style, str)

    def test_combat(self):
        text = self.text("combat", **{"combat.sortie_map": "6-4",
                                      "combat.fleet_mode": "ctf",
                                      "combat.fleet_presets": [1, 2]})
        self.assertIn("6-4  ctf", text)
        self.assertIn("preset 1,2", text)
        self.assertNotIn("push", text)

    def test_combat_push_nodes_are_flagged(self):
        lines = summarize("combat", self.values(**{"combat.push_nodes": ["D", "Z"]}))
        push = [(t, s) for t, s in lines if "push" in t]
        self.assertEqual(push, [("⚠ push D,Z", "bold red")])

    def test_expedition_shows_destinations_and_preset_only(self):
        text = self.text("expedition", **{
            "expedition.fleet_2": ["auto"], "expedition.fleet_3": [5, 21],
            "expedition.fleet_4": [], "expedition.fleet_preset": "auto",
            "expedition.desire_oil": 300000})
        self.assertIn("fleet 2  auto", text)
        self.assertIn("fleet 3  5,21", text)
        self.assertIn("fleet 4  -", text)
        self.assertIn("preset   auto", text)
        self.assertNotIn("oil", text)            # 資源目標量不再顯示
        self.assertNotIn("300k", text)

    def test_expedition_without_preset(self):
        self.assertIn("preset   -", self.text("expedition"))

    def test_pvp_unset_preset(self):
        self.assertIn("preset -", self.text("pvp"))
        self.assertIn("preset auto", self.text("pvp", **{"pvp.fleet_preset": "auto"}))

    def test_quest_counts_and_truncates(self):
        self.assertIn("0 quests", self.text("quest"))
        self.assertIn("1 quest\n", self.text("quest", **{"quest.quests": ["Bd1"]}) + "\n")
        many = [f"Bd{i}" for i in range(1, 10)]
        text = self.text("quest", **{"quest.quests": many})
        self.assertIn("9 quests", text)
        self.assertIn("…", text)

    def test_scheduler_lists_rules(self):
        rules = ["time:0230:stop:kcauto", "sorties_run:15:stop:combat",
                 "a:1:stop:x", "b:2:stop:y", "c:3:stop:z"]
        text = self.text("scheduler", **{"scheduler.rules": rules})
        self.assertIn("5 rules", text)
        self.assertIn("time:0230:stop:kcauto", text)
        self.assertIn("+2 more", text)

    def test_general_formats_jst_sign(self):
        self.assertIn("JST   +0", self.text("general"))
        self.assertIn("JST   -3", self.text("general", **{"general.jst_offset": -3}))

    def test_broken_values_never_raise(self):
        broken = self.values(**{
            "combat.fleet_presets": 5, "combat.push_nodes": object(),
            "expedition.desire_oil": None, "quest.quests": "oops",
            "scheduler.rules": None, "factory.build_recipe": None,
            "ship_switcher.slots": [], "general.jst_offset": "x",
        })
        for module in MODULES:
            self.assertTrue(summarize(module, broken), module)

    def test_missing_key_is_reported_not_raised(self):
        lines = summarize("combat", {})
        self.assertEqual(lines[0][1], "red")


if __name__ == "__main__":
    unittest.main()
