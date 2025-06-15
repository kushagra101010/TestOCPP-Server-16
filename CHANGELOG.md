# Changelog - OCPP 1.6 Server

All notable changes to this OCPP 1.6 Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-06-15

### 🎉 Major Release - OCPP Python Library Upgrade

This is a major release of the **OCPP 1.6 Server** (software version 2.0.0) that upgrades the underlying Python OCPP library to version 2.0.0 and includes significant improvements and bug fixes.

**Important**: This server implements **OCPP 1.6 Protocol** - the version 2.0.0 refers to this server software release, not the OCPP protocol version.

### ✨ Added
- **OCPP Python Library 2.0.0 Support**: Upgraded from ocpp 1.x to ocpp 2.0.0 Python library for better compatibility and features
- **Enhanced Error Handling**: Added comprehensive try-catch blocks for all OCPP handlers
- **Improved Data Type Validation**: Added proper type conversion and validation for all remote commands
- **Better Logging**: Enhanced error logging with stack traces for debugging

### 🔧 Changed
- **Breaking Change**: Updated OCPP handler decorators from `@on(Action.XXX)` to `@on('XXX')` string format
- **Breaking Change**: Updated OCPP call format from `call.XXXPayload()` to `call.XXX()` for ocpp Python library 2.0.0
- **Parameter Order Fix**: Fixed parameter order in remote_start_transaction API call
- **Version Bump**: Updated server software version from v1.1.0 to v2.0.0

### 🐛 Fixed
- **Critical**: Fixed `TypeConstraintViolationError` in RemoteStartTransaction commands
- **Critical**: Fixed `InternalError` responses from OCPP message handlers
- **Critical**: Fixed parameter order mismatch between API and handler functions
- **Package Versions**: Fixed invalid package versions in requirements.txt:
  - `uvicorn==0.32.2` → `uvicorn==0.34.3` (0.32.2 didn't exist)
  - `sqlite3-utils==3.37` → `sqlite-utils==3.38` (wrong package name)
  - `jsonschema==3.2.0` → `jsonschema>=4.0.0,<5.0.0` (compatibility with ocpp Python library 2.0.0)
- **Batch Script**: Fixed Python detection in setup.bat for PowerShell environments
- **Data Types**: Fixed connector_id and transaction_id type conversion (string → integer)

### 🔄 Updated Dependencies
- `ocpp` (Python library): `0.19.0` → `2.0.0` (major upgrade)
- `uvicorn[standard]`: `0.32.2` → `0.34.3`
- `sqlite-utils`: `3.37` → `3.38` (fixed package name from sqlite3-utils)
- `jsonschema`: `3.2.0` → `>=4.0.0,<5.0.0`

### 🧪 Testing
- **Remote Commands**: All remote commands now work correctly with proper data types
- **OCPP Compatibility**: Full compatibility with OCPP 1.6 protocol using ocpp Python library 2.0.0
- **Error Handling**: Comprehensive error handling prevents server crashes

### 📋 Technical Details

#### OCPP Handler Updates
- Removed deprecated `Action` enum imports
- Updated all `@on(Action.XXX)` decorators to `@on('XXX')` string format
- Updated all remote command calls to use new `call.XXX()` format
- Added proper exception handling to all handler methods

#### API Improvements
- Fixed parameter order in `remote_start_transaction()` call
- Added type validation for connector_id and transaction_id
- Improved error responses and logging

#### Setup & Deployment
- Fixed setup.bat Python detection for PowerShell environments
- Updated version numbers across all batch files
- Enhanced installation process with better error handling

### 🚀 Migration Guide

If upgrading from v1.x:

1. **Run Setup**: Execute `cmd /c setup.bat` to reinstall dependencies with new versions
2. **No Code Changes**: All OCPP message handling remains backward compatible
3. **API Compatibility**: All existing API endpoints work the same way
4. **Configuration**: No configuration changes required

### 🔗 Compatibility

- **OCPP Protocol**: Fully compatible with **OCPP 1.6** (this server does NOT support OCPP 2.0.1)
- **Python**: Requires Python 3.8+
- **Operating System**: Windows (batch scripts), Linux/Mac compatible with manual setup
- **Chargers**: Compatible with all OCPP 1.6 compliant charging stations

---

## [1.1.0] - Previous Release

### Features
- Basic OCPP 1.6 server implementation
- Web dashboard for charger management
- Remote start/stop transactions
- Local authorization list management
- Configuration management
- Real-time charger status monitoring

## [1.0.0] - 2024-12-14

### 🎉 Initial Release

#### ✅ Added
- **Core OCPP 1.6 Support**
  - Complete OCPP 1.6J protocol implementation
  - WebSocket communication with chargers
  - Real-time message handling

- **Web Dashboard**
  - Modern responsive web interface
  - Real-time charger monitoring
  - Live message logs viewer
  - Configuration management interface

- **Charger Management**
  - Multi-charger support
  - Remote start/stop transactions
  - Heartbeat monitoring
  - Status notifications
  - Meter values tracking

- **Configuration System**
  - Smart configuration editor
  - Read-only parameter detection
  - Bulk configuration changes
  - Real-time validation

- **Demo Features**
  - Included demo charger simulator
  - Automatic charging session simulation
  - Complete OCPP message examples

- **Distribution Package**
  - One-click setup script
  - Easy-to-use batch files
  - Comprehensive documentation
  - Troubleshooting guides

#### 🔧 Technical Features
- FastAPI-based REST API
- Uvicorn ASGI server
- SQLite database support
- JSON message logging
- CORS support for web access
- Virtual environment isolation

#### 📋 Supported OCPP Messages
- **Core Profile:**
  - Authorize, BootNotification, ChangeAvailability
  - ChangeConfiguration, ClearCache, DataTransfer
  - GetConfiguration, Heartbeat, MeterValues
  - RemoteStartTransaction, RemoteStopTransaction
  - Reset, StartTransaction, StatusNotification
  - StopTransaction, UnlockConnector

- **Firmware Management:**
  - GetDiagnostics, UpdateFirmware

- **Local Auth List Management:**
  - GetLocalListVersion, SendLocalList

- **Remote Trigger:**
  - TriggerMessage

- **Reservation:**
  - CancelReservation, ReserveNow

- **Smart Charging:**
  - ClearChargingProfile, GetCompositeSchedule
  - SetChargingProfile

#### 🛠️ System Requirements
- Windows 10/11
- Python 3.8+
- 2GB RAM minimum
- 500MB storage space
- Network connectivity

---

## Future Releases

### Planned Features
- [ ] Database persistence improvements
- [ ] User authentication system
- [ ] Advanced reporting and analytics
- [ ] Email notifications
- [ ] Mobile app support
- [ ] Cloud deployment options
- [ ] Load balancing for multiple servers
- [ ] Advanced security features

### Known Issues
- None reported in initial release

---

**Note:** This changelog follows [Keep a Changelog](https://keepachangelog.com/) format. 