# UnlockConnector Feature

## Overview
Added comprehensive UnlockConnector functionality to the OCPP server, allowing central management system operators to remotely unlock charging connectors on demand. This is particularly useful for emergency situations, maintenance operations, or when users experience issues with connector locking mechanisms.

## Features Added

### 🔓 UnlockConnector Command
Allows the CMS to instruct a charger to physically unlock a specific connector.

**OCPP 1.6 Compliance:**
- ✅ Supports required parameter: `connectorId`
- ✅ Handles all possible response statuses: `Unlocked`, `UnlockFailed`, `NotSupported`
- ✅ Full OCPP 1.6 message format compliance
- ✅ Proper error handling and validation

**UI Features:**
- Clean Bootstrap modal with connector selection dropdown
- Safety warning about potential charging session interruption
- Confirmation dialog to prevent accidental unlocking
- Real-time status feedback with explanations
- Supports connectors 1-10 (standard OCPP range)

## Technical Implementation

### Backend Changes

#### 1. OCPP Handler (`backend/ocpp_handler.py`)
```python
async def unlock_connector(self, connector_id: int):
    """Send UnlockConnector request to charger."""
    # Full implementation with error handling and logging
    # Returns charger response with status
```

#### 2. API Routes (`backend/api_routes.py`)
```python
@router.post("/api/send/{charge_point_id}/unlock_connector")
async def unlock_connector(charge_point_id: str, request: UnlockConnectorRequest):
    # RESTful API endpoint with connector ID validation
    # Validates connector ID range (1-10)
```

### Frontend Changes

#### 1. User Interface (`frontend/templates/index.html`)
- Added "Unlock Connector" button in the Connector Management section
- Created comprehensive modal with connector selection dropdown
- Added warning messages about potential charging session interruption
- Included information about possible response statuses

#### 2. JavaScript Functions (`frontend/static/app.js`)
```javascript
function showUnlockConnectorModal()   // Show unlock connector modal
async function unlockConnector()      // Handle unlock connector API call
```

#### 3. Message Filtering
- UnlockConnector already included in log filtering system
- Proper categorization as Server → Charger command
- Integrated with multi-select message type filters

## Usage Example

### Unlock a Connector
1. Select a connected charger
2. Click **"Unlock Connector"** button
3. Select connector to unlock:
   - **Connector ID**: Choose from dropdown (1-10)
4. Review warning message
5. Click **"Unlock Connector"**
6. Confirm the action in the confirmation dialog

The charger will respond with one of three statuses:
- **`Unlocked`**: Connector successfully unlocked
- **`UnlockFailed`**: Failed to unlock connector (mechanical issue, active transaction, etc.)
- **`NotSupported`**: Charger doesn't support remote unlocking

## Response Status Meanings

### Unlocked
- ✅ **Meaning**: Connector was successfully unlocked
- **User Action**: Connector is now physically unlocked and cable can be removed
- **Use Cases**: Emergency release, maintenance access, user assistance

### UnlockFailed
- ❌ **Meaning**: Charger could not unlock the connector
- **Possible Causes**:
  - Active charging session preventing unlock
  - Mechanical failure in locking mechanism
  - Safety interlocks engaged
  - Connector not properly seated
- **User Action**: Check charger status, ensure no active transaction, contact technical support if needed

### NotSupported
- ⚠️ **Meaning**: This charger model doesn't support remote unlocking
- **Possible Causes**:
  - Older charger firmware without unlock capability
  - Hardware limitation (no unlock actuator)
  - Feature disabled in charger configuration
- **User Action**: Use manual unlock mechanism or contact charger manufacturer

## Safety Considerations

### Warning System
- **Modal Warning**: Clear warning about potential charging session interruption
- **Confirmation Dialog**: Requires explicit confirmation before sending command
- **Status Feedback**: Immediate feedback on unlock attempt result

### Best Practices
1. **Check Transaction Status**: Verify no active charging session before unlocking
2. **Emergency Use**: Primarily for emergency situations or user assistance
3. **Maintenance Windows**: Prefer unlocking during maintenance periods
4. **User Communication**: Inform users before unlocking their connector

## Error Handling

### Validation
- **Connector ID Range**: Validates connector ID is between 1-10
- **Connection Validation**: Ensures charger is connected before sending command
- **Input Validation**: Prevents empty or invalid connector selections

