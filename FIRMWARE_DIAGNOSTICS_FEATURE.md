# Firmware Update & Diagnostics Feature

## Overview
Added comprehensive firmware update and diagnostics functionality to the OCPP server, allowing central management system operators to remotely update charger firmware and retrieve diagnostic information.

## Features Added

### 🔧 UpdateFirmware Command
Allows the CMS to instruct a charger to download and install new firmware from a specified location.

**OCPP 1.6 Compliance:**
- ✅ Supports all required parameters: `location`, `retrieveDate`
- ✅ Supports optional parameters: `retries`, `retryInterval`
- ✅ Handles FirmwareStatusNotification responses from chargers
- ✅ Full ISO 8601 datetime support

**UI Features:**
- Modern Bootstrap modal with form validation
- Default retrieve date set to 5 minutes from current time
- Configurable retry settings
- Warning about potential disconnection during update
- Real-time feedback with success/error messages

### 🏥 GetDiagnostics Command
Enables the CMS to request diagnostic files from chargers for troubleshooting and analysis.

**OCPP 1.6 Compliance:**
- ✅ Supports required parameter: `location`
- ✅ Supports optional parameters: `startTime`, `stopTime`, `retries`, `retryInterval`
- ✅ Handles DiagnosticsStatusNotification responses from chargers
- ✅ Returns filename in response for tracking

**UI Features:**
- Intuitive modal with datetime pickers for diagnostic period
- Optional time range selection for targeted diagnostics
- Configurable retry settings
- Shows expected filename when available

## Technical Implementation

### Backend Changes

#### 1. OCPP Handler (`backend/ocpp_handler.py`)
```python
async def update_firmware(self, location: str, retrieve_date: str, 
                         retries: int = None, retry_interval: int = None):
    """Send UpdateFirmware request to charger."""
    # Full implementation with error handling and logging

async def get_diagnostics(self, location: str, retries: int = None, 
                         retry_interval: int = None, start_time: str = None, 
                         stop_time: str = None):
    """Send GetDiagnostics request to charger."""
    # Full implementation with optional parameters
```

#### 2. API Routes (`backend/api_routes.py`)
```python
@router.post("/api/send/{charge_point_id}/update_firmware")
async def update_firmware(charge_point_id: str, request: UpdateFirmwareRequest):
    # RESTful API endpoint with validation

@router.post("/api/send/{charge_point_id}/get_diagnostics")
async def get_diagnostics(charge_point_id: str, request: GetDiagnosticsRequest):
    # RESTful API endpoint with datetime validation
```

### Frontend Changes

#### 1. User Interface (`frontend/templates/index.html`)
- Added "Firmware & Diagnostics" section with two buttons
- Created comprehensive modals with form validation
- Integrated with existing Bootstrap styling
- Added appropriate icons and warning messages

#### 2. JavaScript Functions (`frontend/static/app.js`)
```javascript
function showUpdateFirmwareModal()    // Show firmware update modal
function showGetDiagnosticsModal()    // Show diagnostics modal
async function updateFirmware()       // Handle firmware update API call
async function getDiagnostics()       // Handle diagnostics API call
```

#### 3. Message Filtering
- Added UpdateFirmware and GetDiagnostics to log filtering system
- Included in multi-select message type filters
- Proper categorization as Server → Charger commands

## Usage Examples

### Update Firmware
1. Select a connected charger
2. Click **"Update Firmware"** button
3. Fill in firmware details:
   - **Location**: `https://firmware.example.com/charger-v2.1.bin`
   - **Retrieve Date**: `2024-12-25 10:00` (auto-set to +5 minutes)
   - **Retries**: `3` (optional)
   - **Retry Interval**: `60` (optional, seconds)
4. Click **"Update Firmware"**

The charger will:
- Download firmware at the specified time
- Send FirmwareStatusNotification messages:
  - `Downloading` → `Downloaded` → `Installing` → `Installed`

