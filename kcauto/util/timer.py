import time

class Timer(object):
    """kcauto timer module.
    """

    alarm_time = 0

    def __init__(self):
        self.alarm_time = 0

    def set(self, seconds):
        self.alarm_time = time.time() + seconds

    def is_time_up(self):
        return time.time() > self.alarm_time


