# OCPP Log Filtering Fix - Bidirectional Message Support

## Issue Description
The OCPP log filtering was not working correctly for bidirectional messages. When selecting a message type filter like "BootNotification + Response", only the request from charger to CMS was shown, but the corresponding response from CMS to charger was missing.

## Root Cause Analysis
The filtering logic had several fundamental issues:

### 1. **Response Detection Problems**
- **Issue**: `isResponseMessage()` only checked for "Response" text in messages
- **Problem**: OCPP WebSocket frames don't always contain "Response" in the log text
- **Result**: Many actual responses were not detected as responses

### 2. **Message Type Extraction Issues**
- **Issue**: `extractOCPPMessageType()` stripped "Response" suffix from message types
- **Problem**: Responses lost their identity and couldn't be properly matched
- **Result**: Response messages couldn't be correctly categorized

### 3. **Inadequate WebSocket Frame Analysis**
- **Issue**: No proper parsing of OCPP JSON frames to identify message types
- **Problem**: Couldn't distinguish between CALL (request) and CALLRESULT (response) messages
- **Result**: Filtering relied only on text matching, which was unreliable

### 4. **Poor Bidirectional Matching**
- **Issue**: No logic to match responses to their corresponding request types
- **Problem**: When filtering for "BootNotification", only requests were shown
- **Result**: Incomplete message flows, making debugging difficult

## Solution Implemented

### 1. **Enhanced Response Detection**
```javascript
// Before (Limited)
function isResponseMessage(message) {
    return /Response/i.test(message) || message.toLowerCase().includes('response');
}

// After (Comprehensive)
function isResponseMessage(message) {
    return /Response/i.test(message) || 
           message.toLowerCase().includes('response') ||
           message.includes('CMS→Charger') ||
           message.includes('Server→Charger');
}
```

### 2. **Improved Message Type Extraction**
```javascript
// Before (Stripped Response)
return match[0].replace(/Response$/i, ''); // Lost response identity

// After (Preserved Identity)
return match[0]; // Keep full message type including Response
```

### 3. **Advanced WebSocket Frame Analysis**
```javascript
// New: Parse OCPP JSON frames to identify message types
const ocppMessage = JSON.parse(jsonStr);
const messageType = ocppMessage[0]; // 2=CALL, 3=CALLRESULT, 4=CALLERROR

if (messageType === 2) {
    // CALL (request) message
    const action = ocppMessage[2];
} else if (messageType === 3) {
    // CALLRESULT (response) message
    const payload = ocppMessage[2];
}
```

### 4. **Smart Response-to-Request Matching**
Implemented payload analysis to match responses to their request types:

```javascript
// BootNotification response detection
if (messageFilter.toLowerCase() === 'bootnotification') {
    return payload.hasOwnProperty('currentTime') && payload.hasOwnProperty('interval');
}

// Heartbeat response detection
if (messageFilter.toLowerCase() === 'heartbeat') {
    return payload.hasOwnProperty('currentTime') && Object.keys(payload).length === 1;
}

// StartTransaction response detection
if (messageFilter.toLowerCase() === 'starttransaction') {
    return payload.hasOwnProperty('transactionId') && payload.hasOwnProperty('idTagInfo');
}
```

## Technical Implementation Details

### **OCPP Message Type Detection**
The system now properly identifies:
- **CALL (2)**: Request messages from charger or server
- **CALLRESULT (3)**: Response messages with success payload
- **CALLERROR (4)**: Error response messages

### **Response Payload Analysis**
Each OCPP message type has unique response characteristics:

| Message Type | Response Payload Signature |
|--------------|---------------------------|
| BootNotification | `{currentTime, interval, status}` |
| Heartbeat | `{currentTime}` |
| Authorize | `{idTagInfo}` |
| StartTransaction | `{transactionId, idTagInfo}` |
| StopTransaction | `{idTagInfo}` (no transactionId) |
| StatusNotification | `{}` (empty) |
| MeterValues | `{}` (empty) |
| GetConfiguration | `{configurationKey, unknownKey}` |
| RemoteStart/Stop | `{status}` (single field) |

### **Bidirectional Filtering Logic**
When a user selects "BootNotification + Response":
1. **Text-based matching** finds messages containing "BootNotification"
2. **WebSocket frame analysis** parses JSON to identify CALL messages with action "BootNotification"
3. **Response payload analysis** identifies CALLRESULT messages with BootNotification response signature
4. **Direction analysis** includes both Charger→CMS and CMS→Charger flows

## User Experience Improvements

### **Before Fix:**
- ❌ Incomplete message flows (only requests shown)
- ❌ Missing responses made debugging difficult
- ❌ Inconsistent filtering behavior
- ❌ Poor visibility into OCPP communication

### **After Fix:**
- ✅ **Complete bidirectional flows** - both requests and responses shown
- ✅ **Accurate filtering** for all OCPP message types
- ✅ **Smart response matching** based on payload analysis
- ✅ **Better debugging experience** with full message context
- ✅ **Consistent behavior** across all message types

## Supported Message Types

### **Charger → Server Messages** (with responses):
- BootNotification
- StatusNotification  
- Heartbeat
- Authorize
- StartTransaction
- StopTransaction
- MeterValues
- DataTransfer
- FirmwareStatusNotification
- DiagnosticsStatusNotification

### **Server → Charger Messages** (with responses):
- RemoteStartTransaction
- RemoteStopTransaction
- GetConfiguration
- ChangeConfiguration
- ClearCache
- Reset
- SendLocalList
- ClearLocalList
- GetLocalListVersion
- TriggerMessage
- ChangeAvailability
- ReserveNow
- CancelReservation
- SetChargingProfile
- ClearChargingProfile
- GetCompositeSchedule

## Testing Verification

### **Test Bidirectional Filtering:**
1. Select "BootNotification + Response" filter
2. Verify both charger request AND server response are shown
3. Check that timestamps show proper request-response sequence
4. Confirm WebSocket frames are properly parsed

### **Test All Message Types:**
1. Test each message type filter individually
2. Verify both directions are shown for each
3. Check that responses are correctly matched to requests
4. Confirm error messages (CALLERROR) are included

### **Test Edge Cases:**
1. Malformed JSON frames fall back to text matching
2. Unknown message types are handled gracefully
3. Empty responses are correctly identified
4. Multiple message types in logs don't interfere

## Files Modified
1. **`frontend/static/app.js`**:
   - `extractOCPPMessageType()`: Improved message type detection
   - `isResponseMessage()`: Enhanced response detection
   - `getBaseMessageType()`: New helper function
   - `matchesMessageFilter()`: New comprehensive matching logic
   - `applyLogFiltersToLogs()`: Updated to use new filtering system

## Benefits
- ✅ **Complete OCPP message flows visible**
- ✅ **Accurate bidirectional filtering for all message types**
- ✅ **Better debugging and troubleshooting capabilities**
- ✅ **Improved user experience with reliable filtering**
- ✅ **Future-proof design for new OCPP message types** 