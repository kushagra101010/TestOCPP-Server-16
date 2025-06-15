# OCPP 1.6 Server v2.1.0 - Release Notes

**Release Date:** January 15, 2025  
**Version:** 2.1.0  
**Protocol:** OCPP 1.6  

## 🎉 Minor Release Overview

This is a **minor release** of the OCPP 1.6 Server software that adds enhanced TriggerMessage support, improved CSV export functionality, and additional OCPP message handlers. The version 2.1.0 refers to our server software release, while continuing to implement the OCPP 1.6 protocol.

## 🚀 What's New

### 🔔 Enhanced TriggerMessage Support
- **FirmwareStatusNotification Handler**: Added proper handler for firmware status updates
- **DiagnosticsStatusNotification Handler**: Added handler for diagnostics status notifications
- **Complete Trigger Support**: Server now properly responds to all TriggerMessage requests
- **Improved Error Handling**: Better error handling and logging for triggered messages

### 📊 CSV Export Improvements
- **Corrected Message Flow**: Fixed direction indicators from "CMS->CI" to "CMS->CP" and "CP->CMS"
- **Compact JSON Format**: CSV now exports single-line JSON instead of formatted multi-line JSON
- **Proper Column Structure**: Enhanced CPID, RecieveTime, UniqueID, MsgFlow, Command, PayloadData format
- **Reverse Chronological Order**: Latest logs now appear first in CSV exports
- **Enhanced JSON Parsing**: Improved parsing of WebSocket frames with multi-line JSON data

### 🛠️ Handler Enhancements
- **Missing Handlers Added**: Implemented previously missing OCPP message handlers
- **Better Compliance**: Enhanced OCPP 1.6 protocol compliance
- **Error Response Fixes**: Eliminated "NotImplemented" responses for supported messages

## 🔥 Key Improvements

### TriggerMessage Functionality
```diff
- ❌ Server responds with "NotImplemented" for FirmwareStatusNotification
+ ✅ Proper handler responds with appropriate status and logging
```

### CSV Export Quality
```diff
- ❌ CSV shows "Raw" data with incorrect message flow directions
+ ✅ Properly formatted CSV with correct CP/CMS directions and compact JSON
```

### Message Handler Coverage
```diff
- ❌ Missing handlers causing protocol compliance issues
+ ✅ Complete handler coverage for all supported OCPP messages
```

## 📋 Technical Changes

### New Message Handlers
- **@on('FirmwareStatusNotification')**: Handles firmware update status reports
- **@on('DiagnosticsStatusNotification')**: Handles diagnostics operation status reports
- **Proper Error Handling**: Both handlers include comprehensive error handling
- **Consistent Logging**: Follows existing logging patterns for debugging

### CSV Export Enhancements
- **Message Flow Detection**: Properly detects CMS->CP vs CP->CMS message directions
- **JSON Compaction**: Converts formatted JSON to single-line format for CSV
- **OCPP Structure Parsing**: Enhanced parsing of OCPP message arrays [MessageType, UniqueID, Command, PayloadData]
- **Multi-line JSON Support**: Added regex flag for parsing formatted JSON from WebSocket frames
- **Chronological Ordering**: Reversed log order to show most recent entries first

### Protocol Compliance
- **Handler Registration**: All new handlers properly registered with ChargePoint class
- **Response Consistency**: Consistent response patterns matching existing handlers
- **Error Management**: Proper exception handling prevents server crashes

## 🧪 Testing & Validation

### TriggerMessage Testing
- ✅ **FirmwareStatusNotification**: Confirmed proper handling and response
- ✅ **DiagnosticsStatusNotification**: Verified status processing and logging
- ✅ **TriggerMessage Integration**: All trigger types now work without "NotImplemented" errors

