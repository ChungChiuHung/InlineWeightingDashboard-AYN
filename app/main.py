import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

# 引入核心模組
from .gateway import RealGateway, SimGateway
from .historian import Historian
from .ws_hub import WsHub
from .write_controller import WriteController

# 載入設定
import yaml
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

# 初始化元件
ws_hub = WsHub()
historian = Historian(config['database']['path'])

# 根據設定決定啟動真實或模擬 Gateway
if config['system'].get('simulation_mode', False):
    gateway = SimGateway(config, historian, ws_hub)
else:
    gateway = RealGateway(config, historian, ws_hub)

write_controller = WriteController(gateway)

# FastAPI 生命週期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時
    historian.init_db()
    asyncio.create_task(gateway.start())
    yield
    # 關閉時
    await gateway.stop()

app = FastAPI(lifespan=lifespan)

# 掛載靜態檔案與樣板
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# --- 頁面路由 (Page Routes) ---

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/ui/categories")
async def categories_page(request: Request):
    return templates.TemplateResponse("categories.html", {"request": request})

@app.get("/ui/history")
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})

# --- API 路由 (Data Routes) ---

@app.get("/api/status")
async def get_system_status():
    """取得當前所有標籤快照"""
    return gateway.get_snapshot()

@app.get("/api/history/stats")
async def get_daily_stats():
    """
    [新增] 取得今日產量統計，供圓餅圖使用
    """
    # 這裡直接呼叫 historian 的方法 (需在 historian.py 實作)
    # 範例回傳:
    return {
        "labels": ["白鯧", "鮭魚", "鮪魚"],
        "data": [120, 45, 80]
    }

@app.post("/api/control/category")
async def set_category(data: dict):
    """設定當前魚種代碼"""
    code = data.get("code")
    success = await write_controller.set_fish_type(code)
    return {"success": success, "code": code}

# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_hub.connect(websocket)
    try:
        while True:
            # 保持連線，也可以處理客戶端傳來的訊息
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_hub.disconnect(websocket)