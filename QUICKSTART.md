Quick Start GuidePrerequisitesPython 3.12 or higherMitsubishi FX5U PLC with Modbus TCP enabledRaspberry Pi or Linux server (recommended for production)Installation1. Clone the Repositorygit clone [https://github.com/ChungChiuHung/InlineWeightingDashboard-AYN.git](https://github.com/ChungChiuHung/InlineWeightingDashboard-AYN.git)
cd InlineWeightingDashboard-AYN
2. Create Virtual Environmentpython3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
3. Install Dependenciespip install -r requirements.txt
4. Configure the ApplicationEdit config/config.yaml:system:
  name: "PLC Gateway"
  version: "2.5.0"

plc:
  host: "192.168.1.5"  # Change to your PLC IP
  port: 502
  poll_interval: 0.1
  
  registers:
    read_start: 40001
    read_count: 132
    
    map:
      weight_now: 40001
      # ... (see config.yaml for full map)
      fish_code: 40131

database:
  path: "data/history.db"

logging:
  level: "INFO"
Running the ApplicationDevelopment Mode (with auto-reload)uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
Production Modeuvicorn app.main:app --host 0.0.0.0 --port 8001
Accessing the DashboardWeb Dashboard: http://localhost:8001Categories Management: http://localhost:8001/ui/categoriesHistory View: http://localhost:8001/ui/historyAPI Documentation: http://localhost:8001/docs (auto-generated)Health Check: http://localhost:8001/statusTesting the APIsGet Current Statuscurl http://localhost:8001/api/status
Get Fish Typescurl http://localhost:8001/api/fish-types
Add/Update Fish Typecurl -X POST http://localhost:8001/api/fish-types \
  -H "Content-Type: application/json" \
  -d '{"code": "F005", "name": "鱈魚 (Cod)"}'
Delete Fish Typecurl -X DELETE http://localhost:8001/api/fish-types/F005
Get Historical Datacurl "http://localhost:8001/api/history?limit=100"
Check Healthcurl http://localhost:8001/status
Production DeploymentUsing systemd (Recommended)Create service file /etc/systemd/system/plc-gateway.service:[Unit]
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
Create health check service /etc/systemd/system/plc-gateway-health.service:[Unit]
Description=PLC Gateway Health Check
After=plc-gateway.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c '\
  curl -sf [http://127.0.0.1:8001/status](http://127.0.0.1:8001/status) >/dev/null \
  || systemctl restart plc-gateway.service \
'
Create health check timer /etc/systemd/system/plc-gateway-health.timer:[Unit]
Description=PLC Gateway Health Timer

[Timer]
OnBootSec=30s
OnUnitActiveSec=10s
AccuracySec=1s

[Install]
WantedBy=timers.target
Enable and start services:sudo systemctl daemon-reload
sudo systemctl enable plc-gateway
sudo systemctl enable plc-gateway-health.timer
sudo systemctl start plc-gateway
sudo systemctl start plc-gateway-health.timer
Check status:sudo systemctl status plc-gateway
sudo journalctl -u plc-gateway -f
TroubleshootingApplication won't startCheck logs:cat logs/app.log
Cannot connect to PLCVerify PLC IP address in config/config.yamlCheck network connectivity: ping <PLC_IP>Verify Modbus TCP is enabled on PLCCheck firewall settingsDatabase errorsEnsure data/ directory existsCheck file permissionsRemove corrupted database: rm data/history.db (will be recreated)WebSocket not connectingCheck browser console for errorsVerify server is running: curl http://localhost:8001/statusCheck firewall/proxy settingsSupportFor issues or questions:Review logs in logs/app.logCreate an issue on GitHubVersion: 2.5.0 (Production)Last Updated: 2026-01-13