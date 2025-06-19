# MSIL Data Transfer - Disabled by Default

## Change Summary

MSIL Data Transfer functionality has been **disabled by default** in the UI configuration.

## What Changed

### 1. Configuration File (`config.ini`)
```ini
[UI_FEATURES]
show_jio_bp_data_transfer = true
show_msil_data_transfer = false  # ← Now disabled by default
show_cz_data_transfer = true
```

### 2. Backend Default Configuration (`backend/config.py`)
- Updated default configuration to set MSIL as `false`
- Ensures new installations have MSIL disabled by default

### 3. Documentation Updated
- Updated `UI_CONFIGURATION_FEATURE.md` to reflect new defaults
- Examples now show MSIL as disabled

## Current UI Behavior

### ✅ Enabled by Default:
- **Jio_BP Data Transfer** - Shows in dashboard
- **CZ Data Transfer** - Shows in dashboard

### ❌ Disabled by Default:
- **MSIL Data Transfer** - Hidden from dashboard

## How to Enable MSIL

### Method 1: Configuration File
Edit `config.ini`:
```ini
[UI_FEATURES]
show_msil_data_transfer = true
```
Then restart the server.

### Method 2: Web Interface
1. Open http://localhost:8000
2. Go to "Configuration" tab
3. Toggle "MSIL Data Transfer" switch to ON
4. Click "Save Configuration"
5. Refresh the page

## Why This Change?

- **MSIL sends OCPP violation packets** (object data instead of string)
- **Reduces UI complexity** for most users who don't need MSIL
- **Safer default configuration** - users must explicitly enable non-standard features
- **Cleaner dashboard** with only standard OCPP-compliant features visible by default

## Impact

- **Existing configurations**: No change if already configured
- **New installations**: MSIL will be hidden by default
- **User control**: Can still be enabled via configuration or UI
- **Functionality**: MSIL code remains fully functional when enabled

The server has been restarted with the new configuration and MSIL Data Transfer is now disabled by default. 