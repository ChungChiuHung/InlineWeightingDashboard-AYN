import asyncio
import logging
import os
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

if config['system'].get('simulation_mode', False):
    logger.info("Starting in SIMULATION mode")
    gateway = SimGateway(config, historian, ws_hub)
else:
    logger.info("Starting in REAL mode - connecting to PLC")
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
    """Get current system data snapshot"""
    return gateway.get_snapshot()

@app.get("/status")
async def health_check():
    """Health check endpoint for systemd monitoring"""
    try:
        # Check if gateway is running
        if not gateway.running:
            raise HTTPException(status_code=503, detail="Gateway not running")
        
        # Check if we have recent data (updated in last 30 seconds)
        import time
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
        logging.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="System unhealthy")

@app.get("/api/history/stats")
async def get_daily_stats():
    """Get daily production statistics"""
    return historian.get_daily_stats()

@app.get("/api/history")
async def get_history(
    start_time: str = None,
    end_time: str = None,
    fish_code: str = None,
    limit: int = 1000
):
    """Get historical data with optional filters"""
    if limit > 10000:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 10000")
    
    data = historian.get_history_data(
        start_time=start_time,
        end_time=end_time,
        fish_code=fish_code,
        limit=limit
    )
    return data

# [關鍵] 魚種管理 API (CRUD)
# 前端 categories.js 會呼叫這些接口

@app.get("/api/fish-types")
async def get_fish_types():
    """取得所有魚種列表"""
    return historian.get_all_fish_types()

@app.post("/api/fish-types")
async def save_fish_type(item: FishTypeItem):
    """新增或更新魚種 with validation"""
    # Input validation
    code = item.code.strip().upper()
    name = item.name.strip()
    
    # Validate code format: must be exactly 4 alphanumeric characters
    if not code or len(code) != 4 or not code.isalnum():
        raise HTTPException(status_code=400, detail="Code must be exactly 4 alphanumeric characters")
    
    # Validate name
    if not name or len(name) > 100:
        raise HTTPException(status_code=400, detail="Name must be between 1 and 100 characters")
    
    # 呼叫 historian 儲存
    success = historian.upsert_fish_type(code, name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save to database")
    return {"status": "ok", "code": code, "name": name}

@app.delete("/api/fish-types/{code}")
async def delete_fish_type(code: str):
    """刪除魚種 with validation"""
    # Validate code
    if not code or len(code) > 10:  # Reasonable limit
        raise HTTPException(status_code=400, detail="Invalid code")
    
    success = historian.delete_fish_type(code)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete")
    return {"status": "ok", "code": code}

# 控制指令 API (寫入 PLC)
@app.post("/api/control/category")
async def set_category(data: dict):
    """Set fish type category on PLC with validation"""
    code = data.get("code", "").strip().upper()
    
    # Validate code
    if not code or len(code) != 4 or not code.isalnum():
        raise HTTPException(status_code=400, detail="Invalid code format")
    
    success = await write_controller.set_fish_type(code)
    return {"success": success, "code": code}

# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data updates"""
    await ws_hub.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            # Echo back for connection keep-alive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_hub.disconnect(websocket)
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_hub.disconnect(websocket)