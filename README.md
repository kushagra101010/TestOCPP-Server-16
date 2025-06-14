# OCPP Server v1.6 - Central Management System

Professional OCPP 1.6 Central Management System (CMS) for EV charging stations with web-based dashboard and real-time monitoring.

![OCPP Server](https://img.shields.io/badge/OCPP-1.6-blue) ![Python](https://img.shields.io/badge/Python-3.8+-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## 🚀 Quick Start

### Prerequisites
- **Windows 10/11** (Linux/Mac versions available on request)
- **Python 3.8+** - Download from [python.org](https://python.org)
- **Internet connection** (for initial setup only)

### Installation (3 Simple Steps)

1. **Extract** the OCPP Server files to a folder
2. **Double-click** `setup.bat` - This will install everything automatically
3. **Double-click** `start_server.bat` - This will start the server

That's it! The server will be running at `http://localhost:8000`

## 🎯 Features

### ✅ Core OCPP 1.6 Features
- **Real-time charger monitoring** - Live status updates
- **Remote start/stop transactions** - Control charging sessions
- **Configuration management** - Modify charger settings remotely
- **Hard & Soft Reset** - Remote charger restart capabilities
- **Heartbeat monitoring** - Track charger connectivity
- **Status notifications** - Real-time charger state changes
- **Meter values** - Energy consumption tracking

### ✅ Web Dashboard
- **Modern responsive UI** - Works on desktop and mobile
- **Smart logs viewer** - Real-time monitoring with intelligent clearing
- **Charger management** - Add, remove, and configure chargers
- **Reset controls** - Hard and soft reset buttons with confirmations
- **Transaction history** - Track all charging sessions
- **Configuration editor** - Smart readonly/editable parameter detection

### ✅ Advanced Features
- **Multi-charger support** - Connect unlimited chargers
- **WebSocket communication** - Real-time bidirectional messaging
- **JSON message logging** - Complete OCPP message history
- **Demo charger included** - Test without real hardware
- **Network discovery** - Automatic IP detection

## 🌐 Connecting Chargers

### For Real Chargers
Configure your OCPP 1.6 compatible chargers with:

```
WebSocket URL: ws://YOUR_COMPUTER_IP:8000/ws/CHARGER_ID
```

**Example:**
- Server IP: `192.168.1.100`
- Charger ID: `STATION_001`
- WebSocket URL: `ws://192.168.1.100:8000/ws/STATION_001`

### For Testing (Demo Charger)
1. Start the server: `start_server.bat`
2. In a new window, run: `demo_charger.bat`
3. Watch the demo charger connect and simulate charging sessions

## 📋 Usage Guide

### Starting the Server
```batch
# First time setup
setup.bat

# Start server
start_server.bat
```

### Accessing the Dashboard
Open your web browser and go to:
- **Local access:** `http://localhost:8000`
- **Network access:** `http://YOUR_IP:8000`

### Managing Chargers
1. **View connected chargers** - See all active connections
2. **Send commands** - Start/stop transactions, get configuration, reset chargers
3. **Monitor logs** - Real-time OCPP message viewer with smart clearing
4. **Configure settings** - Modify charger parameters
5. **Reset operations** - Perform hard or soft resets remotely

### Configuration Management
1. Click **"Get Configuration"** to retrieve all settings
2. Click **"Change Configuration"** to modify parameters
3. **Read-only parameters** are clearly marked and disabled
4. **Editable parameters** can be modified and applied

### Reset Operations
The server supports both types of OCPP 1.6 reset operations:

#### 🔴 Hard Reset
- **Purpose:** Complete system restart (hardware + software)
- **Effect:** Charger performs full reboot/power cycle
- **Use case:** Resolve hardware issues, apply firmware updates
- **Transaction handling:** Active sessions are stopped with "PowerLoss" reason

#### 🟠 Soft Reset
- **Purpose:** Software restart only (no power cycle)
- **Effect:** Charger restarts application software
- **Use case:** Apply configuration changes, resolve software issues
- **Transaction handling:** Active sessions are stopped with "SoftReset" reason

**How to use:**
1. Select a connected charger
2. Click **"Hard Reset"** or **"Soft Reset"** button
3. Confirm the action in the dialog
4. Monitor logs for reset confirmation and reconnection

**Note:** Both reset types will automatically stop any active charging transactions before performing the reset.

## 🔧 File Structure

```
OCPP_Server_v1.6/
├── setup.bat              # One-time installation script
├── start_server.bat        # Start the OCPP server
├── demo_charger.bat        # Run demo charger for testing
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── backend/               # Server code
│   ├── main.py           # Main server application
│   ├── api_routes.py     # REST API endpoints
│   └── ocpp_handler.py   # OCPP protocol handler
├── frontend/              # Web interface
│   ├── templates/        # HTML templates
│   └── static/          # CSS, JavaScript, images
└── demo_charger.py       # Demo charger simulator
```

## 🛠️ Troubleshooting

### Common Issues

**❌ "Python is not installed"**
- Download Python from [python.org](https://python.org)
- Make sure to check "Add Python to PATH" during installation

**❌ "Virtual environment not found"**
- Run `setup.bat` first to install dependencies

**❌ "Charger not connecting"**
- Check the WebSocket URL format: `ws://IP:8000/ws/CHARGER_ID`
- Ensure both server and charger are on the same network
- Verify firewall settings allow port 8000

**❌ "Web dashboard not loading"**
- Make sure the server is running (`start_server.bat`)
- Try `http://localhost:8000` instead of the IP address
- Check if another application is using port 8000

### Getting Help
1. Check the console output for error messages
2. Verify all files are extracted properly
3. Ensure Python 3.8+ is installed correctly

## 📊 System Requirements

### Minimum Requirements
- **OS:** Windows 10/11
- **RAM:** 2GB available
- **Storage:** 500MB free space
- **Network:** WiFi or Ethernet connection

### Recommended Requirements
- **OS:** Windows 11
- **RAM:** 4GB available
- **Storage:** 1GB free space
- **Network:** Gigabit Ethernet for multiple chargers

## 🔒 Security Notes

- This version is designed for **local network use**
- For internet deployment, additional security measures are recommended
- Default configuration allows all origins (suitable for development/testing)
- Change default settings for production environments

## 📞 Support & Contact

For technical support, feature requests, or bug reports:
- **Email:** [Your Email]
- **Documentation:** Included in this package
- **Updates:** Check for newer versions periodically

## 📄 License

This software is provided under the MIT License. See LICENSE file for details.

---

**© 2024 OCPP Server v1.6 - Professional EV Charging Management System** 