"""kcauto 行程控制。與 Textual 無關,透過 callback 回報日誌與狀態。

沿用舊 CUI(``cui/util.py``)的行為
  * 指令:優先 ``./bin/kcauto_custom/kcauto_custom[.exe]``,否則 ``python kcauto``,
    參數固定 ``--cli --cfg <config 名稱>``。
  * 暫停:用 psutil 對行程 suspend / resume(整個行程凍結)。
  * 輸出含 ``Press Enter to continue`` 時進入「等待 Enter」,由使用者決定何時往 stdin 寫入換行。
  * 重新載入設定 = 結束行程後重新啟動(kcauto 沒有熱重載)。

與舊版不同(皆為修正)
  * 結束行程時連同子行程一起結束,避免殘留(舊版只 kill 主行程)。
  * 設定 PYTHONUNBUFFERED / PYTHONIOENCODING,日誌不會被管線緩衝延遲、
    Windows 上也不會因 locale 編碼而亂碼。
  * Python 備援模式使用 ``sys.executable``,不再依賴 PATH 上的 python / python3。
  * 不會自動啟動;由使用者明確操作。
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
READ_LIMIT = 1 << 20          # 單行輸出上限(預設 64 KiB 太小)

LOG_OUTPUT = "output"         # kcauto 的輸出(可能含 ANSI)
LOG_SYSTEM = "system"         # CUI 自己的訊息


class RunState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class UnsupportedPlatform(RuntimeError):
    pass


@dataclass(frozen=True)
class ProcSample:
    pid: int
    uptime: float      # 秒
    cpu: float         # %,可能超過 100(多核心)
    rss: int           # bytes


# ---------------------------------------------------------------------- #
def build_command(
    cwd: str | os.PathLike,
    *,
    config_name: str = "config_cui",
    platform: str = sys.platform,
    python: str = sys.executable,
    isfile: Callable[[str], bool] = os.path.isfile,
) -> tuple[list[str], str]:
    """回傳 (指令, 要顯示在日誌的說明)。"""
    if platform.startswith("linux"):
        filename = "kcauto_custom"
    elif platform in ("darwin", "win32"):
        filename = "kcauto_custom.exe"
    else:
        raise UnsupportedPlatform(f"不支援的作業系統:{platform}")

    args = ["--cli", "--cfg", config_name]
    # 用絕對路徑:Windows 的 CreateProcess 對相對執行檔路徑的解析和 cwd 參數有出入
    exec_path = os.path.join(os.path.abspath(cwd), "bin", "kcauto_custom", filename)
    if isfile(exec_path):
        return [exec_path, *args], f"從 {filename} 啟動 kcauto"
    return [python, "kcauto", *args], f"找不到 {filename},改用 Python 啟動 kcauto"


def kill_tree(ps: Optional[psutil.Process], pid: int, timeout: float) -> None:
    """結束行程與其所有子行程(包含被 suspend 的)。"""
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
    # 只等孫行程。直接子行程(procs 最後一個)的結束狀態必須留給 asyncio 讀取,
    # 否則 asyncio 會回報 "exit status already read" 並拿到錯誤的 exit code。
    descendants = procs[:-1]
    if descendants:
        psutil.wait_procs(descendants, timeout=timeout)


LogCallback = Callable[[str, str], None]            # (kind, text)
StateCallback = Callable[["RunState", bool], None]  # (state, waiting_enter)


class Runner:
    def __init__(
        self,
        *,
        cwd: str | os.PathLike | None = None,
        config_name: str = "config_cui",
        command_builder: Callable[[], tuple[Sequence[str], str]] | None = None,
        env: dict[str, str] | None = None,
        on_log: LogCallback | None = None,
        on_state: StateCallback | None = None,
        stop_timeout: float = 5.0,
    ) -> None:
        self.cwd = os.fspath(cwd) if cwd is not None else os.getcwd()
        self.config_name = config_name
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
    # 狀態
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
    # 啟動 / 結束
    # ------------------------------------------------------------------ #
    def _build(self) -> tuple[Sequence[str], str]:
        if self._command_builder is not None:
            return self._command_builder()
        return build_command(self.cwd, config_name=self.config_name)

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
        except UnsupportedPlatform as exc:
            self._log(LOG_SYSTEM, f"無法啟動 kcauto:{exc}")
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
            self._log(LOG_SYSTEM, f"啟動失敗:{exc}")
            return False

        self._proc = proc
        self._paused = False
        self._waiting = False
        self._stopping = False
        try:
            self._ps = psutil.Process(proc.pid)
            self._ps.cpu_percent(None)       # 預熱,之後的取樣才有意義
        except psutil.Error:
            self._ps = None
        self._reader = asyncio.create_task(self._read(proc))
        self._emit_state()
        return True

    async def stop(self) -> bool:
        """結束行程(含子行程)。原本就沒在跑時回傳 False。"""
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
        """重新載入設定 = 結束後重新啟動(沒在跑就直接啟動)。"""
        if await self.stop():
            self._log(LOG_SYSTEM, "kcauto 重新啟動")
        return await self.start()

    def kill_now(self) -> None:
        """同步結束行程;給 App 關閉時的最後保險,不等待日誌收尾。"""
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return
        self._stopping = True
        kill_tree(self._ps, proc.pid, 1.0)

    # ------------------------------------------------------------------ #
    # 暫停 / 繼續
    # ------------------------------------------------------------------ #
    def pause(self) -> bool:
        if not self.is_alive or self._paused or self._ps is None:
            return False
        try:
            self._ps.suspend()
        except psutil.Error as exc:
            self._log(LOG_SYSTEM, f"暫停失敗:{exc}")
            return False
        self._paused = True
        self._log(LOG_SYSTEM, "kcauto 已暫停")
        self._emit_state()
        return True

    def resume(self) -> bool:
        if not self.is_alive or not self._paused or self._ps is None:
            return False
        try:
            self._ps.resume()
        except psutil.Error as exc:
            self._log(LOG_SYSTEM, f"繼續失敗:{exc}")
            return False
        self._paused = False
        self._log(LOG_SYSTEM, "kcauto 已繼續")
        self._emit_state()
        return True

    def toggle_pause(self) -> Optional[bool]:
        """切換暫停/繼續,回傳切換後是否處於暫停;沒在執行時回傳 None。"""
        if not self.is_alive:
            return None
        if self._paused:
            self.resume()
        else:
            self.pause()
        return self._paused

    # ------------------------------------------------------------------ #
    # 等待 Enter
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
    # 取樣
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
    # 讀取輸出
    # ------------------------------------------------------------------ #
    async def _read(self, proc: asyncio.subprocess.Process) -> None:
        try:
            stream = proc.stdout
            assert stream is not None
            while True:
                try:
                    raw = await stream.readline()
                except ValueError:                    # 單行超過 READ_LIMIT
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
        if proc is not self._proc:        # 已經被新的行程取代
            return
        stopping = self._stopping
        self._proc = None
        self._ps = None
        self._paused = False
        self._waiting = False
        self._stopping = False
        if stopping:
            self._log(LOG_SYSTEM, "kcauto 已終止")
        else:
            self._log(LOG_SYSTEM, f"kcauto 已結束(exit code {code})")
        self._emit_state()
