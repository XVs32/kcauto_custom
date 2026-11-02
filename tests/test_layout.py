import unittest
from pathlib import Path

from tui.layout import (
    ALL_CLASSES,
    CARD_MIN_WIDTH,
    CHROME_ROWS,
    LOG_BOTTOM,
    LOG_HIDDEN,
    LOG_MIN_HEIGHT,
    LOG_MIN_WIDTH,
    LOG_RIGHT,
    MAX_COLUMNS,
    MIN_CARD_HEIGHT,
    SCROLLBAR_WIDTH,
    LayoutPlan,
    card_heights,
    choose_layout,
    grid_height,
)
from tui.modules import CARDS, move_index
from tui.schema import defaults
from tui.summaries import LINE_MAX, summarize

CSS = (Path(__file__).resolve().parent.parent / "tui" / "theme.tcss").read_text(
    encoding="utf-8"
)


class Heights(unittest.TestCase):
    def test_default_heights(self):
        heights = card_heights(defaults())
        self.assertEqual(len(heights), len(CARDS))
        self.assertTrue(all(h >= MIN_CARD_HEIGHT for h in heights))
        # expedition: 1 line of fleet settings + 1 line of auto assign + top and bottom borders
        self.assertEqual(heights[1], 4)

    def test_heights_grow_with_content(self):
        v = defaults()
        v["combat.push_nodes"] = ["A", "B"]
        before = card_heights(defaults())[0]
        after = card_heights(v)[0]
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

    def test_wide_keeps_two_columns_when_cards_fit_and_gives_the_log_the_rest(self):
        for width in (120, 150, 180, 400):
            self.assertEqual(self.plan(width, 40), LayoutPlan(2, LOG_RIGHT), width)

    def test_more_columns_only_when_two_do_not_fit_the_height(self):
        need2 = CHROME_ROWS + grid_height(self.heights, 2)
        need3 = CHROME_ROWS + grid_height(self.heights, 3)
        self.assertGreater(
            need2, need3
        )  # with the default content 3 columns is shorter
        self.assertEqual(self.plan(180, need2), LayoutPlan(2, LOG_RIGHT))
        self.assertEqual(self.plan(180, need2 - 1), LayoutPlan(3, LOG_RIGHT))
        self.assertEqual(
            self.plan(180, need3 - 1).columns, 4
        )  # only use 4 columns when 3 do not fit either
        # when the width is not enough, the column count is limited by the log's minimum width
        self.assertEqual(self.plan(120, 10), LayoutPlan(2, LOG_RIGHT))
        self.assertEqual(self.plan(150, 10), LayoutPlan(3, LOG_RIGHT))
        self.assertEqual(
            self.plan(400, 10), LayoutPlan(4, LOG_RIGHT)
        )  # upper limit of 4 columns

    def test_column_thresholds(self):
        step = CARD_MIN_WIDTH
        base = LOG_MIN_WIDTH + SCROLLBAR_WIDTH
        h = 10  # very short: always use the most columns the width allows
        self.assertEqual(self.plan(base + 2 * step, h).columns, 2)
        self.assertEqual(self.plan(base + 3 * step - 1, h).columns, 2)
        self.assertEqual(self.plan(base + 3 * step, h).columns, 3)
        self.assertEqual(self.plan(base + 4 * step, h).columns, 4)
        # one column short is not enough: the log moves below
        self.assertNotEqual(self.plan(base + step - 1, 60).log, LOG_RIGHT)
        self.assertNotEqual(
            self.plan(base + 2 * step - 1, h).log, LOG_RIGHT
        )  # one column does not fit either

    def test_one_column_when_it_fits_the_height(self):
        need1 = CHROME_ROWS + grid_height(self.heights, 1)
        base = LOG_MIN_WIDTH + SCROLLBAR_WIDTH
        self.assertEqual(self.plan(300, need1), LayoutPlan(1, LOG_RIGHT))
        self.assertEqual(
            self.plan(300, need1 - 1).columns, 2
        )  # one row short → switch to 2 columns
        self.assertEqual(
            self.plan(base + CARD_MIN_WIDTH, need1), LayoutPlan(1, LOG_RIGHT)
        )

    def test_wide_ignores_height(self):
        self.assertEqual(self.plan(120, 10), LayoutPlan(2, LOG_RIGHT))

    def test_narrow_with_enough_height_puts_log_below(self):
        plan = self.plan(70, 60)  # so narrow that even 1 column + the log does not fit
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
        # a single column is taller, so the log may not fit at the same height
        needed_2 = CHROME_ROWS + grid_height(self.heights, 2) + LOG_MIN_HEIGHT
        self.assertEqual(self.plan(50, needed_2).log, LOG_HIDDEN)

    def test_invariants_over_many_sizes(self):
        for w in range(10, 301, 3):
            for h in (10, 24, 30, 45, 60, 100):
                plan = self.plan(w, h)
                self.assertTrue(1 <= plan.columns <= MAX_COLUMNS, (w, h, plan))
                self.assertIn(plan.log, (LOG_RIGHT, LOG_BOTTOM, LOG_HIDDEN))
                if plan.log == LOG_RIGHT:
                    self.assertGreaterEqual(plan.columns, 1, (w, h))
                    # card area + log fit
                    used = plan.columns * CARD_MIN_WIDTH + SCROLLBAR_WIDTH
                    self.assertGreaterEqual(w - used, LOG_MIN_WIDTH, (w, h))
                else:
                    # cards use the full width, each column not narrower than the minimum width (except an extremely narrow single column)
                    if plan.columns > 1:
                        self.assertGreaterEqual(
                            (w - SCROLLBAR_WIDTH) // plan.columns, CARD_MIN_WIDTH
                        )

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
    """The constants in layout.py must match the values in theme.tcss."""

    def test_grid_sizes_for_every_column_count(self):
        for n in range(1, MAX_COLUMNS + 1):
            self.assertIn(f"#main.cols-{n} #cards {{ grid-size: {n}; }}", CSS)

    def test_right_mode_widths(self):
        for n in range(1, MAX_COLUMNS + 1):
            width = n * CARD_MIN_WIDTH + SCROLLBAR_WIDTH
            self.assertIn(f"#main.log-right.cols-{n} #cards {{ width: {width}; }}", CSS)

    def test_heights_match(self):
        self.assertIn(f"min-height: {LOG_MIN_HEIGHT};", CSS)
        self.assertIn(f"min-height: {MIN_CARD_HEIGHT};", CSS)

    def test_every_layout_class_has_rules(self):
        for name in ("log-right", "log-bottom", "log-hidden"):
            self.assertIn(f"#main.{name}", CSS)

    def test_fullscreen_log_rules_come_after_hidden_rules(self):
        # with the same selector weight the later rule wins; the full-screen log must override log-hidden's display: none
        hidden = CSS.index("#main.log-hidden #log-box")
        full = CSS.index("#main.log-full #log-box")
        self.assertGreater(full, hidden)
        self.assertIn("#main.log-full #cards { display: none; }", CSS)

    def test_summary_lines_fit_in_a_card(self):
        # inner card width = 34 − border 2 − padding 2; one less when there is a scrollbar (cell width 33)
        self.assertLessEqual(LINE_MAX + 4 + 1, CARD_MIN_WIDTH)

    def test_long_values_never_exceed_line_max(self):
        v = defaults()
        v.update(
            {
                "combat.sortie_map": "E-1",
                "combat.fleet_presets": list(range(1, 16)),
                "combat.push_nodes": list("ABCDEFGHIJ"),
                "combat.lbas_groups": [1, 2, 3],
                "expedition.fleet_2": list(range(1, 30)),
                "quest.quests": [f"Bd{i}" for i in range(20)],
                "scheduler.rules": ["time:0230:stop:kcauto:with_a_very_long_extra"] * 5,
                "factory.build_recipe": [4000, 4000, 4000, 4000],
                "factory.develop_recipe": [300, 300, 300, 300],
            }
        )
        for spec in CARDS:
            for text, _ in summarize(spec.module, v):
                self.assertLessEqual(len(text), LINE_MAX, (spec.module, text))


class GridNavigationWithColumns(unittest.TestCase):
    def test_three_columns(self):
        self.assertEqual(move_index(0, 1, 0, columns=3), 1)
        self.assertEqual(move_index(2, 1, 0, columns=3), 2)  # right edge
        self.assertEqual(move_index(1, 0, 1, columns=3), 4)
        self.assertEqual(move_index(3, -1, 0, columns=3), 3)  # left edge

    def test_four_columns_with_ragged_last_row(self):
        self.assertEqual(move_index(8, 1, 0, count=10, columns=4), 9)
        self.assertEqual(move_index(9, 1, 0, count=10, columns=4), 9)
        self.assertEqual(move_index(5, 0, 1, count=10, columns=4), 9)
        self.assertEqual(move_index(6, 0, 1, count=10, columns=4), 6)  # no box below

    def test_single_column(self):
        self.assertEqual(move_index(3, 0, 1, count=10, columns=1), 4)
        self.assertEqual(move_index(3, 1, 0, count=10, columns=1), 3)


if __name__ == "__main__":
    unittest.main()