### Error Responses
- **404**: Charger not connected
- **400**: Invalid connector ID (outside 1-10 range)
- **500**: Internal server errors with detailed messages

### User Feedback
- Success messages with unlock status explanation
- Clear error messages for validation failures
- Real-time log updates showing command execution
- Modal prevents invalid submissions

## Use Cases

### 🆘 Emergency Situations
```
Scenario: EV driver cannot release charging cable
Action: Use UnlockConnector to release cable remotely
Result: Driver can safely disconnect and move vehicle
```

### 🔧 Maintenance Operations
```
Scenario: Technician needs access to connector for cleaning/inspection
Action: Unlock connector remotely before maintenance
Result: Safe access without requiring physical key
```

### 🎯 User Assistance
```
Scenario: User reports "stuck" charging cable
Action: Check logs, then unlock connector if safe
Result: Improved customer satisfaction and reduced support calls
```

### 🏢 Fleet Management
```
Scenario: Fleet vehicle needs to be moved urgently
Action: Remotely unlock connector for fleet operator
Result: Faster vehicle turnaround and operational efficiency
```

## Testing

### Test Script Support
The updated test script (`test_firmware_diagnostics.py`) now includes UnlockConnector testing:

```bash
python test_firmware_diagnostics.py
```

**Test Features:**
- Simulates realistic unlock responses with weighted probabilities
- 80% success rate (`Unlocked`)
- 10% failure rate (`UnlockFailed`) 
- 10% not supported (`NotSupported`)
- Console logging for all unlock operations

### Manual Testing
1. Start the OCPP server: `python -m backend.main` (use PowerShell syntax: `python -m backend.main`)
2. Run the test charger: `python test_firmware_diagnostics.py`
3. Open the web UI: `http://localhost:8000`
4. Select charger `TEST_FW_DIAG`
5. Test unlock connector with different connector IDs
6. Observe different response statuses in test console

## Security Considerations

### Access Control
- Commands only work with authenticated web sessions
- Charger must be actively connected
- No persistent command queuing for security

### Audit Trail
- All unlock attempts logged with timestamps
- Command parameters recorded (connector ID)
- Response status captured for accountability
- Full OCPP message logging available

### Abuse Prevention
- Confirmation dialog prevents accidental unlocking
- Warning messages about potential service interruption
- Clear status feedback prevents repeated attempts

## Integration with Existing Features

### Log Filtering
- UnlockConnector messages appear in filtered logs
- Can filter specifically for unlock operations
- Integrated with multi-select filtering system

### Charger Management
- Works with existing charger connection management
- Uses same authentication and session handling
- Consistent error handling patterns

### UI Design
- Follows existing modal design patterns
- Consistent with other command interfaces
- Maintains visual hierarchy and user experience

## Future Enhancements

### Potential Improvements
1. **Bulk Unlock**: Unlock multiple connectors simultaneously
2. **Scheduled Unlock**: Schedule unlock operations for maintenance windows
3. **Conditional Unlock**: Unlock only if no active transaction
4. **Lock Command**: Add companion command to lock connectors
5. **Status Monitoring**: Real-time connector lock/unlock status display

### Advanced Features
1. **Integration with Transaction Management**: Automatic unlock after transaction completion
2. **Emergency Unlock Protocol**: Rapid unlock for emergency situations
3. **User Notification**: Send notifications to users when their connector is unlocked
4. **Unlock History**: Track unlock operations for analytics and reporting

## Compliance Notes

This implementation fully complies with OCPP 1.6 specifications:
- ✅ **UnlockConnector**: Section 5.18 of OCPP 1.6 specification
- ✅ **Message Structure**: Correct OCPP JSON message formatting
- ✅ **Response Handling**: Proper handling of all defined response statuses
- ✅ **Error Handling**: Compliant error response formats

The implementation matches the official OCPP 1.6 JSON schema provided in `OCPP_1.6_documentation/schemas/json/UnlockConnector.json`.

## PowerShell Command Note

For Windows PowerShell users, use the following command to start the server:
```powershell
python -m backend.main
```

Instead of the bash-style:
```bash
cd TestOCPP-Server-16 && python -m backend.main  # This won't work in PowerShell
``` 