### CSV Export Testing
- ✅ **Message Direction**: Verified correct CMS->CP and CP->CMS labeling
- ✅ **JSON Format**: Confirmed compact single-line JSON in CSV output
- ✅ **Column Structure**: Validated proper CPID, RecieveTime, UniqueID, MsgFlow, Command, PayloadData format
- ✅ **Chronological Order**: Confirmed latest entries appear first

### Compatibility Testing
- ✅ **OCPP 1.6 Protocol**: Full compliance maintained with additional handlers
- ✅ **Existing Functionality**: All previous features continue to work
- ✅ **Web Dashboard**: Confirmed all UI features remain functional
- ✅ **Demo Charger**: Verified simulation continues to work properly

## 🔄 Migration Guide

### From v2.0.0 to v2.1.0

**No migration steps required** - this is a backward-compatible minor release.

1. **Optional: Update Server** (recommended)
   ```batch
   start_server.bat
   ```

2. **No Configuration Changes**: All existing settings and configurations remain valid
3. **No API Changes**: All existing API endpoints work identically
4. **Enhanced Features**: New functionality is automatically available

## 📊 Performance Impact

- **Minimal Performance Impact**: New handlers add negligible overhead
- **Improved CSV Generation**: More efficient JSON processing for exports
- **Better Error Handling**: Reduced server resource usage from error conditions
- **Enhanced Logging Efficiency**: More targeted logging reduces log file growth

## 🔒 Security & Stability

- **Input Validation**: Enhanced validation for new message handlers
- **Error Containment**: Proper exception handling prevents cascading failures
- **Data Integrity**: Improved JSON parsing ensures data consistency
- **Log Security**: Better log formatting prevents potential data exposure

## 🌐 Compatibility Matrix

| Component | Version | Status |
|-----------|---------|--------|
| OCPP Protocol | 1.6 | ✅ Enhanced Support |
| Python | 3.8+ | ✅ Tested |
| Windows | 10/11 | ✅ Supported |
| Linux | Ubuntu 20.04+ | ✅ Compatible |
| macOS | 10.15+ | ✅ Compatible |

## 📞 Support & Feedback

### Known Issues
- None currently identified

### Fixed Issues from v2.0.0
- ✅ **TriggerMessage "NotImplemented" responses**: Now properly handled
- ✅ **CSV export formatting issues**: Corrected message flow and JSON format
- ✅ **Missing OCPP handlers**: Added FirmwareStatusNotification and DiagnosticsStatusNotification

### Getting Help
1. **Check Logs**: Review console output for detailed error messages
2. **Troubleshooting**: Refer to README.md troubleshooting section
3. **Documentation**: Complete documentation included in package

## 🎯 What's Next

### Future Roadmap
- **Additional OCPP Messages**: Continue expanding message handler coverage
- **Advanced CSV Features**: More export options and filtering capabilities
- **Enhanced Dashboard**: Real-time trigger message monitoring
- **Automated Testing**: Comprehensive test suite for all OCPP operations

## 📄 Files Changed

### Updated Files
- `backend/ocpp_handler.py` - Added FirmwareStatusNotification and DiagnosticsStatusNotification handlers
- `frontend/static/js/app.js` or CSV export logic - Enhanced CSV formatting and JSON parsing
- `start_server.bat` - Updated version numbers to v2.1.0
- `README.md` - Updated version references and feature descriptions
- `CHANGELOG.md` - Added v2.1.0 entry with detailed changes

### New Files
- `RELEASE_NOTES_v2.1.0.md` - This file

## 🏆 Acknowledgments

Special thanks to:
- Users who reported TriggerMessage and CSV export issues
- The community for providing detailed feedback on expected CSV format
- Testing efforts that identified missing message handlers

---

**Download:** [OCPP 1.6 Server v2.1.0]  
**Previous Version:** [v2.0.0 Release Notes](RELEASE_NOTES_v2.0.0.md)  
**Documentation:** [README.md](README.md)  
**Changes:** [CHANGELOG.md](CHANGELOG.md)  

**© 2025 OCPP 1.6 Server v2.1.0 - Professional EV Charging Management System** 