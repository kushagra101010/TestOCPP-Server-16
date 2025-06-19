# Raw WebSocket Message Feature

## Overview

A new feature has been implemented that allows sending raw WebSocket messages directly to chargers without any OCPP validation or processing. This is designed for advanced testing, debugging, and custom packet experimentation.

## ⚠️ Important Warning

**This feature bypasses all OCPP validation and sends messages directly to the charger. Use with extreme caution as invalid messages may cause unexpected charger behavior.**

## Features

### 1. Raw Message Sending
- Send any JSON WebSocket message directly to the charger
- Bypasses all OCPP library validation
- Logs all sent messages for debugging
- Basic JSON syntax validation only

### 2. Built-in Examples
- DataTransfer examples
- GetConfiguration examples  
- Reset command examples
- Custom message templates

### 3. Safety Features
- JSON format validation
- Confirmation dialog with warning
- Detailed logging of sent messages
- Error handling and reporting

## How to Use

### 1. Web Interface

1. **Select a Charger**: Choose a connected charger from the list
2. **Open Raw Message Modal**: Click "Send Raw Message" button (red button with code icon)
3. **Enter Raw Message**: Type or paste your raw WebSocket message
4. **Use Examples**: Click example buttons to load common message templates
5. **Send Message**: Click "Send Raw Message" after confirming the warning

### 2. Message Format

OCPP WebSocket messages follow this JSON array format:
```json
[MessageType, MessageId, Action, Payload]
```

Where:
- **MessageType**: 2=CALL, 3=CALLRESULT, 4=CALLERROR  
- **MessageId**: Unique identifier for the message
- **Action**: OCPP action name (e.g., "DataTransfer", "GetConfiguration")
- **Payload**: JSON object with action-specific parameters

### 3. Example Messages

#### DataTransfer
```json
[2, "msg-123", "DataTransfer", {"vendorId": "Custom", "messageId": "Test", "data": "test-data"}]
```

#### GetConfiguration
```json
[2, "msg-456", "GetConfiguration", {}]
```

#### Reset Command
```json
[2, "msg-789", "Reset", {"type": "Soft"}]
```

#### Custom Message
```json
[2, "msg-custom", "CustomAction", {"customField": "customValue", "number": 123}]
```

## API Endpoint

### POST `/api/send/{charge_point_id}/raw_message`

Send a raw WebSocket message to the specified charger.

**Request Body:**
```json
{
    "raw_message": "[2, \"msg-123\", \"DataTransfer\", {\"vendorId\": \"Test\"}]"
}
```

**Response:**
```json
{
    "status": "success",
    "data": {
        "status": "success", 
        "message": "Raw message sent successfully"
    }
}
```

## Files Modified

### Backend Changes

1. **`backend/ocpp_handler.py`**
   - Added `send_raw_message()` method to ChargePoint class
   - Direct WebSocket message sending
   - JSON validation and logging

2. **`backend/api_routes.py`**
   - Added `/api/send/{charge_point_id}/raw_message` endpoint
   - Request validation and error handling

### Frontend Changes

1. **`frontend/templates/index.html`**
   - Added "Send Raw Message" button in Actions section
   - Added Raw Message modal with examples and warnings
   - Safety warnings and user guidance

2. **`frontend/static/app.js`**
   - Added `showRawMessageModal()` function
   - Added `loadRawMessageExample()` for templates
   - Added `sendRawMessage()` with validation and confirmation

## Safety Measures

### 1. User Warnings
- Clear warning about bypassing OCPP validation
- Confirmation dialog before sending
- Visual indicators (red button, warning icons)

### 2. Validation
- JSON format validation before sending
- Error handling for invalid messages
- Detailed error reporting

### 3. Logging
- All raw messages logged with special markers
- JSON validation results logged
- Success/failure status logged
- Messages appear in charger logs with 📤 icon

## Use Cases

### 1. Testing Custom Protocols
- Test vendor-specific extensions
- Validate charger responses to custom messages
- Protocol conformance testing

### 2. Debugging
- Send malformed messages to test error handling
- Test edge cases and boundary conditions
- Reproduce specific message sequences

### 3. Development
- Test new OCPP features before library support
- Prototype custom implementations
- Educational purposes

### 4. Compliance Testing
- Send non-standard messages to verify rejection
- Test charger behavior with invalid data
- Security testing

## Example Testing Scenarios

### 1. Invalid Message Types
```json
[99, "test", "InvalidAction", {}]
```

### 2. Missing Required Fields
```json
[2, "test", "RemoteStartTransaction", {}]
```

### 3. Custom Vendor Extensions
```json
[2, "test", "VendorSpecificAction", {"customParam": "value"}]
```

### 4. Malformed JSON
```json
[2, "test", "DataTransfer", {"vendorId": "Test", "data": 
```

## Logging Examples

When sending raw messages, you'll see logs like:
```
📤 Raw WebSocket Message (No Validation): [2, "msg-123", "DataTransfer", {"vendorId": "Test"}]
✅ Raw message is valid JSON
✅ Raw WebSocket message sent successfully (bypassed all OCPP validation)
```

## Security Considerations

1. **Production Use**: This feature should be disabled in production environments
2. **Access Control**: Consider restricting access to authorized users only
3. **Monitoring**: Log all raw message usage for audit purposes
4. **Charger Safety**: Ensure chargers can handle malformed messages gracefully

## Future Enhancements

1. **Message Templates**: Save and reuse custom message templates
2. **Response Monitoring**: Automatically capture and display responses
3. **Batch Testing**: Send multiple messages in sequence
4. **Validation Options**: Optional OCPP schema validation
5. **Message History**: Track previously sent raw messages 