# Changelog - OCPP 1.6 Server

All notable changes to this OCPP 1.6 Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2025-01-16

### 🎨 UI/UX Improvements - Enhanced Charger Management

This is a minor release that introduces significant UI improvements for better charger management and enhanced multi-charger testing capabilities.

### ✨ Added
- **Vertical Scrolling**: Fixed-height charger list that displays 5 chargers at a time with smooth scrolling
- **Enhanced Visual Design**: Improved spacing, padding, and visual hierarchy for charger status items
- **Professional Styling**: Better borders, badges, and typography for a more polished interface
- **Scalable Interface**: UI now gracefully handles large numbers of connected chargers (tested with 20+)

### 🔧 Enhanced
- **Multi-Charger Testing**: Updated `test_multiple_chargers.py` to support 20 concurrent chargers instead of 5
- **OCPP-Compliant Heartbeats**: Heartbeat intervals now properly follow server response from BootNotification
- **Continuous Operation**: Test chargers now run indefinitely with proper heartbeat cycles
- **Server-Controlled Timing**: Heartbeat intervals dynamically set by server response instead of hardcoded 10 seconds

### 🎯 Technical Improvements
- **UI Container**: Added `max-height: 400px` to charger list for exactly 5 visible chargers
- **CSS Enhancements**: Improved padding (`12px 16px`), margins, and border radius (`8px`) for list items
- **Badge Styling**: Consistent badge sizing (`min-width: 90px`) and better visual presentation
- **Heartbeat Logic**: Enhanced heartbeat interval extraction from BootNotification response with 300s default

### 🧪 Testing
- **Multi-Charger Scale**: Tested with 20 concurrent charger connections
- **UI Responsiveness**: Verified proper scrolling and display with large charger lists
- **OCPP Compliance**: Confirmed heartbeat behavior follows OCPP 1.6 specification
- **Continuous Operation**: Validated persistent WebSocket connections without timeouts

### 📋 Impact
- **Better Scalability**: UI can now handle large numbers of charging stations efficiently
- **Improved UX**: Professional appearance with better information hierarchy
- **Enhanced Testing**: Better tools for testing multi-charger deployment scenarios
- **OCPP Compliance**: More accurate implementation of heartbeat interval management

---

## [2.1.1] - 2025-01-15

### 🔧 Bug Fixes - Status Display Accuracy

This is a patch release that fixes critical status display issues where charger status was not properly following OCPP StatusNotification messages.

### 🐛 Fixed
- **Status Display Logic**: Fixed charger status display to properly follow StatusNotification messages instead of showing default "Available"
- **Real-time Status Updates**: Charger status now accurately reflects OCPP StatusNotification states (Available, Preparing, Charging, SuspendedEV, etc.)
- **Connection vs Status Logic**: Improved status logic to show "Disconnected" only when WebSocket connection is lost, not as default status
- **Frontend Display Bug**: Fixed UI JavaScript to correctly display actual charger status from API instead of ignoring it

### 🔄 Technical Changes
- **Backend**: Removed conflicting status updates from connection/disconnection events
- **ChargerStore**: Modified `add_charger()` method to preserve existing StatusNotification status
- **API Routes**: Enhanced status logic for proper WebSocket connectivity handling  
- **Frontend**: Updated JavaScript to use main `charger.status` field instead of `connector_status`

### 🧪 Testing
- **Status Accuracy**: Verified charger status correctly shows "Preparing" when in preparing state
- **Connection Handling**: Confirmed "Disconnected" only shows when WebSocket is actually lost
- **UI Consistency**: Tested frontend displays match backend API responses
- **Real-time Updates**: Verified status changes immediately reflect in UI

### 📋 Impact
- **User Experience**: Users now see accurate real-time charger status instead of misleading "Available" 
- **OCPP Compliance**: Better adherence to OCPP 1.6 protocol for status handling
- **Debugging**: Easier troubleshooting with accurate status information
- **Transaction Management**: Better visibility into charging session states

---

## [2.1.0] - 2025-01-15

### 🔔 Enhanced TriggerMessage Support

This is a minor release that adds complete TriggerMessage support, improved CSV export functionality, and additional OCPP message handlers for better protocol compliance.

### ✨ Added
- **FirmwareStatusNotification Handler**: Added `@on('FirmwareStatusNotification')` handler for firmware update status reports
- **DiagnosticsStatusNotification Handler**: Added `@on('DiagnosticsStatusNotification')` handler for diagnostics operation status reports
- **Enhanced CSV Export Format**: Improved CSV download with proper message flow directions and compact JSON
- **Complete Error Handling**: Added comprehensive error handling for all new message handlers

### 🔧 Changed
- **CSV Message Flow**: Updated direction indicators from "CMS->CI" to "CMS->CP" and "CP->CMS"
- **CSV JSON Format**: Changed from formatted multi-line JSON to compact single-line JSON in CSV exports
- **CSV Column Order**: Enhanced CPID, RecieveTime, UniqueID, MsgFlow, Command, PayloadData structure
- **Log Chronology**: Reversed CSV order to show latest logs first (reverse chronological)

### 🐛 Fixed
- **TriggerMessage "NotImplemented"**: Fixed server responding with "NotImplemented" for FirmwareStatusNotification and DiagnosticsStatusNotification
- **CSV Raw Data**: Fixed CSV showing "Raw" data with "[" payload instead of proper JSON parsing
- **Message Flow Direction**: Corrected message flow indicators in CSV exports
- **Multi-line JSON Parsing**: Enhanced JSON parsing with `/s` regex flag for WebSocket frames with formatted JSON

### 🔄 Enhanced Features
- **Protocol Compliance**: Better OCPP 1.6 compliance with additional message handlers
- **CSV Export Quality**: More professional CSV format matching industry standards
- **Handler Registration**: All new handlers properly registered with ChargePoint class
- **Error Management**: Consistent error handling patterns across all handlers

### 🧪 Testing
- **TriggerMessage Support**: Verified FirmwareStatusNotification and DiagnosticsStatusNotification handlers work correctly
- **CSV Format**: Confirmed proper message flow directions and compact JSON format in exports
- **Handler Integration**: Tested all new handlers are properly loaded and accessible
- **Backward Compatibility**: Ensured all existing functionality continues to work

### 📋 Technical Details

#### New Message Handlers
```python
@on('FirmwareStatusNotification')
async def on_firmware_status_notification(self, status):
    # Handles firmware update status reports
    
@on('DiagnosticsStatusNotification')  
async def on_diagnostics_status_notification(self, status):
    # Handles diagnostics operation status reports
```

#### CSV Export Improvements
- **Message Flow Detection**: Proper CMS->CP and CP->CMS direction identification
- **JSON Compaction**: Converts formatted JSON to single-line format
- **OCPP Structure Parsing**: Enhanced parsing of [MessageType, UniqueID, Command, PayloadData] arrays
- **Chronological Ordering**: Latest entries appear first in CSV exports

---

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