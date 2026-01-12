---

# PLC Gateway & WebUI System

**FX5U Modbus TCP → Raspberry Pi → Web Dashboard**

---

## 1. 專案目的（Purpose）

本系統用於：

* 從 **三菱 FX5U PLC（Modbus TCP）** 讀取機台與生產資料
* 將資料即時顯示於 **Web Dashboard（手機 / 平板 / PC 皆可）**
* 支援：

  * 即時監控（WebSocket）
  * 歷史資料記錄（SQLite）
  * PLC 寫入控制（設定值 / 代號）
* 解決 PLC **無法儲存中文** 的限制（以代號 + DB 對照）

---

## 2. 系統架構（Architecture）

```
┌────────────┐
│  FX5U PLC  │
│            │
│ Modbus TCP │
│ (40001~)   │
└─────▲──────┘
      │
      │ Modbus TCP
      │
┌─────┴─────────────────────────┐
│ Raspberry Pi (Debian Linux)    │
│                                 │
│  FastAPI Gateway                │
│  ├─ RealGateway / SimGateway    │
│  ├─ Polling (100ms)             │
│  ├─ Parser / TagCache           │
│  ├─ Historian (SQLite)          │
│  ├─ Write Controller            │
│  └─ WebSocket Hub               │
│                                 │
│  WebUI (Jinja2 + JS)            │
│  ├─ Dashboard                   │
│  ├─ Categories (魚種設定)       │
│  └─ Status / History            │
└──────────▲─────────────────────┘
           │
           │ HTTP / WebSocket
           │
      ┌────┴────┐
      │ Browser │
      │ Phone   │
      │ Tablet  │
      └─────────┘
```

---

## 3. 技術選型（Tech Stack）

### 系統 / 環境

* OS：Debian Linux (aarch64)
* Python：3.13.x
* 硬體：Raspberry Pi 4B

### 後端

* FastAPI
* Uvicorn
* pymodbus (Async)
* SQLite3
* Jinja2

### 前端

* HTML (Jinja2 Templates)
* CSS（自製，Mobile-first）
* JavaScript（原生 ES Module）
* WebSocket（即時更新）

---

## 4. 專案目錄結構

```
/opt/plc-system/gateway/
├── app/
│   ├── main.py
│   ├── gateway.py
│   ├── historian.py
│   ├── tag_cache.py
│   ├── write_controller.py
│   └── ...
├── config/
│   ├── config.yaml
│   └── enums/
├── data/
│   └── history.db
├── web/
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── categories.html
│   └── static/
│       ├── css/app.css
│       └── js/
│           ├── api.js
│           ├── dashboard.js
│           └── categories.js
├── venv/
├── requirements.txt
└── README.md
```

---

## 5. PLC 設計原則（重要）

### 5.1 PLC 不存中文

* PLC **只存代號（ASCII）**
* 例如：`F001`
* 中文名稱只存在 DB / WebUI

### 5.2 魚種代號（範例）

| PLC 位址      | 說明      | 型態                     |
| ----------- | ------- | ---------------------- |
| 40131~40132 | 分類種類A編號 | String (4 bytes ASCII) |

範例：

```
F001
F002
```

---

## 6. DB 設計（SQLite）

### 6.1 魚種對照表

```sql
CREATE TABLE fish_type (
    code TEXT PRIMARY KEY,
    name_zh TEXT NOT NULL,
    name_en TEXT,
    enabled INTEGER DEFAULT 1
);
```

### 6.2 歷史資料

* Historian 只記錄「代號」
* 查詢時 join 中文名稱

---

## 7. WebUI 頁面說明

### 7.1 Dashboard (`/`)

* 即時顯示：

  * 機台狀態（RUN / IDLE / ALARM）
  * 即時重量
  * 魚種代號（轉中文顯示）
* WebSocket 即時更新

### 7.2 魚種設定 (`/ui/categories`)

* 下拉選單顯示中文
* 實際寫入 PLC 為代號（如 `F001`）

---

## 8. 常用開發指令（摘要）

### 進入環境

```bash
cd /opt/plc-system/gateway
source venv/bin/activate
```

### 啟動（開發）

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### systemd

```bash
sudo systemctl restart plc-gateway
journalctl -u plc-gateway -f
```

---

## 9. Simulation 模式

* 無 PLC 時可使用 `SimGateway`
* 功能：

  * 模擬魚進料
  * 模擬重量（≤ 2kg）
  * 模擬 RUN / IDLE / ALARM
* 用於：

  * WebUI 開發
  * Demo
  * 教育訓練

---

## 10. 系統設計原則（總結）

* **PLC = 資料來源，不是語意層**
* **DB = 語意與對照**
* **WebUI = 顯示與操作**
* 所有設計可：

  * 擴充
  * 交付
  * 長期維護

---

## 11. 後續可擴充項目

* OEE 圖表
* ALARM 歷史 / 確認流程
* 多機台支援
* 使用者權限
* 匯出 CSV / Excel

---

### 文件狀態

* 類型：**可交付技術文件**
* 適用對象：

  * 工程師
  * 系統整合商
  * 客戶 IT / 自動化部門

---
