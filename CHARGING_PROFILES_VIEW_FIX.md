# Charging Profiles View Fix

## Issue Description
Charging profiles were being set successfully but not appearing in the "View Profiles" modal. The modal would show "No charging profiles found" even after successfully setting profiles.

## Root Cause Analysis
The issue was caused by a mismatch between field naming conventions and data structure expectations:

### 1. **Field Naming Convention Mismatch**
- **API/Frontend**: Uses `snake_case` field names (`charging_profile_id`, `stack_level`, etc.)
- **Storage Code**: Was looking for `camelCase` field names (`chargingProfileId`, `stackLevel`, etc.)
- **Result**: Profiles were stored but couldn't be retrieved due to field name mismatch

### 2. **Data Structure Mismatch**
- **Storage Format**: Nested object structure: `{ "connector_1": { "1": profile_data } }`
- **Frontend Expectation**: Flat array structure: `[profile_data, profile_data]`
- **Result**: Frontend couldn't parse the nested structure returned by the API

## Solution Implemented

### 1. **Fixed Storage Field Names**
Updated `charger_store.py` to handle both naming conventions:

```python
# Before (Broken)
profile_id = charging_profile.get('chargingProfileId')

# After (Fixed)
profile_id = charging_profile.get('charging_profile_id') or charging_profile.get('chargingProfileId')
```

**Files Modified:**
- `add_charging_profile()` method: Now handles both `charging_profile_id` and `chargingProfileId`
- `clear_charging_profiles()` method: Updated to handle both naming conventions for all fields

### 2. **Fixed Frontend Data Structure Handling**
Updated `displayChargingProfiles()` function to handle nested object structure:

```javascript
// Before (Broken)
function displayChargingProfiles(profiles) {
    if (profiles.length === 0) { // Expected array, got object
        // ...
    }
}

// After (Fixed)
function displayChargingProfiles(profiles) {
    // Convert nested object to flat array
    const profilesArray = [];
    for (const connectorKey in profiles) {
        const connectorProfiles = profiles[connectorKey];
        for (const profileId in connectorProfiles) {
            profilesArray.push(connectorProfiles[profileId]);
        }
    }
    // ...
}
```

### 3. **Enhanced Field Name Compatibility**
Frontend now handles both naming conventions:

```javascript
// Handle both snake_case and camelCase field names
const profileId = profile.charging_profile_id || profile.chargingProfileId;
const stackLevel = profile.stack_level || profile.stackLevel;
const purpose = profile.charging_profile_purpose || profile.chargingProfilePurpose;
```

## Technical Implementation Details

### **Storage Structure**
Charging profiles are stored in the database as:
```json
{
  "connector_1": {
    "1": {
      "charging_profile_id": 1,
      "stack_level": 0,
      "charging_profile_purpose": "ChargePointMaxProfile",
      "charging_schedule": {
        "charging_rate_unit": "W",
        "charging_schedule_period": [
          {"start_period": 0, "limit": 3200},
          {"start_period": 3600, "limit": 1600}
        ]
      },
      "created_at": "2024-01-15T10:30:00",
      "connector_id": 1
    }
  }
}
```

### **API Response Format**
The `/api/charging_profiles/{charge_point_id}` endpoint returns:
```json
{
  "charge_point_id": "DEMO001",
  "connector_id": null,
  "charging_profiles": {
    "connector_1": {
      "1": { /* profile data */ }
    }
  }
}
```

### **Frontend Processing**
The JavaScript now:
1. Extracts profiles from nested structure
2. Converts to flat array for display
3. Handles both naming conventions
4. Shows creation timestamp and formatted data

## User Experience Improvements

### **Before Fix:**
- ❌ Profiles set successfully but not visible
- ❌ "No charging profiles found" message always shown
- ❌ No way to verify profile configuration
- ❌ Frustrating user experience

### **After Fix:**
- ✅ Profiles appear immediately after setting
- ✅ Detailed profile information displayed
- ✅ Multiple periods shown with clear formatting
- ✅ Creation timestamp for tracking
- ✅ Both connector-specific and all-connector views work

## Enhanced Profile Display

### **Profile Information Shown:**
- **Profile ID** and **Connector ID**
- **Stack Level**, **Purpose**, and **Kind**
- **Transaction ID** (if applicable)
- **Validity Period** (from/to dates in IST)
- **Charging Rate Unit** and **Duration**
- **Number of Periods** with detailed breakdown
- **Creation Timestamp**

### **Period Details:**
Each charging period displays:
- Start time (in seconds from schedule start)
- Charging limit with units (W or A)
- Number of phases (if specified)

## Testing Verification

### **Test Profile Creation and Viewing:**
1. Set a charging profile with multiple periods
2. Open "View Profiles" modal
3. Verify profile appears with correct details
4. Check that all periods are displayed properly

### **Test Different Profile Types:**
1. Set profiles with different purposes (ChargePointMaxProfile, TxProfile, etc.)
2. Set profiles on different connectors
3. Verify all profiles appear correctly
4. Test connector filtering functionality

### **Test Profile Management:**
1. Set multiple profiles
2. Clear specific profiles
3. Verify remaining profiles still display correctly
4. Test "Refresh" button functionality

## Files Modified
1. **`backend/charger_store.py`**:
   - `add_charging_profile()`: Fixed field name handling
   - `clear_charging_profiles()`: Enhanced field name compatibility

2. **`frontend/static/app.js`**:
   - `displayChargingProfiles()`: Fixed data structure handling and field name compatibility

## Benefits
- ✅ **Charging profiles now visible after setting**
- ✅ **Comprehensive profile information display**
- ✅ **Support for both naming conventions**
- ✅ **Better user experience and debugging capabilities**
- ✅ **Future-proof field name handling** 