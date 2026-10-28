import unittest
from pathlib import Path

from tui.layout import (
    ALL_CLASSES, CARD_MIN_WIDTH, CHROME_ROWS, LOG_BOTTOM, LOG_HIDDEN,
    LOG_MIN_HEIGHT, LOG_MIN_WIDTH, LOG_RIGHT, MAX_COLUMNS, MIN_CARD_HEIGHT,
    SCROLLBAR_WIDTH, LayoutPlan, card_heights, choose_layout, grid_height,
)
from tui.modules import CARDS, move_index
from tui.schema import defaults
from tui.summaries import LINE_MAX, summarize

CSS = (Path(__file__).resolve().parent.parent / "tui" / "theme.tcss").read_text(
    encoding="utf-8")


class Heights(unittest.TestCase):
    def test_default_heights(self):
        heights = card_heights(defaults())
        self.assertEqual(len(heights), len(CARDS))
        self.assertTrue(all(h >= MIN_CARD_HEIGHT for h in heights))
        # expedition:3 行艦隊目的地 + 1 行 preset + 上下邊框
        self.assertEqual(heights[1], 6)

    def test_heights_grow_with_content(self):
        v = defaults()
        v["scheduler.rules"] = ["a:1:b:c"] * 6
        before = card_heights(defaults())[4]
        after = card_heights(v)[4]
        self.assertGreater(after, before)

    def test_grid_height(self):
        heights = [4, 8, 4, 4]
        self.assertEqual(grid_height(heights, 1), 20)
        self.assertEqual(grid_height(heights, 2), 12)
        self.assertEqual(grid_height(heights, 3), 12)
        self.assertEqual(grid_height(heights, 4), 8)


