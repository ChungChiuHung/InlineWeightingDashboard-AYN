import logging
import asyncio
from typing import List
from fastapi import WebSocket

logger = logging.getLogger("ws_hub")

class WsHub:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """接受並儲存新的 WebSocket 連線"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """移除斷開的連線"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """
        將 JSON 訊息推播給所有已連線的客戶端
        包含自動清除失效連線的機制
        """
        if not self.active_connections:
            return
        
        # 遍歷副本以避免在迭代時修改列表
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending to client (removing): {e}")
                self.disconnect(connection)