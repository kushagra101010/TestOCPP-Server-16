# UI Configuration Feature

## Overview

A new configuration system has been implemented that allows you to control which data transfer functions are shown in the UI through the `config.ini` file. This gives you fine-grained control over which features are visible to users without code changes.

## Features

### 1. Configuration File Control

The `config.ini` file now includes a new `[UI_FEATURES]` section:

```ini
[UI_FEATURES]
# UI Feature toggles - controls which data transfer functions are shown
show_jio_bp_data_transfer = true
show_msil_data_transfer = false
show_cz_data_transfer = true
```

### 2. Web UI Configuration Tab

A new "Configuration" tab has been added to the web interface that allows you to:

- View current configuration settings
- Toggle data transfer functions on/off
- Save changes to the config.ini file
- Real-time preview of settings

### 3. API Endpoints

Two new API endpoints have been added:

- `GET /api/config/ui-features` - Get current UI feature configuration
- `POST /api/config/ui-features` - Update UI feature configuration

## Files Modified

### Backend Changes

1. **`backend/config.py`** (New file)
   - Configuration management module
   - Handles reading and writing config.ini
   - Provides type-safe configuration access

2. **`backend/main.py`**
   - Updated to import and use the configuration module
   - Passes UI features to the frontend template
   - Uses configuration for server settings

3. **`backend/api_routes.py`**
   - Added UI configuration endpoints
   - Handles getting and updating UI features

4. **`config.ini`**
   - Added `[UI_FEATURES]` section
   - Configuration options for each data transfer function

### Frontend Changes

1. **`frontend/templates/index.html`**
   - Added "Configuration" tab
   - Conditional rendering of data transfer sections based on config
   - UI for managing configuration settings

2. **`frontend/static/app.js`**
   - Added JavaScript functions for configuration management
   - Toast notifications for user feedback
   - API calls to backend configuration endpoints

## How to Use

### 1. Configuration File Method

Edit the `config.ini` file directly:

```ini
[UI_FEATURES]
show_jio_bp_data_transfer = true   # Show Jio_BP Data Transfer
show_msil_data_transfer = false    # Hide MSIL Data Transfer (disabled by default)
show_cz_data_transfer = true       # Show CZ Data Transfer
```

Restart the server to apply changes.

### 2. Web UI Method

1. Open the OCPP CMS web interface
2. Click on the "Configuration" tab
3. Use the toggle switches to enable/disable features
4. Click "Save Configuration"
5. Refresh the page to see changes

## Technical Implementation

### Configuration Flow

1. **Server Startup**: Configuration is loaded from `config.ini`
2. **Template Rendering**: UI features are passed to the Jinja2 template
3. **Conditional Rendering**: Sections are shown/hidden based on configuration
4. **Runtime Changes**: Configuration can be updated via API and saved to file

### Template Logic

The frontend uses Jinja2 conditional rendering:

```html
{% if ui_features.get('show_msil_data_transfer', True) %}
<div class="card mt-3">
    <!-- MSIL Data Transfer Section -->
</div>
{% endif %}
```

### Default Behavior

- If a configuration option is missing, it defaults to `True` (feature enabled)
- If the `[UI_FEATURES]` section doesn't exist, all features are enabled
- Configuration is validated and type-checked

## Benefits

1. **Flexibility**: Control UI features without code changes
2. **Deployment**: Different configurations for different environments
3. **User Experience**: Hide unused features to reduce UI complexity
4. **Maintenance**: Easy to enable/disable features based on requirements

## Testing

The server is currently running on port 8000. You can test the feature by:

1. Opening http://localhost:8000 in your browser
2. Going to the "Configuration" tab
3. Toggling the data transfer features on/off
4. Saving and refreshing to see the changes

## Future Enhancements

This configuration system can be extended to control other UI features:

- Advanced functions visibility
- Feature-specific settings
- User role-based feature access
- Dynamic feature loading

## Example Use Cases

1. **Customer-Specific Deployments**: Show only relevant data transfer functions
2. **Testing Environments**: Enable specific features for testing
3. **Phased Rollouts**: Gradually enable features in production
4. **Maintenance Mode**: Temporarily disable certain features 