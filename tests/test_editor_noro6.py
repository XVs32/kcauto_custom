"""noro6 讀取:LZString 解壓縮與出擊節點索引。"""
import json
import os
import random
import tempfile
import unittest
from pathlib import Path

from tests.lz_compress import compress_utf16
from tui.editor import noro6


def preset(name):
    return {"name": name, "isDirectory": False, "manager": "{}"}


def folder(name, *children):
    return {"name": name, "isDirectory": True, "childItems": list(children)}


SAMPLE = {"savedata": folder("root", folder("1: sea",
          preset("B-1-1"), preset("By2-1-1"), preset("B-2-2"), preset("B-2-2-A"),
          preset("B-2-2-B-bak"), folder("old-bak", preset("B-9-9-X")),
          preset("B-5-6-G"), preset("B-5-6-R"), preset("2610B2-2-2"), preset("D-A2"),
          preset("B-7-2-G"), preset("B-7-2-M")))}


def write(root, data, rel="configs/noro6/noro6"):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(compress_utf16(json.dumps(data)), encoding="utf-8")


class LzStringTests(unittest.TestCase):
    def test_roundtrip(self):
        random.seed(7)
        samples = ["a", "abc", "艦これ" * 30, json.dumps(SAMPLE, ensure_ascii=False)]
        samples += ["".join(random.choice("abcdef日本 {}\":,") for _ in range(random.randint(1, 1500)))
                    for _ in range(40)]
        for text in samples:
            self.assertEqual(noro6.decompress_utf16(compress_utf16(text)), text)

    def test_garbage_does_not_raise(self):
        for junk in ("", "x", "abc" * 20, "\u0000" * 10):
            noro6.decompress_utf16(junk)


class PresetTests(unittest.TestCase):
    def test_names_skip_bak_and_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, SAMPLE)
            names = noro6.load_preset_names(tmp)
        self.assertIn("B-2-2-A", names)
        self.assertNotIn("B-2-2-B-bak", names)
        self.assertNotIn("B-9-9-X", names)               # -bak 資料夾連同子項都略過

    def test_sortie_nodes_only_plain_b_presets_with_a_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, SAMPLE)
            index = noro6.load_sortie_nodes(tmp)
        self.assertEqual(index, {("2", 2): ["A"], ("5", 6): ["G", "R"], ("7", 2): ["G", "M"]})

    def test_falls_back_to_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, SAMPLE, "template/configs/noro6/noro6")
            self.assertIn("template", noro6.find_file(tmp).parts)
            self.assertIn(("2", 2), noro6.load_sortie_nodes(tmp))

    def test_config_wins_over_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, {"savedata": folder("r", preset("B-1-1-X"))})
            write(tmp, SAMPLE, "template/configs/noro6/noro6")
            self.assertEqual(noro6.load_sortie_nodes(tmp), {("1", 1): ["X"]})

    def test_missing_or_broken_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(noro6.load_sortie_nodes(tmp), {})
            path = Path(tmp) / "configs/noro6/noro6"
            path.parent.mkdir(parents=True)
            path.write_text("not compressed at all", encoding="utf-8")
            self.assertEqual(noro6.load_sortie_nodes(tmp), {})
            write(tmp, ["not", "a", "dict"])
            self.assertEqual(noro6.load_sortie_nodes(tmp), {})

    def test_real_file_if_provided(self):
        path = os.environ.get("KCAUTO_NORO6")
        if not path:
            self.skipTest("設 KCAUTO_NORO6=<configs/noro6/noro6> 可檢查實際檔案")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "configs/noro6/noro6"
            target.parent.mkdir(parents=True)
            target.write_bytes(Path(path).read_bytes())
            index = noro6.load_sortie_nodes(tmp)
        self.assertIn(("2", 2), index)
        self.assertIn("A", index[("2", 2)])


if __name__ == "__main__":
    unittest.main()
