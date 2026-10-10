import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "kcauto"))

from util import poi_plugins  # noqa: E402


def write_plugin(plugins_dir, name, version):
    plugin_dir = plugins_dir / "node_modules" / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    with (plugin_dir / "package.json").open("w", encoding="utf-8") as manifest:
        json.dump({"name": name, "version": version}, manifest)
    return plugin_dir


class PoiPluginsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.plugins_dir = Path(self._tmp.name) / "plugins"
        (self.plugins_dir / "node_modules").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_plugins_are_reported(self):
        problems = poi_plugins.check_required_plugins(self.plugins_dir)
        reported = {name for name, _ in problems}
        self.assertEqual(reported, set(poi_plugins.REQUIRED_POI_PLUGINS))
        self.assertTrue(all("not installed" in msg for _, msg in problems))

    def test_installed_plugins_pass_check(self):
        for name in poi_plugins.REQUIRED_POI_PLUGINS:
            write_plugin(self.plugins_dir, name, "9.9.9")
        self.assertEqual(poi_plugins.check_required_plugins(self.plugins_dir), [])

    def test_outdated_forwarder_is_reported(self):
        for name in poi_plugins.REQUIRED_POI_PLUGINS:
            write_plugin(self.plugins_dir, name, "9.9.9")
        write_plugin(self.plugins_dir, "poi-plugin-forwarder", "1.0.0")

        problems = poi_plugins.check_required_plugins(self.plugins_dir)
        self.assertEqual(len(problems), 1)
        name, message = problems[0]
        self.assertEqual(name, "poi-plugin-forwarder")
        self.assertIn("1.1.0", message)
        self.assertIn("1.0.0", message)

    def test_unrelated_and_scoped_packages_are_ignored(self):
        for name in poi_plugins.REQUIRED_POI_PLUGINS:
            write_plugin(self.plugins_dir, name, "9.9.9")
        write_plugin(self.plugins_dir, "react", "18.0.0")
        scoped = self.plugins_dir / "node_modules" / "@poi" / "plugin-eslint"
        scoped.mkdir(parents=True)
        with (scoped / "package.json").open("w", encoding="utf-8") as manifest:
            json.dump({"name": "@poi/plugin-eslint", "version": "1.0.0"}, manifest)

        installed = poi_plugins.get_installed_plugins(self.plugins_dir)
        self.assertIn("@poi/plugin-eslint", installed)
        self.assertIn("poi-plugin-forwarder", installed)
        self.assertNotIn("react", installed)
        self.assertEqual(poi_plugins.check_required_plugins(self.plugins_dir), [])

    def test_install_hints_cover_every_required_plugin(self):
        hints = "\n".join(poi_plugins.build_install_hints(self.plugins_dir))
        for name in poi_plugins.REQUIRED_POI_PLUGINS:
            self.assertIn(name, hints)
        self.assertIn("npm install", hints)

    def test_check_without_plugin_directory_reports_missing(self):
        missing = Path(self._tmp.name) / "does-not-exist"
        problems = poi_plugins.check_required_plugins(missing)
        self.assertEqual(
            {name for name, _ in problems},
            set(poi_plugins.REQUIRED_POI_PLUGINS),
        )

    def test_real_install_check_runs_against_live_poi(self):
        plugins_dir = poi_plugins.find_poi_plugins_dir()
        if plugins_dir is None:
            self.skipTest("POI plugin directory not present on this machine")
        problems = poi_plugins.check_required_plugins(plugins_dir)
        self.assertEqual(
            problems,
            [],
            f"local POI install has plugin problems: {problems}",
        )


if __name__ == "__main__":
    unittest.main()