### Get Diagnostics
1. Select a connected charger
2. Click **"Get Diagnostics"** button
3. Configure diagnostic request:
   - **Location**: `https://diagnostics.example.com/upload/`
   - **Start Time**: `2024-12-20 00:00` (optional)
   - **Stop Time**: `2024-12-24 23:59` (optional)
   - **Retries**: `3` (optional)
4. Click **"Get Diagnostics"**

The charger will:
- Generate diagnostic files for the specified period
- Upload to the specified location
- Send DiagnosticsStatusNotification messages:
  - `Uploading` → `Uploaded`

## Status Notifications

### Firmware Status Values
- `Idle` - No firmware operation in progress
- `Downloading` - Downloading firmware
- `Downloaded` - Firmware download completed
- `Installing` - Installing firmware
- `Installed` - Firmware installation completed
- `DownloadFailed` - Firmware download failed
- `InstallationFailed` - Firmware installation failed

### Diagnostics Status Values
- `Idle` - No diagnostics operation in progress
- `Uploading` - Uploading diagnostic files
- `Uploaded` - Upload completed successfully
- `UploadFailed` - Upload failed

## Testing

### Test Script
Use the included test script to simulate a charger that responds to firmware and diagnostics commands:

```bash
python test_firmware_diagnostics.py
```

This creates a test charger `TEST_FW_DIAG` that:
- Connects to the OCPP server
- Responds to UpdateFirmware commands
- Responds to GetDiagnostics commands
- Simulates realistic status notification sequences

### Manual Testing
1. Start the OCPP server: `python -m backend.main`
2. Run the test charger: `python test_firmware_diagnostics.py`
3. Open the web UI: `http://localhost:8000`
4. Select charger `TEST_FW_DIAG`
5. Test both firmware update and diagnostics functions

## Error Handling

### Validation
- **URL Validation**: Ensures location URLs are properly formatted
- **DateTime Validation**: Validates ISO 8601 datetime formats
- **Connection Validation**: Checks if charger is connected before sending commands
- **Parameter Validation**: Validates optional parameters (retries, intervals)

### Error Responses
- **404**: Charger not connected
- **400**: Invalid request parameters (bad URLs, dates)
- **500**: Internal server errors with detailed messages

### User Feedback
- Success messages with command details
- Clear error messages with specific issues
- Real-time log updates showing command execution
- Modal validation prevents invalid submissions

## Security Considerations

### Input Validation
- URL sanitization for firmware and diagnostic locations
- DateTime format validation to prevent injection
- Integer validation for retry parameters
- Required field validation

### Access Control
- Commands only work with authenticated web sessions
- Charger must be actively connected
- No persistent command queuing (for security)

## Future Enhancements

### Potential Improvements
1. **Firmware Version Tracking**: Track installed firmware versions
2. **Diagnostic Analysis**: Built-in log analysis tools
3. **Bulk Operations**: Update multiple chargers simultaneously
4. **Scheduling**: Advanced scheduling for firmware updates
5. **Progress Tracking**: Real-time progress bars for operations
6. **File Management**: Direct file upload/download capabilities

### Integration Possibilities
1. **Firmware Repository**: Integrated firmware version management
2. **Diagnostic Dashboard**: Visual diagnostic analysis tools
3. **Automated Updates**: Scheduled maintenance windows
4. **Alert System**: Notifications for failed operations

## Compliance Notes

This implementation fully complies with OCPP 1.6 specifications:
- ✅ **UpdateFirmware**: Section 5.15 of OCPP 1.6 specification
- ✅ **GetDiagnostics**: Section 5.14 of OCPP 1.6 specification
- ✅ **Status Notifications**: Proper handling of async status updates
- ✅ **Error Handling**: Compliant error response formats
- ✅ **Message Structure**: Correct OCPP JSON message formatting

All message schemas match the official OCPP 1.6 JSON schemas provided in the `OCPP_1.6_documentation/schemas/json/` directory. 