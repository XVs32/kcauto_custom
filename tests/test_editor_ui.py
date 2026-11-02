"""UI tests for the editor (Textual pilot). The whole group is skipped when Textual is not installed.

The sandbox has no Textual, so these tests have not actually been run yet; run them in a real environment:
    python -m unittest tests.test_editor_ui -v
"""

import unittest

try:
    import textual  # noqa: F401
except ImportError:  # pragma: no cover
    textual = None

from tests.test_app import BIG, _AppTestBase


@unittest.skipIf(textual is None, "textual is not installed")
class EditorTests(_AppTestBase):
    async def open_editor(self, pilot, hotkey="c"):
        from tui.editor.screen import EditorScreen

        await pilot.press(hotkey, "enter")
        await pilot.pause()
        self.assertIsInstance(pilot.app.screen, EditorScreen)
        return pilot.app.screen

    async def test_enter_opens_editor_on_that_module_and_esc_returns(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "e")
            self.assertEqual(screen.entry.module, "expedition")
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 1)
            self.assertEqual(app.focused.id, "card-expedition")

    async def test_dashboard_keys_are_inert_while_editing(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.open_editor(pilot)
            await pilot.press("q")
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 2)  # q does not quit the program

    async def test_enter_then_arrows_toggle_bool_and_dashboard_follows(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.pause()
            self.assertEqual(screen.focused.key, "combat.enabled")
            await pilot.press(
                "enter"
            )  # entering edit mode: the value has not changed yet
            self.assertFalse(self.store.get("combat.enabled"))
            await pilot.press("right")
            self.assertTrue(self.store.get("combat.enabled"))
            await pilot.press("enter")  # confirm, back to the list
            self.assertIsNone(screen._edit_row)
            await pilot.press("down", "up")  # after returning to the list ↑↓ move again
            self.assertEqual(screen.focused.key, "combat.enabled")

    async def test_module_hotkeys_and_brackets(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.press("f")
            self.assertEqual(screen.entry.module, "factory")
            await pilot.press("right_square_bracket")
            self.assertEqual(screen.entry.module, "passive_repair")
            await pilot.press("left_square_bracket", "left_square_bracket")
            self.assertEqual(screen.entry.module, "scheduler")
            await pilot.press("o")
            self.assertEqual(screen.entry.module, "other")

    async def test_arrows_move_between_rows(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            first = screen.focused.key
            await pilot.press("down")
            self.assertNotEqual(screen.focused.key, first)
            await pilot.press("up")
            self.assertEqual(screen.focused.key, first)

    async def test_plus_minus_only_work_while_editing(self):
        self.store.set("combat.retreat_limit", 2)
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(
                r for r in screen._field_rows() if r.key == "combat.retreat_limit"
            ).focus()
            await pilot.press("plus")
            self.assertEqual(
                self.store.get("combat.retreat_limit"), 2
            )  # list level: does not move
            await pilot.press("enter", "plus", "plus", "minus")
            self.assertEqual(self.store.get("combat.retreat_limit"), 3)
            await pilot.press("enter")

    async def test_default_and_undo_keys(self):
        self.store.set("combat.retreat_limit", 2)
        self.store.save()
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            target = next(
                r for r in screen._field_rows() if r.key == "combat.retreat_limit"
            )
            target.focus()
            await pilot.press("enter", "right", "enter")  # 2 → 3
            self.assertEqual(self.store.get("combat.retreat_limit"), 3)
            await pilot.press("z")
            self.assertEqual(self.store.get("combat.retreat_limit"), 2)
            await pilot.press("d")
            self.assertEqual(self.store.get("combat.retreat_limit"), 4)

    async def test_text_dialog_for_secretary_accepts_int_and_str(self):
        from tui.editor.dialogs import TextDialog

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "f")
            next(
                r for r in screen._field_rows() if r.key == "factory.build_secretary"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, TextDialog)
            for _ in range(6):
                await pilot.press("backspace")
            await pilot.press("enter")  # empty: must not crash, only shows an error
            await pilot.pause()
            self.assertIsInstance(app.screen, TextDialog)
            await pilot.press("A", "k", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("factory.build_secretary"), "Ak")

    async def test_ok_button_click_works_in_dialogs(self):
        """Regression: clicking the OK / Remove / Cancel buttons used to crash."""
        from tui.editor.widgets import ActionLabel

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "e")
            next(
                r for r in screen._field_rows() if r.key == "expedition.fleet_2"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("5", "enter")
            await pilot.pause()
            labels = {w.command: w for w in app.screen.query(ActionLabel)}
            for command in ("remove", "ok"):  # click Remove, then OK with the mouse
                region = labels[command].region
                await pilot.click(offset=(region.x + 1, region.y))
                await pilot.pause()
            self.assertEqual(self.store.get("expedition.fleet_2"), [])

    async def test_escape_cancels_dialog_without_change(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            target = next(
                r for r in screen._field_rows() if r.key == "combat.sortie_map"
            )
            target.focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("x", "escape")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.sortie_map"), "1-1")

    async def test_list_dialog_adds_items(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(
                r for r in screen._field_rows() if r.key == "combat.retreat_points"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press(
                "a", "enter", "b", "enter", "enter"
            )  # add A, B; Enter on empty input = OK
            await pilot.pause()
            self.assertEqual(self.store.get("combat.retreat_points"), ["a", "b"])

    async def test_push_nodes_requires_confirmation(self):
        from tui.editor.dialogs import DangerDialog

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(
                r for r in screen._field_rows() if r.key == "combat.push_nodes"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("a", "enter", "enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, DangerDialog)
            self.assertEqual(self.store.get("combat.push_nodes"), [])
            await pilot.press("n")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.push_nodes"), [])
            # once more, this time confirm
            next(
                r for r in screen._field_rows() if r.key == "combat.push_nodes"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("a", "enter", "enter")
            await pilot.pause()
            await pilot.press("y")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.push_nodes"), ["a"])

    async def test_recipe_two_levels(self):
        from tui.editor.dialogs import NumberDialog
        from tui.editor.widgets import WheelPicker

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "f")
            next(
                r for r in screen._field_rows() if r.key == "factory.build_recipe"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, NumberDialog)
            picker = app.screen.query_one(WheelPicker)
            self.assertEqual(picker.level, "group")  # level 1: pick a resource
            await pilot.press("down")  # move to ammo
            self.assertEqual(picker.level, "group")
            await pilot.press("up", "enter")  # back to fuel, enter level 2
            self.assertEqual(picker.level, "digit")
            await pilot.press(
                "right", "right", "down", "enter"
            )  # tens digit +1 → confirm, back to level 1
            self.assertEqual(picker.level, "group")
            await pilot.press(
                "down", "down", "enter"
            )  # move to OK → confirm the whole dialog
            await pilot.pause()
            self.assertEqual(self.store.get("factory.build_recipe"), [40, 30, 30, 30])

    async def test_recipe_escape_undoes_one_resource_then_cancels(self):
        from tui.editor.widgets import WheelPicker

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "f")
            next(
                r for r in screen._field_rows() if r.key == "factory.build_recipe"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            picker = app.screen.query_one(WheelPicker)
            await pilot.press(
                "enter", "down", "escape"
            )  # fuel: change it, then Esc → restored, back to level 1
            self.assertEqual(picker.level, "group")
            self.assertEqual("".join(picker.values()[:4]), "0030")
            self.assertEqual(len(app.screen_stack), 3)  # the dialog is still there
            await pilot.press("escape")  # level 1 Esc → cancel the dialog
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 2)
            self.assertEqual(self.store.get("factory.build_recipe"), [30, 30, 30, 30])

    async def test_sortie_map_wheel(self):
        from tui.editor.dialogs import MapDialog

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(
                r for r in screen._field_rows() if r.key == "combat.sortie_map"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, MapDialog)
            await pilot.press(
                "down", "down", "right", "down", "down"
            )  # world 1→3, map 1→3
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.sortie_map"), "3-3")

    async def test_arrows_move_rows_even_when_pane_must_scroll(self):
        """Regression: when the panel is not tall enough (scrolling appears), ↑↓ must change rows instead of scrolling the whole panel."""
        app = self.make_app()
        async with app.run_test(size=(100, 16)) as pilot:
            screen = await self.open_editor(pilot)
            rows = screen._field_rows()
            self.assertGreater(len(rows), 12)
            for i in range(1, 13):
                await pilot.press("down")
                self.assertIs(screen.focused, rows[i])
            for i in range(12, 6, -1):
                await pilot.press("up")
                self.assertIs(screen.focused, rows[i - 1])
            await pilot.press("end")
            self.assertIs(screen.focused, rows[-1])
            await pilot.press("home")
            self.assertIs(screen.focused, rows[0])

    async def test_node_wheel_uses_noro6_presets(self):
        import json, os, tempfile
        from pathlib import Path
        from tests.lz_compress import compress_utf16

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "configs" / "noro6" / "noro6"
        path.parent.mkdir(parents=True)
        leaf = lambda n: {"name": n, "isDirectory": False}
        tree = {
            "savedata": {
                "name": "r",
                "isDirectory": True,
                "childItems": [leaf("B-2-2"), leaf("B-2-2-A")],
            }
        }
        path.write_text(compress_utf16(json.dumps(tree)), encoding="utf-8")
        old = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, old)
        self.store.set("combat.sortie_map", "2-2")
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(
                r for r in screen._field_rows() if r.key == "combat.sortie_map"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("right", "right", "down", "enter")  # node — → A
            await pilot.pause()
            self.assertEqual(self.store.get("combat.sortie_map"), "2-2-A")

    async def test_recipe_dialog_is_two_by_two(self):
        from tui.editor.dialogs import NumberDialog
        from tui.editor.widgets import WheelPicker

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "f")
            next(
                r for r in screen._field_rows() if r.key == "factory.build_recipe"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            picker = app.screen.query_one(WheelPicker)
            labels = [
                [picker.wheels[i].label for i in row if picker.wheels[i].label]
                for row in picker._block_rows()
            ]
            self.assertEqual(labels, [["fuel", "steel"], ["ammo", "bauxite"]])

    async def test_int_wheel_clamps_to_range(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "g")
            next(
                r for r in screen._field_rows() if r.key == "general.jst_offset"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press(
                "right", "down", "down", "down", "enter"
            )  # tens digit 0→3: clamped to 20
            await pilot.pause()
            self.assertEqual(self.store.get("general.jst_offset"), 20)

    async def test_edit_level_adjusts_with_left_right_and_escape_restores(self):
        self.store.set("combat.retreat_limit", 2)
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            row = next(
                r for r in screen._field_rows() if r.key == "combat.retreat_limit"
            )
            row.focus()
            await pilot.press("enter")
            self.assertTrue(row.in_edit)
            await pilot.press("left")
            self.assertEqual(self.store.get("combat.retreat_limit"), 1)
            await pilot.press("right", "right", "right", "right")
            self.assertEqual(
                self.store.get("combat.retreat_limit"), 4
            )  # no wrap-around at the end
            await pilot.press(
                "down", "c", "w"
            )  # other keys have no effect while editing
            self.assertIs(screen.focused, row)
            self.assertEqual(screen.entry.module, "combat")
            await pilot.press("escape")  # restored to the 2 from before entering
            self.assertEqual(self.store.get("combat.retreat_limit"), 2)
            self.assertFalse(row.in_edit)
            self.assertEqual(len(app.screen_stack), 2)  # still in the editor
            next(r for r in screen._field_rows() if r.key == "combat.enabled").focus()
            await pilot.press("enter", "right")
            self.assertTrue(self.store.get("combat.enabled"))
            await pilot.press("left")
            self.assertFalse(self.store.get("combat.enabled"))
            await pilot.press("enter")

    async def test_left_on_the_list_goes_to_module_list_for_every_kind_of_row(self):
        from tui.editor.screen import ModuleList

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            for key in ("combat.sortie_map", "combat.retreat_limit", "combat.enabled"):
                next(r for r in screen._field_rows() if r.key == key).focus()
                before = self.store.get(key)
                await pilot.press("left")
                self.assertIsInstance(screen.focused, ModuleList, key)
                self.assertEqual(
                    self.store.get(key), before, key
                )  # ← no longer changes the value

    async def test_expedition_bulk_row(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "e")
            bulk = next(
                r for r in screen._field_rows() if r.key == "@expedition.all_fleets"
            )
            bulk.focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("down", "enter")  # overnight
            await pilot.pause()
            for key in (
                "expedition.fleet_2",
                "expedition.fleet_3",
                "expedition.fleet_4",
            ):
                self.assertEqual(self.store.get(key), ["overnight"])
            await pilot.press("d")  # restore the defaults of the three fleets
            self.assertEqual(self.store.get("expedition.fleet_3"), [])

    async def test_quest_dialog_lists_only_catalog(self):
        import json, os, tempfile
        from pathlib import Path
        from tui.editor.dialogs import QuestDialog

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        qdir = Path(tmp.name) / "data" / "quests"
        qdir.mkdir(parents=True)
        (qdir / "quests.json").write_text(
            json.dumps(
                {
                    "Bd1": {"id": 201, "type": "daily"},
                    "Cd1": {"id": 303, "type": "daily"},
                }
            )
        )
        old = os.getcwd()
        os.chdir(tmp.name)
        self.addCleanup(os.chdir, old)
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "u")
            next(r for r in screen._field_rows() if r.key == "quest.quests").focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, QuestDialog)
            self.assertEqual([g for g, _ in app.screen.groups], ["Bd", "Cd"])
            await pilot.press("down", "space", "enter")  # tick Bd1
            await pilot.pause()
            self.assertEqual(self.store.get("quest.quests"), ["Bd1"])

    async def test_fleet_preset_is_a_single_value_wheel(self):
        from tui.editor.dialogs import PresetWheelDialog
        from tui.editor.widgets import WheelPicker

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(
                r for r in screen._field_rows() if r.key == "combat.fleet_presets"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, PresetWheelDialog)
            picker = app.screen.query_one(WheelPicker)
            self.assertEqual(picker.wheels[0].items[:3], ["disable", "auto", "1"])
            self.assertEqual(picker.values(), ["disable"])  # default [] → disable
            await pilot.press("down", "down", "down", "enter")  # disable → auto → 1 → 2
            await pilot.pause()
            self.assertEqual(self.store.get("combat.fleet_presets"), [2])

    async def test_fleet_preset_auto_and_pvp(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(
                r for r in screen._field_rows() if r.key == "combat.fleet_presets"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("down", "enter")  # the item after disable = auto
            await pilot.pause()
            self.assertEqual(self.store.get("combat.fleet_presets"), ["auto"])
            next(
                r for r in screen._field_rows() if r.key == "combat.fleet_presets"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("up", "enter")  # back to disable
            await pilot.pause()
            self.assertEqual(self.store.get("combat.fleet_presets"), [])
            await pilot.press("escape")
            await pilot.pause()
            screen = await self.open_editor(pilot, "p")
            next(r for r in screen._field_rows() if r.key == "pvp.fleet_preset").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("down", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("pvp.fleet_preset"), "auto")

    async def test_enter_never_opens_a_dialog_for_adjustable_rows(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            for key in ("combat.fleet_mode", "combat.retreat_limit", "combat.enabled"):
                before = self.store.get(key)
                next(r for r in screen._field_rows() if r.key == key).focus()
                await pilot.press("enter")
                await pilot.pause()
                self.assertEqual(len(app.screen_stack), 2, key)  # no dialog popped up
                self.assertEqual(
                    self.store.get(key), before, key
                )  # entering edit mode does not change the value
                await pilot.press("space")  # Space while editing = next value
                self.assertNotEqual(self.store.get(key), before, key)
                await pilot.press("enter")  # confirm
                self.assertIsNone(screen._edit_row)

    async def test_click_selects_then_enters_then_arrows_adjust(self):
        self.store.set("combat.retreat_limit", 2)
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            screen._field_rows()[0].focus()
            await pilot.pause()
            row = next(
                r for r in screen._field_rows() if r.key == "combat.retreat_limit"
            )
            region = row.region
            where = (region.x + 3 + 14 + 2, region.y)
            await pilot.click(offset=where)  # 1) only selects
            await pilot.pause()
            self.assertIs(screen.focused, row)
            self.assertFalse(row.in_edit)
            self.assertEqual(self.store.get("combat.retreat_limit"), 2)
            self.assertEqual(len(app.screen_stack), 2)  # no dialog opened
            await pilot.click(offset=where)  # 2) click again → enter editing
            await pilot.pause()
            self.assertTrue(row.in_edit)
            self.assertTrue(row._arrows_drawn)
            _, (l0, l1), (r0, r1) = row._zones  # 3) clicking an arrow changes the value
            await pilot.click(offset=(region.x + r0 + 1, region.y))
            await pilot.pause()
            self.assertEqual(self.store.get("combat.retreat_limit"), 3)
            await pilot.click(offset=(region.x + l0 + 1, region.y))
            await pilot.click(offset=(region.x + l0 + 1, region.y))
            await pilot.pause()
            self.assertEqual(self.store.get("combat.retreat_limit"), 1)
            await pilot.press("enter")
            self.assertFalse(row.in_edit)

    async def test_clicking_another_row_confirms_the_edit(self):
        self.store.set("combat.retreat_limit", 2)
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            row = next(
                r for r in screen._field_rows() if r.key == "combat.retreat_limit"
            )
            row.focus()
            await pilot.press("enter", "right")
            other = next(
                r for r in screen._field_rows() if r.key == "combat.sortie_map"
            )
            await pilot.click(offset=(other.region.x + 20, other.region.y))
            await pilot.pause()
            self.assertFalse(row.in_edit)
            self.assertEqual(
                self.store.get("combat.retreat_limit"), 3
            )  # keep the change

    async def test_clicking_a_wide_field_still_opens_its_editor(self):
        from tui.editor.dialogs import MapDialog

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            row = next(r for r in screen._field_rows() if r.key == "combat.sortie_map")
            await pilot.click(offset=(row.region.x + 20, row.region.y))
            await pilot.pause()
            self.assertIsInstance(app.screen, MapDialog)

    async def test_recipe_dialog_tab_walks_resources_then_buttons(self):
        from tui.editor.widgets import WheelPicker

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "f")
            next(
                r for r in screen._field_rows() if r.key == "factory.build_recipe"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            picker = app.screen.query_one(WheelPicker)
            seen = []
            for _ in range(6):
                kind, value = picker._current_target()
                seen.append(picker.wheels[value].label if kind == "group" else value)
                await pilot.press("tab")
            self.assertEqual(seen, ["fuel", "steel", "ammo", "bauxite", "OK", "Cancel"])

    async def test_table_dialog_adds_node_select(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            next(
                r for r in screen._field_rows() if r.key == "combat.node_selects"
            ).focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("a", "tab", "b", "enter", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("combat.node_selects"), ["a>b"])

    async def test_scheduler_rule_row(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "s")
            next(r for r in screen._field_rows() if r.key == "scheduler.rules").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("space", "o")
            await pilot.pause()
            self.assertEqual(
                self.store.get("scheduler.rules"), ["time:0300:stop:kcauto"]
            )

    async def test_json_dialog_edits_unknown_object(self):
        self.store.set("extra.tree", {})
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "o")
            next(r for r in screen._field_rows() if r.key == "extra.tree").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("ctrl+s")
            await pilot.pause()
            self.assertEqual(self.store.get("extra.tree"), {})

    async def test_tree_editor_builds_slots(self):
        from tui.editor.dialogs import TreeDialog

        self.store.set("extra.tree", {})
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "o")
            next(r for r in screen._field_rows() if r.key == "extra.tree").focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertIsInstance(app.screen, TreeDialog)
            await pilot.press("a")  # add an object
            await pilot.pause()
            await pilot.press("s", "1", "enter")  # key = s1, jump to the type list
            await pilot.press("down", "down", "down", "down", "down", "enter")  # object
            await pilot.pause()
            await pilot.press("a")  # add an int under s1
            await pilot.pause()
            await pilot.press(
                "n", "enter", "down", "enter"
            )  # key = n, type int → open the wheel
            await pilot.pause()
            await pilot.press(
                "right", "right", "down", "down", "enter"
            )  # after scrolling to 0..0, + 2
            await pilot.pause()
            await pilot.press("ctrl+s")
            await pilot.pause()
            value = self.store.get("extra.tree")
            self.assertEqual(list(value), ["s1"])
            self.assertEqual(list(value["s1"]), ["n"])
            self.assertIsInstance(value["s1"]["n"], int)

    async def test_tree_editor_edits_existing_slots_and_cancel_keeps_original(self):
        self.store.set("extra.tree", {"1": {"ship": 5, "name": "x"}})
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "o")
            next(r for r in screen._field_rows() if r.key == "extra.tree").focus()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.press("down", "x")  # delete ship
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(
                self.store.get("extra.tree"), {"1": {"ship": 5, "name": "x"}}
            )

    async def test_akashi_switch_sets_enabled_and_slots(self):
        from tui import akashi

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot, "h")
            rows = [r.key for r in screen._field_rows()]
            self.assertEqual(
                rows, ["ship_switcher.enabled"]
            )  # slots is not shown directly
            next(
                r for r in screen._field_rows() if r.key == "ship_switcher.enabled"
            ).focus()
            await pilot.press("enter", "space", "enter")
            await pilot.pause()
            self.assertTrue(self.store.get("ship_switcher.enabled"))
            self.assertEqual(self.store.get("ship_switcher.slots"), akashi.AKASHI_SLOTS)
            await pilot.press("enter", "space", "enter")
            await pilot.pause()
            self.assertEqual(self.store.get("ship_switcher.slots"), {})

    async def test_compact_layout_on_a_narrow_terminal(self):
        from tui.editor.screen import ModuleTabs

        app = self.make_app()
        async with app.run_test(size=(44, 28)) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.pause()
            self.assertTrue(screen.has_class("narrow"))
            self.assertTrue(screen.has_class("compact"))
            row = screen._field_rows()[0]
            self.assertEqual(row.size.height, 2)
            tabs = screen.query_one(ModuleTabs)
            self.assertTrue(tabs.display)
            self.assertFalse(screen.query_one("#ed-left").display)
            before = screen.entry.module
            await pilot.click(ModuleTabs, offset=(tabs.size.width - 2, 0))
            await pilot.pause()
            self.assertNotEqual(screen.entry.module, before)
            await pilot.click(ModuleTabs, offset=(1, 0))
            await pilot.pause()
            self.assertEqual(screen.entry.module, before)

    async def test_rows_are_one_line_again_when_the_terminal_grows(self):
        app = self.make_app()
        async with app.run_test(size=(44, 28)) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.pause()
            self.assertEqual(screen._field_rows()[0].size.height, 2)
            await pilot.resize_terminal(120, 40)
            await pilot.pause()
            self.assertFalse(screen.has_class("compact"))
            self.assertFalse(screen.has_class("narrow"))
            self.assertEqual(screen._field_rows()[0].size.height, 1)

    async def test_arrows_still_move_rows_in_compact_mode(self):
        app = self.make_app()
        async with app.run_test(size=(44, 20)) as pilot:
            screen = await self.open_editor(pilot)
            rows = screen._field_rows()
            for i in range(1, 8):
                await pilot.press("down")
                self.assertIs(screen.focused, rows[i])

    async def test_dialogs_work_on_a_narrow_terminal(self):
        app = self.make_app()
        async with app.run_test(size=(50, 30)) as pilot:
            screen = await self.open_editor(pilot, "s")
            next(r for r in screen._field_rows() if r.key == "scheduler.rules").focus()
            await pilot.press("enter")
            await pilot.pause()
            self.assertTrue(app.screen.has_class("narrow"))
            await pilot.press("space", "o")
            await pilot.pause()
            self.assertEqual(
                self.store.get("scheduler.rules"), ["time:0300:stop:kcauto"]
            )

    async def test_dashboard_survives_very_small_terminals(self):
        from tui.widgets.bars import StatusBar

        app = self.make_app()
        for size in ((30, 12), (36, 20), (60, 14)):
            async with app.run_test(size=size) as pilot:
                await pilot.pause()
                app.query_one(StatusBar).refresh_from(self.store)
                app = self.make_app()

    async def test_search_jumps_to_field(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.press("slash")
            await pilot.pause()
            for ch in "secretary":
                await pilot.press(ch)
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(screen.entry.module, "factory")
            self.assertTrue(screen.focused.key.endswith("secretary"))

    async def test_unknown_keys_appear_under_other(self):
        self.store.set("future.thing", 5)
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.press(
                "o"
            )  # "o" is a shortcut inside the editor; the dashboard has none
            self.assertEqual(screen.entry.module, "other")
            self.assertEqual([r.key for r in screen._field_rows()], ["future.thing"])

    async def test_save_from_editor_writes_file(self):
        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.open_editor(pilot)
            await pilot.press(
                "enter", "right", "enter", "w"
            )  # enter, change to on, confirm, save
            await pilot.pause()
        self.assertTrue(self.path.exists())

    async def test_logs_still_arrive_while_editor_is_open(self):
        from tui.runner import LOG_OUTPUT

        app = self.make_app()
        async with app.run_test(size=BIG) as pilot:
            await self.open_editor(pilot)
            self.runner.on_log(LOG_OUTPUT, "hello from kcauto")
            await pilot.pause()
            log = app._dash.query_one("LogBox")
            self.assertTrue(any("hello from kcauto" in t.plain for t in log.history))

    async def test_narrow_terminal_hides_module_list(self):
        app = self.make_app()
        async with app.run_test(size=(60, 30)) as pilot:
            screen = await self.open_editor(pilot)
            await pilot.pause()
            self.assertTrue(screen.has_class("narrow"))
            # level 1 (list) ← → are always navigation: narrow window = switch module, the switch's value is not changed
            next(r for r in screen._field_rows() if r.key == "combat.enabled").focus()
            await pilot.press("right")
            self.assertEqual(screen.entry.module, "expedition")
            self.assertFalse(self.store.get("combat.enabled"))


if __name__ == "__main__":
    unittest.main()
