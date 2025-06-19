# Log Storage Increase and Delete Charger Feature

## Overview
Enhanced the OCPP Server with increased log storage capacity and the ability to delete chargers and their data through the UI.

## Changes Made

### 1. Increased Log Storage Limit

**File Modified:** `backend/charger_store.py`

- **Previous:** 1000 logs per charger  
- **New:** 5000 logs per charger
- **Behavior:** Automatic rollover when limit is reached (oldest logs are deleted)

```python
# Keep only last 5000 logs (increased from 1000)
logs = logs[-5000:]
```

### 2. Delete Charger Functionality

#### Backend Changes

**File Modified:** `backend/charger_store.py`
- Added `delete_charger_completely()` method
- Removes charger from memory store and transaction tracking
- Deletes all database records including logs, settings, profiles, etc.

**File Modified:** `backend/api_routes.py`
- Added `DELETE /api/chargers/{charge_point_id}` endpoint
- Removes from active connections if connected
- Returns success/error status

#### Frontend Changes

**File Modified:** `frontend/templates/index.html`
- Added "Delete Charger" button in logs header (red button with trash icon)
- Added comprehensive confirmation modal with:
  - Warning about permanent deletion
  - List of data that will be deleted
  - Required charger ID confirmation input
  - Disabled delete button until confirmation matches

**File Modified:** `frontend/static/app.js`
- Added `showDeleteChargerModal()` function
- Added `deleteCharger()` function with multiple confirmation steps
- Real-time validation of confirmation input
- Toast notifications for success/error feedback
- Automatic UI refresh after deletion

## Features

### Log Storage
- **Capacity:** 5000 logs per charger (5x increase)
- **Rollover:** Automatic when limit reached
- **Behavior:** Oldest logs deleted first (FIFO)
- **Performance:** No impact on database performance

### Delete Charger
- **Access:** Red "Delete Charger" button in logs panel
- **Security:** Multiple confirmation steps:
  1. Must select a charger first
  2. Must type exact charger ID to confirm
  3. Final browser confirmation dialog
- **Data Deleted:**
  - All logs (up to 5000 entries)
  - Configuration settings
  - Charging profiles
  - Reservations
  - Data transfer settings
  - Connection history
  - All database records

### Safety Measures
- **Irreversible Warning:** Clear messaging that action cannot be undone
- **Input Validation:** Delete button only enabled when confirmation text matches exactly
- **Multiple Confirmations:** Modal confirmation + browser alert
- **Visual Feedback:** Toast notifications for success/error states
- **UI Updates:** Automatic refresh of charger list and log clearing

## Usage

### Viewing Enhanced Log Storage
1. Connect chargers and generate activity
2. Logs will automatically roll over after 5000 entries
3. Older logs are deleted when limit is reached

### Deleting a Charger
1. Select a charger from the charger list
2. Click the red "Delete Charger" button in the logs panel
3. Read the warning and list of data to be deleted
4. Type the exact charger ID in the confirmation field
5. Click "DELETE PERMANENTLY" (only enabled when ID matches)
6. Confirm in the browser alert dialog
7. Charger and all data will be permanently deleted

## Technical Details

### Database Impact
- Log storage uses JSON field in SQLAlchemy
- Deletion removes entire charger record (cascades to all related data)
- No orphaned data remains after deletion

### Memory Management
- Active connections removed from memory store
- Transaction tracking cleaned up
- Charger selection cleared in UI

### Error Handling
- API errors displayed via toast notifications
- Database rollback on errors
- Graceful handling of missing chargers

## Benefits

1. **Increased Capacity:** 5x more log storage for better debugging
2. **Database Cleanup:** Easy removal of test/obsolete chargers
3. **Complete Deletion:** All associated data removed (no orphaned records)
4. **Safety First:** Multiple confirmations prevent accidental deletion
5. **User Feedback:** Clear visual feedback for all operations

## Backward Compatibility

- Existing logs are preserved
- No breaking changes to API
- UI layout remains consistent
- All existing features work unchanged

## Testing

The implementation includes:
- Input validation for charger ID confirmation
- Error handling for network/database issues
- UI state management after deletion
- Toast notification system for feedback
- Automatic list refresh after changes

This enhancement provides better log management and database maintenance capabilities while maintaining the highest safety standards for destructive operations. 