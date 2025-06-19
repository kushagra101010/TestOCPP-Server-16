# Charging Schedule Multiple Periods Enhancement

## Overview
Enhanced the OCPP 1.6 Set Charging Profile functionality to support multiple charging schedule periods as per the JSON specification. Previously, the system only supported a single charging period, but OCPP 1.6 allows for multiple periods with different charging rates over time.

## OCPP 1.6 JSON Schema Compliance
According to OCPP 1.6 JSON schema, `chargingSchedulePeriod` is an **array** of objects where each period defines:

```json
{
  "chargingSchedulePeriod": [
    {
      "startPeriod": 0,        // Required: Start time in seconds
      "limit": 3200.0,         // Required: Maximum charging rate
      "numberPhases": 3        // Optional: Number of phases (1-3)
    },
    {
      "startPeriod": 1800,     // After 30 minutes
      "limit": 1600.0,         // Reduce to 1600W
      "numberPhases": 1        // Single phase
    }
  ]
}
```

## UI Enhancements

### New Features
1. **Dynamic Period Management**
   - Add Period button to create additional charging periods
   - Remove Period button for each period (hidden for single period)
   - Visual period numbering (Period 1, Period 2, etc.)

2. **Smart Period Suggestions**
   - New periods default to 1 hour after the previous period
   - Suggested power reduction for subsequent periods
   - Automatic period sorting by start time

3. **Enhanced Validation**
   - Start times must be in ascending order
   - No duplicate start times allowed
   - Period overlap prevention
   - Required field validation per period

### UI Components

#### Period Container
```html
<div class="charging-period border rounded p-3 mb-2">
  <div class="d-flex justify-content-between align-items-center mb-2">
    <h6 class="mb-0">Period 1</h6>
    <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeChargingPeriod(0)">
      <i class="bi bi-trash"></i>
    </button>
  </div>
  <div class="row">
    <!-- Start Period, Limit, Number of Phases inputs -->
  </div>
</div>
```

#### Add Period Button
```html
<button type="button" class="btn btn-sm btn-success" onclick="addChargingPeriod()">
  <i class="bi bi-plus-circle"></i> Add Period
</button>
```

## JavaScript Implementation

### Key Functions

#### `addChargingPeriod()`
- Creates new period with suggested start time
- Increments period counter
- Updates remove button visibility
- Suggests reduced power for new periods

#### `removeChargingPeriod(index)`
- Removes specified period
- Renumbers remaining periods
- Updates remove button visibility
- Prevents removal of last period

#### `updateRemoveButtons()`
- Shows/hides remove buttons based on period count
- Ensures at least one period always exists

#### Enhanced `setChargingProfile()`
- Collects all period data from UI
- Validates period sequence and values
- Sorts periods by start time
- Constructs proper OCPP JSON payload

### Validation Logic

```javascript
// Validate period values
if (isNaN(startPeriod) || isNaN(limit)) {
    alert(`Period ${i + 1}: Please enter valid start period and limit values`);
    return;
}

// Sort periods by start_period
chargingPeriods.sort((a, b) => a.start_period - b.start_period);

// Validate ascending order
for (let i = 1; i < chargingPeriods.length; i++) {
    if (chargingPeriods[i].start_period <= chargingPeriods[i-1].start_period) {
        alert(`Invalid period sequence: Period start times must be in ascending order and unique`);
        return;
    }
}
```

## Use Cases and Examples

### Example 1: Time-based Power Reduction
```json
{
  "chargingSchedulePeriod": [
    {
      "startPeriod": 0,      // Start immediately
      "limit": 3200.0        // Full power: 3.2kW
    },
    {
      "startPeriod": 1800,   // After 30 minutes  
      "limit": 1600.0        // Reduce to: 1.6kW
    },
    {
      "startPeriod": 3600,   // After 1 hour
      "limit": 800.0         // Further reduce to: 0.8kW
    }
  ]
}
```

### Example 2: Peak/Off-Peak Charging
```json
{
  "chargingSchedulePeriod": [
    {
      "startPeriod": 0,      // Night charging
      "limit": 7400.0,       // High power: 7.4kW
      "numberPhases": 3
    },
    {
      "startPeriod": 21600,  // After 6 hours (morning)
      "limit": 3700.0,       // Reduced power: 3.7kW  
      "numberPhases": 1
    }
  ]
}
```

### Example 3: Load Management
```json
{
  "chargingSchedulePeriod": [
    {
      "startPeriod": 0,      // Start with low power
      "limit": 1600.0
    },
    {
      "startPeriod": 7200,   // After 2 hours, increase
      "limit": 3200.0        
    },
    {
      "startPeriod": 14400,  // After 4 hours, back to low
      "limit": 1600.0
    }
  ]
}
```

## Technical Benefits

1. **OCPP 1.6 Compliance**: Full support for multiple periods as per specification
2. **Flexible Charging Management**: Support for complex charging scenarios
3. **Load Balancing**: Enable dynamic power management over time
4. **Peak Shaving**: Reduce power during peak hours
5. **Battery Protection**: Implement taper charging profiles

## User Experience Improvements

1. **Intuitive Interface**: Visual period management with clear numbering
2. **Smart Defaults**: Suggested values for new periods
3. **Real-time Validation**: Immediate feedback on period conflicts
4. **Helpful Examples**: Built-in examples in the UI
5. **Clear Documentation**: Comprehensive help text and tooltips

## Files Modified

1. **`frontend/templates/index.html`**
   - Replaced single limit input with dynamic periods section
   - Added period management buttons and examples

2. **`frontend/static/app.js`**
   - Enhanced `setChargingProfile()` function for multiple periods
   - Added `addChargingPeriod()`, `removeChargingPeriod()`, `updateRemoveButtons()`
   - Improved modal initialization with period reset

3. **`CHARGING_SCHEDULE_MULTIPLE_PERIODS_ENHANCEMENT.md`**
   - This documentation file

## Backward Compatibility

The enhancement is fully backward compatible:
- Single period profiles work exactly as before
- API interface remains unchanged
- OCPP message structure follows specification
- Existing profiles continue to function

## Testing Scenarios

1. **Single Period**: Verify basic functionality still works
2. **Multiple Periods**: Test adding/removing periods
3. **Validation**: Test period sequence validation
4. **OCPP Compliance**: Verify JSON payload matches specification
5. **UI Responsiveness**: Test period management interactions

This enhancement significantly improves the flexibility and OCPP compliance of the charging profile management system while maintaining ease of use. 