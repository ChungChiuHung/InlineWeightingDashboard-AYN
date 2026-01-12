import asyncio
import yaml
import sqlite3
import time

from fastapi import FastAPI, WebSocket, HTTPException
from app.gateway import RealGateway, SimGateway
from app.register_cache import RegisterCache
from app.tag_cache import TagCache
from app.parser import parse_tag
from app.ws_hub import WebSocketHub
from app.historian import Historian
from app.encoder import encode_value
from app.write_controller import WriteController
from app.status import GatewayStatus
from app.enum_loader import enum_loader

# NOTE:
# Initialization order matters.
# Order must be:
# 1. load cfg
# 2. create status
# 3. create historian
# 4. create tag_cache
# 5. create gateway
app = FastAPI()

with open("config/config.yaml") as f:
    cfg = yaml.safe_load(f)

status = GatewayStatus()
status.mode = cfg["mode"]

ws_hub = WebSocketHub()

historian = Historian(
    db_path="/opt/plc-system/gateway/data/history.db",
    flush_interval=1.0,
    tag_whitelist=cfg.get("historian", {}).get("tag_whitelist"),
    status=status
)

tag_cache = TagCache(
    hub=ws_hub, 
    historian=historian
)

register_cache = RegisterCache()

write_ctrl = WriteController(cfg["wo"])

# Select gateway
if cfg["mode"] == "simulation":
    gateway = SimGateway()
else:
    gateway = RealGateway(cfg["plc"])

groups = {g["name"]: g for g in cfg["groups"]}
tags = cfg["tags"]

@app.get("/health")
def health():
    return {"status": "ok", "mode": cfg["mode"]}

@app.get("/tags")
def tags_snapshot():
    return tag_cache.snapshot()

async def poll_group(group):
    start = group["start"]
    count = group["count"]
    interval = group["interval_ms"] / 1000

    while True:
        t0 = time.time()
        try:
            regs = await gateway.read_block(start, count)
            register_cache.update_block(group["name"], regs)

            # parse tags belonging to this group
            for tag in tags:
                if tag["group"] != group["name"]:
                    continue

                value = parse_tag(
                    regs,
                    tag["offset"],
                    tag["type"],
                    tag.get("length", 0)
                )
                await tag_cache.update(tag["name"], value)
            
            status.plc_connected = True
            status.mark_poll_ok(group["name"])

        except Exception as e:
            status.plc_connected = False
            status.mark_poll_error(group["name"], e)
            await asyncio.sleep(1)  # wait before retrying
            continue
        
        elapsed = time.time() - t0
        if elapsed > interval:
            print(f"[WARN] polling group {group['name']} took {elapsed:.3f}s, which is longer than the interval {interval:.3f}s")
        await asyncio.sleep(max(0, interval - elapsed))

@app.on_event("startup")
async def startup():
    await gateway.connect()
    for group in groups.values():
        asyncio.create_task(poll_group(group))

@app.websocket("/ws/tags")
async def ws_tags(ws: WebSocket):
    await ws_hub.connect(ws)
    try:
        # 連線後先送一次 snapshot（避免空畫面）
        await ws.send_json({
            "type": "snapshot",
            "data": tag_cache.snapshot()
        })
        while True:
            await ws.receive_text()  # keep alive
    except Exception:
        pass
    finally:
        await ws_hub.disconnect(ws)

@app.get("/history/{tag}")
def query_history(
    tag: str,
    start: int,
    end: int,
    limit: int = 1000
    ):
    conn = sqlite3.connect("/opt/plc-system/gateway/data/history.db")
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ts, avg, min, max, last
        FROM history
        WHERE tag=? AND ts BETWEEN ? AND ?
        ORDER BY ts DESC
        LIMIT ?
        """,
        (tag, start, end, limit)
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "ts": ts,
            "avg": avg,
            "min": mn,
            "max": mx,
            "last": last
        }
        for ts, avg, mn, mx, last in reversed(rows)
    ]

@app.post("/write/{tag}")
async def write_tag(tag: str, payload: dict):
    try:
        value = payload.get("value")
        t = write_ctrl.validate(tag, value)
        regs = encode_value(value, t["type"], t.get("length", 0))
        await gateway.write_holding(address=t["address"], values=regs)
        return {"status": "ok", "tag": tag, "value": value}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
def get_status():
    now = time.time()

    machine_status = tag_cache.data.get("machine_status", 0)
    error_code = tag_cache.data.get("machine_error_code", 0)
    alarm_code = tag_cache.data.get("machine_alarm_code", 0)

    status_text = MACHINE_STATUS_TEXT.get(machine_status, "UNKNOWN")
    status_level = MACHINE_STATUS_LEVEL.get(machine_status, "gray")

    error_text = ERROR_CODE_TEXT.get(error_code, "UNKNOWN_ERROR")
    alarm_text = ALARM_CODE_TEXT.get(alarm_code, "UNKNOWN_ALARM")

    polling = {}
    for g in groups.keys():
        last = status.last_poll_ts.get(g)
        polling[g] = {
            "last_poll_sec_ago": None if last is None else round(now - last, 2),
            "error": status.last_poll_error.get(g)
        }

    healthy = (
        status.plc_connected and
        all(
            p["last_poll_sec_ago"] is not None and p["last_poll_sec_ago"] < 2
            for p in polling.values()
        )
    )

    if not healthy:
        responese.status_code = 503

    return {
        "mode": status.mode,
        "uptime_sec": status.uptime(),

        "machine": {
            "status": machine_status,
            "status_text": status_text,
            "status_level": status_level,
            "error_code": error_code,
            "error_text": error_text,
            "alarm_code": alarm_code,
            "alarm_text": alarm_text,
        },

        "plc_connected": status.plc_connected,
        "healthy": healthy,
    }

@app.get("/enums")
def get_enums():
    return {
        "machine_status": enum_loader.load("machine_status"),
        "machine_error":  enum_loader.load("machine_error"),
        "machine_alarm":  enum_loader.load("machine_alarm"),
    }

@app.post("/enums/reload")
def reload_enums():
    enum_loader._cache.clear()
    return { "status": "reloaded" }


from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

@app.get("/")
def ui_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/ui/buckets")
def ui_buckets(request: Request):
    return templates.TemplateResponse("buckets.html", {"request": request})

@app.get("/ui/categories")
def ui_categories(request: Request):
    return templates.TemplateResponse("categories.html", {"request": request})

@app.get("/ui/history")
def ui_history(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})

@app.get("/ui/system")
def ui_system(request: Request):
    return templates.TemplateResponse("system.html", {"request": request})

@app.get("/api/fish-types")
def list_fish_types():
    conn = sqlite3.connect("data/history.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT code, name_zh FROM fish_type WHERE enabled=1 ORDER BY code"
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {"code": code, "name": name}
        for code, name in rows
    ]
