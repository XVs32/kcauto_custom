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
        reserved = set(
            "qwabkl?"
        )  # quit, save, apply, pause(break), stop(kill), log, help
        self.assertFalse(reserved & {c.hotkey for c in CARDS})

    def test_only_general_is_not_toggleable(self):
        self.assertEqual([c.module for c in CARDS if not c.toggleable], ["general"])
        self.assertEqual(CARD_BY_MODULE["combat"].enabled_key, "combat.enabled")

    def test_hotkey_markup(self):
        self.assertEqual(hotkey_markup("combat", "c", "b"), "[b]c[/]ombat")
        self.assertEqual(hotkey_markup("quests", "u", "b"), "q[b]u[/]ests")
        self.assertEqual(
            hotkey_markup("ship switcher", "h", "b"), "s[b]h[/]ip switcher"
        )
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
        # 5 boxes: nothing exists to the right of or below the last cell (index 4)
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
        text = self.text(
            "combat",
            **{
                "combat.sortie_map": "6-4",
                "combat.fleet_mode": "ctf",
                "combat.fleet_presets": [1, 2],
            },
        )
        self.assertIn("6-4  ctf", text)
        self.assertIn("preset 1,2", text)
        self.assertNotIn("push", text)

    def test_combat_push_nodes_are_flagged(self):
        lines = summarize(
            "combat",
            self.values(**{"combat.push_nodes": ["D", "Z"], "combat.override": True}),
        )
        push = [(t, s) for t, s in lines if "push" in t]
        self.assertEqual(push, [("⚠ push D,Z", "bold red")])

    def test_combat_settings_are_dimmed_while_override_is_off(self):
        lines = summarize(
            "combat",
            self.values(
                **{
                    "combat.push_nodes": ["D"],
                    "combat.lbas_groups": [1],
                    "combat.override": False,
                }
            ),
        )
        self.assertEqual(
            [(t, s) for t, s in lines if "push" in t or "LBAS" in t],
            [("LBAS 1", "dim"), ("⚠ push D", "dim")],
        )

    def test_expedition_one_line_of_fleets_and_auto_assign(self):
        text = self.text(
            "expedition",
            **{
                "expedition.fleet_2": ["auto"],
                "expedition.fleet_3": [5, 21],
                "expedition.fleet_4": ["overnight"],
                "expedition.fleet_preset": "auto",
                "expedition.desire_oil": 300000,
            },
        )
        self.assertEqual(text.split("\n")[0].split(), ["auto", "5,21", "overnight"])
        self.assertIn("auto assign", text.split("\n")[1])
        self.assertNotIn("no auto", text)
        self.assertNotIn("fleet", text)
        self.assertNotIn("300000", text)

    def test_expedition_without_auto_assign(self):
        text = self.text("expedition", **{"expedition.fleet_preset": None})
        self.assertIn("no auto assign", text)

    def test_pvp_unset_preset(self):
        self.assertIn("preset -", self.text("pvp"))
        self.assertIn("preset auto", self.text("pvp", **{"pvp.fleet_preset": "auto"}))

    def test_quest_counts_and_truncates(self):
        self.assertIn("0 quests", self.text("quest"))
        self.assertIn(
            "1 quest\n", self.text("quest", **{"quest.quests": ["Bd1"]}) + "\n"
        )
        many = [f"Bd{i}" for i in range(1, 10)]
        text = self.text("quest", **{"quest.quests": many})
        self.assertIn("9 quests", text)
        self.assertIn("…", text)

    def test_scheduler_reads_naturally(self):
        rules = ["time:0230:stop:kcauto", "sorties_run:15:stop:combat", "c:3:stop:z"]
        lines = self.text("scheduler", **{"scheduler.rules": rules}).split("\n")
        self.assertEqual(lines, ["stop kcauto at 02:30", "stop combat at 15 sorties"])
        self.assertNotIn("rules", "".join(lines))
        one = self.text(
            "scheduler", **{"scheduler.rules": ["sorties_run:1:stop:combat"]}
        )
        self.assertEqual(one, "stop combat at 1 sortie")

    def test_scheduler_without_rules(self):
        self.assertEqual(
            self.text("scheduler", **{"scheduler.rules": []}), "no stop rules"
        )

    def test_ship_switcher_shows_akashi_state(self):
        from tui import akashi

        self.assertIn("off", self.text("ship_switcher"))
        on = self.text(
            "ship_switcher",
            **{
                "ship_switcher.enabled": True,
                "ship_switcher.slots": akashi.akashi_slots(),
            },
        )
        self.assertIn("Akashi repair  on", on)
        self.assertIn(
            "off (combat on)", self.text("ship_switcher", **{"combat.enabled": True})
        )
        custom = self.text(
            "ship_switcher",
            **{"ship_switcher.enabled": True, "ship_switcher.slots": {"1": "x"}},
        )
        self.assertIn("custom rules (1 slots)", custom)

    def test_general_formats_jst_sign(self):
        self.assertIn("JST   +0", self.text("general"))
        self.assertIn("JST   -3", self.text("general", **{"general.jst_offset": -3}))

    def test_broken_values_never_raise(self):
        broken = self.values(
            **{
                "combat.fleet_presets": 5,
                "combat.push_nodes": object(),
                "expedition.desire_oil": None,
                "quest.quests": "oops",
                "scheduler.rules": None,
                "factory.build_recipe": None,
                "ship_switcher.slots": [],
                "general.jst_offset": "x",
            }
        )
        for module in MODULES:
            self.assertTrue(summarize(module, broken), module)

    def test_missing_key_is_reported_not_raised(self):
        lines = summarize("combat", {})
        self.assertEqual(lines[0][1], "red")


if __name__ == "__main__":
    unittest.main()
