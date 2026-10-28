"""Runner 測試:使用真正的子行程(Python 腳本)驗證行為。"""
import asyncio
import os
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

import psutil

from tui.runner import (
    LOG_OUTPUT, LOG_SYSTEM, RunState, Runner, UnsupportedPlatform, build_command,
)

PY = sys.executable


def script(body: str) -> list:
    return [PY, "-c", textwrap.dedent(body)]


class BuildCommand(unittest.TestCase):
    def test_uses_exe_when_present(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d, "bin", "kcauto_custom", "kcauto_custom")
            exe.parent.mkdir(parents=True)
            exe.write_text("")
            cmd, note = build_command(d, platform="linux", config_name="cfg")
            self.assertEqual(cmd, [str(exe), "--cli", "--cfg", "cfg"])
            self.assertTrue(os.path.isabs(cmd[0]))
            self.assertIn("kcauto_custom", note)

    def test_falls_back_to_python(self):
        with tempfile.TemporaryDirectory() as d:
            cmd, note = build_command(d, platform="linux", python="/x/py")
            self.assertEqual(cmd, ["/x/py", "kcauto", "--cli", "--cfg", "config_cui"])
            self.assertIn("Python", note)

    def test_exe_name_per_platform(self):
        seen = []

        def fake_isfile(path):
            seen.append(os.path.basename(path))
            return True

        for plat, name in (("linux", "kcauto_custom"), ("linux2", "kcauto_custom"),
                           ("darwin", "kcauto_custom.exe"), ("win32", "kcauto_custom.exe")):
            cmd, _ = build_command(".", platform=plat, isfile=fake_isfile)
            self.assertEqual(os.path.basename(cmd[0]), name)

    def test_unsupported_platform(self):
        with self.assertRaises(UnsupportedPlatform):
            build_command(".", platform="freebsd13")


class RunnerCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.logs = []
        self.states = []
        self.runners = []

    async def asyncTearDown(self):
        for runner in self.runners:
            runner.kill_now()
        await asyncio.sleep(0.05)

    def make(self, command, **kw):
        runner = Runner(
            command_builder=lambda: (command, "test command"),
            on_log=lambda kind, text: self.logs.append((kind, text)),
            on_state=lambda state, waiting: self.states.append((state, waiting)),
            stop_timeout=5.0, **kw,
        )
        self.runners.append(runner)
        return runner

    async def wait_for(self, predicate, timeout=5.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if predicate():
                return True
            await asyncio.sleep(0.02)
        return False

    def outputs(self):
        return [t for k, t in self.logs if k == LOG_OUTPUT]

    def system(self):
        return [t for k, t in self.logs if k == LOG_SYSTEM]


class Lifecycle(RunnerCase):
    async def test_runs_and_reports_output_and_exit_code(self):
        runner = self.make(script("""
            print('\\x1b[92mstatus line\\x1b[0m', flush=True)
            print('', flush=True)
            print('second', flush=True)
            raise SystemExit(3)
        """))
        self.assertEqual(runner.state, RunState.STOPPED)
        self.assertTrue(await runner.start())
        self.assertTrue(await self.wait_for(lambda: runner.state == RunState.STOPPED))
        self.assertEqual(self.outputs(), ["\x1b[92mstatus line\x1b[0m", "second"])  # 空行略過
        self.assertIn("test command", self.system())
        self.assertTrue(any("exit code 3" in t for t in self.system()))
        self.assertEqual(self.states[0], (RunState.RUNNING, False))
        self.assertEqual(self.states[-1], (RunState.STOPPED, False))

    async def test_start_while_running_is_refused(self):
        runner = self.make(script("import time; time.sleep(30)"))
        self.assertTrue(await runner.start())
        self.assertFalse(await runner.start())
        self.assertIsNotNone(runner.pid)
        self.assertTrue(await runner.stop())

    async def test_stop_terminates_and_reports(self):
        runner = self.make(script("import time; time.sleep(30)"))
        await runner.start()
        pid = runner.pid
        # 不可出現 asyncio 的 "exit status already read" 警告(代表有人搶先 waitpid)
        with self.assertNoLogs("asyncio", level="WARNING"):
            self.assertTrue(await runner.stop())
        self.assertEqual(runner.state, RunState.STOPPED)
        self.assertIsNone(runner.pid)
        self.assertIn("kcauto 已終止", self.system())
        self.assertFalse(any("exit code" in t for t in self.system()))
        self.assertTrue(await self.wait_for(
            lambda: not psutil.pid_exists(pid) or
            psutil.Process(pid).status() == psutil.STATUS_ZOMBIE))

    async def test_stop_when_not_running(self):
        runner = self.make(script("pass"))
        self.assertFalse(await runner.stop())

    async def test_restart_gives_new_pid(self):
        runner = self.make(script("import time; time.sleep(30)"))
        await runner.start()
        first = runner.pid
        self.assertTrue(await runner.restart())
        self.assertNotEqual(runner.pid, first)
        self.assertEqual(runner.state, RunState.RUNNING)
        self.assertIn("kcauto 重新啟動", self.system())
        await runner.stop()

    async def test_restart_when_stopped_just_starts(self):
        runner = self.make(script("import time; time.sleep(30)"))
        self.assertTrue(await runner.restart())
        self.assertEqual(runner.state, RunState.RUNNING)
        self.assertNotIn("kcauto 重新啟動", self.system())
        await runner.stop()

    async def test_start_failure_is_reported(self):
        runner = Runner(
            command_builder=lambda: (["/definitely/not/here"], "x"),
            on_log=lambda k, t: self.logs.append((k, t)),
        )
        self.assertFalse(await runner.start())
        self.assertTrue(any("啟動失敗" in t for t in self.system()))
        self.assertEqual(runner.state, RunState.STOPPED)

    async def test_unsupported_platform_is_reported(self):
        def boom():
            raise UnsupportedPlatform("nope")

        runner = Runner(command_builder=boom,
                        on_log=lambda k, t: self.logs.append((k, t)))
        self.assertFalse(await runner.start())
        self.assertTrue(any("nope" in t for t in self.system()))


class Output(RunnerCase):
    async def test_unbuffered_output_arrives_while_child_is_still_running(self):
        # 子行程「沒有 flush」就睡覺:若沒設 PYTHONUNBUFFERED,這行要等結束才會出現
        runner = self.make(script("""
            import time
            print('early line')
            time.sleep(30)
        """))
        await runner.start()
        self.assertTrue(await self.wait_for(lambda: "early line" in self.outputs(), 4.0))
        await runner.stop()

    async def test_utf8_output_is_decoded(self):
        runner = self.make(script("""
            import sys
            sys.stdout.write('出擊 ⚠ 6-4\\n')
        """))
        await runner.start()
        self.assertTrue(await self.wait_for(lambda: runner.state == RunState.STOPPED))
        self.assertEqual(self.outputs(), ["出擊 ⚠ 6-4"])

    async def test_invalid_bytes_do_not_crash(self):
        runner = self.make(script("""
            import sys
            sys.stdout.buffer.write(b'bad \\xff\\xfe bytes\\n')
        """))
        await runner.start()
        self.assertTrue(await self.wait_for(lambda: runner.state == RunState.STOPPED))
        self.assertEqual(len(self.outputs()), 1)
        self.assertTrue(self.outputs()[0].startswith("bad "))

    async def test_very_long_line_is_not_fatal(self):
        runner = self.make(script("""
            print('x' * 200000, flush=True)
            print('after', flush=True)
        """))
        await runner.start()
        self.assertTrue(await self.wait_for(lambda: runner.state == RunState.STOPPED))
        self.assertIn("after", self.outputs())
        self.assertEqual(len(self.outputs()[0]), 200000)

    async def test_stderr_is_merged(self):
        runner = self.make(script("""
            import sys
            print('to stderr', file=sys.stderr, flush=True)
        """))
        await runner.start()
        self.assertTrue(await self.wait_for(lambda: runner.state == RunState.STOPPED))
        self.assertIn("to stderr", self.outputs())


class PressEnter(RunnerCase):
    PROMPT_SCRIPT = """
        import sys
        print('working', flush=True)
        print('Press Enter to continue', flush=True)
        sys.stdin.readline()
        print('got enter', flush=True)
    """

    async def test_prompt_enters_waiting_and_send_enter_continues(self):
        runner = self.make(script(self.PROMPT_SCRIPT))
        await runner.start()
        self.assertFalse(await runner.send_enter())            # 還沒出現提示
        self.assertTrue(await self.wait_for(lambda: runner.waiting_enter))
        self.assertIn((RunState.RUNNING, True), self.states)
        self.assertTrue(await runner.send_enter())
        self.assertFalse(runner.waiting_enter)
        self.assertTrue(await self.wait_for(lambda: "got enter" in self.outputs()))
        self.assertTrue(await self.wait_for(lambda: runner.state == RunState.STOPPED))

    async def test_send_enter_twice_only_works_once(self):
        runner = self.make(script("""
            import sys, time
            print('Press Enter to continue', flush=True)
            sys.stdin.readline()
            time.sleep(30)
        """))
        await runner.start()
        await self.wait_for(lambda: runner.waiting_enter)
        self.assertTrue(await runner.send_enter())
        self.assertFalse(await runner.send_enter())
        await runner.stop()

    async def test_waiting_flag_clears_when_process_ends(self):
        runner = self.make(script("""
            print('Press Enter to continue', flush=True)
        """))
        await runner.start()
        self.assertTrue(await self.wait_for(lambda: runner.state == RunState.STOPPED))
        self.assertFalse(runner.waiting_enter)


class PauseResume(RunnerCase):
    LOOP = """
        import time
        while True:
            time.sleep(0.05)
    """

    async def test_pause_suspends_and_resume_continues(self):
        runner = self.make(script(self.LOOP))
        await runner.start()
        ps = psutil.Process(runner.pid)
        self.assertTrue(runner.pause())
        self.assertEqual(runner.state, RunState.PAUSED)
        self.assertTrue(await self.wait_for(lambda: ps.status() == psutil.STATUS_STOPPED))
        self.assertFalse(runner.pause())                        # 已經暫停
        self.assertTrue(runner.resume())
        self.assertEqual(runner.state, RunState.RUNNING)
        self.assertTrue(await self.wait_for(lambda: ps.status() != psutil.STATUS_STOPPED))
        self.assertFalse(runner.resume())                       # 沒有暫停
        await runner.stop()

    async def test_toggle(self):
        runner = self.make(script(self.LOOP))
        self.assertIsNone(runner.toggle_pause())                # 沒在跑
        await runner.start()
        self.assertTrue(runner.toggle_pause())
        self.assertFalse(runner.toggle_pause())
        await runner.stop()

    async def test_stop_works_while_paused(self):
        runner = self.make(script(self.LOOP))
        await runner.start()
        runner.pause()
        self.assertTrue(await runner.stop())
        self.assertEqual(runner.state, RunState.STOPPED)

    async def test_pause_state_is_cleared_after_restart(self):
        runner = self.make(script(self.LOOP))
        await runner.start()
        runner.pause()
        await runner.restart()
        self.assertEqual(runner.state, RunState.RUNNING)
        await runner.stop()


class ProcessTree(RunnerCase):
    async def test_stop_kills_grandchildren(self):
        runner = self.make(script("""
            import subprocess, sys, time
            child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
            print(child.pid, flush=True)
            time.sleep(60)
        """))
        await runner.start()
        self.assertTrue(await self.wait_for(lambda: bool(self.outputs())))
        grandchild = int(self.outputs()[0])
        self.assertTrue(psutil.pid_exists(grandchild))
        with self.assertNoLogs("asyncio", level="WARNING"):
            await runner.stop()

        def gone():
            if not psutil.pid_exists(grandchild):
                return True
            return psutil.Process(grandchild).status() == psutil.STATUS_ZOMBIE

        self.assertTrue(await self.wait_for(gone, 5.0), "孫行程沒有被結束")

    async def test_kill_now_is_synchronous_and_idempotent(self):
        runner = self.make(script("import time; time.sleep(60)"))
        await runner.start()
        pid = runner.pid
        runner.kill_now()
        runner.kill_now()
        self.assertTrue(await self.wait_for(lambda: runner.state == RunState.STOPPED))
        self.assertFalse(psutil.pid_exists(pid) and
                         psutil.Process(pid).status() != psutil.STATUS_ZOMBIE)


class Sampling(RunnerCase):
    async def test_sample_reports_pid_uptime_and_memory(self):
        runner = self.make(script("import time; time.sleep(30)"))
        self.assertIsNone(runner.sample())
        await runner.start()
        await asyncio.sleep(0.2)
        sample = runner.sample()
        self.assertEqual(sample.pid, runner.pid)
        self.assertGreater(sample.rss, 0)
        self.assertGreaterEqual(sample.uptime, 0.0)
        self.assertGreaterEqual(sample.cpu, 0.0)
        await runner.stop()
        self.assertIsNone(runner.sample())


class Environment(RunnerCase):
    async def test_child_gets_unbuffered_and_utf8_env_and_extra_env(self):
        runner = self.make(script("""
            import os
            for key in ('PYTHONUNBUFFERED', 'PYTHONIOENCODING', 'KC_EXTRA'):
                print(key, os.environ.get(key), flush=True)
        """), env={"KC_EXTRA": "yes"})
        await runner.start()
        self.assertTrue(await self.wait_for(lambda: runner.state == RunState.STOPPED))
        self.assertEqual(self.outputs(), [
            "PYTHONUNBUFFERED 1", "PYTHONIOENCODING utf-8", "KC_EXTRA yes"])

    async def test_cwd_is_applied(self):
        with tempfile.TemporaryDirectory() as d:
            runner = self.make(script("import os; print(os.getcwd())"), cwd=d)
            await runner.start()
            self.assertTrue(await self.wait_for(lambda: runner.state == RunState.STOPPED))
            self.assertEqual(os.path.realpath(self.outputs()[0]), os.path.realpath(d))


if __name__ == "__main__":
    unittest.main()
