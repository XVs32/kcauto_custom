"""Static checks that need no Textual: whether bound actions and message handlers really exist.

When the sandbox or CI has no Textual, this is the only test that catches "a key is bound but there is no matching method".
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
                methods = {
                    n.name
                    for n in node.body
                    if isinstance(n, ast.FunctionDef)
                    or isinstance(n, ast.AsyncFunctionDef)
                }
                bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                bindings = []
                for n in node.body:
                    if isinstance(n, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id == "BINDINGS"
                        for t in n.targets
                    ):
                        for call in ast.walk(n.value):
                            if (
                                isinstance(call, ast.Call)
                                and getattr(call.func, "id", "") == "Binding"
                                and len(call.args) >= 2
                                and isinstance(
                                    call.args[1], (ast.Constant, ast.JoinedStr)
                                )
                            ):
                                if isinstance(call.args[1], ast.Constant):
                                    bindings.append(call.args[1].value)
                                else:  # f-string:goto_module('...')
                                    first = call.args[1].values[0]
                                    bindings.append(
                                        first.value
                                        if isinstance(first, ast.Constant)
                                        else ""
                                    )
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


def _snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _custom_messages():
    """{(Widget, Message): attributes the message sets in __init__}."""
    out = {}
    for path in FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for widget in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            for inner in [n for n in widget.body if isinstance(n, ast.ClassDef)]:
                attrs = set()
                for node in ast.walk(inner):
                    if (
                        isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "self"
                        and isinstance(node.ctx, ast.Store)
                    ):
                        attrs.add(node.attr)
                out[(widget.name, inner.name)] = attrs
    return out


class StaticChecks(unittest.TestCase):
    def test_handlers_only_read_attributes_the_message_defines(self):
        """Clicked once set .action while the handler read .command, so every button click crashed."""
        messages = _custom_messages()
        by_handler = {f"on_{_snake(w)}_{_snake(m)}": (w, m) for (w, m) in messages}
        common = {"stop", "prevent_default", "control", "message"}
        checked = 0
        for path in FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for func in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
                key = None
                if func.name in by_handler:
                    key = by_handler[func.name]
                for arg in func.args.args:  # event: Widget.Message
                    ann = arg.annotation
                    if (
                        isinstance(ann, ast.Attribute)
                        and isinstance(ann.value, ast.Name)
                        and (ann.value.id, ann.attr) in messages
                    ):
                        key = (ann.value.id, ann.attr)
                if key is None:
                    continue
                allowed = messages[key] | common
                for node in ast.walk(func):
                    if (
                        isinstance(node, ast.Attribute)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "event"
                    ):
                        self.assertIn(
                            node.attr,
                            allowed,
                            f"{path.name}:{func.name} reads event.{node.attr},"
                            f"but {key[0]}.{key[1]} only has {sorted(messages[key])}",
                        )
                        checked += 1
        self.assertGreater(checked, 15)

    def test_every_binding_action_has_a_method(self):
        classes = _load()
        checked = 0
        for name, (_, _, bindings) in classes.items():
            available = _all_methods(classes, name)
            for action in bindings:
                action_name = re.match(r"[A-Za-z_]\w*", action)
                self.assertTrue(action_name, f"{name}: {action!r}")
                method = "action_" + action_name.group(0)
                self.assertIn(
                    method, available, f"{name} binds {action!r} but has no {method}"
                )
                checked += 1
        self.assertGreater(checked, 40)

    def test_message_handlers_match_message_classes(self):
        """Handlers of the form on_<widget>_<message> must correspond to a message class that actually exists."""
        widget_msgs = {
            "pick_list": {"chosen", "toggled", "edge", "moved"},
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
                        self.assertIn(m[len(prefix) :], msgs, f"{name}.{m}")

    def test_dialog_commands_are_handled(self):
        """Commands used by ActionLabel buttons must be handled by the dialog's run_command (or passed on to the base cancel)."""
        text = (ROOT / "editor" / "dialogs.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            src = ast.get_source_segment(text, cls)
            used = set(re.findall(r'\("[A-Z][^"]*", "([a-z_]+)"\)', src))
            used -= {"cancel"}
            if not used:
                continue
            for command in used:
                self.assertIn(
                    f'"{command}"',
                    src.split("def run_command")[-1],
                    f"{cls.name} does not handle button command {command}",
                )

    def test_no_attribute_shadows_a_textual_internal(self):
        """self.<name> = … must not overwrite Textual widget built-in attributes.

        Writing self._nodes = None in EditorScreen once broke the editor on open (DOMNode uses it to store child widgets); Widget.visible controls visibility, and using it for "rows shown" also causes problems.
        """
        reserved = {
            "_nodes",
            "_id",
            "_classes",
            "_name",
            "_size",
            "_parent",
            "_bindings",
            "_styles",
            "visible",
            "display",
            "disabled",
            "loading",
            "size",
            "region",
            "styles",
            "id",
            "classes",
            "name",
            "parent",
            "children",
            "app",
            "screen",
            "focused",
            "tooltip",
            "expand",
            "shrink",
            "border_title",
            "border_subtitle",
            "title",
            "sub_title",
            "root",
            "nodes",
            "rows",
            "columns",
            "layout",
            "offset",
            "content",
            "renderable",
            "_widgets",
            "_rows",
            "can_focus",
            "has_focus",
            "mouse_hover",
            "message_queue",
        }
        # PickList.rows is a deliberate public field: it does not clash with Textual (verified on real Textual), listed as an exception
        allowed = {("PickList", "rows")}
        for path in FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
                for node in ast.walk(cls):
                    if (
                        isinstance(node, ast.Attribute)
                        and isinstance(node.ctx, ast.Store)
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "self"
                        and node.attr in reserved
                        and (cls.name, node.attr) not in allowed
                    ):
                        self.fail(
                            f"{path.name}:{cls.name} sets self.{node.attr},"
                            f"which may overwrite a Textual built-in attribute"
                        )

    def test_widget_visible_property_is_never_used_for_our_own_state(self):
        """Widget.visible controls visibility and cannot be used to store things like "rows shown" (reading it is not allowed either)."""
        for path in FILES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "self"
                    and node.attr == "visible"
                ):
                    self.fail(f"{path.name}:{node.lineno} uses self.visible")

    def test_scrolling_containers_do_not_steal_arrow_keys(self):
        """VerticalScroll has built-in ↑↓ scroll bindings that steal the editor's previous/next row when the content exceeds the screen.

        It must be written as the class keyword argument inherit_bindings=False; a same-named attribute inside the class has no effect.
        """
        text = (ROOT / "editor" / "screen.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        checked = 0
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            bases = {b.id for b in cls.bases if isinstance(b, ast.Name)}
            if bases & {"VerticalScroll", "ScrollableContainer", "VerticalGroup"}:
                kw = {k.arg: k.value for k in cls.keywords}
                self.assertIn(
                    "inherit_bindings",
                    kw,
                    f"{cls.name} must declare inherit_bindings=False in the class statement",
                )
                self.assertIs(kw["inherit_bindings"].value, False)
                checked += 1
        self.assertGreaterEqual(checked, 1)

    def test_hotkeys_do_not_collide_with_editor_keys(self):
        from tui.editor.model import MODULE_ENTRIES

        screen = (ROOT / "editor" / "screen.py").read_text(encoding="utf-8")
        fixed = set(re.findall(r'Binding\("([a-z])", ', screen))
        for e in MODULE_ENTRIES:
            self.assertNotIn(e.hotkey, fixed)


if __name__ == "__main__":
    unittest.main()
