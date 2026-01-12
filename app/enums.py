from enum import IntEnum

class MachineStatus(IntEnum):
    UNKNOWN = 0
    RUN = 1
    IDLE = 2
    ALARM = 3
    STOP = 4

# fallback（僅在 JSON 失效時用）
DEFAULT_MACHINE_STATUS = {
    0: {"code": "UNKNOWN", "text": "Unknown", "level": "gray"},
    1: {"code": "RUN",     "text": "Running", "level": "green"},
    2: {"code": "IDLE",    "text": "Idle",    "level": "yellow"},
    3: {"code": "ALARM",   "text": "Alarm",   "level": "red"},
    4: {"code": "STOP",    "text": "Stopped", "level": "gray"},
}
