"""kcauto process control. Independent of Textual; reports log and state through callbacks.

Keeps the behaviour of the old CUI (``cui/util.py``)
  * Command: prefer ``./bin/kcauto_custom/kcauto_custom[.exe]``, otherwise ``python kcauto``,
    with fixed arguments ``--cli --cfg <config name>`` (plus ``--debug-output`` in debug mode).
  * Pause: suspend / resume the process with psutil (the whole process is frozen).
  * When the output contains ``Press Enter to continue`` it enters "waiting for Enter" and the user decides when to write a newline to stdin.
  * Reloading config = end the process and start it again (kcauto has no hot reload).

Differences from the old version (all fixes)
  * Ending the process also ends its child processes, so nothing is left behind (the old version only killed the main process).
  * Sets PYTHONUNBUFFERED / PYTHONIOENCODING, so the log is not delayed by pipe buffering and is not garbled by the locale encoding on Windows.
  * The Python fallback uses ``sys.executable`` instead of relying on python / python3 on PATH.
  * Never starts automatically; the user must start it explicitly.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Sequence

import psutil

PROMPT = "Press Enter to continue"
READ_LIMIT = 1 << 20  # per-line output limit (the default 64 KiB is too small)

DEBUG_FLAG = "--debug-output"  # appended to the kcauto command line in debug mode

LOG_OUTPUT = "output"  # kcauto output (may contain ANSI)
LOG_SYSTEM = "system"  # messages from the CUI itself


class RunState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class StartError(RuntimeError):
    """kcauto cannot be started (the message is shown in the log)."""


class KcautoNotFound(StartError):
    """Packaged CUI, but ``bin/kcauto_custom`` is missing: there is no Python fallback in a frozen build."""


class UnsupportedPlatform(StartError):
    pass


@dataclass(frozen=True)
class ProcSample:
    pid: int
    uptime: float  # seconds
    cpu: float  # %, may exceed 100 (multiple cores)
    rss: int  # bytes


# ---------------------------------------------------------------------- #
def build_command(
    cwd: str | os.PathLike,
    *,
    config_name: str = "config_cui",
    debug: bool = False,
    platform: str = sys.platform,
    python: str = sys.executable,
    isfile: Callable[[str], bool] = os.path.isfile,
    frozen: bool = bool(getattr(sys, "frozen", False)),
) -> tuple[list[str], str]:
    """Return (command, a note to show in the log)."""
    if platform.startswith("linux"):
        filename = "kcauto_custom"
    elif platform in ("darwin", "win32"):
        filename = "kcauto_custom.exe"
    else:
        raise UnsupportedPlatform(f"Unsupported platform: {platform}")

    args = ["--cli", "--cfg", config_name]
    if debug:
        args.append(DEBUG_FLAG)
    # Use an absolute path: on Windows CreateProcess resolves relative executable paths differently from the cwd argument
    exec_path = os.path.join(os.path.abspath(cwd), "bin", "kcauto_custom", filename)
    if isfile(exec_path):
        return [exec_path, *args], f"Starting kcauto from {filename}"
    if frozen:
        raise KcautoNotFound(f"{exec_path} not found")
    return [
        python,
        "kcauto",
        *args,
    ], f"{filename} not found; starting kcauto with Python"


def kill_tree(ps: Optional[psutil.Process], pid: int, timeout: float) -> None:
    """End the process and all its children (including suspended ones)."""
    try:
        root = ps if ps is not None else psutil.Process(pid)
    except psutil.Error:
        return
    try:
        procs = root.children(recursive=True) + [root]
    except psutil.Error:
        procs = [root]
    for proc in procs:
        try:
            proc.kill()
        except psutil.Error:
            pass
    # Only wait for grandchildren. The exit status of the direct child (the last in procs) must be left for asyncio to read,
    # otherwise asyncio reports "exit status already read" and gets the wrong exit code.
    descendants = procs[:-1]
    if descendants:
        psutil.wait_procs(descendants, timeout=timeout)


LogCallback = Callable[[str, str], None]  # (kind, text)
StateCallback = Callable[["RunState", bool], None]  # (state, waiting_enter)


class Runner:
    def __init__(
        self,
        *,
        cwd: str | os.PathLike | None = None,
        config_name: str = "config_cui",
        debug: bool = False,
        command_builder: Callable[[], tuple[Sequence[str], str]] | None = None,
        env: dict[str, str] | None = None,
        on_log: LogCallback | None = None,
        on_state: StateCallback | None = None,
        stop_timeout: float = 5.0,
    ) -> None:
        self.cwd = os.fspath(cwd) if cwd is not None else os.getcwd()
        self.config_name = config_name
        self.debug = (
            debug  # read at every start, so a change applies from the next start
        )
        self.on_log = on_log
        self.on_state = on_state
        self.stop_timeout = stop_timeout
        self._command_builder = command_builder
        self._extra_env = env or {}

        self._proc: Optional[asyncio.subprocess.Process] = None
        self._ps: Optional[psutil.Process] = None
        self._reader: Optional[asyncio.Task] = None
        self._paused = False
        self._waiting = False
        self._stopping = False
        self._last_emitted: tuple[RunState, bool] | None = None

    # ------------------------------------------------------------------ #
    # state
    # ------------------------------------------------------------------ #
    @property
    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    @property
    def state(self) -> RunState:
        if not self.is_alive:
            return RunState.STOPPED
        return RunState.PAUSED if self._paused else RunState.RUNNING

    @property
    def waiting_enter(self) -> bool:
        return self.is_alive and self._waiting

    @property
    def pid(self) -> Optional[int]:
        return self._proc.pid if self.is_alive else None

    def _emit_state(self) -> None:
        current = (self.state, self.waiting_enter)
        if current == self._last_emitted:
            return
        self._last_emitted = current
        if self.on_state:
            self.on_state(*current)

    def _log(self, kind: str, text: str) -> None:
        if self.on_log:
            self.on_log(kind, text)

    # ------------------------------------------------------------------ #
    # start / exit
    # ------------------------------------------------------------------ #
    def _build(self) -> tuple[Sequence[str], str]:
        if self._command_builder is not None:
            return self._command_builder()
        return build_command(self.cwd, config_name=self.config_name, debug=self.debug)

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.setdefault("PYTHONUNBUFFERED", "1")
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.update(self._extra_env)
        return env

    async def start(self) -> bool:
        if self.is_alive:
            return False
        try:
            command, note = self._build()
        except StartError as exc:
            self._log(LOG_SYSTEM, f"Cannot start kcauto: {exc}")
            return False
        self._log(LOG_SYSTEM, note)
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self.cwd,
                env=self._env(),
                limit=READ_LIMIT,
            )
        except OSError as exc:
            self._log(LOG_SYSTEM, f"Failed to start: {exc}")
            return False

        self._proc = proc
        self._paused = False
        self._waiting = False
        self._stopping = False
        try:
            self._ps = psutil.Process(proc.pid)
            self._ps.cpu_percent(None)  # warm-up, so later samples are meaningful
        except psutil.Error:
            self._ps = None
        self._reader = asyncio.create_task(self._read(proc))
        self._emit_state()
        return True

    async def stop(self) -> bool:
        """End the process (and its children). Returns False when it was not running."""
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return False
        self._stopping = True
        await asyncio.to_thread(kill_tree, self._ps, proc.pid, self.stop_timeout)
        reader = self._reader
        if reader is not None:
            try:
                await asyncio.wait_for(asyncio.shield(reader), self.stop_timeout)
            except asyncio.TimeoutError:
                reader.cancel()
                self._finish(proc, proc.returncode)
        return True

    async def restart(self) -> bool:
        """Reload config = restart after ending (just start if it is not running)."""
        if await self.stop():
            self._log(LOG_SYSTEM, "kcauto restarting")
        return await self.start()

    def kill_now(self) -> None:
        """End the process synchronously; a last safeguard when the App closes, does not wait for the log to finish."""
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return
        self._stopping = True
        kill_tree(self._ps, proc.pid, 1.0)

    # ------------------------------------------------------------------ #
    # pause / resume
    # ------------------------------------------------------------------ #
    def pause(self) -> bool:
        if not self.is_alive or self._paused or self._ps is None:
            return False
        try:
            self._ps.suspend()
        except psutil.Error as exc:
            self._log(LOG_SYSTEM, f"Pause failed: {exc}")
            return False
        self._paused = True
        self._log(LOG_SYSTEM, "kcauto paused")
        self._emit_state()
        return True

    def resume(self) -> bool:
        if not self.is_alive or not self._paused or self._ps is None:
            return False
        try:
            self._ps.resume()
        except psutil.Error as exc:
            self._log(LOG_SYSTEM, f"Resume failed: {exc}")
            return False
        self._paused = False
        self._log(LOG_SYSTEM, "kcauto resumed")
        self._emit_state()
        return True

    def toggle_pause(self) -> Optional[bool]:
        """Toggle pause / resume; returns whether it is paused afterwards, or None when not running."""
        if not self.is_alive:
            return None
        if self._paused:
            self.resume()
        else:
            self.pause()
        return self._paused

    # ------------------------------------------------------------------ #
    # waiting for Enter
    # ------------------------------------------------------------------ #
    async def send_enter(self) -> bool:
        proc = self._proc
        if proc is None or proc.stdin is None or not self.waiting_enter:
            return False
        try:
            proc.stdin.write(b"\n")
            await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False
        self._waiting = False
        self._emit_state()
        return True

    # ------------------------------------------------------------------ #
    # sampling
    # ------------------------------------------------------------------ #
    def sample(self) -> Optional[ProcSample]:
        ps = self._ps
        if ps is None or not self.is_alive:
            return None
        try:
            with ps.oneshot():
                return ProcSample(
                    pid=ps.pid,
                    uptime=max(time.time() - ps.create_time(), 0.0),
                    cpu=ps.cpu_percent(None),
                    rss=ps.memory_info().rss,
                )
        except psutil.Error:
            return None

    # ------------------------------------------------------------------ #
    # reading output
    # ------------------------------------------------------------------ #
    async def _read(self, proc: asyncio.subprocess.Process) -> None:
        try:
            stream = proc.stdout
            assert stream is not None
            while True:
                try:
                    raw = await stream.readline()
                except ValueError:  # a single line exceeded READ_LIMIT
                    raw = await stream.read(READ_LIMIT)
                if not raw:
                    break
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if not line.strip():
                    continue
                self._log(LOG_OUTPUT, line)
                if PROMPT in line and not self._waiting:
                    self._waiting = True
                    self._emit_state()
        finally:
            code = await proc.wait()
            self._finish(proc, code)

    def _finish(self, proc: asyncio.subprocess.Process, code: Optional[int]) -> None:
        if proc is not self._proc:  # already replaced by a newer process
            return
        stopping = self._stopping
        self._proc = None
        self._ps = None
        self._paused = False
        self._waiting = False
        self._stopping = False
        if stopping:
            self._log(LOG_SYSTEM, "kcauto stopped")
        else:
            self._log(LOG_SYSTEM, f"kcauto exited (exit code {code})")
        self._emit_state()
