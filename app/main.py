import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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

if config['system'].get('simulation_mode', False):
    gateway = SimGateway(config, historian, ws_hub)
else:
    gateway = RealGateway(config, historian, ws_hub)

write_controller = WriteController(gateway)

# [關鍵] 定義資料模型 (用於驗證前端傳來的 JSON)
# 如果缺少這段，API 會報錯 422 或 500
class FishTypeItem(BaseModel):
    code: str
    name: str

# FastAPI 生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時初始化資料庫 (建立資料表)
    historian.init_db()
    asyncio.create_task(gateway.start())
    yield
    await gateway.stop()

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# --- Page Routes ---
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/ui/categories")
async def categories_page(request: Request):
    return templates.TemplateResponse("categories.html", {"request": request})

@app.get("/ui/history")
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})

# --- Data API Routes ---

@app.get("/api/status")
async def get_system_status():
    return gateway.get_snapshot()

@app.get("/api/history/stats")
async def get_daily_stats():
    return historian.get_daily_stats()

# [關鍵] 魚種管理 API (CRUD)
# 前端 categories.js 會呼叫這些接口

@app.get("/api/fish-types")
async def get_fish_types():
    """取得所有魚種列表"""
    return historian.get_all_fish_types()

@app.post("/api/fish-types")
async def save_fish_type(item: FishTypeItem):
    """新增或更新魚種"""
    # 簡單驗證：代碼長度 (對應 PLC ASCII 長度限制)
    if len(item.code) > 4:
         raise HTTPException(status_code=400, detail="Code length must be <= 4 characters")
    
    # 呼叫 historian 儲存
    success = historian.upsert_fish_type(item.code, item.name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save to database")
    return {"status": "ok"}

@app.delete("/api/fish-types/{code}")
async def delete_fish_type(code: str):
    """刪除魚種"""
    success = historian.delete_fish_type(code)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete")
    return {"status": "ok"}

# 控制指令 API (寫入 PLC)
@app.post("/api/control/category")
async def set_category(data: dict):
    code = data.get("code")
    success = await write_controller.set_fish_type(code)
    return {"success": success, "code": code}

# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_hub.disconnect(websocket)