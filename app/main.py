import asyncio
import logging
import os
import time
import random
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import yaml

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/app.log')
    ]
)
logger = logging.getLogger(__name__)

# 引入核心模組
from .gateway import RealGateway, SimGateway
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

# 根據設定決定啟動模擬模式或真實模式
if config['system'].get('simulation_mode', False):
    logger.info("Starting in SIMULATION mode")
    gateway = SimGateway(config, historian, ws_hub)
else:
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

# --- FastAPI 生命周期管理 ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時初始化資料庫
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

# 掛載靜態檔案與樣板
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# 設定全域版本號 (Cache Busting)
templates.env.globals['v'] = "2.4.0"

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
            "simulation_mode": config['system'].get('simulation_mode', False),
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

# --- Fish Type Management APIs ---

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

# --- Control APIs ---

@app.post("/api/control/category")
async def set_category(data: dict):
    code = data.get("code", "").strip().upper()
    if not code or len(code) != 4 or not code.isalnum():
        raise HTTPException(status_code=400, detail="Invalid code format")
    
    success = await write_controller.set_fish_type(code)
    return {"success": success, "code": code}

# --- Recipe Management APIs ---

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
    success = await write_controller.write_recipe(item.params)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to write to PLC")
    return {"success": True}

# --- Debug API (For Chart Testing) ---
@app.post("/api/debug/seed")
async def seed_data():
    """生成隨機歷史資料供測試圖表使用"""
    logger.info("Generating seed data...")
    import sqlite3
    try:
        # 直接使用 historian 的 connection manager
        with historian.get_connection() as conn:
            # 產生過去 24 小時的數據
            base_time = datetime.now()
            records = []
            
            fish_opts = ['F001', 'F002', 'F003', 'F004']
            
            for i in range(100):
                # 隨機時間 (過去 24 小時內)
                delta_min = random.randint(0, 1440)
                ts = (base_time - timedelta(minutes=delta_min)).strftime('%Y-%m-%d %H:%M:%S')
                
                # 隨機魚種
                code = random.choice(fish_opts)
                
                # 隨機重量 (常態分佈模擬)
                # 平均值 500g, 標準差 50g
                weight = round(random.gauss(500, 50), 2)
                if weight < 0: weight = 0
                
                status = 'RUN'
                
                records.append((ts, code, weight, status))
            
            conn.executemany(
                'INSERT INTO history (timestamp, fish_code, weight, status) VALUES (?, ?, ?, ?)',
                records
            )
        return {"status": "ok", "message": "Inserted 100 test records"}
    except Exception as e:
        logger.error(f"Seed failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_hub.connect(websocket)
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