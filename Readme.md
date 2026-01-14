# PLC Gateway systemd 自動重啟設定說明

本文件說明如何使用 **systemd + HTTP health check**，在 PLC Gateway 回傳 **HTTP 503（不健康）** 時，自動重啟服務。

適用場景：
- Raspberry Pi / Debian / Ubuntu
- FastAPI Gateway
- `/status` endpoint 於異常時回傳 HTTP 503

---

## 架構概念

```

systemd timer (每 10 秒)
↓
health-check service
↓
curl /status
├─ HTTP 200 → 正常
└─ HTTP 503 / timeout → 重啟 plc-gateway

```

---

## 1. PLC Gateway 主服務

### 檔案路徑
```

/etc/systemd/system/plc-gateway.service

````

### 內容

```ini
[Unit]
Description=PLC Gateway
After=network.target

[Service]
User=pi
WorkingDirectory=/opt/plc-system/gateway
ExecStart=/opt/plc-system/gateway/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
````

### 說明

* `Restart=always`：允許外部重啟
* `RestartSec=2`：避免重啟風暴
* `WorkingDirectory`：確保相對路徑（config / DB）正確

---

## 2. Health Check Service（檢查 /status）

### 檔案路徑

```
/etc/systemd/system/plc-gateway-health.service
```

### 內容

```ini
[Unit]
Description=PLC Gateway Health Check
After=plc-gateway.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c '\
  curl -sf http://127.0.0.1:8001/status >/dev/null \
  || systemctl restart plc-gateway.service \
'
```

### 行為說明

* `curl -s -f`

  * HTTP 200 → exit 0（正常）
  * HTTP 503 / timeout → exit 非 0
* 當 curl 失敗時，自動執行：

  ```
  systemctl restart plc-gateway.service
  ```

---

## 3. Health Check Timer（定期執行）

### 檔案路徑

```
/etc/systemd/system/plc-gateway-health.timer
```

### 內容

```ini
[Unit]
Description=PLC Gateway Health Timer

[Timer]
OnBootSec=30s
OnUnitActiveSec=10s
AccuracySec=1s

[Install]
WantedBy=timers.target
```

### 建議設定

* 開機 30 秒後開始檢查
* 每 10 秒檢查一次
* 適合 100 ms polling 系統

---

## 4. 啟用與啟動

```bash
sudo systemctl daemon-reload

sudo systemctl enable plc-gateway
sudo systemctl enable plc-gateway-health.timer

sudo systemctl start plc-gateway
sudo systemctl start plc-gateway-health.timer
```

---

## 5. 驗證方式

### 檢查 Timer 是否啟用

```bash
systemctl list-timers | grep plc-gateway
```

---

### 即時查看 Health Check Log

```bash
journalctl -u plc-gateway-health -f
```

---

### 測試自動重啟（擇一）

#### 方法 A：讓 `/status` 回傳 HTTP 503

（例如 PLC 斷線）

#### 方法 B：手動中止 Gateway

```bash
pkill -f uvicorn
```

### 預期結果

* Health service 偵測失敗
* systemd 自動重啟 `plc-gateway`
* 服務恢復為 `active (running)`

---

## 6. 為什麼使用這種方式

| 項目    | 說明                |
| ----- | ----------------- |
| 不需改程式 | 使用既有 `/status`    |
| 易除錯   | curl + journalctl |
| 現場友善  | systemd 原生        |
| 可擴充   | 未來可接監控            |

---

## 7. 建議事項（實務）

* 檢查頻率不建議 < 5 秒
* `/status` 判斷應嚴格但避免抖動
* 搭配 `RestartSec` 防止重啟風暴

---