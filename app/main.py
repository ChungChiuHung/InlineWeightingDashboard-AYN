import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import yaml

# ... (Logging設定) ...
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/app.log')
    ]
)
logger = logging.getLogger(__name__)

from .gateway import RealGateway
from .historian import Historian
from .ws_hub import WsHub
from .write_controller import WriteController

# 載入設定
try:
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise

# 初始化元件
ws_hub = WsHub()
historian = Historian(config['database']['path'])

# 強制使用真實模式 (Real Mode)
logger.info("Starting in REAL mode - connecting to PLC")
gateway = RealGateway(config, historian, ws_hub)
write_controller = WriteController(gateway)

# --- 資料模型定義 ---
class FishTypeItem(BaseModel):
    code: str
    name: str

class RecipeItem(BaseModel):
    fish_code: str
    params: dict 

# --- FastAPI 生命周期 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Initializing database...")
        historian.init_db()
        logger.info("Starting gateway...")
        asyncio.create_task(gateway.start())
        logger.info("Application startup complete")
        yield
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    finally:
        logger.info("Shutting down gateway...")
        await gateway.stop()
        logger.info("Application shutdown complete")

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")
templates.env.globals['v'] = "2.9.0"

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

@app.get("/ui/buckets")
async def buckets_page(request: Request):
    return templates.TemplateResponse("buckets.html", {"request": request})

@app.get("/ui/system")
async def system_page(request: Request):
    return templates.TemplateResponse("system.html", {"request": request})

# --- Data API Routes ---
@app.get("/api/status")
async def get_system_status():
    return gateway.get_snapshot()

@app.get("/status")
async def health_check():
    try:
        if not gateway.running:
            raise HTTPException(status_code=503, detail="Gateway not running")
        
        if hasattr(gateway, 'last_update'):
            time_since_update = time.time() - gateway.last_update
            if time_since_update > 30:
                raise HTTPException(status_code=503, detail="No recent data from PLC")
        
        return {
            "status": "healthy",
            "gateway_running": gateway.running,
            "timestamp": time.time()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="System unhealthy")

@app.get("/api/history/stats")
async def get_daily_stats():
    return historian.get_daily_stats()

@app.get("/api/history")
async def get_history(
    start_time: str = None,
    end_time: str = None,
    fish_code: str = None,
    limit: int = 1000
):
    if limit > 10000:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 10000")
    
    data = historian.get_history_data(
        start_time=start_time,
        end_time=end_time,
        fish_code=fish_code,
        limit=limit
    )
    return data

# --- Fish Type Management ---
@app.get("/api/fish-types")
async def get_fish_types():
    return historian.get_all_fish_types()

@app.post("/api/fish-types")
async def save_fish_type(item: FishTypeItem):
    code = item.code.strip().upper()
    name = item.name.strip()
    
    if not code or len(code) != 4 or not code.isalnum():
        raise HTTPException(status_code=400, detail="Code must be exactly 4 alphanumeric characters")
    if not name or len(name) > 100:
        raise HTTPException(status_code=400, detail="Name must be between 1 and 100 characters")
    
    success = historian.upsert_fish_type(code, name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save to database")
    return {"status": "ok", "code": code, "name": name}

@app.delete("/api/fish-types/{code}")
async def delete_fish_type(code: str):
    if not code or len(code) > 10:
        raise HTTPException(status_code=400, detail="Invalid code")
    
    success = historian.delete_fish_type(code)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete")
    return {"status": "ok", "code": code}

# --- Control APIs (寫入控制) ---

@app.post("/api/control/category")
async def set_category(data: dict):
    code = data.get("code", "").strip().upper()
    if not code or len(code) != 4 or not code.isalnum():
        raise HTTPException(status_code=400, detail="Invalid code format")
    
    success = await write_controller.set_fish_type(code)
    if not success:
        raise HTTPException(status_code=503, detail="Failed to write to PLC (Check connection)")
    return {"success": True, "code": code}

@app.get("/api/recipes/{code}")
async def get_recipe(code: str):
    return historian.get_recipe(code)

@app.post("/api/recipes")
async def save_recipe(item: RecipeItem):
    if not historian.save_recipe(item.fish_code, item.params):
        raise HTTPException(status_code=500, detail="Failed to save recipe")
    return {"status": "ok"}

@app.post("/api/control/write-recipe")
async def write_recipe_plc(item: RecipeItem):
    if not item.params:
        raise HTTPException(status_code=400, detail="No parameters to write")

    success = await write_controller.write_recipe(item.params)
    if not success:
        raise HTTPException(status_code=503, detail="Failed to write recipe to PLC (Partial or Total Failure)")
    return {"success": True}

# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_hub.connect(websocket)
    
    # 建立連線時發送初始快照
    try:
        current_data = gateway.get_snapshot()
        if current_data:
            await websocket.send_json(current_data)
    except Exception as e:
        logger.error(f"Error sending initial snapshot: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_hub.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_hub.disconnect(websocket)