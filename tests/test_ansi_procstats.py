import unittest

from tui.ansi import (
    ERROR_STYLE, LOG_STYLE, STATUS_STYLE, WARNING_STYLE, parse_ansi, plain_text,
)
from tui.procstats import SPARK_CHARS, fmt_bytes, fmt_duration, sparkline


class AnsiParsing(unittest.TestCase):
    def test_plain_text_has_one_default_segment(self):
        self.assertEqual(parse_ansi("hello"), [("hello", "")])
        self.assertEqual(parse_ansi(""), [])

    def test_four_kcauto_colors(self):
        cases = {"91": ERROR_STYLE, "92": STATUS_STYLE,
                 "93": WARNING_STYLE, "94": LOG_STYLE}
        for code, style in cases.items():
            self.assertEqual(parse_ansi(f"\x1b[{code}mmsg\x1b[0m"), [("msg", style)])

    def test_reset_and_mixed_segments(self):
        segs = parse_ansi("a \x1b[92mgreen\x1b[0m b \x1b[91mred\x1b[0m")
        self.assertEqual(segs, [("a ", ""), ("green", STATUS_STYLE), (" b ", ""),
                                ("red", ERROR_STYLE)])
        self.assertEqual(plain_text(segs), "a green b red")

    def test_unknown_codes_are_debug_default(self):
        self.assertEqual(parse_ansi("\x1b[37mdebug\x1b[0m"), [("debug", "")])

    def test_compound_parameters_do_not_leak_as_text(self):
        # 舊版 isdigit() 判斷會把 "91;1" 當文字印出來
        self.assertEqual(parse_ansi("\x1b[1;91mboom\x1b[0m"), [("boom", ERROR_STYLE)])
        self.assertEqual(parse_ansi("\x1b[91;1mboom"), [("boom", ERROR_STYLE)])

    def test_bare_reset_without_params(self):
        self.assertEqual(parse_ansi("\x1b[92mx\x1b[my"), [("x", STATUS_STYLE), ("y", "")])

    def test_non_color_sequences_are_stripped(self):
        self.assertEqual(parse_ansi("\x1b[2K\x1b[1Gloading"), [("loading", "")])
        self.assertEqual(parse_ansi("\x1b[?25lhi\x1b[?25h"), [("hi", "")])
        self.assertEqual(parse_ansi("\x1b]0;window title\x07text"), [("text", "")])

    def test_stray_escape_and_unterminated_sequence(self):
        self.assertEqual(plain_text(parse_ansi("a\x1bb")), "ab")
        self.assertNotIn("\x1b", plain_text(parse_ansi("x\x1b[92")))

    def test_adjacent_same_style_segments_merge(self):
        segs = parse_ansi("\x1b[92ma\x1b[92mb")
        self.assertEqual(segs, [("ab", STATUS_STYLE)])

    def test_unicode_survives(self):
        self.assertEqual(plain_text(parse_ansi("\x1b[93m⚠ 出擊 6-4\x1b[0m")), "⚠ 出擊 6-4")


class Sparkline(unittest.TestCase):
    def test_width_is_constant(self):
        for n in range(0, 12):
            self.assertEqual(len(sparkline([50] * n, width=8)), 8)

    def test_scaling(self):
        self.assertEqual(sparkline([0], width=1), SPARK_CHARS[0])
        self.assertEqual(sparkline([100], width=1), SPARK_CHARS[-1])
        self.assertEqual(sparkline([500], width=1), SPARK_CHARS[-1])   # 超過上限
        self.assertEqual(sparkline([-5], width=1), SPARK_CHARS[0])
        self.assertEqual(sparkline([50], maximum=200, width=1), SPARK_CHARS[2])

    def test_pads_left_and_keeps_latest(self):
        self.assertEqual(sparkline([100], width=3), "  " + SPARK_CHARS[-1])
        out = sparkline(list(range(0, 100, 10)), width=4)
        self.assertEqual(len(out), 4)
        self.assertEqual(out[-1], SPARK_CHARS[round(90 / 100 * 7)])

    def test_degenerate(self):
        self.assertEqual(sparkline([1, 2], width=0), "")
        self.assertEqual(sparkline([5], maximum=0, width=1), SPARK_CHARS[0])


class Formatting(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(fmt_duration(0), "00:00:00")
        self.assertEqual(fmt_duration(192), "00:03:12")
        self.assertEqual(fmt_duration(3 * 3600 + 5), "03:00:05")
        self.assertEqual(fmt_duration(2 * 86400 + 3600), "2d 01:00:00")
        self.assertEqual(fmt_duration(-5), "00:00:00")

    def test_bytes(self):
        self.assertEqual(fmt_bytes(0), "0B")
        self.assertEqual(fmt_bytes(512), "512B")
        self.assertEqual(fmt_bytes(512 * 1024), "512K")
        self.assertEqual(fmt_bytes(180 * 1024 ** 2), "180M")
        self.assertEqual(fmt_bytes(int(1.5 * 1024 ** 2)), "1.5M")
        self.assertEqual(fmt_bytes(1024 ** 3), "1G")
        self.assertEqual(fmt_bytes(int(1.2 * 1024 ** 3)), "1.2G")


if __name__ == "__main__":
    unittest.main()
