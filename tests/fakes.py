"""UI 測試用的假 Runner:介面與 ``tui.runner.Runner`` 相同,但不啟動任何行程。"""
from tui.runner import ProcSample, RunState


class FakeRunner:
    def __init__(self):
        self.on_log = None
        self.on_state = None
        self.calls = []
        self.sample_value = None
        self._state = RunState.STOPPED
        self._waiting = False

    # --- 狀態 ----------------------------------------------------------- #
    @property
    def state(self):
        return self._state

    @property
    def waiting_enter(self):
        return self._waiting and self._state is not RunState.STOPPED

    def _set(self, state, waiting=False):
        self._state = state
        self._waiting = waiting
        if self.on_state:
            self.on_state(state, self.waiting_enter)

    # --- 與 Runner 相同的操作 -------------------------------------------- #
    async def start(self):
        self.calls.append("start")
        if self._state is not RunState.STOPPED:
            return False
        self._set(RunState.RUNNING)
        return True

    async def stop(self):
        if self._state is RunState.STOPPED:
            return False
        self.calls.append("stop")
        self._set(RunState.STOPPED)
        return True

    async def restart(self):
        self.calls.append("restart")
        self._set(RunState.RUNNING)
        return True

    def pause(self):
        if self._state is not RunState.RUNNING:
            return False
        self.calls.append("pause")
        self._set(RunState.PAUSED, self._waiting)
        return True

    def resume(self):
        if self._state is not RunState.PAUSED:
            return False
        self.calls.append("resume")
        self._set(RunState.RUNNING, self._waiting)
        return True

    def toggle_pause(self):
        if self._state is RunState.STOPPED:
            return None
        if self._state is RunState.PAUSED:
            self.resume()
        else:
            self.pause()
        return self._state is RunState.PAUSED

    async def send_enter(self):
        if not self.waiting_enter:
            return False
        self.calls.append("send_enter")
        self._set(self._state, False)
        return True

    def sample(self):
        return self.sample_value

    def kill_now(self):
        self.calls.append("kill_now")

    # --- 測試輔助 -------------------------------------------------------- #
    def emit(self, kind, text):
        self.on_log(kind, text)

    def set_waiting(self, flag):
        self._set(self._state, flag)

    @staticmethod
    def make_sample(**kw):
        values = dict(pid=1234, uptime=192.0, cpu=12.0, rss=180 * 1024 ** 2)
        values.update(kw)
        return ProcSample(**values)
