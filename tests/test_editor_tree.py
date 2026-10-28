"""JSON 樹狀編輯的純邏輯測試。"""
import copy
import unittest

from tui.editor import tree as T


def sample():
    return {"1": {"ship": 123, "rules": ["a", True, None], "name": "x"}, "2": {}}


class KindTests(unittest.TestCase):
    def test_kind_of(self):
        cases = {None: "null", True: "bool", 3: "int", 1.5: "float", "s": "str",
                 {}: "object", []: "list"} if False else [
            (None, "null"), (True, "bool"), (False, "bool"), (3, "int"), (1.5, "float"),
            ("s", "str"), ({}, "object"), ([], "list")]
        for value, kind in cases:
            self.assertEqual(T.kind_of(value), kind, value)

    def test_defaults_roundtrip(self):
        for kind in T.KINDS:
            self.assertEqual(T.kind_of(T.default_for(kind)), kind)

    def test_defaults_are_fresh_objects(self):
        a, b = T.default_for("list"), T.default_for("list")
        a.append(1)
        self.assertEqual(b, [])

    def test_convert(self):
        self.assertEqual(T.convert("12", "int"), 12)
        self.assertEqual(T.convert(" -3 ", "int"), -3)
        self.assertEqual(T.convert("abc", "int"), 0)
        self.assertEqual(T.convert(7, "str"), "7")
        self.assertEqual(T.convert(True, "str"), "true")
        self.assertEqual(T.convert(None, "str"), "")
        self.assertEqual(T.convert(1, "bool"), True)
        self.assertEqual(T.convert(0, "bool"), False)
        self.assertEqual(T.convert("True", "bool"), True)
        self.assertEqual(T.convert("x", "bool"), False)
        self.assertEqual(T.convert("2.5", "float"), 2.5)
        self.assertEqual(T.convert(3, "float"), 3.0)
        self.assertEqual(T.convert("x", "object"), {})
        self.assertEqual(T.convert({"a": 1}, "str"), "")        # 容器不轉成字串
        self.assertEqual(T.convert({"a": 1}, "object"), {"a": 1})
        self.assertIsNone(T.convert(5, "null"))


class EditTests(unittest.TestCase):
    def test_get_set_delete(self):
        root = sample()
        self.assertEqual(T.get_at(root, ("1", "rules", 0)), "a")
        T.set_at(root, ("1", "ship"), 9)
        self.assertEqual(root["1"]["ship"], 9)
        T.delete_at(root, ("1", "rules", 1))
        self.assertEqual(root["1"]["rules"], ["a", None])
        T.delete_at(root, ("2",))
        self.assertNotIn("2", root)
        self.assertEqual(T.set_at(root, (), [1]), [1])           # 取代根

    def test_add_child(self):
        root = sample()
        self.assertEqual(T.add_child(root, ("1",), "new", 5), ("1", "new"))
        self.assertEqual(T.add_child(root, ("1", "rules"), None, "z"), ("1", "rules", 3))
        self.assertEqual(root["1"]["rules"][-1], "z")
        with self.assertRaises(ValueError):
            T.add_child(root, ("1",), None, 1)

    def test_rename_keeps_order(self):
        root = {"a": 1, "b": 2, "c": 3}
        self.assertEqual(T.rename_key(root, ("b",), "x"), ("x",))
        self.assertEqual(list(root), ["a", "x", "c"])
        self.assertEqual(root["x"], 2)
        with self.assertRaises(ValueError):
            T.rename_key({"l": [1]}, ("l", 0), "k")

    def test_key_validation(self):
        parent = {"a": 1, "b": 2}
        self.assertIsNone(T.key_error(parent, "c"))
        self.assertIn("exists", T.key_error(parent, "a"))
        self.assertIsNone(T.key_error(parent, "a", current="a"))   # 改回自己的名字沒問題
        self.assertIn("empty", T.key_error(parent, "  "))
        self.assertEqual(T.unique_key({"new": 1, "new_2": 1}), "new_3")


class FlattenTests(unittest.TestCase):
    def test_collapsed_shows_only_top_level(self):
        rows = T.flatten(sample(), set())
        self.assertEqual([r.path for r in rows], [("1",), ("2",)])
        self.assertTrue(all(r.expandable and not r.expanded for r in rows))

    def test_expanded_order_and_depth(self):
        root = sample()
        rows = T.flatten(root, T.all_container_paths(root))
        self.assertEqual([r.depth for r in rows], [0, 1, 1, 2, 2, 2, 1, 0])
        self.assertEqual(rows[3].key, 0)
        self.assertEqual(rows[3].kind, "str")

    def test_initial_expanded_limits(self):
        small = sample()
        self.assertEqual(len(T.flatten(small, T.initial_expanded(small))), 8)
        big = {str(i): {"a": [1, 2, 3], "b": {"c": 1}} for i in range(30)}
        expanded = T.initial_expanded(big)
        self.assertTrue(all(len(p) == 1 for p in expanded))     # 只展開第一層

    def test_scalar_and_empty_root(self):
        self.assertEqual(T.flatten({}, set()), [])
        self.assertEqual(T.flatten([1, 2], set())[1].key, 1)

    def test_text(self):
        root = sample()
        rows = T.flatten(root, T.all_container_paths(root))
        width = T.key_column_width(rows, 60)
        lines = [T.row_text(r, width, 60) for r in rows]
        self.assertIn("▾ 1", lines[0])
        self.assertIn("object {3}", lines[0])
        self.assertIn('"a"', lines[3])
        self.assertIn("on", lines[4])
        self.assertIn("null", lines[5])
        for line in lines:
            self.assertLessEqual(T.cell_len(line), 60)
        narrow = [T.row_text(r, T.key_column_width(rows, 24), 24) for r in rows]
        for line in narrow:
            self.assertLessEqual(T.cell_len(line), 24)

    def test_path_text(self):
        self.assertEqual(T.path_text(()), "(root)")
        self.assertEqual(T.path_text(("1", "rules", 0)), "1.rules[0]")

    def test_path_survives_mutations_made_on_copies(self):
        root = sample()
        work = T.make_working_copy(root)
        T.set_at(work, ("1", "ship"), 1)
        self.assertEqual(root["1"]["ship"], 123)               # 原本的不受影響


if __name__ == "__main__":
    unittest.main()
