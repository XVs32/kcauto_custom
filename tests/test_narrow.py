"""窄視窗的純函式測試。"""
import unittest

from tui.editor import narrow as N
from tui.editor.model import MODULE_ENTRIES, cell_len
from tui.layout import fit_segments


class FitSegmentsTests(unittest.TestCase):
    PARTS = [("title", 10), ("state", 8), ("mode", 12), ("file", 14), ("errors", 5)]

    def test_everything_fits(self):
        self.assertEqual(fit_segments(self.PARTS, ("title", "mode"), 100),
                         {"title", "state", "mode", "file", "errors"})

    def test_unmeasured_width_keeps_all(self):
        self.assertEqual(len(fit_segments(self.PARTS, ("title", "mode"), 0)), 5)

    def test_drops_in_order_until_it_fits(self):
        kept = fit_segments(self.PARTS, ("title", "mode"), 40)       # 總 49 → 丟 title 後 39
        self.assertEqual(kept, {"state", "mode", "file", "errors"})
        kept = fit_segments(self.PARTS, ("title", "mode"), 30)
        self.assertEqual(kept, {"state", "file", "errors"})

    def test_never_drops_unlisted_parts(self):
        kept = fit_segments(self.PARTS, ("title", "mode"), 5)
        self.assertEqual(kept, {"state", "file", "errors"})

    def test_ignores_unknown_names_in_drop_order(self):
        self.assertEqual(len(fit_segments(self.PARTS, ("nope", "title"), 45)), 4)


class RowColumnTests(unittest.TestCase):
    def test_wide_layout(self):
        label, value = N.row_columns(100, False)
        self.assertEqual((label, value), (30, 65))
        label, value = N.row_columns(40, False)
        self.assertEqual(label, 16)
        self.assertEqual(label + value + 5, 40)

    def test_compact_uses_full_width_for_both_lines(self):
        label, value = N.row_columns(40, True)
        self.assertEqual(label, value)
        self.assertEqual(label, 37)
        self.assertGreaterEqual(N.row_columns(5, True)[0], 8)

    def test_thresholds_are_ordered(self):
        self.assertLess(N.COMPACT_WIDTH, N.NARROW_WIDTH)


class TabsTests(unittest.TestCase):
    LABELS = [e.label for e in MODULE_ENTRIES]

    def width(self, segments):
        return sum(cell_len(t) for t, _ in segments)

    def test_picks_the_most_detailed_layout_that_fits(self):
        full = N.tabs_layout(self.LABELS, 1, 80)
        self.assertEqual([t for t, r in full if r == "side"], ["combat", "pvp"])
        self.assertEqual([t for t, r in full if r == "current"], ["[ expedition ]"])
        mid = N.tabs_layout(self.LABELS, 1, 30)
        self.assertEqual([r for _, r in mid], ["arrow", "current", "pos", "arrow"])
        self.assertIn(" 2/11", [t for t, _ in mid])
        small = N.tabs_layout(self.LABELS, 1, 16)
        self.assertEqual([t for t, _ in small], ["‹ ", "expedition", " ›"])

    def test_always_fits_when_possible(self):
        for index in range(len(self.LABELS)):
            for width in (30, 40, 60, 71):
                self.assertLessEqual(self.width(N.tabs_layout(self.LABELS, index, width)),
                                     width, (index, width))

    def test_wraps_around_at_the_ends(self):
        first = N.tabs_layout(self.LABELS, 0, 80)
        self.assertEqual([t for t, r in first if r == "side"], ["other", "expedition"])
        last = N.tabs_layout(self.LABELS, len(self.LABELS) - 1, 80)
        self.assertEqual([t for t, r in last if r == "side"][1], "combat")

    def test_click_zones(self):
        self.assertEqual(N.tabs_step(0, 60), -1)
        self.assertEqual(N.tabs_step(19, 60), -1)
        self.assertEqual(N.tabs_step(30, 60), 0)
        self.assertEqual(N.tabs_step(40, 60), 1)
        self.assertEqual(N.tabs_step(59, 60), 1)
        self.assertEqual(N.tabs_step(0, 1), -1)                      # 極窄也不除以零


class ArrowTests(unittest.TestCase):
    def test_zones_follow_the_value_position(self):
        line, left, right = N.arrow_zones(20, 4, False)
        self.assertEqual(line, 0)
        x0 = 3 + 20 + 2
        self.assertEqual(left, (x0 - 1, x0 + 1))
        self.assertEqual(right, (x0 + 2 + 4 + 1 - 1, x0 + 2 + 4 + 1 + 1))

    def test_compact_uses_the_second_line(self):
        line, left, right = N.arrow_zones(37, 3, True)
        self.assertEqual(line, 1)
        self.assertEqual(left, (2, 4))

    def test_hit_testing(self):
        zones = N.arrow_zones(20, 4, False)
        x0 = 25
        self.assertEqual(N.arrow_hit(zones, x0, 0), -1)
        self.assertEqual(N.arrow_hit(zones, x0 - 1, 0), -1)
        self.assertEqual(N.arrow_hit(zones, x0 + 1, 0), -1)
        self.assertEqual(N.arrow_hit(zones, x0 + 2 + 4 + 1, 0), 1)
        self.assertEqual(N.arrow_hit(zones, x0 + 4, 0), 0)            # 值的中間不算
        self.assertEqual(N.arrow_hit(zones, x0, 1), 0)                # 錯的那一列
        self.assertEqual(N.arrow_hit(zones, 3, 0), 0)                 # 標籤上


class HintTests(unittest.TestCase):
    def test_essentials_survive_the_narrowest_bar(self):
        descs = {d for _, d in N.EDITOR_HINTS}
        for essential in ("save", "back"):
            self.assertIn(essential, descs)
            self.assertNotIn(essential, N.EDITOR_HINT_DROP)
        for name in N.EDITOR_HINT_DROP:
            self.assertIn(name, descs)


if __name__ == "__main__":
    unittest.main()
