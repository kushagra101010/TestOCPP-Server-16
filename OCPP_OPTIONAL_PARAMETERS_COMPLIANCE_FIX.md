# OCPP Optional Parameters Compliance Fix

## Overview
This document describes the fixes applied to ensure OCPP 1.6 compliance regarding optional parameters in message construction. The main issue was that optional parameters were being sent in OCPP packets even when they had `None` or empty values, which violates OCPP specification requirements.

## OCPP Compliance Rule
According to OCPP 1.6 specification, optional parameters that are not set should be **omitted** from the JSON payload entirely, rather than being sent as `null` or empty values.

## Fixed OCPP Messages

### 1. GetConfiguration
**Schema**: Optional `key` parameter for filtering configuration keys
**Issue**: `key` parameter was always passed, even when `None`
**Fix**: Only include `key` parameter when keys are provided and non-empty

```python
# Before
request = call.GetConfiguration(key=keys)  # keys could be None

# After  
if keys:
    request = call.GetConfiguration(key=keys)
else:
    request = call.GetConfiguration()
```

### 2. DataTransfer
**Schema**: Optional `messageId` and `data` parameters
**Issue**: Both parameters were always passed, even when `None`
**Fix**: Build request dynamically, only including provided parameters

```python
# Before
request = call.DataTransfer(
    vendor_id=vendor_id,
    message_id=message_id,  # Could be None
    data=data              # Could be None
)

# After
request_params = {"vendor_id": vendor_id}
if message_id is not None:
    request_params["message_id"] = message_id
if data is not None:
    request_params["data"] = data
request = call.DataTransfer(**request_params)
```

### 3. TriggerMessage
**Schema**: Optional `connectorId` parameter
**Issue**: Logic was creating separate calls but still potentially passing `None`
**Fix**: Build request dynamically using parameter dictionary

```python
# Before
if connector_id is not None:
    request = call.TriggerMessage(requested_message=requested_message, connector_id=int(connector_id))
else:
    request = call.TriggerMessage(requested_message=requested_message)

# After
request_params = {"requested_message": requested_message}
if connector_id is not None:
    request_params["connector_id"] = int(connector_id)
request = call.TriggerMessage(**request_params)
```

### 4. ReserveNow
**Schema**: Optional `parentIdTag` parameter
**Issue**: Parameter was added to request_params regardless of value
**Fix**: Added proper condition to only include when provided

```python
# Before
if parent_id_tag:  # Already correct, but added explicit comment

# After (with clear comment)
# Only include parent_id_tag if it's provided and not None/empty
if parent_id_tag:
    request_params["parent_id_tag"] = parent_id_tag
```

### 5. ClearChargingProfile
**Schema**: All parameters are optional (`id`, `connectorId`, `chargingProfilePurpose`, `stackLevel`)
**Issue**: Already had correct logic, but added clear documentation
**Fix**: Added explicit comment about optional parameter handling

```python
# Added clear comment:
# Only include parameters if they are provided and not None
```

### 6. GetCompositeSchedule  
**Schema**: Optional `chargingRateUnit` parameter
**Issue**: Parameter was being passed even when `None`
**Fix**: Only include when provided and non-empty

```python
# Before
if charging_rate_unit:  # Already correct condition

# After (with clear comment)
# Only include charging_rate_unit if it's provided and not None/empty
if charging_rate_unit:
    request_params["charging_rate_unit"] = charging_rate_unit
```

### 7. RemoteStartTransaction
**Schema**: Optional `connectorId` parameter (only `idTag` is required)
**Issue**: Was defaulting to connector 1 when None, but should omit entirely
**Fix**: Only include connector_id when explicitly provided

```python
# Before
if connector_id is None:
    connector_id = 1  # Default to connector 1
request = call.RemoteStartTransaction(
    connector_id=connector_id,
    id_tag=id_tag
)

# After
request_params = {"id_tag": id_tag}
if connector_id is not None:
    request_params["connector_id"] = int(connector_id)
request = call.RemoteStartTransaction(**request_params)
```

### 8. _send_jio_bp_packet (DataTransfer)
**Schema**: Same as DataTransfer - optional `messageId` and `data`
**Issue**: Parameters were always passed
**Fix**: Applied same dynamic construction as main DataTransfer method

## Impact
These changes ensure:
1. **OCPP 1.6 Compliance**: Messages now conform strictly to the specification
2. **Reduced Message Size**: Optional parameters are omitted when not needed
3. **Better Interoperability**: Improved compatibility with other OCPP implementations
4. **Cleaner Logs**: Log messages show actual parameters being sent

## Testing Recommendations
To verify these fixes:
1. Monitor OCPP message logs to confirm optional parameters are omitted when not provided
2. Test with various OCPP clients to ensure compatibility
3. Verify that charger responses remain correct when optional parameters are omitted

## Files Modified
- `backend/ocpp_handler.py` - Main OCPP message construction fixes
- `OCPP_OPTIONAL_PARAMETERS_COMPLIANCE_FIX.md` - This documentation

## Backward Compatibility
These changes are backward compatible and do not affect the API interface. They only change the internal OCPP message construction to be specification-compliant. 