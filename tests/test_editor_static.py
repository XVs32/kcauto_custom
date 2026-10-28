"""不需要 Textual 的靜態檢查:綁定的動作、訊息處理器是否真的存在。

沙盒與 CI 沒有 Textual 時,這是唯一能抓到「按鍵綁了卻沒有對應方法」的測試。
"""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "tui"
FILES = [ROOT / "editor" / n for n in ("widgets.py", "dialogs.py", "screen.py")]


def _load():
    classes = {}
    for path in FILES + [ROOT / "app.py"]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = {n.name for n in node.body if isinstance(n, ast.FunctionDef)
                           or isinstance(n, ast.AsyncFunctionDef)}
                bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                bindings = []
                for n in node.body:
                    if isinstance(n, ast.Assign) and any(
                            isinstance(t, ast.Name) and t.id == "BINDINGS" for t in n.targets):
                        for call in ast.walk(n.value):
                            if (isinstance(call, ast.Call) and getattr(call.func, "id", "") == "Binding"
                                    and len(call.args) >= 2
                                    and isinstance(call.args[1], (ast.Constant, ast.JoinedStr))):
                                if isinstance(call.args[1], ast.Constant):
                                    bindings.append(call.args[1].value)
                                else:   # f-string:goto_module('...')
                                    first = call.args[1].values[0]
                                    bindings.append(first.value if isinstance(first, ast.Constant) else "")
                classes[node.name] = (methods, bases, bindings)
    return classes


def _all_methods(classes, name, seen=None):
    seen = seen or set()
    if name in seen or name not in classes:
        return set()
    seen.add(name)
    methods, bases, _ = classes[name]
    out = set(methods)
    for b in bases:
        out |= _all_methods(classes, b, seen)
    return out


class StaticChecks(unittest.TestCase):
    def test_every_binding_action_has_a_method(self):
        classes = _load()
        checked = 0
        for name, (_, _, bindings) in classes.items():
            available = _all_methods(classes, name)
            for action in bindings:
                action_name = re.match(r"[A-Za-z_]\w*", action)
                self.assertTrue(action_name, f"{name}: {action!r}")
                method = "action_" + action_name.group(0)
                self.assertIn(method, available, f"{name} 綁定了 {action!r} 但沒有 {method}")
                checked += 1
        self.assertGreater(checked, 40)

    def test_message_handlers_match_message_classes(self):
        """on_<widget>_<message> 形式的處理器必須對應到實際存在的訊息類別。"""
        widget_msgs = {
            "pick_list": {"chosen", "toggled", "edge"},
            "cycle_box": {"submitted"},
            "preset_grid": {"accepted"},
            "action_label": {"clicked"},
        }
        classes = _load()
        for name, (methods, _, _) in classes.items():
            for m in methods:
                for widget, msgs in widget_msgs.items():
                    prefix = f"on_{widget}_"
                    if m.startswith(prefix):
                        self.assertIn(m[len(prefix):], msgs, f"{name}.{m}")

    def test_dialog_commands_are_handled(self):
        """按鈕 ActionLabel 用到的指令,該對話框的 run_command 要處理(或交給基底的 cancel)。"""
        text = (ROOT / "editor" / "dialogs.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            src = ast.get_source_segment(text, cls)
            used = set(re.findall(r'\("[^"]+", "(\w+)"\)', src))
            used -= {"cancel"}
            if not used:
                continue
            for command in used:
                self.assertIn(f'"{command}"', src.split("def run_command")[-1],
                              f"{cls.name} 未處理按鈕指令 {command}")

    def test_hotkeys_do_not_collide_with_editor_keys(self):
        from tui.editor.model import MODULE_ENTRIES
        screen = (ROOT / "editor" / "screen.py").read_text(encoding="utf-8")
        fixed = set(re.findall(r'Binding\("([a-z])", ', screen))
        for e in MODULE_ENTRIES:
            self.assertNotIn(e.hotkey, fixed)


if __name__ == "__main__":
    unittest.main()
