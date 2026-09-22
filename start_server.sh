#!/bin/bash

# 設定專案路徑
PROJECT_DIR="/home/jhs/projects/InlineWeightingDashboard-AYN"

echo "=========================================="
echo "啟動 PLC Gateway 系統"
echo "=========================================="

# 1. 切換到專案目錄
if [ -d "$PROJECT_DIR" ]; then
    cd "$PROJECT_DIR" || exit 1
    echo "[OK] 已進入專案目錄: $PROJECT_DIR"
else
    echo "[錯誤] 找不到專案目錄: $PROJECT_DIR"
    echo "請確認您是否已經將專案 Clone 下來。"
    exit 1
fi

# 2. 檢查並建立虛擬環境 (venv)
if [ ! -d "venv" ]; then
    echo "[INFO] 找不到 venv，正在建立虛擬環境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[錯誤] 建立虛擬環境失敗。"
        exit 1
    fi
    echo "[OK] 虛擬環境建立完成。"
else
    echo "[OK] 虛擬環境 (venv) 已存在。"
fi

# 3. 啟動虛擬環境並安裝依賴
echo "[INFO] 正在啟用虛擬環境並安裝 requirements.txt..."
source venv/bin/activate
pip install -r requirements.txt

# 4. 啟動伺服器
echo "=========================================="
echo "[INFO] 準備啟動 Uvicorn 伺服器..."
echo "伺服器預計運行於: http://0.0.0.0:8001"
echo "=========================================="

# 依照 systemd 設定檔的參數啟動伺服器
uvicorn app.main:app --host 0.0.0.0 --port 8001
