import time

class GatewayStatus:
    def __init__(self):
        self.mode = None
        self.plc_connected = False
        self.last_poll_ts = {}
        self.last_poll_error = {}
        self.last_flush_ts = None
        self.start_ts = time.time()

    def mark_poll_ok(self, group):
        self.last_poll_ts[group] = time.time()
        self.last_poll_error.pop(group, None)

    def mark_poll_error(self, group, err):
        self.last_poll_error[group] = str(err)

    def mark_flush(self):
        self.last_flush_ts = time.time()

    def uptime(self):
        return int(time.time() - self.start_ts)
