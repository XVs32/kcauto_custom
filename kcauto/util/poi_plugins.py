import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from util.logger import Log

REQUIRED_POI_PLUGINS: Dict[str, str] = {
    "poi-plugin-forwarder": (
        "forwards KCSAPI and map resources to kcauto and hosts the POI "
        "interaction service"
    ),
    "poi-plugin-noro6-exporter": "exports ships and equipment to Noro6",
}

# The interaction service was added in this version. Older releases only
# forward KCSAPI, so the control port stays closed.
MIN_PLUGIN_VERSIONS: Dict[str, Tuple[int, ...]] = {
    "poi-plugin-forwarder": (1, 1, 0),
}

FORWARDER_GIT_INSTALL = (
    'npm install "git+https://github.com/pmsleepcheck/'
    'poi-plugin-api-forwarder.git#feature/poi-interaction-server" '
    "--allow-git=all"
)


def find_poi_plugins_dir() -> Optional[Path]:
    """Locate the directory POI installs its plugins into."""
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None
        candidates = [Path(appdata) / "poi" / "plugins"]
    elif sys.platform == "darwin":
        candidates = [
            Path.home() / "Library" / "Preferences" / "poi" / "plugins",
            Path.home() / "Library" / "Application Support" / "poi" / "plugins",
        ]
    else:
        candidates = [
            Path.home() / ".config" / "poi" / "plugins",
            Path.home() / ".poi" / "plugins",
        ]

    for candidate in candidates:
        if (candidate / "node_modules").is_dir():
            return candidate
    return None


def get_installed_plugins(plugins_dir: Path) -> Dict[str, str]:
    """Return plugin name to installed version for every POI plugin found."""
    installed = {}
    node_modules = plugins_dir / "node_modules"
    if not node_modules.is_dir():
        return installed

    for entry in node_modules.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith("@"):
            for scoped in entry.iterdir():
                if scoped.is_dir():
                    installed[f"{name}/{scoped.name}"] = _read_version(scoped)
            continue
        if not name.startswith("poi-plugin-"):
            continue
        installed[name] = _read_version(entry)
    return installed


def _read_version(plugin_dir: Path) -> str:
    manifest = plugin_dir / "package.json"
    if not manifest.is_file():
        return ""
    try:
        with manifest.open(encoding="utf-8") as manifest_file:
            return str(json.load(manifest_file).get("version", ""))
    except (OSError, ValueError):
        return ""


def _parse_version(version: str) -> Optional[Tuple[int, ...]]:
    parts: List[int] = []
    for chunk in version.split("."):
        digits = "".join(character for character in chunk if character.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts) if parts else None


def check_required_plugins(
    plugins_dir: Optional[Path] = None,
) -> List[Tuple[str, str]]:
    """Check POI for the plugins kcauto needs.

    Returns a list of (plugin name, problem description) pairs.
    """
    if plugins_dir is None:
        plugins_dir = find_poi_plugins_dir()
    if plugins_dir is None:
        return []

    installed = get_installed_plugins(plugins_dir)
    problems = []

    for name in REQUIRED_POI_PLUGINS:
        if name not in installed:
            problems.append((name, "not installed"))
            continue

        minimum = MIN_PLUGIN_VERSIONS.get(name)
        found = _parse_version(installed[name])
        if minimum is not None and (found is None or found < minimum):
            pretty_minimum = ".".join(str(part) for part in minimum)
            problems.append(
                (
                    name,
                    f"version {installed[name] or 'unknown'} is too old, "
                    f"{pretty_minimum} or newer is required",
                )
            )

    return problems


def build_install_hints(plugins_dir: Path) -> List[str]:
    """Build copy-pasteable install commands for the missing plugins."""
    hints = [f'cd "{plugins_dir}"']
    for name in REQUIRED_POI_PLUGINS:
        if name == "poi-plugin-forwarder":
            hints.append(f"{FORWARDER_GIT_INSTALL}  # {name}")
        else:
            hints.append(f"npm install {name}")
    return hints


def check_and_prompt() -> bool:
    """Log actionable install instructions for missing POI plugins.

    Returns True when every required plugin is present.
    """
    plugins_dir = find_poi_plugins_dir()
    if plugins_dir is None:
        Log.log_warn(
            "Could not locate the POI plugin directory. Skipping POI plugin check."
        )
        return True

    problems = check_required_plugins(plugins_dir)
    if not problems:
        Log.log_debug_1(f"POI plugins OK in {plugins_dir}.")
        return True

    Log.log_error(
        "POI plugins required by kcauto are missing or outdated. Install "
        "them, then restart POI:"
    )
    for name, problem in problems:
        purpose = REQUIRED_POI_PLUGINS.get(name, "")
        Log.log_error(f"  {name}: {problem} ({purpose})")
    for hint in build_install_hints(plugins_dir):
        Log.log_error(f"  {hint}")
    return False