class Planner(unittest.TestCase):
    def setUp(self):
        self.heights = card_heights(defaults())

    def plan(self, w, h):
        return choose_layout(w, h, self.heights)

    def test_wide_puts_log_right_with_more_columns(self):
        self.assertEqual(self.plan(120, 40), LayoutPlan(2, LOG_RIGHT))
        self.assertEqual(self.plan(150, 40), LayoutPlan(3, LOG_RIGHT))
        self.assertEqual(self.plan(180, 40), LayoutPlan(4, LOG_RIGHT))
        self.assertEqual(self.plan(400, 40), LayoutPlan(4, LOG_RIGHT))   # 上限 4 欄

    def test_column_thresholds(self):
        step = CARD_MIN_WIDTH
        base = LOG_MIN_WIDTH + SCROLLBAR_WIDTH
        self.assertEqual(self.plan(base + 2 * step, 40).columns, 2)
        self.assertEqual(self.plan(base + 3 * step - 1, 40).columns, 2)
        self.assertEqual(self.plan(base + 3 * step, 40).columns, 3)
        self.assertEqual(self.plan(base + 4 * step, 40).columns, 4)
        # 差 1 欄就不夠:日誌改到下方
        self.assertNotEqual(self.plan(base + 2 * step - 1, 60).log, LOG_RIGHT)

    def test_wide_ignores_height(self):
        self.assertEqual(self.plan(120, 10), LayoutPlan(2, LOG_RIGHT))

    def test_narrow_with_enough_height_puts_log_below(self):
        plan = self.plan(80, 60)
        self.assertEqual(plan, LayoutPlan(2, LOG_BOTTOM))

    def test_narrow_and_short_hides_log(self):
        self.assertEqual(self.plan(80, 24), LayoutPlan(2, LOG_HIDDEN))

    def test_bottom_boundary_is_exact(self):
        needed = CHROME_ROWS + grid_height(self.heights, 2) + LOG_MIN_HEIGHT
        self.assertEqual(self.plan(80, needed).log, LOG_BOTTOM)
        self.assertEqual(self.plan(80, needed - 1).log, LOG_HIDDEN)

    def test_very_narrow_uses_one_column(self):
        self.assertEqual(self.plan(50, 100), LayoutPlan(1, LOG_BOTTOM))
        self.assertEqual(self.plan(20, 100).columns, 1)

    def test_one_column_needs_more_height(self):
        # 單欄更高,同樣高度下可能放不下日誌
        needed_2 = CHROME_ROWS + grid_height(self.heights, 2) + LOG_MIN_HEIGHT
        self.assertEqual(self.plan(50, needed_2).log, LOG_HIDDEN)

    def test_invariants_over_many_sizes(self):
        for w in range(10, 301, 3):
            for h in (10, 24, 30, 45, 60, 100):
                plan = self.plan(w, h)
                self.assertTrue(1 <= plan.columns <= MAX_COLUMNS, (w, h, plan))
                self.assertIn(plan.log, (LOG_RIGHT, LOG_BOTTOM, LOG_HIDDEN))
                if plan.log == LOG_RIGHT:
                    self.assertGreaterEqual(plan.columns, 2, (w, h))
                    # 方框區 + 日誌放得下
                    used = plan.columns * CARD_MIN_WIDTH + SCROLLBAR_WIDTH
                    self.assertGreaterEqual(w - used, LOG_MIN_WIDTH, (w, h))
                else:
                    # 方框用滿寬度,每欄不小於最小寬度(除了極窄的單欄)
                    if plan.columns > 1:
                        self.assertGreaterEqual(
                            (w - SCROLLBAR_WIDTH) // plan.columns, CARD_MIN_WIDTH)

    def test_columns_never_decrease_when_widening_with_log_right(self):
        last = 0
        for w in range(110, 400):
            plan = self.plan(w, 40)
            self.assertEqual(plan.log, LOG_RIGHT)
            self.assertGreaterEqual(plan.columns, last)
            last = plan.columns

    def test_plan_classes(self):
        self.assertEqual(LayoutPlan(3, LOG_RIGHT).classes, ("cols-3", "log-right"))
        for name in LayoutPlan(4, LOG_HIDDEN).classes:
            self.assertIn(name, ALL_CLASSES)


class CssStaysInSync(unittest.TestCase):
    """layout.py 的常數與 theme.tcss 的數值必須一致。"""

    def test_grid_sizes_for_every_column_count(self):
        for n in range(1, MAX_COLUMNS + 1):
            self.assertIn(f"#main.cols-{n} #cards {{ grid-size: {n}; }}", CSS)

    def test_right_mode_widths(self):
        for n in range(2, MAX_COLUMNS + 1):
            width = n * CARD_MIN_WIDTH + SCROLLBAR_WIDTH
            self.assertIn(
                f"#main.log-right.cols-{n} #cards {{ width: {width}; }}", CSS)

    def test_heights_match(self):
        self.assertIn(f"min-height: {LOG_MIN_HEIGHT};", CSS)
        self.assertIn(f"min-height: {MIN_CARD_HEIGHT};", CSS)

    def test_every_layout_class_has_rules(self):
        for name in ("log-right", "log-bottom", "log-hidden"):
            self.assertIn(f"#main.{name}", CSS)

    def test_fullscreen_log_rules_come_after_hidden_rules(self):
        # 同樣的選擇器權重下,後面的規則勝出;全螢幕日誌必須覆蓋 log-hidden 的 display: none
        hidden = CSS.index("#main.log-hidden #log-box")
        full = CSS.index("#main.log-full #log-box")
        self.assertGreater(full, hidden)
        self.assertIn("#main.log-full #cards { display: none; }", CSS)

    def test_summary_lines_fit_in_a_card(self):
        # 方框內寬 = 34 − 邊框 2 − padding 2;有捲軸時再少 1(格寬 33)
        self.assertLessEqual(LINE_MAX + 4 + 1, CARD_MIN_WIDTH)

    def test_long_values_never_exceed_line_max(self):
        v = defaults()
        v.update({
            "combat.sortie_map": "E-1", "combat.fleet_presets": list(range(1, 16)),
            "combat.push_nodes": list("ABCDEFGHIJ"), "combat.lbas_groups": [1, 2, 3],
            "expedition.fleet_2": list(range(1, 30)),
            "quest.quests": [f"Bd{i}" for i in range(20)],
            "scheduler.rules": ["time:0230:stop:kcauto:with_a_very_long_extra"] * 5,
            "factory.build_recipe": [4000, 4000, 4000, 4000],
            "factory.develop_recipe": [300, 300, 300, 300],
        })
        for spec in CARDS:
            for text, _ in summarize(spec.module, v):
                self.assertLessEqual(len(text), LINE_MAX, (spec.module, text))


class GridNavigationWithColumns(unittest.TestCase):
    def test_three_columns(self):
        self.assertEqual(move_index(0, 1, 0, columns=3), 1)
        self.assertEqual(move_index(2, 1, 0, columns=3), 2)      # 右緣
        self.assertEqual(move_index(1, 0, 1, columns=3), 4)
        self.assertEqual(move_index(3, -1, 0, columns=3), 3)     # 左緣

    def test_four_columns_with_ragged_last_row(self):
        self.assertEqual(move_index(8, 1, 0, count=10, columns=4), 9)
        self.assertEqual(move_index(9, 1, 0, count=10, columns=4), 9)
        self.assertEqual(move_index(5, 0, 1, count=10, columns=4), 9)
        self.assertEqual(move_index(6, 0, 1, count=10, columns=4), 6)   # 下方沒有方框

    def test_single_column(self):
        self.assertEqual(move_index(3, 0, 1, count=10, columns=1), 4)
        self.assertEqual(move_index(3, 1, 0, count=10, columns=1), 3)


if __name__ == "__main__":
    unittest.main()
