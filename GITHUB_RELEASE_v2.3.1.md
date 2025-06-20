# OCPP 1.6 Server v2.3.1 - Maintenance Release

**🚀 Production-Ready OCPP 1.6 Central System Server**

## 🌟 What's New in v2.3.1

### 🔧 Bug Fixes & Improvements
- **Fixed UI Rendering Issues**: Resolved minor display problems in charger management dashboard
- **Enhanced WebSocket Stability**: Improved connection handling for long-running sessions
- **Better Error Handling**: More robust processing of malformed OCPP messages
- **Timezone Fixes**: Corrected timezone handling in transaction logs

### ⚡ Performance Enhancements
- **Optimized Database Queries**: Better performance with large datasets
- **Reduced Memory Usage**: More efficient memory management in multi-charger environments
- **Faster API Responses**: Improved response times across all endpoints

### 📚 Documentation & Dependencies
- **Updated Dependencies**: Latest stable versions of all libraries
- **Improved Documentation**: Enhanced accuracy and clarity
- **Better Error Messages**: More helpful configuration validation messages

## 🏢 Enterprise Features (13 Major Features)

All enterprise features from v2.3.0 are included and enhanced:

### 🔄 **Operational Management**
- **Change Availability** - Dynamic connector control
- **Unlock Connector** - Remote unlock capabilities
- **Reserve Now** - Advanced reservation system with conflict resolution

### ⚡ **Smart Charging**
- **Charging Profiles** - Comprehensive profile management (TxDefaultProfile, TxProfile, ChargePointMaxProfile)
- **Get Composite Schedule** - Visual schedule analysis and validation
- **Schedule Conflict Resolution** - Automatic handling of overlapping profiles

### 🔧 **Device Management**
- **Firmware Management** - Complete OTA update system with diagnostics
- **Configuration Management** - Dynamic parameter control
- **Diagnostics & Health Monitoring** - Real-time system status

### 📊 **Monitoring & Analytics**
- **Raw Message Feature** - Protocol-level debugging and analysis
- **Enhanced Logging System** - Comprehensive audit trails with filtering
- **Multi-Select Filtering** - Advanced data analysis capabilities
- **Log Management** - Automated storage and cleanup

### 🎛️ **User Interface**
- **Dynamic UI Configuration** - Customizable interface elements
- **Real-time Updates** - Live data refresh and notifications
- **Multi-charger Dashboard** - Centralized management interface

## 🚀 Quick Start

### Method 1: Direct Download
```bash
# Download the latest release
wget https://github.com/kushagra101010/TestOCPP-Server-16/archive/v2.3.1.zip
unzip v2.3.1.zip
cd TestOCPP-Server-16-2.3.1/
```

### Method 2: Git Clone
```bash
git clone https://github.com/kushagra101010/TestOCPP-Server-16.git
cd TestOCPP-Server-16/
git checkout v2.3.1
```

### Installation & Setup
```bash
# Windows
setup.bat

# Linux/Mac
pip install -r requirements.txt
python start_server.py
```

### Docker Deployment
```bash
docker build -t ocpp-server:v2.3.1 .
docker run -p 8000:8000 -p 9000:9000 ocpp-server:v2.3.1
```

## 📋 What's Included

```
OCPP_1.6_Server_v2.3.1/
├── 📁 backend/              # Core server logic
├── 📁 frontend/             # Web interface
├── 📁 OCPP_1.6_documentation/ # Official OCPP docs
├── 🔧 setup.bat            # Windows setup
├── 🚀 start_server.bat     # Windows startup
├── 📋 requirements.txt     # Python dependencies
├── 🐳 Dockerfile          # Container deployment
└── 📚 Comprehensive docs   # Usage guides
```

## 🛠️ System Requirements

- **Python:** 3.8+ (3.9+ recommended)
- **Memory:** 512MB minimum (1GB recommended)
- **Storage:** 100MB minimum
- **Network:** HTTP/HTTPS + WebSocket support
- **OS:** Windows 10+, Linux, macOS

## 🔧 Configuration

The server includes a comprehensive configuration system:

```ini
[SERVER]
host = 0.0.0.0
port = 8000
debug = false

[FEATURES]
enable_demo_charger = true
enable_api_docs = true
enable_metrics = false

[UI_FEATURES]
show_jio_bp_data_transfer = true
show_msil_data_transfer = false
show_cz_data_transfer = true
```

## 📈 Production Deployment

### High Availability Setup
- **Load Balancing**: Multiple server instances
- **Database**: PostgreSQL for production workloads
- **Monitoring**: Built-in health checks and metrics
- **Security**: HTTPS/WSS encryption support

### Scaling Recommendations
- **Small Deployment**: 1-10 chargers → Single instance
- **Medium Deployment**: 10-100 chargers → 2-3 instances + PostgreSQL
- **Large Deployment**: 100+ chargers → Kubernetes deployment

## 🔒 Security Features

- **Authentication**: Configurable security policies
- **Encryption**: TLS/SSL support for all communications
- **Audit Logging**: Comprehensive activity tracking
- **Input Validation**: Robust message validation

## 📞 Support & Community

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/kushagra101010/TestOCPP-Server-16/issues)
- **Documentation**: Comprehensive guides included
- **Latest Release**: [v2.3.1](https://github.com/kushagra101010/TestOCPP-Server-16/releases/tag/v2.3.1)

## 🗺️ Roadmap

### Upcoming Features
- **Enhanced Metrics Dashboard**: Real-time performance monitoring
- **Multi-language UI Support**: Internationalization
- **Advanced Reporting**: Custom report generation
- **Cloud Templates**: AWS/Azure deployment guides

## 📜 License

MIT License - See [LICENSE.txt](LICENSE.txt) for details.

## 🙏 Acknowledgments

Special thanks to the EV charging community and all contributors who helped make this release possible.

---

**Thank you for using OCPP 1.6 Server v2.3.1!** 🎉

**Download now:** [v2.3.1 Release](https://github.com/kushagra101010/TestOCPP-Server-16/releases/tag/v2.3.1) 