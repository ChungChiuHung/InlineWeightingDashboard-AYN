# Quick Start Guide

## Prerequisites

- Python 3.12 or higher
- Mitsubishi FX5U PLC with Modbus TCP enabled (for production mode)
- Raspberry Pi or Linux server (recommended for production)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ChungChiuHung/InlineWeightingDashboard-AYN.git
cd InlineWeightingDashboard-AYN
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Application

Edit `config/config.yaml`:

```yaml
system:
  name: "PLC Gateway"
  version: "2.1.0"
  # Set to true for testing without PLC
  simulation_mode: true

plc:
  host: "192.168.1.5"  # Change to your PLC IP
  port: 502
  poll_interval: 0.1
  
  registers:
    read_start: 40131
    read_count: 10
    
    map:
      fish_code: 40131
      weight: 40133
      status: 40135

database:
  path: "data/history.db"

logging:
  level: "INFO"
```

## Running the Application

### Development Mode (with auto-reload)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## Accessing the Dashboard

1. **Web Dashboard**: http://localhost:8001
2. **Categories Management**: http://localhost:8001/ui/categories
3. **History View**: http://localhost:8001/ui/history
4. **API Documentation**: http://localhost:8001/docs (auto-generated)
5. **Health Check**: http://localhost:8001/status

## Testing the APIs

### Get Current Status
```bash
curl http://localhost:8001/api/status
```

### Get Fish Types
```bash
curl http://localhost:8001/api/fish-types
```

### Add/Update Fish Type
```bash
curl -X POST http://localhost:8001/api/fish-types \
  -H "Content-Type: application/json" \
  -d '{"code": "F005", "name": "鱈魚 (Cod)"}'
```

### Delete Fish Type
```bash
curl -X DELETE http://localhost:8001/api/fish-types/F005
```

### Get Historical Data
```bash
curl "http://localhost:8001/api/history?limit=100"
```

### Check Health
```bash
curl http://localhost:8001/status
```

## Simulation Mode

For testing without a physical PLC:

1. Set `simulation_mode: true` in `config/config.yaml`
2. The system will generate random data:
   - Status: RUN, IDLE, or ALARM
   - Weight: 0-3 kg
   - Fish codes: F001, F002, F003

## Production Deployment

### Using systemd (Recommended)

1. Create service file `/etc/systemd/system/plc-gateway.service`:

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
```

2. Create health check service `/etc/systemd/system/plc-gateway-health.service`:

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

3. Create health check timer `/etc/systemd/system/plc-gateway-health.timer`:

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

4. Enable and start services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable plc-gateway
sudo systemctl enable plc-gateway-health.timer
sudo systemctl start plc-gateway
sudo systemctl start plc-gateway-health.timer
```

5. Check status:

```bash
sudo systemctl status plc-gateway
sudo journalctl -u plc-gateway -f
```

## Troubleshooting

### Application won't start

Check logs:
```bash
cat logs/app.log
```

### Cannot connect to PLC

1. Verify PLC IP address in `config/config.yaml`
2. Check network connectivity: `ping <PLC_IP>`
3. Verify Modbus TCP is enabled on PLC
4. Check firewall settings

### Database errors

1. Ensure `data/` directory exists
2. Check file permissions
3. Remove corrupted database: `rm data/history.db` (will be recreated)

### WebSocket not connecting

1. Check browser console for errors
2. Verify server is running: `curl http://localhost:8001/status`
3. Check firewall/proxy settings

## Logs

- Application logs: `logs/app.log`
- systemd logs: `journalctl -u plc-gateway`
- Real-time logs: `tail -f logs/app.log`

## Default Fish Types

The system comes pre-seeded with:
- F001: 白鯧 (White Pomfret)
- F002: 鮭魚 (Salmon)
- F003: 鮪魚 (Tuna)
- F004: 吳郭魚 (Tilapia)

You can add/modify these through the Categories page.

## Support

For issues or questions:
1. Check `OPTIMIZATION_SUMMARY.md` for detailed documentation
2. Check `DEV_COMMANDS.md` for development commands
3. Review logs in `logs/app.log`
4. Create an issue on GitHub

## Next Steps

1. **Configure your PLC**: Set `simulation_mode: false` and update PLC IP
2. **Customize fish types**: Add your product codes in Categories page
3. **Set up systemd**: Enable automatic start and health monitoring
4. **Configure backups**: Set up database backup schedule
5. **Monitor logs**: Set up log rotation and monitoring

---
**Version**: 2.1.0 (Optimized)  
**Last Updated**: 2026-01-12
