# Release Notes - OCPP 1.6 Server v2.1.1

**Release Date:** January 15, 2025  
**Type:** Patch Release (Bug Fix)  
**Previous Version:** v2.1.0

## 🎯 Overview

OCPP 1.6 Server v2.1.1 is a critical patch release that fixes status display issues where charger status was not properly following OCPP StatusNotification messages. This ensures users see accurate real-time charger status instead of misleading default values.

## 🐛 Critical Bug Fixes

### Status Display Accuracy
- **Fixed charger status display** to properly follow StatusNotification messages
- **Real-time status updates** now accurately reflect OCPP StatusNotification states (Available, Preparing, Charging, SuspendedEV, etc.)
- **Improved connection logic** to show "Disconnected" only when WebSocket connection is actually lost
- **Fixed frontend display bug** where UI was ignoring actual charger status from API

## 🔧 Technical Improvements

### Backend Changes
- **Removed conflicting status updates** from connection/disconnection events
- **Enhanced ChargerStore** to preserve StatusNotification status in `add_charger()` method
- **Improved API routes** with better status logic for WebSocket connectivity
- **Better OCPP compliance** by making StatusNotification the single source of truth

### Frontend Changes
- **Updated JavaScript** to use main `charger.status` field instead of `connector_status`
- **Fixed status display logic** to show actual status instead of defaulting to "Available"
- **Improved real-time updates** with accurate status reflection in UI

## 📋 Impact & Benefits

### For Users
- **Accurate Status Visibility**: See real charger status (Preparing, Charging, etc.) instead of misleading "Available"
- **Better Transaction Monitoring**: Improved visibility into charging session states
- **Enhanced Debugging**: Easier troubleshooting with accurate status information
- **OCPP Compliance**: Better adherence to OCPP 1.6 protocol standards

### For Developers
- **Cleaner Code Structure**: Removed conflicting status update logic
- **Better Separation of Concerns**: Connection status vs. operational status properly separated
- **Improved Maintainability**: Single source of truth for status updates

## 🧪 Testing & Validation

### Status Accuracy
- ✅ Verified charger status correctly shows "Preparing" when in preparing state
- ✅ Confirmed "Disconnected" only shows when WebSocket is actually lost
- ✅ Tested frontend displays match backend API responses
- ✅ Verified status changes immediately reflect in UI

### Regression Testing
- ✅ All existing functionality preserved
- ✅ Remote commands still work correctly
- ✅ Transaction management unaffected
- ✅ Configuration management unchanged

## 🚀 Upgrade Instructions

### From v2.1.0
1. **Stop the current server** (Ctrl+C in terminal)
2. **Replace files** with v2.1.1 version
3. **Restart server** using `start_server.bat`
4. **Hard refresh browser** (Ctrl+F5) to clear JavaScript cache

**Note:** No database changes or configuration updates required.

### From Earlier Versions
1. **Run setup.bat** to ensure all dependencies are current
2. **Follow standard upgrade process**
3. **Clear browser cache** for frontend updates

## 🔄 Compatibility

- **OCPP Protocol**: Fully compatible with OCPP 1.6 (no protocol changes)
- **Database**: No database schema changes
- **API**: All existing API endpoints unchanged
- **Configuration**: No configuration file updates needed
- **Chargers**: All existing charger connections continue to work

## 📚 Documentation Updates

- Updated README.md with v2.1.1 information
- Enhanced CHANGELOG.md with detailed bug fix information
- Updated version numbers in all batch files
- No changes required to user documentation or setup guides

## 🛡️ Known Issues & Limitations

No new known issues introduced in this release. All previous functionality preserved.

## 🙏 Acknowledgments

This release addresses user-reported issues with status display accuracy. Thank you to all users who provided feedback and helped identify these critical UI issues.

## 📞 Support

- **Documentation**: README.md, CHANGELOG.md
- **Issues**: Check console logs for detailed error messages
- **Requirements**: Windows 10/11, Python 3.8+, OCPP 1.6 compatible chargers

---

**Next Release**: v2.2.0 (planned features to be announced)  
**Support**: This release includes all features from v2.1.0 plus critical bug fixes. 