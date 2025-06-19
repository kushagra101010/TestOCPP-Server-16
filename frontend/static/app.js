// Global variables
let selectedChargerId = null;
let logPollingInterval = null;
let autoScrollEnabled = true;
let currentLogs = []; // Store current logs for CSV download
const POLLING_INTERVAL = 2000; // 2 seconds

// Store packets data for easy access
let packetsData = [];

// Utility function to format UTC time to IST
function formatToIST(utcTimeString) {
    try {
        // Parse the UTC time string
        const utcDate = new Date(utcTimeString);
        
        // Convert to IST (UTC+5:30)
        const istDate = new Date(utcDate.getTime() + (5.5 * 60 * 60 * 1000));
        
        // Format as readable string
        const options = {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        };
        
        return istDate.toLocaleString('en-IN', options) + ' IST';
    } catch (error) {
        console.error('Error formatting time to IST:', error);
        return utcTimeString; // Fallback to original string
    }
}

// Store configuration data from Get Configuration response
let configurationData = null;

// Bootstrap modal instances
const modals = {
    remoteStart: new bootstrap.Modal(document.getElementById('remoteStartModal')),
    remoteStop: new bootstrap.Modal(document.getElementById('remoteStopModal')),
    getConfig: new bootstrap.Modal(document.getElementById('getConfigModal')),
    changeConfig: new bootstrap.Modal(document.getElementById('changeConfigModal')),
    sendLocalList: new bootstrap.Modal(document.getElementById('sendLocalListModal')),
    dataTransfer: new bootstrap.Modal(document.getElementById('dataTransferModal')),
    dataTransferPackets: new bootstrap.Modal(document.getElementById('dataTransferPacketsModal')),
    triggerMessage: new bootstrap.Modal(document.getElementById('triggerMessageModal')),
    rawMessage: new bootstrap.Modal(document.getElementById('rawMessageModal')),
    // Advanced function modals
    changeAvailability: new bootstrap.Modal(document.getElementById('changeAvailabilityModal')),
    reserveNow: new bootstrap.Modal(document.getElementById('reserveNowModal')),
    cancelReservation: new bootstrap.Modal(document.getElementById('cancelReservationModal')),
    reservations: new bootstrap.Modal(document.getElementById('reservationsModal')),
    setChargingProfile: new bootstrap.Modal(document.getElementById('setChargingProfileModal')),
    clearChargingProfile: new bootstrap.Modal(document.getElementById('clearChargingProfileModal')),
    chargingProfiles: new bootstrap.Modal(document.getElementById('chargingProfilesModal')),
    getCompositeSchedule: new bootstrap.Modal(document.getElementById('getCompositeScheduleModal')),
    jioBpSettings: new bootstrap.Modal(document.getElementById('jioBpSettingsModal')),
    msilSettings: new bootstrap.Modal(document.getElementById('msilSettingsModal')),
    czSettings: new bootstrap.Modal(document.getElementById('czSettingsModal')),
};

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    // Start polling for chargers
    pollChargers();
    setInterval(pollChargers, POLLING_INTERVAL);

    // Load ID tags
    loadIdTags();

    // Load data transfer packets
    loadDataTransferPackets();

    // Initialize the multi-select filter system
    initializeLogFilters();
});

// Initialize the multi-select filter system
function initializeLogFilters() {
    console.log('Initializing log filters'); // Debug log
    
    // Set "Show All" as default
    const showAllCheckbox = document.getElementById('filter_all');
    if (showAllCheckbox) {
        showAllCheckbox.checked = true;
        console.log('Show All checkbox initialized as checked'); // Debug log
    } else {
        console.error('Show All checkbox not found!'); // Debug log
    }
    
    // Ensure all other checkboxes are unchecked
    const otherCheckboxes = document.querySelectorAll('#logMessageFilterDropdown input[type="checkbox"]:not(#filter_all)');
    otherCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    console.log('All other checkboxes unchecked'); // Debug log
    
    updateFilterButtonText();
    
    // Prevent dropdown from closing when clicking inside
    const dropdown = document.querySelector('#logMessageFilterDropdown + .dropdown-menu');
    if (dropdown) {
        dropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });
        console.log('Dropdown click prevention added'); // Debug log
    } else {
        console.error('Dropdown menu not found!'); // Debug log
    }
}

// Charger selection
// Charger selection is now handled directly in updateChargerList click events

// Poll for connected chargers
async function pollChargers() {
    try {
        const response = await fetch('/api/chargers');
        const data = await response.json();
        updateChargerList(data.chargers);
    } catch (error) {
        console.error('Error polling chargers:', error);
        console.error('Error details:', error.message);
        console.error('Current URL:', window.location.href);
    }
}

// Global variables for charger management

// Global variable for hide disconnected state
let hideDisconnectedChargers = true;

// Toggle hide disconnected chargers functionality
function toggleHideDisconnected() {
    hideDisconnectedChargers = document.getElementById('hideDisconnectedChargers').checked;
    // Trigger a refresh of the charger list with current data
    pollChargers();
}

// Update charger list in UI
function updateChargerList(chargers) {
    const list = document.getElementById('chargerList');
    
    if (!list) {
        console.error('Charger list element not found');
        return;
    }
    
    list.innerHTML = '';

    // Filter chargers based on hide disconnected setting
    let filteredChargers = chargers;
    if (hideDisconnectedChargers) {
        filteredChargers = chargers.filter(charger => charger.connected);
    }

    // Sort chargers: connected first, then disconnected
    // Within each group, sort by ID for consistency
    const sortedChargers = filteredChargers.sort((a, b) => {
        // First sort by connection status (connected first)
        if (a.connected !== b.connected) {
            return b.connected - a.connected; // true (1) comes before false (0)
        }
        // Then sort by ID alphabetically
        return a.id.localeCompare(b.id);
    });

    // Add status info about filtering
    if (hideDisconnectedChargers && chargers.length > filteredChargers.length) {
        const hiddenCount = chargers.length - filteredChargers.length;
        const statusInfo = document.createElement('div');
        statusInfo.className = 'alert alert-info py-2 mb-2';
        statusInfo.innerHTML = `
            <small>
                <i class="bi bi-eye-slash"></i> 
                Showing ${filteredChargers.length} connected chargers 
                (${hiddenCount} disconnected hidden)
                <button class="btn btn-sm btn-outline-primary ms-2" onclick="document.getElementById('hideDisconnectedChargers').checked = false; toggleHideDisconnected();">
                    <i class="bi bi-eye"></i> Show All
                </button>
            </small>
        `;
        list.appendChild(statusInfo);
    }

    // Show filtered chargers in the list
    sortedChargers.forEach(charger => {
        const item = document.createElement('div');
        item.className = `list-group-item list-group-item-action ${charger.id === selectedChargerId ? 'active' : ''}`;
        item.style.cursor = 'pointer';
        
        // Use the main charger status (from StatusNotification) - this is the primary status
        let statusDisplay = charger.status || 'Unknown';
        let statusClass = charger.connected ? 'bg-success' : 'bg-danger';
        
        // Check if charger is in a charging state based on the main status
        const isCharging = statusDisplay && ['charging', 'preparing'].includes(statusDisplay.toLowerCase());
        const chargingIndicator = isCharging ? '<i class="bi bi-lightning-charge-fill text-warning"></i> ' : '';
        const transactionInfo = isCharging ? '<br><small class="text-warning"><i class="bi bi-info-circle"></i> Active transaction</small>' : '';
        
        // Enhanced connection status indicators
        let connectionIcon, connectionBadge, connectionClass;
        
        if (charger.websocket_connected) {
            // Actively connected via WebSocket
            connectionIcon = '<i class="bi bi-wifi text-success"></i> ';
            connectionBadge = 'Connected';
            connectionClass = 'bg-success';
        } else if (charger.recently_active) {
            // Recently active but no WebSocket
            connectionIcon = '<i class="bi bi-wifi-1 text-warning"></i> ';
            connectionBadge = 'Recently Active';
            connectionClass = 'bg-warning text-dark';
        } else {
            // Disconnected
            connectionIcon = '<i class="bi bi-wifi-off text-danger"></i> ';
            connectionBadge = 'Disconnected';
            connectionClass = 'bg-danger';
        }
        
        // Add tooltip for connection status
        const connectionTooltip = charger.websocket_connected 
            ? 'Active WebSocket connection - can send commands' 
            : charger.recently_active 
                ? 'Recently active but no WebSocket - cannot send commands' 
                : 'Not connected';
        
        item.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">${connectionIcon}${chargingIndicator}${charger.id}</h6>
                    <small class="text-muted">Status: ${statusDisplay}</small>
                    <br>
                    <small class="text-muted">Last seen: ${charger.last_seen ? formatToIST(charger.last_seen) : 'Never'}</small>
                    ${transactionInfo}
                </div>
                <span class="badge ${connectionClass}" title="${connectionTooltip}">
                    ${connectionBadge}
                </span>
            </div>
        `;
        
        // Allow clicking on any charger to select it
        item.addEventListener('click', async (e) => {
            e.preventDefault();
            
            // Remove active class from all items
            document.querySelectorAll('#chargerList .list-group-item').forEach(el => {
                el.classList.remove('active');
            });
            
            // Add active class to clicked item
            item.classList.add('active');
            
            // Set selected charger
            selectedChargerId = charger.id;
            
            // Don't clear logs on charger selection - preserve logs across browser reloads
            // Only clear logs manually or when server restarts
            
            // Start polling logs for selected charger
            if (logPollingInterval) {
                clearInterval(logPollingInterval);
            }
            await loadLogs();
            logPollingInterval = setInterval(loadLogs, POLLING_INTERVAL);
            
            console.log(`Selected charger: ${selectedChargerId}`);
        });
        
        list.appendChild(item);
    });
}

// Load and display logs
async function loadLogs() {
    if (!selectedChargerId) return;

    try {
        const response = await fetch(`/api/logs/${selectedChargerId}`);
        const logs = await response.json();
        displayLogs(logs);
    } catch (error) {
        console.error('Error loading logs:', error);
        console.error('Error details:', error.message);
        console.error('Current URL:', window.location.href);
    }
}

// Display logs in UI
function displayLogs(logs) {
    const container = document.getElementById('logContainer');
    
    // Save current scroll position before updating logs
    const savedScrollTop = container.scrollTop;
    const savedScrollHeight = container.scrollHeight;
    const wasAtBottom = (savedScrollTop + container.clientHeight) >= (savedScrollHeight - 10); // 10px tolerance
    
    container.innerHTML = '';
    
    // Store logs for CSV download and filtering
    currentLogs = logs;
    allLogs = logs; // Store unfiltered logs

    // Apply current filters
    const filteredLogs = applyLogFiltersToLogs(logs);

    filteredLogs.forEach(log => {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        // Add data attributes for filtering
        entry.setAttribute('data-message', log.message.toLowerCase());
        entry.setAttribute('data-ocpp-type', extractOCPPMessageType(log.message));
        
        // Format timestamp to show both IST and UTC
        // The server timestamp is in UTC format, ensure it's parsed as UTC
        let timestamp;
        if (log.timestamp.includes('T')) {
            // ISO format: 2025-06-13T21:10:26.777787 (this is UTC time from server)
            // Force it to be interpreted as UTC by adding 'Z' if not present
            const utcTimestamp = log.timestamp.includes('Z') ? log.timestamp : log.timestamp + 'Z';
            timestamp = new Date(utcTimestamp);
        } else {
            // Fallback for other formats
            timestamp = new Date(log.timestamp + 'Z');
        }
        
        // Format IST time (UTC + 5:30) - this will correctly convert from UTC to IST
        const istTime = timestamp.toLocaleString('en-IN', { 
            timeZone: 'Asia/Kolkata',
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        });
        
        // Format UTC time - this will show the original UTC time
        const utcTime = timestamp.toLocaleString('en-GB', { 
            timeZone: 'UTC',
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        
        entry.innerHTML = `
            <div class="log-timestamp">
                <small class="text-muted">IST: ${istTime} | UTC: ${utcTime}</small>
            </div>
            <div class="log-message">${log.message}</div>
        `;
        container.appendChild(entry);
    });

    // Show filter status
    updateFilterStatus(logs.length, filteredLogs.length);

    // Auto-scroll to bottom if enabled
    if (autoScrollEnabled) {
        container.scrollTop = container.scrollHeight;
    }
}

// Global variables for log filtering
let allLogs = [];

// Extract OCPP message type from log message
function extractOCPPMessageType(message) {
    // Check for OCPP message patterns in the log message (including responses)
    const ocppPatterns = [
        // Charger to Server (Requests) and their responses
        /BootNotification/i,
        /StatusNotification/i,
        /Heartbeat/i,
        /Authorize/i,
        /StartTransaction/i,
        /StopTransaction/i,
        /MeterValues/i,
        /DataTransfer/i,
        /FirmwareStatusNotification/i,
        /DiagnosticsStatusNotification/i,
        // Server to Charger (Commands) and their responses
        /RemoteStartTransaction/i,
        /RemoteStopTransaction/i,
        /GetConfiguration/i,
        /ChangeConfiguration/i,
        /ClearCache/i,
        /Reset/i,
        /SendLocalList/i,
        /ClearLocalList/i,
        /GetLocalListVersion/i,
        /TriggerMessage/i,
        /ChangeAvailability/i,
        /ReserveNow/i,
        /CancelReservation/i,
        /SetChargingProfile/i,
        /ClearChargingProfile/i,
        /GetCompositeSchedule/i,
        /UpdateFirmware/i,
        /GetDiagnostics/i,
        /UnlockConnector/i
    ];

    for (const pattern of ocppPatterns) {
        const match = message.match(pattern);
        if (match) {
            // Return the base message type (keep as-is, don't strip Response)
            return match[0];
        }
    }

    // Check for system message types
    if (message.toLowerCase().includes('connected') || message.toLowerCase().includes('disconnected')) {
        return 'connection';
    }
    if (message.toLowerCase().includes('error') || message.toLowerCase().includes('failed')) {
        return 'error';
    }

    return 'other';
}

// Check if a message is a connection event (HTTP handshake requests/responses)
function isConnectionEvent(message) {
    const connectionPatterns = [
        // WebSocket connection events
        /connected/i,
        /disconnected/i,
        /connection/i,
        // HTTP handshake patterns
        /handshake/i,
        /websocket.*upgrade/i,
        /http.*upgrade/i,
        /101.*switching.*protocols/i,
        // Connection establishment patterns
        /establishing.*connection/i,
        /connection.*established/i,
        /connection.*closed/i,
        /connection.*failed/i,
        /connection.*lost/i,
        /connection.*timeout/i,
        // WebSocket specific patterns
        /websocket.*connected/i,
        /websocket.*disconnected/i,
        /websocket.*error/i,
        /websocket.*close/i,
        /websocket.*open/i
    ];
    
    return connectionPatterns.some(pattern => pattern.test(message));
}

// Check if a message is an error message
function isErrorMessage(message) {
    const errorPatterns = [
        // General error patterns
        /error/i,
        /failed/i,
        /failure/i,
        /exception/i,
        /timeout/i,
        /refused/i,
        /rejected/i,
        /invalid/i,
        /unauthorized/i,
        /forbidden/i,
        /not.*found/i,
        /bad.*request/i,
        /internal.*server.*error/i,
        // OCPP specific error patterns
        /callerror/i,
        /ocpp.*error/i,
        /protocol.*error/i,
        /format.*error/i,
        /security.*error/i,
        /property.*constraint.*violation/i,
        /occurrence.*constraint.*violation/i,
        /type.*constraint.*violation/i,
        /generic.*error/i,
        // Connection error patterns
        /connection.*error/i,
        /connection.*failed/i,
        /handshake.*failed/i,
        /websocket.*error/i,
        // Transaction error patterns
        /transaction.*error/i,
        /transaction.*failed/i,
        /start.*transaction.*failed/i,
        /stop.*transaction.*failed/i,
        // Authentication error patterns
        /authentication.*failed/i,
        /authorization.*failed/i,
        /invalid.*id.*tag/i,
        /expired.*id.*tag/i,
        /blocked.*id.*tag/i
    ];
    
    return errorPatterns.some(pattern => pattern.test(message));
}

// Extract OCPP message ID from WebSocket frame
function extractOCPPMessageId(message) {
    try {
        // Look for WebSocket frame content
        const jsonMatch = message.match(/Frame:\s*(\[.*\])/s);
        if (jsonMatch) {
            const jsonStr = jsonMatch[1];
            const ocppMessage = JSON.parse(jsonStr);
            
            if (Array.isArray(ocppMessage) && ocppMessage.length >= 2) {
                // OCPP message format: [messageType, messageId, ...]
                // messageType: 2=CALL, 3=CALLRESULT, 4=CALLERROR
                const messageId = ocppMessage[1];
                return messageId;
            }
        }
    } catch (e) {
        // If parsing fails, return null
    }
    return null;
}

// Extract OCPP action/command from WebSocket frame
function extractOCPPAction(message) {
    try {
        // Look for WebSocket frame content
        const jsonMatch = message.match(/Frame:\s*(\[.*\])/s);
        if (jsonMatch) {
            const jsonStr = jsonMatch[1];
            const ocppMessage = JSON.parse(jsonStr);
            
            if (Array.isArray(ocppMessage)) {
                const messageType = ocppMessage[0]; // 2=CALL, 3=CALLRESULT, 4=CALLERROR
                
                if (messageType === 2 && ocppMessage.length >= 3) {
                    // This is a CALL (request) message
                    return ocppMessage[2]; // action name
                }
            }
        }
    } catch (e) {
        // If parsing fails, return null
    }
    return null;
}

// Get message type from OCPP message (2=CALL, 3=CALLRESULT, 4=CALLERROR)
function getOCPPMessageType(message) {
    try {
        const jsonMatch = message.match(/Frame:\s*(\[.*\])/s);
        if (jsonMatch) {
            const jsonStr = jsonMatch[1];
            const ocppMessage = JSON.parse(jsonStr);
            
            if (Array.isArray(ocppMessage) && ocppMessage.length >= 1) {
                return ocppMessage[0]; // messageType
            }
        }
    } catch (e) {
        // If parsing fails, return null
    }
    return null;
}

// Check if a message is a response to an OCPP message
function isResponseMessage(message) {
    // Check if message contains response indicators
    return /Response/i.test(message) || 
           message.toLowerCase().includes('response') ||
           message.includes('CMS→Charger') ||
           message.includes('Server→Charger');
}

// Get the base message type without Response suffix for filtering purposes
function getBaseMessageType(message) {
    const messageType = extractOCPPMessageType(message);
    return messageType.replace(/Response$/i, '');
}

// Check if a response payload matches the expected message type
function matchesResponsePayload(payload, messageFilter, isError = false) {
    if (isError) {
        // CALLERROR messages - these are always related if we got here via message ID correlation
        return true;
    }
    
    if (!payload || typeof payload !== 'object') {
        return false;
    }
    
    const filterLower = messageFilter.toLowerCase();
    
    // Analyze payload to determine what request type this is a response to
    switch (filterLower) {
        case 'bootnotification':
            return payload.hasOwnProperty('currentTime') && 
                   payload.hasOwnProperty('interval') && 
                   payload.hasOwnProperty('status');
        
        case 'heartbeat':
            return payload.hasOwnProperty('currentTime') && 
                   Object.keys(payload).length === 1;
        
        case 'authorize':
            return payload.hasOwnProperty('idTagInfo') && 
                   !payload.hasOwnProperty('transactionId');
        
        case 'starttransaction':
            return payload.hasOwnProperty('transactionId') && 
                   payload.hasOwnProperty('idTagInfo');
        
        case 'stoptransaction':
            return payload.hasOwnProperty('idTagInfo') && 
                   !payload.hasOwnProperty('transactionId');
        
        case 'statusnotification':
        case 'metervalues':
        case 'datatransfer':
        case 'firmwarestatusnotification':
        case 'diagnosticsstatusnotification':
            // These typically have empty responses
            return Object.keys(payload).length === 0;
        
        case 'getconfiguration':
            return payload.hasOwnProperty('configurationKey') || 
                   payload.hasOwnProperty('unknownKey');
        
        case 'changeconfiguration':
        case 'clearcache':
        case 'reset':
        case 'triggermessage':
        case 'changeavailability':
        case 'reservenow':
        case 'cancelreservation':
        case 'setchargingprofile':
        case 'clearchargingprofile':
        case 'updatefirmware':
        case 'getdiagnostics':
        case 'unlockconnector':
        case 'remotestarttransaction':
        case 'remotestoptransaction':
            return payload.hasOwnProperty('status');
        
        case 'sendlocallist':
            return payload.hasOwnProperty('status');
        
        case 'getlocallistversion':
            return payload.hasOwnProperty('listVersion');
        
        case 'getcompositeschedule':
            return payload.hasOwnProperty('status') && 
                   (payload.hasOwnProperty('connectorId') || payload.hasOwnProperty('scheduleStart'));
        
        default:
            // For unknown message types, be permissive if we got here via message ID correlation
            return true;
    }
}

// Check if a log message matches the selected filter
function matchesMessageFilter(log, messageFilter) {
    const message = log.message;
    const messageText = message.toLowerCase();
    const filterText = messageFilter.toLowerCase();
    
    // Special filter types
    if (messageFilter === 'connection') {
        return isConnectionEvent(message);
    }
    if (messageFilter === 'error') {
        return isErrorMessage(message);
    }
    if (messageFilter === 'charger-to-server' || messageFilter === 'server-to-charger') {
        return getMessageDirection(message) === messageFilter;
    }
    
    // OCPP message filtering - match both command and response
    // 1. Direct message type matches (e.g., "StatusNotification: connector=1")
    if (messageText.startsWith(filterText + ':') || 
        messageText.startsWith(filterText + ' ')) {
        return true;
    }
    
    // 2. Response messages (e.g., "StatusNotification received", "StartTransaction response")
    // Be more strict: ensure it's an exact word match, not a substring
    const filterRegex = new RegExp('\\b' + filterText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'i');
    if (filterRegex.test(messageText) && 
        (messageText.includes('received') || messageText.includes('response'))) {
        return true;
    }
    
    // 3. WebSocket frame analysis
    if (message.includes('WebSocket') && message.includes('Frame:')) {
        try {
            const jsonMatch = message.match(/Frame:\s*(\[.*\])/s);
            if (jsonMatch) {
                const jsonStr = jsonMatch[1];
                const ocppMessage = JSON.parse(jsonStr);
                
                if (Array.isArray(ocppMessage) && ocppMessage.length >= 3) {
                    const messageType = ocppMessage[0]; // 2=CALL, 3=CALLRESULT, 4=CALLERROR
                    
                    if (messageType === 2) {
                        // CALL (request) message
                        const action = ocppMessage[2];
                        return action && action.toLowerCase() === filterText;
                    } else if (messageType === 3 || messageType === 4) {
                        // CALLRESULT/CALLERROR - check if this is a response we should include
                        // This function is called during correlation, so we need to validate
                        // that this response matches the expected message type
                        return matchesResponsePayload(ocppMessage[2], filterText, messageType === 4);
                    }
                }
            }
        } catch (e) {
            // JSON parsing failed, continue with text matching
        }
    }
    
    // 4. Extract OCPP action and match
    const extractedAction = extractOCPPAction(message);
    if (extractedAction && extractedAction.toLowerCase() === filterText) {
        return true;
    }
    
    return false;
}

// Determine message direction (charger-to-server or server-to-charger)
function getMessageDirection(message) {
    // Charger to Server messages (requests from charger)
    const chargerToServerMessages = [
        'BootNotification', 'StatusNotification', 'Heartbeat', 'Authorize',
        'StartTransaction', 'StopTransaction', 'MeterValues', 'DataTransfer',
        'FirmwareStatusNotification', 'DiagnosticsStatusNotification'
    ];
    
    // Server to Charger messages (commands from server)
    const serverToChargerMessages = [
        'RemoteStartTransaction', 'RemoteStopTransaction', 'GetConfiguration',
        'ChangeConfiguration', 'ClearCache', 'Reset', 'SendLocalList',
        'ClearLocalList', 'GetLocalListVersion', 'TriggerMessage',
        'ChangeAvailability', 'ReserveNow', 'CancelReservation',
        'SetChargingProfile', 'ClearChargingProfile', 'GetCompositeSchedule',
        'UpdateFirmware', 'GetDiagnostics', 'UnlockConnector'
    ];

    // Check if message contains "Charger→CMS" or "CMS→Charger" frame indicators
    if (message.includes('Charger→CMS') || message.includes('Charger→Server')) {
        return 'charger-to-server';
    }
    if (message.includes('CMS→Charger') || message.includes('Server→Charger')) {
        return 'server-to-charger';
    }

    // Check by message type
    const messageType = extractOCPPMessageType(message);
    
    if (chargerToServerMessages.some(msg => msg.toLowerCase() === messageType.toLowerCase())) {
        return 'charger-to-server';
    }
    if (serverToChargerMessages.some(msg => msg.toLowerCase() === messageType.toLowerCase())) {
        return 'server-to-charger';
    }

    return 'unknown';
}

// Get selected message filters (multiple selection support)
function getSelectedMessageFilters() {
    console.log('🔍 Getting selected filters...'); // Debug log
    
    // Try multiple selectors to find the checked checkboxes
    const dropdownContainer = document.getElementById('logMessageFilterDropdown');
    if (!dropdownContainer) {
        console.error('❌ Dropdown container not found!');
        return [];
    }
    
    // Check all possible selectors
    const selectors = [
        '#logMessageFilterDropdown input[type="checkbox"]:checked',
        '.dropdown-menu input[type="checkbox"]:checked',
        'input[type="checkbox"]:checked'
    ];
    
    let checkboxes = null;
    let workingSelector = null;
    
    for (const selector of selectors) {
        checkboxes = document.querySelectorAll(selector);
        if (checkboxes.length > 0) {
            workingSelector = selector;
            console.log(`✅ Found ${checkboxes.length} checked checkboxes with selector: ${selector}`);
            break;
        }
    }
    
    if (!checkboxes || checkboxes.length === 0) {
        console.log('⚠️ No checked checkboxes found with any selector');
        
        // Debug: Show all checkboxes and their states
        const allCheckboxes = document.querySelectorAll('input[type="checkbox"]');
        console.log(`📋 Total checkboxes found: ${allCheckboxes.length}`);
        allCheckboxes.forEach((cb, index) => {
            console.log(`  ${index}: id="${cb.id}", value="${cb.value}", checked=${cb.checked}`);
        });
        
        return [];
    }
    
    const selectedFilters = [];
    
    checkboxes.forEach((checkbox, index) => {
        console.log(`📋 Checkbox ${index}: id="${checkbox.id}", value="${checkbox.value}", checked=${checkbox.checked}`);
        if (checkbox.value !== 'all') {
            selectedFilters.push(checkbox.value);
            console.log(`  ➕ Added filter: ${checkbox.value}`);
        } else {
            console.log(`  ⏭️ Skipped "Show All" checkbox`);
        }
    });
    
    console.log(`🎯 Final selected filters:`, selectedFilters);
    return selectedFilters;
}

// Update filter button text based on selected filters
function updateFilterButtonText() {
    const selectedFilters = getSelectedMessageFilters();
    const buttonText = document.getElementById('filterButtonText');
    const showAllCheckbox = document.getElementById('filter_all');
    
    if (showAllCheckbox.checked || selectedFilters.length === 0) {
        buttonText.textContent = 'Show All Messages';
    } else if (selectedFilters.length === 1) {
        buttonText.textContent = selectedFilters[0] + ' + Response';
    } else if (selectedFilters.length <= 3) {
        buttonText.textContent = selectedFilters.join(', ') + ' (+ Responses)';
    } else {
        buttonText.textContent = `${selectedFilters.length} Message Types Selected`;
    }
}

// Handle "Show All" filter checkbox
function handleShowAllFilter(checkbox) {
    if (checkbox.checked) {
        // Uncheck all other filters when "Show All" is selected
        console.log('Show All selected - clearing all other filters'); // Debug log
        const otherCheckboxes = document.querySelectorAll('#logMessageFilterDropdown input[type="checkbox"]:not(#filter_all)');
        otherCheckboxes.forEach(cb => {
            cb.checked = false;
            console.log('Unchecked filter:', cb.value); // Debug log
        });
    } else {
        // If "Show All" is unchecked and no other filters are selected, check it back
        const selectedFilters = getSelectedMessageFilters();
        if (selectedFilters.length === 0) {
            console.log('No filters selected - re-checking Show All'); // Debug log
            checkbox.checked = true;
        }
    }
    updateFilterButtonText();
    applyLogFilter();
}

// Handle individual message filter updates
function updateMessageFilter() {
    // If any specific filter is selected, uncheck "Show All"
    const showAllCheckbox = document.getElementById('filter_all');
    const selectedFilters = getSelectedMessageFilters();
    
    console.log('updateMessageFilter called, selected filters:', selectedFilters); // Debug log
    
    if (selectedFilters.length > 0) {
        console.log('Unchecking Show All because specific filters are selected'); // Debug log
        showAllCheckbox.checked = false;
    } else {
        console.log('No specific filters selected, checking Show All'); // Debug log
        showAllCheckbox.checked = true;
    }
    
    updateFilterButtonText();
    applyLogFilter();
}

// Select all filters - shows all messages (same as "Show All")
function selectAllFilters() {
    console.log('selectAllFilters called'); // Debug log
    
    // Try multiple selectors to find all specific filter checkboxes
    const selectors = [
        '#logMessageFilterDropdown input[type="checkbox"]:not(#filter_all)',
        '.dropdown-menu input[type="checkbox"]:not(#filter_all)',
        'input[type="checkbox"]:not(#filter_all)'
    ];
    
    let specificCheckboxes = null;
    let workingSelector = null;
    
    for (const selector of selectors) {
        specificCheckboxes = document.querySelectorAll(selector);
        if (specificCheckboxes.length > 0) {
            workingSelector = selector;
            console.log(`✅ Found ${specificCheckboxes.length} specific checkboxes with selector: ${selector}`);
            break;
        }
    }
    
    if (!specificCheckboxes || specificCheckboxes.length === 0) {
        console.error('❌ No specific filter checkboxes found with any selector!');
        // Try to find all checkboxes and exclude 'filter_all' manually
        const allCheckboxes = document.querySelectorAll('input[type="checkbox"]');
        specificCheckboxes = Array.from(allCheckboxes).filter(cb => cb.id !== 'filter_all');
        console.log(`🔄 Fallback: Found ${specificCheckboxes.length} checkboxes by manual filtering`);
    }
    
    // Uncheck all specific filters
    specificCheckboxes.forEach(checkbox => {
        if (checkbox.checked) {
            checkbox.checked = false;
            console.log('✅ Unchecked:', checkbox.id, checkbox.value); // Debug log
        }
    });
    
    // Check "Show All"
    const showAllCheckbox = document.getElementById('filter_all');
    if (showAllCheckbox) {
        showAllCheckbox.checked = true;
        console.log('✅ Checked Show All'); // Debug log
    } else {
        console.error('❌ Show All checkbox not found!');
    }
    
    // Clear button states - remove focus and active states
    clearFilterButtonStates();
    
    updateFilterButtonText();
    applyLogFilter();
}

// Clear all filters
function clearAllFilters() {
    console.log('clearAllFilters called'); // Debug log
    
    // Try multiple selectors to find all specific filter checkboxes
    const selectors = [
        '#logMessageFilterDropdown input[type="checkbox"]:not(#filter_all)',
        '.dropdown-menu input[type="checkbox"]:not(#filter_all)',
        'input[type="checkbox"]:not(#filter_all)'
    ];
    
    let specificCheckboxes = null;
    let workingSelector = null;
    
    for (const selector of selectors) {
        specificCheckboxes = document.querySelectorAll(selector);
        if (specificCheckboxes.length > 0) {
            workingSelector = selector;
            console.log(`✅ Found ${specificCheckboxes.length} specific checkboxes with selector: ${selector}`);
            break;
        }
    }
    
    if (!specificCheckboxes || specificCheckboxes.length === 0) {
        console.error('❌ No specific filter checkboxes found with any selector!');
        // Try to find all checkboxes and exclude 'filter_all' manually
        const allCheckboxes = document.querySelectorAll('input[type="checkbox"]');
        specificCheckboxes = Array.from(allCheckboxes).filter(cb => cb.id !== 'filter_all');
        console.log(`🔄 Fallback: Found ${specificCheckboxes.length} checkboxes by manual filtering`);
    }
    
    // Uncheck all specific filters (exclude "Show All")
    specificCheckboxes.forEach(checkbox => {
        if (checkbox.checked) {
            checkbox.checked = false;
            console.log('✅ Unchecked:', checkbox.id, checkbox.value); // Debug log
        }
    });
    
    // Check "Show All" 
    const showAllCheckbox = document.getElementById('filter_all');
    if (showAllCheckbox) {
        showAllCheckbox.checked = true;
        console.log('✅ Checked Show All'); // Debug log
    } else {
        console.error('❌ Show All checkbox not found!');
    }
    
    // Clear search filter as well
    const searchFilter = document.getElementById('logSearchFilter');
    if (searchFilter && searchFilter.value) {
        searchFilter.value = '';
        console.log('✅ Cleared search filter'); // Debug log
    }
    
    // Clear button states - remove focus and active states
    clearFilterButtonStates();
    
    updateFilterButtonText();
    applyLogFilter();
}

// Select only common/frequently used filters
function selectCommonFilters() {
    const commonFilters = ['BootNotification', 'StatusNotification', 'Authorize', 'StartTransaction', 'StopTransaction'];
    const checkboxes = document.querySelectorAll('#logMessageFilterDropdown input[type="checkbox"]');
    
    // Clear all first
    checkboxes.forEach(checkbox => checkbox.checked = false);
    
    // Ensure "Show All" is unchecked
    document.getElementById('filter_all').checked = false;
    
    // Select common ones
    commonFilters.forEach(filter => {
        const checkbox = document.getElementById(`filter_${filter}`);
        if (checkbox) checkbox.checked = true;
    });
    
    // Clear button states - remove focus and active states
    clearFilterButtonStates();
    
    updateFilterButtonText();
    applyLogFilter();
}

// Clear button states for filter action buttons
function clearFilterButtonStates() {
    // Remove focus and active states from all filter action buttons
    const filterButtons = document.querySelectorAll('#logMessageFilterDropdown .btn');
    filterButtons.forEach(button => {
        button.blur(); // Remove focus
        button.classList.remove('active'); // Remove active state
    });
    
    // Also remove focus from the main dropdown button
    const dropdownButton = document.getElementById('logMessageFilterDropdown');
    if (dropdownButton) {
        dropdownButton.blur();
    }
}

// Apply filters to logs array (updated for message ID matching)
function applyLogFiltersToLogs(logs) {
    const selectedFilters = getSelectedMessageFilters();
    const searchFilter = document.getElementById('logSearchFilter')?.value?.toLowerCase() || '';
    const showAllChecked = document.getElementById('filter_all')?.checked || false;

    console.log('Applying filters:', { selectedFilters, showAllChecked, totalLogs: logs.length }); // Debug log

    let filteredLogs = logs;

    // Apply OCPP message type filter
    if (!showAllChecked && selectedFilters.length > 0) {
        console.log('Filtering with selected filters:', selectedFilters); // Debug log
        
        // Two-pass filtering for message ID matching
        const matchingMessageIds = new Set();
        const directMatches = [];
        
        // First pass: Find direct matches and collect their message IDs
        logs.forEach(log => {
            let matches = false;
            let matchedFilter = null;
            
            for (const messageFilter of selectedFilters) {
                // Handle grouped direction filters
                if (messageFilter === 'charger-to-server') {
                    if (getMessageDirection(log.message) === 'charger-to-server') {
                        matches = true;
                        matchedFilter = messageFilter;
                        break;
                    }
                } else if (messageFilter === 'server-to-charger') {
                    if (getMessageDirection(log.message) === 'server-to-charger') {
                        matches = true;
                        matchedFilter = messageFilter;
                        break;
                    }
                } else if (messageFilter === 'connection') {
                    // Handle system message filters (no message ID matching needed)
                    if (isConnectionEvent(log.message)) {
                        matches = true;
                        matchedFilter = messageFilter;
                        break;
                    }
                } else if (messageFilter === 'error') {
                    if (isErrorMessage(log.message)) {
                        matches = true;
                        matchedFilter = messageFilter;
                        break;
                    }
                } else {
                    // Handle individual OCPP message type filters - be more strict
                    if (matchesMessageFilter(log, messageFilter)) {
                        // Additional validation: ensure the extracted action exactly matches the filter
                        const extractedAction = extractOCPPAction(log.message);
                        if (extractedAction && extractedAction.toLowerCase() === messageFilter.toLowerCase()) {
                            matches = true;
                            matchedFilter = messageFilter;
                            break;
                        } else {
                            // This prevents false positives from text-based matching
                            console.log(`⚠️ Rejected potential match for "${messageFilter}" - action mismatch: "${extractedAction}"`);
                        }
                    }
                }
            }
            
            if (matches) {
                console.log(`🎯 Direct match for filter "${matchedFilter}": "${log.message.substring(0, 100)}..."`);
                directMatches.push(log);
                
                // Only add message ID for correlation if this is an individual OCPP message type filter
                // Don't correlate for direction or system filters
                if (matchedFilter && !['charger-to-server', 'server-to-charger', 'connection', 'error'].includes(matchedFilter)) {
                    const messageId = extractOCPPMessageId(log.message);
                    if (messageId && !isConnectionEvent(log.message) && !isErrorMessage(log.message)) {
                        // Also verify this is actually an OCPP WebSocket frame before adding to correlation
                        const action = extractOCPPAction(log.message);
                        const messageType = getOCPPMessageType(log.message);
                        
                        if (action && action.toLowerCase() === matchedFilter.toLowerCase()) {
                            matchingMessageIds.add(messageId);
                            console.log(`✅ Added message ID ${messageId} for correlation (matched filter: ${matchedFilter}, action: ${action})`);
                        } else {
                            console.log(`⚠️ Skipped message ID ${messageId} - action "${action}" doesn't match filter "${matchedFilter}"`);
                        }
                    }
                }
            } else {
                console.log(`❌ No match for any filter: "${log.message.substring(0, 100)}..."`);
            }
        });
        
        // Check if we found any direct matches for individual OCPP filters
        const hasIndividualOCPPFilters = selectedFilters.some(filter => 
            !['charger-to-server', 'server-to-charger', 'connection', 'error'].includes(filter)
        );
        
        if (hasIndividualOCPPFilters && directMatches.length === 0) {
            console.log(`⚠️ No direct matches found for OCPP filters: ${selectedFilters.join(', ')}`);
            console.log('This likely means no messages of these types exist in the logs.');
            // Return empty result if no direct matches for specific OCPP message types
            return [];
        }
        
        // Second pass: Find corresponding requests/responses by message ID
        const relatedMatches = [];
        if (matchingMessageIds.size > 0) {
            logs.forEach(log => {
                // Skip if already matched in first pass
                if (directMatches.includes(log)) return;
                
                const messageId = extractOCPPMessageId(log.message);
                if (messageId && matchingMessageIds.has(messageId)) {
                    // Verify this is a valid OCPP response/error related to our selected filters
                    const messageType = getOCPPMessageType(log.message);
                    
                    if (messageType === 3 || messageType === 4) {
                        // This is a CALLRESULT (response) or CALLERROR
                        // Use the improved payload analysis to verify this is the right type of response
                        try {
                            const jsonMatch = log.message.match(/Frame:\s*(\[.*\])/s);
                            if (jsonMatch) {
                                const jsonStr = jsonMatch[1];
                                const ocppMessage = JSON.parse(jsonStr);
                                const payload = ocppMessage[2];
                                
                                // Check if this response matches any of our selected filters
                                const matchesAnyFilter = selectedFilters.some(filter => {
                                    // Skip direction and system filters
                                    if (['charger-to-server', 'server-to-charger', 'connection', 'error'].includes(filter)) {
                                        return false;
                                    }
                                    return matchesResponsePayload(payload, filter, messageType === 4);
                                });
                                
                                if (matchesAnyFilter) {
                                    relatedMatches.push(log);
                                    console.log(`✅ Found related ${messageType === 3 ? 'CALLRESULT' : 'CALLERROR'} with ID ${messageId}:`, log.message.substring(0, 100));
                                } else {
                                    console.log(`⚠️ Skipped correlated message with ID ${messageId} - payload doesn't match any selected filter`);
                                }
                            } else {
                                // Fallback: if we can't parse the frame, include it (legacy text-based matching)
                                relatedMatches.push(log);
                                console.log(`✅ Found related ${messageType === 3 ? 'CALLRESULT' : 'CALLERROR'} with ID ${messageId} (fallback):`, log.message.substring(0, 100));
                            }
                        } catch (e) {
                            // JSON parsing failed, include it anyway (fallback)
                            relatedMatches.push(log);
                            console.log(`✅ Found related ${messageType === 3 ? 'CALLRESULT' : 'CALLERROR'} with ID ${messageId} (parsing failed):`, log.message.substring(0, 100));
                        }
                    } else {
                        // This might be an unrelated CALL message with the same ID (unlikely but possible)
                        const action = extractOCPPAction(log.message);
                        console.log(`⚠️ Skipped unrelated CALL message with ID ${messageId}, action: ${action}`);
                    }
                }
            });
        }
        
        // Combine direct matches and related matches
        filteredLogs = [...directMatches, ...relatedMatches];
        
        // Sort by timestamp to maintain chronological order
        filteredLogs.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        console.log(`Filtered logs: ${directMatches.length} direct + ${relatedMatches.length} related = ${filteredLogs.length} total`); // Debug log
    } else {
        console.log('Show all is checked or no filters selected'); // Debug log
    }

    // Apply search text filter
    if (searchFilter) {
        filteredLogs = filteredLogs.filter(log => {
            return log.message.toLowerCase().includes(searchFilter);
        });
    }

    return filteredLogs;
}

// Apply current filters to displayed logs
function applyLogFilter() {
    console.log('applyLogFilter called'); // Debug log
    
    if (!allLogs || allLogs.length === 0) {
        console.log('No logs available for filtering'); // Debug log
        return;
    }

    console.log('Total logs available:', allLogs.length); // Debug log
    
    const container = document.getElementById('logContainer');
    const filteredLogs = applyLogFiltersToLogs(allLogs);
    
    console.log('Filtered logs count:', filteredLogs.length); // Debug log
    
    // Clear and redisplay filtered logs
    container.innerHTML = '';
    
    filteredLogs.forEach(log => {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
        // Add data attributes for filtering
        entry.setAttribute('data-message', log.message.toLowerCase());
        entry.setAttribute('data-ocpp-type', extractOCPPMessageType(log.message));
        
        // Format timestamp to show both IST and UTC
        let timestamp;
        if (log.timestamp.includes('T')) {
            const utcTimestamp = log.timestamp.includes('Z') ? log.timestamp : log.timestamp + 'Z';
            timestamp = new Date(utcTimestamp);
        } else {
            timestamp = new Date(log.timestamp + 'Z');
        }
        
        const istTime = timestamp.toLocaleString('en-IN', { 
            timeZone: 'Asia/Kolkata',
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        });
        
        const utcTime = timestamp.toLocaleString('en-GB', { 
            timeZone: 'UTC',
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        
        entry.innerHTML = `
            <div class="log-timestamp">
                <small class="text-muted">IST: ${istTime} | UTC: ${utcTime}</small>
            </div>
            <div class="log-message">${log.message}</div>
        `;
        container.appendChild(entry);
    });

    // Update filter status
    updateFilterStatus(allLogs.length, filteredLogs.length);

    // Auto-scroll to bottom if enabled
    if (autoScrollEnabled) {
        container.scrollTop = container.scrollHeight;
    }
    
    console.log('applyLogFilter completed'); // Debug log
}

// Clear all log filters
function clearLogFilters() {
    // Clear all checkboxes
    const checkboxes = document.querySelectorAll('#logMessageFilterDropdown input[type="checkbox"]');
    checkboxes.forEach(checkbox => checkbox.checked = false);
    
    // Check "Show All" by default
    document.getElementById('filter_all').checked = true;
    
    // Clear search filter
    document.getElementById('logSearchFilter').value = '';
    
    // Update button text and apply filters
    updateFilterButtonText();
    applyLogFilter();
}

// Update filter status display
function updateFilterStatus(totalLogs, filteredLogs) {
    const container = document.getElementById('logContainer');
    
    // Remove existing filter status
    const existingStatus = container.querySelector('.filter-status');
    if (existingStatus) {
        existingStatus.remove();
    }

    // Add filter status if filtering is active
    if (totalLogs !== filteredLogs) {
        const statusDiv = document.createElement('div');
        statusDiv.className = 'filter-status alert alert-info mb-2';
        statusDiv.innerHTML = `
            <i class="bi bi-funnel"></i> 
            Showing ${filteredLogs} of ${totalLogs} log entries 
            <button class="btn btn-sm btn-outline-primary ms-2" onclick="clearLogFilters()">
                <i class="bi bi-x-circle"></i> Clear Filters
            </button>
        `;
        container.insertBefore(statusDiv, container.firstChild);
    }
}

// Clear logs
async function clearLogs() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    if (confirm(`Are you sure you want to clear logs for charger ${selectedChargerId}? This will hide all previous logs.`)) {
        try {
            const response = await fetch(`/api/logs/${selectedChargerId}/clear`, {
                method: 'POST'
            });
            
            if (response.ok) {
                // Clear the UI immediately
                document.getElementById('logContainer').innerHTML = '';
                currentLogs = [];
                
                // Show success message
                const container = document.getElementById('logContainer');
                const successMsg = document.createElement('div');
                successMsg.className = 'alert alert-success';
                successMsg.innerHTML = '<i class="bi bi-check-circle"></i> Logs cleared successfully. Only new logs will be shown.';
                container.appendChild(successMsg);
                
                console.log(`Logs cleared for charger: ${selectedChargerId}`);
            } else {
                throw new Error('Failed to clear logs');
            }
        } catch (error) {
            console.error('Error clearing logs:', error);
            alert('Failed to clear logs. Please try again.');
        }
    }
}

// Toggle auto-scroll functionality
function toggleAutoScroll() {
    autoScrollEnabled = !autoScrollEnabled;
    const btn = document.getElementById('autoScrollBtn');
    
    if (autoScrollEnabled) {
        btn.innerHTML = '<i class="bi bi-arrow-down-circle"></i> Auto-scroll: ON';
        btn.className = 'btn btn-sm btn-outline-primary';
        // If we just enabled auto-scroll, scroll to bottom immediately
        const container = document.getElementById('logContainer');
        container.scrollTop = container.scrollHeight;
    } else {
        btn.innerHTML = '<i class="bi bi-arrow-down-circle-fill"></i> Auto-scroll: OFF';
        btn.className = 'btn btn-sm btn-outline-secondary';
    }
}

// Download logs as CSV
function downloadLogsCSV() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    if (!currentLogs || currentLogs.length === 0) {
        alert('No logs available to download');
        return;
    }
    
    // Create CSV content
    const csvHeaders = ['CPID', 'RecieveTime', 'UniqueID', 'MsgFlow', 'Command', 'PayloadData'];
    let csvContent = csvHeaders.join(',') + '\n';
    
    // Process logs in reverse order (latest first)
    const reversedLogs = [...currentLogs].reverse();
    reversedLogs.forEach(log => {
        // Parse timestamp
        let timestamp;
        if (log.timestamp.includes('T')) {
            // ISO format: 2025-06-13T21:10:26.777787 (this is UTC time from server)
            // Force it to be interpreted as UTC by adding 'Z' if not present
            const utcTimestamp = log.timestamp.includes('Z') ? log.timestamp : log.timestamp + 'Z';
            timestamp = new Date(utcTimestamp);
        } else {
            // Fallback for other formats
            timestamp = new Date(log.timestamp + 'Z');
        }
        
        // Format IST time (UTC + 5:30) in M/d/yyyy, h:mm:ss tt format
        const istTime = timestamp.toLocaleString('en-US', { 
            timeZone: 'Asia/Kolkata',
            month: 'numeric',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        }) + ' IST';
        
        // Parse the log message to extract OCPP frame data
        let msgFlow = '';
        let uniqueID = '';
        let command = '';
        let payloadData = '';
        
        const message = log.message;
        let jsonData = null;
        
        if (message.includes('WebSocket CMS→Charger Frame:')) {
            msgFlow = 'CMS -> CP';
            // Extract JSON payload from WebSocket frame (could be multi-line formatted JSON)
            const match = message.match(/WebSocket CMS→Charger Frame: (.*)/s);
            if (match) {
                try {
                    // Handle both single-line and multi-line JSON
                    let jsonStr = match[1].trim();
                    // If it starts with [, it's likely a JSON array
                    if (jsonStr.startsWith('[')) {
                        jsonData = JSON.parse(jsonStr);
                    } else {
                        // Try to parse as-is first
                        jsonData = JSON.parse(jsonStr);
                    }
                } catch (e) {
                    console.log('JSON parse error for CMS->CP:', e, match[1]);
                    payloadData = match[1].trim();
                }
            }
        } else if (message.includes('WebSocket Charger→CMS Frame:')) {
            msgFlow = 'CP -> CMS';
            // Extract JSON payload from WebSocket frame (could be multi-line formatted JSON)
            const match = message.match(/WebSocket Charger→CMS Frame: (.*)/s);
            if (match) {
                try {
                    // Handle both single-line and multi-line JSON
                    let jsonStr = match[1].trim();
                    // If it starts with [, it's likely a JSON array
                    if (jsonStr.startsWith('[')) {
                        jsonData = JSON.parse(jsonStr);
                    } else {
                        // Try to parse as-is first
                        jsonData = JSON.parse(jsonStr);
                    }
                } catch (e) {
                    console.log('JSON parse error for CP->CMS:', e, match[1]);
                    payloadData = match[1].trim();
                }
            }
        } else if (message.includes('send [')) {
            msgFlow = 'CMS -> CP';
            // Extract JSON payload from send message (legacy format)
            const match = message.match(/send \[(.*)\]/);
            if (match) {
                try {
                    jsonData = JSON.parse('[' + match[1] + ']');
                } catch (e) {
                    console.log('JSON parse error for send:', e, match[1]);
                    payloadData = '[' + match[1] + ']';
                }
            }
        } else if (message.includes('receive message [')) {
            msgFlow = 'CP -> CMS';
            // Extract JSON payload from receive message (legacy format)
            const match = message.match(/receive message \[(.*)\]/);
            if (match) {
                try {
                    jsonData = JSON.parse('[' + match[1] + ']');
                } catch (e) {
                    console.log('JSON parse error for receive:', e, match[1]);
                    payloadData = '[' + match[1] + ']';
                }
            }
        }
        
        // Parse OCPP message structure if we have valid JSON
        if (jsonData && Array.isArray(jsonData)) {
            if (jsonData.length >= 2) {
                // OCPP message format: [MessageType, UniqueId, Action, Payload]
                // or [MessageType, UniqueId, Payload] for responses
                const messageType = jsonData[0];
                uniqueID = String(jsonData[1] || ''); // Convert to string to avoid extra quotes
                
                if (messageType === 2) {
                    // CALL message: [2, UniqueId, Action, Payload]
                    command = jsonData[2] || '';
                    payloadData = jsonData[3] ? JSON.stringify(jsonData[3]) : '{}';
                } else if (messageType === 3) {
                    // CALLRESULT message: [3, UniqueId, Payload]
                    // For confirmation messages, try to infer command from payload structure
                    const payload = jsonData[2] || {};
                    
                    // Common OCPP confirmation patterns
                    if (payload.hasOwnProperty('currentTime')) {
                        command = 'HeartbeatConfirmation';
                    } else if (payload.hasOwnProperty('status') && payload.hasOwnProperty('idTagInfo')) {
                        command = 'AuthorizeConfirmation';
                    } else if (payload.hasOwnProperty('status') && payload.hasOwnProperty('transactionId')) {
                        command = 'StartTransactionConfirmation';
                    } else if (payload.hasOwnProperty('idTagInfo') && !payload.hasOwnProperty('transactionId')) {
                        command = 'StopTransactionConfirmation';
                    } else if (Object.keys(payload).length === 0) {
                        // Empty payload - most commonly MeterValuesConfirmation
                        command = 'MeterValuesConfirmation';
                    } else if (payload.hasOwnProperty('status')) {
                        // Just status field - could be various confirmations
                        command = 'StatusConfirmation';
                    } else {
                        command = 'Confirmation';
                    }
                    
                    payloadData = jsonData[2] ? JSON.stringify(jsonData[2]) : '{}';
                } else if (messageType === 4) {
                    // CALLERROR message: [4, UniqueId, ErrorCode, ErrorDescription, ErrorDetails]
                    command = 'Error';
                    payloadData = JSON.stringify({
                        errorCode: jsonData[2] || '',
                        errorDescription: jsonData[3] || '',
                        errorDetails: jsonData[4] || {}
                    });
                } else {
                    // Unknown message type, but still include it
                    command = 'Unknown';
                    payloadData = JSON.stringify(jsonData);
                }
            }
        }
        
        // If we don't have JSON data but have raw payload, use that
        if (!jsonData && payloadData) {
            command = 'Raw';
            // payloadData is already set from the catch blocks
        }
        
        // Skip entries that don't have any meaningful data
        if (!msgFlow) {
            return;
        }
        
        // Escape CSV values (handle commas and quotes)
        const escapeCSV = (value) => {
            if (typeof value !== 'string') value = String(value);
            // Only escape if the value contains commas, quotes, or newlines
            if (value.includes(',') || value.includes('"') || value.includes('\n')) {
                return '"' + value.replace(/"/g, '""') + '"';
            }
            return value;
        };
        
        const row = [
            escapeCSV(selectedChargerId),
            escapeCSV(istTime),
            uniqueID,  // Don't escape uniqueID to avoid extra quotes
            escapeCSV(msgFlow),
            escapeCSV(command),
            escapeCSV(payloadData)
        ];
        
        csvContent += row.join(',') + '\n';
    });
    
    // Create and download file
    const now = new Date();
    const dateTimeStr = now.toISOString().replace(/[:.]/g, '-').slice(0, -5); // Format: 2025-06-13T21-10-26
    const filename = `${selectedChargerId}_${dateTimeStr}.csv`;
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    } else {
        // Fallback for older browsers
        alert('CSV download not supported in this browser');
    }
}

// Load ID tags
async function loadIdTags() {
    try {
        const response = await fetch('/api/idtags');
        const idTags = await response.json();
        updateIdTagList(idTags);
    } catch (error) {
        console.error('Error loading ID tags:', error);
    }
}

// Update ID tag list in UI
function updateIdTagList(idTags) {
    const list = document.getElementById('idTagList');
    const select = document.getElementById('remoteStartIdTag');
    
    list.innerHTML = '';
    if (select) select.innerHTML = '';

    Object.entries(idTags).forEach(([idTag, info]) => {
        // Format expiry date
        let expiryText = '';
        let badgeClass = 'bg-success';
        
        if (info.expiry_date) {
            const expiryDate = new Date(info.expiry_date);
            const now = new Date();
            const isExpired = expiryDate < now;
            const formattedDate = expiryDate.toLocaleString();
            
            if (isExpired) {
                expiryText = `<small class="text-danger"><i class="bi bi-exclamation-triangle"></i> Expired: ${formattedDate}</small>`;
                badgeClass = 'bg-danger';
            } else {
                expiryText = `<small class="text-muted"><i class="bi bi-clock"></i> Expires: ${formattedDate}</small>`;
            }
        } else {
            expiryText = '<small class="text-muted"><i class="bi bi-infinity"></i> No expiry</small>';
        }

        // Create card for each ID tag
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4 mb-3';
        
        col.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="d-flex align-items-start gap-2">
                            <div class="form-check mt-1">
                                <input class="form-check-input idtag-checkbox" type="checkbox" value="${idTag}" id="checkbox-${idTag}" onchange="updateSelectedCount()">
                            </div>
                            <div>
                                <h6 class="card-title mb-1">${idTag}</h6>
                                ${expiryText}
                            </div>
                        </div>
                        <div class="d-flex flex-column align-items-end gap-2">
                            <span class="badge ${badgeClass}">${info.status}</span>
                            <button class="btn btn-danger btn-sm" onclick="deleteIdTag('${idTag}')" title="Delete ID Tag">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        list.appendChild(col);

        // Add to select (only if not expired) - for remote start modal
        if (select && (!info.expiry_date || new Date(info.expiry_date) >= new Date())) {
            const option = document.createElement('option');
            option.value = idTag;
            option.textContent = idTag;
            select.appendChild(option);
        }
    });
    
    // Update selected count after loading
    updateSelectedCount();
}

// Add new ID tag
// Update character count for ID tag input
function updateCharCount() {
    const input = document.getElementById('newIdTag');
    const counter = document.getElementById('charCount');
    const currentLength = input.value.length;
    
    counter.textContent = `${currentLength}/20 characters`;
    
    // Change color based on remaining characters
    if (currentLength >= 18) {
        counter.className = 'text-warning';
    } else if (currentLength === 20) {
        counter.className = 'text-danger';
    } else {
        counter.className = 'text-muted';
    }
}

async function addIdTag() {
    const idTag = document.getElementById('newIdTag').value.trim();
    const expiryDateTime = document.getElementById('newIdTagExpiry').value;
    
    if (!idTag) {
        alert('Please enter an ID tag');
        return;
    }
    
    // Validate ID tag length according to OCPP 1.6 specification (max 20 characters)
    if (idTag.length > 20) {
        alert(`ID tag is too long! Maximum length is 20 characters (OCPP 1.6 specification).\n\nCurrent length: ${idTag.length} characters\nPlease shorten the ID tag.`);
        return;
    }

    try {
        const requestBody = {
            id_tag: idTag,
            status: 'Accepted'
        };
        
        // Add expiry date if provided (datetime-local format)
        if (expiryDateTime) {
            requestBody.expiry_date = expiryDateTime;
        }

        const response = await fetch('/api/idtags', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        if (response.ok) {
            document.getElementById('newIdTag').value = '';
            document.getElementById('newIdTagExpiry').value = '';
            updateCharCount(); // Reset character counter
            loadIdTags();
            alert('ID Tag added successfully!');
        } else {
            const errorData = await response.json();
            alert(`Error adding ID tag: ${errorData.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error adding ID tag:', error);
        alert('Error adding ID tag');
    }
}

// Delete ID tag
async function deleteIdTag(idTag) {
    if (!confirm(`Are you sure you want to delete ID tag "${idTag}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/idtags/${encodeURIComponent(idTag)}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadIdTags();
            alert('ID Tag deleted successfully!');
        } else {
            const errorData = await response.json();
            alert(`Error deleting ID tag: ${errorData.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error deleting ID tag:', error);
        alert('Error deleting ID tag');
    }
}

// Update selected count and button state
function updateSelectedCount() {
    const checkboxes = document.querySelectorAll('.idtag-checkbox');
    const selectedCheckboxes = document.querySelectorAll('.idtag-checkbox:checked');
    const selectedCount = selectedCheckboxes.length;
    
    // Update count display
    document.getElementById('selectedCount').textContent = selectedCount;
    
    // Enable/disable delete button
    const deleteBtn = document.getElementById('deleteSelectedBtn');
    deleteBtn.disabled = selectedCount === 0;
    
    // Update select all button text
    const selectAllBtn = document.getElementById('selectAllBtn');
    if (selectedCount === checkboxes.length && checkboxes.length > 0) {
        selectAllBtn.innerHTML = '<i class="bi bi-check-all"></i> All Selected';
        selectAllBtn.classList.add('active');
    } else {
        selectAllBtn.innerHTML = '<i class="bi bi-check-all"></i> Select All';
        selectAllBtn.classList.remove('active');
    }
}

// Select all ID tags
function selectAllIdTags() {
    const checkboxes = document.querySelectorAll('.idtag-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
    });
    updateSelectedCount();
}

// Deselect all ID tags
function deselectAllIdTags() {
    const checkboxes = document.querySelectorAll('.idtag-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    updateSelectedCount();
}

// Delete selected ID tags
async function deleteSelectedIdTags() {
    const selectedCheckboxes = document.querySelectorAll('.idtag-checkbox:checked');
    const selectedIdTags = Array.from(selectedCheckboxes).map(cb => cb.value);
    
    if (selectedIdTags.length === 0) {
        alert('No ID tags selected');
        return;
    }
    
    const confirmMessage = selectedIdTags.length === 1 
        ? `Are you sure you want to delete the selected ID tag "${selectedIdTags[0]}"?`
        : `Are you sure you want to delete ${selectedIdTags.length} selected ID tags?\n\nTags to delete:\n${selectedIdTags.join('\n')}`;
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    // Show progress
    const deleteBtn = document.getElementById('deleteSelectedBtn');
    const originalText = deleteBtn.innerHTML;
    deleteBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Deleting...';
    deleteBtn.disabled = true;
    
    let successCount = 0;
    let errorCount = 0;
    const errors = [];
    
    try {
        // Delete each ID tag
        for (const idTag of selectedIdTags) {
            try {
                const response = await fetch(`/api/idtags/${encodeURIComponent(idTag)}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    successCount++;
                } else {
                    errorCount++;
                    const errorData = await response.json();
                    errors.push(`${idTag}: ${errorData.detail || 'Unknown error'}`);
                }
            } catch (error) {
                errorCount++;
                errors.push(`${idTag}: ${error.message}`);
            }
        }
        
        // Show results
        let message = '';
        if (successCount > 0) {
            message += `Successfully deleted ${successCount} ID tag${successCount > 1 ? 's' : ''}`;
        }
        if (errorCount > 0) {
            if (message) message += '\n\n';
            message += `Failed to delete ${errorCount} ID tag${errorCount > 1 ? 's' : ''}:\n${errors.join('\n')}`;
        }
        
        if (message) {
            alert(message);
        }
        
        // Reload the list
        loadIdTags();
        
    } finally {
        // Reset button
        deleteBtn.innerHTML = originalText;
        updateSelectedCount();
    }
}

// Generate random ID tags and add them directly to the database
async function generateRandomIdTags(count = 10, validityDays = 1) {
    if (!confirm(`Generate ${count} random ID tags with ${validityDays} day(s) validity?\n\nThese will be added directly to your ID tag database.`)) {
        return;
    }
    
    const now = new Date();
    const expiryDate = new Date(now.getTime() + (validityDays * 24 * 60 * 60 * 1000));
    
    let addedCount = 0;
    let errors = [];
    const addedTags = [];
    
    for (let i = 0; i < count; i++) {
        // Generate random ID tag - exactly 20 characters as per OCPP 1.6 specification
        // Format: TAG + 17 random alphanumeric characters = 20 total characters
        let randomId = 'TAG';
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        for (let j = 0; j < 17; j++) {
            randomId += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        
        try {
            const response = await fetch('/api/idtags', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    id_tag: randomId,
                    status: 'Accepted',
                    expiry_date: expiryDate.toISOString()
                })
            });
            
            if (response.ok) {
                addedCount++;
                addedTags.push(randomId);
            } else {
                const error = await response.text();
                errors.push(`Failed to add ${randomId}: ${error}`);
            }
        } catch (error) {
            console.error(`Error adding ID tag ${randomId}:`, error);
            errors.push(`Error adding ${randomId}: ${error.message}`);
        }
    }
    
    // Show results
    let message = `✅ Successfully generated and added ${addedCount} random ID tags!`;
    message += `\n\n📋 Generated tags:\n${addedTags.join(', ')}`;
    message += `\n\n⏰ Validity: ${validityDays} day(s) (expires ${expiryDate.toLocaleDateString()})`;
    
    if (errors.length > 0) {
        message += `\n\n❌ Errors (${errors.length}):\n${errors.join('\n')}`;
    }
    
    alert(message);
    
    // Refresh the ID tags list to show the new tags
    await loadIdTags();
    
    // Log to console for debugging
    console.log(`Generated ${addedCount} random ID tags:`, addedTags);
}

// Modal show functions
function showRemoteStartModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    modals.remoteStart.show();
}

async function showRemoteStopModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Show modal first with loading indicator
    modals.remoteStop.show();
    
    // Show loading state
    const select = document.getElementById('remoteStopTransactionId');
    select.innerHTML = '<option value="">Loading transactions...</option>';
    
    // Load fresh transaction data
    await loadActiveTransactions();
}

function showGetConfigModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    modals.getConfig.show();
}

function showChangeConfigModal() {
    console.log('=== SHOW CHANGE CONFIG MODAL DEBUG START ===');
    console.log('Selected charger ID:', selectedChargerId);
    console.log('configurationData status:', configurationData ? 'Available' : 'Not available');
    
    if (!selectedChargerId) {
        console.log('ERROR: No charger selected');
        alert('Please select a charger first');
        return;
    }
    
    console.log('About to populate configuration list...');
    // Populate configuration list if data is available
    populateConfigurationList();
    console.log('Configuration list populated, showing modal...');
    modals.changeConfig.show();
    console.log('=== SHOW CHANGE CONFIG MODAL DEBUG END ===');
}

function populateConfigurationList() {
    console.log('=== POPULATE CONFIGURATION LIST DEBUG START ===');
    
    const configList = document.getElementById('configurationList');
    const noConfigMessage = document.getElementById('noConfigurationMessage');
    
    console.log('configList element:', configList);
    console.log('noConfigMessage element:', noConfigMessage);
    console.log('configurationData:', configurationData);
    console.log('typeof configurationData:', typeof configurationData);
    
    if (!configurationData) {
        // No configuration data available
        console.log('No configuration data available - showing no config message');
        configList.innerHTML = '';
        noConfigMessage.style.display = 'block';
        console.log('=== POPULATE CONFIGURATION LIST DEBUG END (no data) ===');
        return;
    }
    
    // OCPP response structure check - could be configurationKey or configuration_key
    let configKeys = configurationData.configuration_key || configurationData.configurationKey;
    
    console.log('Available configuration data fields:', Object.keys(configurationData));
    console.log('configurationKey:', configurationData.configurationKey);
    console.log('configuration_key:', configurationData.configuration_key);
    console.log('unknownKey:', configurationData.unknownKey);
    console.log('Full configurationData:', configurationData);
    
    if (!configKeys || !Array.isArray(configKeys)) {
        // Try other possible field names - check all possible OCPP field names
        configKeys = configurationData.unknownKey || 
                    configurationData.UnknownKey || 
                    configurationData.configurationKeys ||
                    configurationData.configuration_keys;
        
        if (!configKeys || !Array.isArray(configKeys)) {
            console.error('Configuration data structure unexpected:', configurationData);
            console.error('Available fields:', Object.keys(configurationData));
            
            let debugInfo = '<div class="alert alert-warning">';
            debugInfo += '<strong>Configuration data received but structure is unexpected.</strong><br>';
            debugInfo += 'Available fields: ' + Object.keys(configurationData).join(', ') + '<br>';
            debugInfo += '<details><summary>Click to see raw data</summary>';
            debugInfo += '<pre>' + JSON.stringify(configurationData, null, 2) + '</pre>';
            debugInfo += '</details>';
            debugInfo += '</div>';
            
            configList.innerHTML = debugInfo;
            noConfigMessage.style.display = 'none';
            return;
        }
    }
    
    noConfigMessage.style.display = 'none';
    
    // Build configuration form
    let html = '<div class="alert alert-success mb-3">';
    html += '<i class="bi bi-check-circle"></i> ';
    html += `Configuration loaded with ${configKeys.length} keys. `;
    html += 'Edit the values below (read-only keys are disabled):';
    html += '</div>';
    
    configKeys.forEach((config, index) => {
        const isReadonly = config.readonly === true;
        const readonlyClass = isReadonly ? 'is-invalid' : '';
        const readonlyAttr = isReadonly ? 'readonly' : '';
        const readonlyIcon = isReadonly ? '<i class="bi bi-lock-fill text-danger"></i>' : '<i class="bi bi-pencil-fill text-success"></i>';
        
        html += `
            <div class="mb-3 border rounded p-3 ${isReadonly ? 'bg-light' : ''}">
                <div class="row align-items-center">
                    <div class="col-md-4">
                        <label class="form-label fw-bold">
                            ${readonlyIcon} ${config.key}
                        </label>
                        <div class="text-muted small">
                            ${isReadonly ? 'Read-only' : 'Editable'}
                        </div>
                    </div>
                    <div class="col-md-8">
                        <input 
                            type="text" 
                            class="form-control ${readonlyClass}" 
                            id="config_${index}" 
                            data-key="${config.key}"
                            data-readonly="${isReadonly}"
                            value="${config.value || ''}" 
                            ${readonlyAttr}
                            placeholder="${isReadonly ? 'This value cannot be changed' : 'Enter new value'}"
                        >
                        ${isReadonly ? '<div class="invalid-feedback">This configuration key is read-only and cannot be modified.</div>' : ''}
                    </div>
                </div>
            </div>
        `;
    });
    
    configList.innerHTML = html;
}

function showSendLocalListModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    modals.sendLocalList.show();
}

function showDataTransferModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    modals.dataTransfer.show();
}

function showDataTransferPacketsModal() {
    loadDataTransferPackets();
    modals.dataTransferPackets.show();
}

// API call functions
async function remoteStartTransaction() {
    const idTag = document.getElementById('remoteStartIdTag').value;
    const connectorId = document.getElementById('remoteStartConnectorId').value;

    try {
        const response = await fetch(`/api/send/${selectedChargerId}/remote_start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                id_tag: idTag,
                connector_id: connectorId ? parseInt(connectorId) : null
            })
        });

        if (response.ok) {
            modals.remoteStart.hide();
            alert('Remote start transaction sent successfully');
        } else {
            alert('Error sending remote start transaction');
        }
    } catch (error) {
        console.error('Error sending remote start transaction:', error);
        alert('Error sending remote start transaction');
    }
}

// Load active transactions for remote stop
async function loadActiveTransactions() {
    try {
        // Add timestamp to prevent caching and ensure fresh data
        const timestamp = new Date().getTime();
        const response = await fetch(`/api/active_transactions/${selectedChargerId}?t=${timestamp}`, {
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache'
            }
        });
        const data = await response.json();
        updateActiveTransactionsList(data.active_transactions);
    } catch (error) {
        console.error('Error loading active transactions:', error);
    }
}

// Update active transactions dropdown
function updateActiveTransactionsList(transactions) {
    const select = document.getElementById('remoteStopTransactionId');
    const stopBtn = document.getElementById('remoteStopBtn');
    
    select.innerHTML = '';
    
    if (transactions.length === 0) {
        select.innerHTML = '<option value="">No active transactions</option>';
        stopBtn.disabled = true;
    } else {
        select.innerHTML = '<option value="">Select a transaction</option>';
        transactions.forEach(transaction => {
            const option = document.createElement('option');
            option.value = transaction.transaction_id;
            option.textContent = `Transaction ${transaction.transaction_id} (${transaction.status})`;
            select.appendChild(option);
        });
        stopBtn.disabled = false;
    }
    
    // Enable/disable stop button based on selection
    select.addEventListener('change', function() {
        stopBtn.disabled = !this.value;
    });
}

async function remoteStopTransaction() {
    const transactionId = document.getElementById('remoteStopTransactionId').value;

    if (!transactionId) {
        alert('Please select a transaction to stop');
        return;
    }

    try {
        const response = await fetch(`/api/send/${selectedChargerId}/remote_stop`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                transaction_id: parseInt(transactionId)
            })
        });

        if (response.ok) {
            modals.remoteStop.hide();
            alert('Remote stop transaction sent successfully');
        } else {
            alert('Error sending remote stop transaction');
        }
    } catch (error) {
        console.error('Error sending remote stop transaction:', error);
        alert('Error sending remote stop transaction');
    }
}

async function getConfiguration() {
    const keys = document.getElementById('getConfigKeys').value;

    console.log('=== GET CONFIGURATION DEBUG START ===');
    console.log('Selected charger ID:', selectedChargerId);
    console.log('Keys filter:', keys);

    try {
        const url = `/api/send/${selectedChargerId}/get_configuration${keys ? `?keys=${keys}` : ''}`;
        console.log('Request URL:', url);
        
        const response = await fetch(url);
        const data = await response.json();

        console.log('Raw API response:', data);
        console.log('Response status:', response.status);
        console.log('Response ok:', response.ok);
        console.log('Response type:', typeof data);

        if (response.ok) {
            console.log('API call successful!');
            
            // Store configuration data for use in Change Configuration modal
            // The API returns {status: "success", response: actualConfigData}
            console.log('Extracting data.response...');
            configurationData = data.response;
            
            console.log('=== CONFIGURATION DATA ANALYSIS ===');
            console.log('Full API response:', JSON.stringify(data, null, 2));
            console.log('Stored configurationData:', JSON.stringify(configurationData, null, 2));
            console.log('Type of configurationData:', typeof configurationData);
            console.log('Is configurationData null?', configurationData === null);
            console.log('Is configurationData undefined?', configurationData === undefined);
            
            if (configurationData) {
                console.log('configurationData keys:', Object.keys(configurationData));
                console.log('configurationData.configurationKey:', configurationData.configurationKey);
                console.log('configurationData.configuration_key:', configurationData.configuration_key);
            }
            
            modals.getConfig.hide();
            alert('Configuration retrieved successfully! You can now use "Change Configuration" to edit values.');
            console.log('=== GET CONFIGURATION DEBUG END ===');
        } else {
            console.error('API call failed:', data);
            alert('Error getting configuration');
        }
    } catch (error) {
        console.error('Error getting configuration:', error);
        alert('Error getting configuration');
    }
}

async function changeConfiguration() {
    if (!configurationData) {
        alert('No configuration data available. Please run "Get Configuration" first.');
        return;
    }
    
    // Get configuration keys array (handle different field names)
    let configKeys = configurationData.configuration_key || configurationData.configurationKey;
    
    if (!configKeys || !Array.isArray(configKeys)) {
        alert('Configuration data structure is unexpected. Please run "Get Configuration" again.');
        return;
    }
    
    // Collect all editable configuration changes
    const changes = [];
    const originalConfig = new Map();
    
    // Create a map of original values for comparison
    configKeys.forEach(config => {
        originalConfig.set(config.key, config.value || '');
    });
    
    // Check each input field for changes
    configKeys.forEach((config, index) => {
        const input = document.getElementById(`config_${index}`);
        if (input && input.dataset.readonly !== 'true') {
            const currentValue = input.value;
            const originalValue = originalConfig.get(config.key);
            
            console.log(`Checking ${config.key}: "${originalValue}" vs "${currentValue}"`);
            
            if (currentValue !== originalValue) {
                changes.push({
                    key: config.key,
                    oldValue: originalValue,
                    newValue: currentValue
                });
                console.log(`Change detected for ${config.key}: "${originalValue}" → "${currentValue}"`);
            }
        }
    });
    
    if (changes.length === 0) {
        alert('No changes detected.');
        return;
    }
    
    // Confirm changes with user
    let confirmMessage = `You are about to change ${changes.length} configuration value(s):\n\n`;
    changes.forEach(change => {
        confirmMessage += `• ${change.key}: "${change.oldValue}" → "${change.newValue}"\n`;
    });
    confirmMessage += '\nDo you want to proceed?';
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    // Apply changes one by one
    let successCount = 0;
    let errors = [];
    
    for (const change of changes) {
        try {
            const response = await fetch(`/api/send/${selectedChargerId}/change_configuration`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    key: change.key,
                    value: change.newValue
                })
            });

            if (response.ok) {
                successCount++;
                console.log(`Successfully changed ${change.key}`);
            } else {
                const errorText = await response.text();
                errors.push(`${change.key}: ${errorText}`);
            }
        } catch (error) {
            console.error(`Error changing ${change.key}:`, error);
            errors.push(`${change.key}: ${error.message}`);
        }
    }
    
    // Show results
    let resultMessage = `Configuration update complete!\n\n`;
    resultMessage += `✅ Successfully changed: ${successCount} values\n`;
    
    if (errors.length > 0) {
        resultMessage += `❌ Failed: ${errors.length} values\n\nErrors:\n`;
        errors.forEach(error => {
            resultMessage += `• ${error}\n`;
        });
    }
    
    alert(resultMessage);
    
    if (successCount > 0) {
        // Clear stored configuration data to force a fresh Get Configuration
        configurationData = null;
        modals.changeConfig.hide();
        
        // Suggest getting configuration again
        if (confirm('Configuration has been updated. Would you like to run "Get Configuration" again to see the current values?')) {
            modals.getConfig.show();
        }
    }
}

async function clearCache() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }

    try {
        const response = await fetch(`/api/send/${selectedChargerId}/clear_cache`, {
            method: 'POST'
        });

        if (response.ok) {
            alert('Cache cleared successfully');
        } else {
            alert('Error clearing cache');
        }
    } catch (error) {
        console.error('Error clearing cache:', error);
        alert('Error clearing cache');
    }
}

async function resetCharger(resetType) {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }

    const resetTypeDisplay = resetType === 'hard' ? 'Hard Reset' : 'Soft Reset';
    const resetDescription = resetType === 'hard' 
        ? 'This will completely restart the charger (power cycle).' 
        : 'This will restart the charger software without power cycle.';

    if (confirm(`Are you sure you want to perform a ${resetTypeDisplay} on charger ${selectedChargerId}?\n\n${resetDescription}\n\nThe charger may disconnect temporarily.`)) {
        try {
            const response = await fetch(`/api/send/${selectedChargerId}/reset`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    type: resetType
                })
            });

            if (response.ok) {
                const result = await response.json();
                alert(`${resetTypeDisplay} request sent successfully!\nResponse: ${JSON.stringify(result.response, null, 2)}\n\nThe charger should restart shortly.`);
            } else {
                const error = await response.json();
                alert(`Failed to send ${resetTypeDisplay} request: ${error.detail}`);
            }
        } catch (error) {
            console.error(`Error sending ${resetTypeDisplay} request:`, error);
            alert(`Failed to send ${resetTypeDisplay} request. Please try again.`);
        }
    }
}

async function sendLocalList() {
    const updateType = document.getElementById('localListUpdateType').value;
    const data = document.getElementById('localListData').value;
    const forceStoreLocally = document.getElementById('forceStoreLocally').checked;

    try {
        const response = await fetch(`/api/send/${selectedChargerId}/send_local_list`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                update_type: updateType,
                local_authorization_list: data ? JSON.parse(data) : null,
                force_store_locally: forceStoreLocally
            })
        });

        if (response.ok) {
            const result = await response.json();
            modals.sendLocalList.hide();
            
            // Count the number of ID tags that were sent
            let tagCount = 0;
            if (data) {
                try {
                    const parsedData = JSON.parse(data);
                    tagCount = Array.isArray(parsedData) ? parsedData.length : 0;
                } catch (e) {
                    tagCount = 0;
                }
            }
            
            // Check if the charger accepted the local list
            if (result.response && result.response.status === 'Accepted') {
                alert(`Local list sent successfully!\n\nCharger response: ${result.response.status}\n${tagCount > 0 ? `\n${tagCount} ID tags have been sent to the charger and stored locally.` : ''}`);
            } else {
                const status = result.response ? result.response.status : 'Unknown';
                if (forceStoreLocally && tagCount > 0) {
                    alert(`Local list sent but charger responded with: ${status}\n\nHowever, ${tagCount} ID tags have been stored locally as requested.`);
                } else {
                    alert(`Local list sent but charger responded with: ${status}\n\nID tags were not stored locally.`);
                }
            }
            
            // Refresh the ID tags list to show any newly added tags
            loadIdTags();
        } else {
            const errorData = await response.json();
            alert(`Error sending local list: ${errorData.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error sending local list:', error);
        alert('Error sending local list. Please check the JSON format and try again.');
    }
}

async function sendDataTransfer() {
    // Check if a charger is selected
    if (!selectedChargerId) {
        alert('Please select a charger first before sending data transfer');
        return;
    }

    const vendorId = document.getElementById('dataTransferVendorId').value;
    const messageId = document.getElementById('dataTransferMessageId').value;
    const data = document.getElementById('dataTransferData').value;

    console.log('Sending data transfer:', {
        selectedChargerId,
        vendorId,
        messageId,
        data
    });

    if (!vendorId) {
        alert('Please enter a vendor ID');
        return;
    }

    try {
        const response = await fetch(`/api/send/${selectedChargerId}/data_transfer`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                vendor_id: vendorId,
                message_id: messageId || null,
                data: data || null
            })
        });

        console.log('Data transfer response:', response.status, response.statusText);

        if (response.ok) {
            const result = await response.json();
            console.log('Data transfer result:', result);
            modals.dataTransfer.hide();
            alert('Data transfer sent successfully');
        } else {
            const errorText = await response.text();
            console.error('Data transfer error:', errorText);
            alert(`Error sending data transfer: ${response.status} - ${errorText}`);
        }
    } catch (error) {
        console.error('Error sending data transfer:', error);
        alert(`Network error sending data transfer: ${error.message}`);
    }
}

// Add new functions for data transfer packets
async function loadDataTransferPackets() {
    try {
        const response = await fetch('/api/data_transfer_packets');
        const packets = await response.json();
        updatePacketsList(packets);
    } catch (error) {
        console.error('Error loading data transfer packets:', error);
    }
}

function updatePacketsList(packets) {
    const list = document.getElementById('packetsList');
    list.innerHTML = '';
    
    // Store packets data globally for easy access
    packetsData = packets;

    packets.forEach(packet => {
        const item = document.createElement('div');
        item.className = 'list-group-item';
        item.setAttribute('data-packet-id', packet.id);
        item.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">${packet.name}</h6>
                    <small class="text-muted">
                        Vendor ID: ${packet.vendor_id}
                        ${packet.message_id ? ` | Message ID: ${packet.message_id}` : ''}
                    </small>
                    ${packet.data ? `<pre class="mt-2 mb-0"><code>${packet.data}</code></pre>` : ''}
                </div>
                <div class="btn-group">
                    <button class="btn btn-sm btn-primary" onclick="useDataTransferPacket(${packet.id})">Use</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteDataTransferPacket(${packet.id})">Delete</button>
                </div>
            </div>
        `;
        list.appendChild(item);
    });
}

async function saveDataTransferPacket() {
    const name = document.getElementById('newPacketName').value.trim();
    const vendorId = document.getElementById('newPacketVendorId').value.trim();
    const messageId = document.getElementById('newPacketMessageId').value.trim();
    const data = document.getElementById('newPacketData').value.trim();

    if (!name || !vendorId) {
        alert('Please enter a name and vendor ID');
        return;
    }

    try {
        const response = await fetch('/api/data_transfer_packets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                vendor_id: vendorId,
                message_id: messageId || null,
                data: data || null
            })
        });

        if (response.ok) {
            // Clear form
            document.getElementById('newPacketName').value = '';
            document.getElementById('newPacketVendorId').value = '';
            document.getElementById('newPacketMessageId').value = '';
            document.getElementById('newPacketData').value = '';

            // Reload packets
            loadDataTransferPackets();
        } else {
            alert('Error saving data transfer packet');
        }
    } catch (error) {
        console.error('Error saving data transfer packet:', error);
        alert('Error saving data transfer packet');
    }
}

async function deleteDataTransferPacket(packetId) {
    if (!confirm('Are you sure you want to delete this packet?')) {
        return;
    }

    try {
        const response = await fetch(`/api/data_transfer_packets/${packetId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadDataTransferPackets();
        } else {
            alert('Error deleting data transfer packet');
        }
    } catch (error) {
        console.error('Error deleting data transfer packet:', error);
        alert('Error deleting data transfer packet');
    }
}

function useDataTransferPacket(packetId) {
    // Find the packet in the stored data
    const packet = packetsData.find(p => p.id === packetId);
    if (!packet) {
        alert('Packet not found');
        return;
    }

    // Fill the data transfer modal
    document.getElementById('dataTransferVendorId').value = packet.vendor_id || '';
    document.getElementById('dataTransferMessageId').value = packet.message_id || '';
    document.getElementById('dataTransferData').value = packet.data || '';

    // Close packets modal and open data transfer modal
    modals.dataTransferPackets.hide();
    
    // Small delay to ensure the first modal is closed before opening the second
    setTimeout(() => {
        modals.dataTransfer.show();
        
        // Show a helpful message if no charger is selected
        if (!selectedChargerId) {
            setTimeout(() => {
                alert('Packet loaded! Please select a charger from the dropdown first, then click Send.');
            }, 500);
        }
    }, 300);
}

async function clearLocalList() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }

    if (confirm(`Are you sure you want to clear the local authorization list on charger ${selectedChargerId}?\n\nThis will remove all locally stored ID tags from the charger.`)) {
        try {
            const response = await fetch(`/api/send/${selectedChargerId}/clear_local_list`, {
                method: 'POST'
            });

            if (response.ok) {
                const result = await response.json();
                alert(`Clear Local List request sent successfully!\n\nResponse: ${JSON.stringify(result.response, null, 2)}\n\nThe charger's local authorization list has been cleared.`);
            } else {
                const error = await response.json();
                alert(`Failed to clear local list: ${error.detail}`);
            }
        } catch (error) {
            console.error('Error clearing local list:', error);
            alert('Failed to clear local list. Please try again.');
        }
    }
}

async function getLocalListVersion() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }

    try {
        const response = await fetch(`/api/send/${selectedChargerId}/get_local_list_version`, {
            method: 'GET'
        });

        if (response.ok) {
            const result = await response.json();
            const version = result.response.listVersion;
            
            let message;
            if (version === -1) {
                message = `Local List Version for ${selectedChargerId}:\n\nVersion: ${version}\n\nNo local authorization list is currently stored on the charger (version -1 indicates no list available).`;
            } else if (version === 0) {
                message = `Local List Version for ${selectedChargerId}:\n\nVersion: ${version}\n\nLocal authorization list is cleared or empty.`;
            } else {
                message = `Local List Version for ${selectedChargerId}:\n\nVersion: ${version}\n\nThe charger has version ${version} of local authorization data.`;
            }
            
            alert(message);
        } else {
            const error = await response.json();
            alert(`Failed to get local list version: ${error.detail}`);
        }
    } catch (error) {
        console.error('Error getting local list version:', error);
        alert('Failed to get local list version. Please try again.');
    }
}

function generateRandomLocalList() {
    // Default: Generate 10 random ID tags with 1-day validity (backward compatibility)
    generateCustomRandomList(10, 1);
}

function generateCustomRandomList(count = 10, validityDays = 1) {
    const tags = [];
    const now = new Date();
    const expiryDate = new Date(now.getTime() + (validityDays * 24 * 60 * 60 * 1000));
    
    for (let i = 0; i < count; i++) {
        // Generate random ID tag - exactly 20 characters as per OCPP 1.6 specification
        // Format: TAG + 17 random alphanumeric characters = 20 total characters
        let randomId = 'TAG';
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
        for (let j = 0; j < 17; j++) {
            randomId += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        
        tags.push({
            idTag: randomId,
            idTagInfo: {
                status: "Accepted",
                expiryDate: expiryDate.toISOString()
            }
        });
    }
    
    // Update the local list textarea
    const localListTextarea = document.getElementById('localListData');
    if (localListTextarea) {
        localListTextarea.value = JSON.stringify(tags, null, 2);
        
        // Show success message
        alert(`Generated ${count} random 20-character ID tags with ${validityDays} day validity (OCPP 1.6 compliant)!\n\nTags are now loaded in the Send Local List dialog. You can review and modify them before sending.\n\nGenerated tags: ${tags.map(t => t.idTag).join(', ')}`);
        
        // Also log to console for debugging
        console.log('Generated random local list:', tags);
    } else {
        console.error('Local list textarea not found');
        alert('Error: Could not find the local list input field.');
    }
}

// TriggerMessage functions
function showTriggerMessageModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Reset form
    document.getElementById('triggerMessageType').value = '';
    document.getElementById('triggerMessageConnectorId').value = '';
    document.getElementById('triggerMessageBtn').disabled = true;
    
    // Show modal
    if (!modals.triggerMessage) {
        modals.triggerMessage = new bootstrap.Modal(document.getElementById('triggerMessageModal'));
    }
    modals.triggerMessage.show();
    
    // Add event listener for message type selection
    document.getElementById('triggerMessageType').addEventListener('change', function() {
        const messageType = this.value;
        const connectorIdField = document.getElementById('triggerMessageConnectorId');
        const triggerBtn = document.getElementById('triggerMessageBtn');
        
        if (messageType) {
            triggerBtn.disabled = false;
            
            // Show/hide connector ID field based on message type
            if (messageType === 'StatusNotification' || messageType === 'MeterValues') {
                connectorIdField.required = true;
                connectorIdField.parentElement.style.display = 'block';
            } else {
                connectorIdField.required = false;
                connectorIdField.value = '';
            }
        } else {
            triggerBtn.disabled = true;
        }
    });
}

async function sendTriggerMessage() {
    const messageType = document.getElementById('triggerMessageType').value;
    const connectorId = document.getElementById('triggerMessageConnectorId').value;
    
    if (!messageType) {
        alert('Please select a message type');
        return;
    }
    
    // Validate connector ID for specific message types
    if ((messageType === 'StatusNotification' || messageType === 'MeterValues') && !connectorId) {
        alert('Connector ID is required for StatusNotification and MeterValues');
        return;
    }
    
    try {
        const requestBody = {
            requested_message: messageType
        };
        
        if (connectorId) {
            requestBody.connector_id = parseInt(connectorId);
        }
        
        const response = await fetch(`/api/send/${selectedChargerId}/trigger_message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (response.ok) {
            const result = await response.json();
            modals.triggerMessage.hide();
            
            // Show success message with response details
            let message = `TriggerMessage sent successfully!\n\nMessage Type: ${messageType}`;
            if (connectorId) {
                message += `\nConnector ID: ${connectorId}`;
            }
            if (result.response) {
                message += `\n\nCharger Response: ${JSON.stringify(result.response, null, 2)}`;
            }
            
            alert(message);
        } else {
            const error = await response.json();
            alert(`Failed to send TriggerMessage: ${error.detail}`);
        }
    } catch (error) {
        console.error('Error sending TriggerMessage:', error);
        alert('Failed to send TriggerMessage. Please try again.');
    }
}

// ============ ADVANCED FUNCTIONS ============

// === CHANGE AVAILABILITY ===

function showChangeAvailabilityModal(availabilityType = 'Inoperative') {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Set the availability type if provided
    document.getElementById('changeAvailabilityType').value = availabilityType;
    
    modals.changeAvailability.show();
}

async function changeAvailability() {
    const connectorId = parseInt(document.getElementById('changeAvailabilityConnectorId').value);
    const availabilityType = document.getElementById('changeAvailabilityType').value;
    
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    try {
        const response = await fetch(`/api/send/${selectedChargerId}/change_availability`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                connector_id: connectorId,
                availability_type: availabilityType
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            alert(`Change Availability command sent successfully!\nStatus: ${result.response?.status || 'Unknown'}`);
            modals.changeAvailability.hide();
        } else {
            const error = await response.text();
            alert(`Failed to change availability: ${error}`);
        }
    } catch (error) {
        console.error('Error changing availability:', error);
        alert(`Error changing availability: ${error.message}`);
    }
}

// === RESERVATION FUNCTIONS ===

async function showReserveNowModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Load ID tags for the dropdown
    await loadIdTagsForDropdown('reserveNowIdTag');
    await loadIdTagsForDropdown('reserveNowParentIdTag');
    
    // Set default expiry date (2 hours from now) in local time
    const now = new Date();
    now.setHours(now.getHours() + 2);
    document.getElementById('reserveNowExpiryDate').value = now.toISOString().slice(0, 16);
    
    // Display current local time for reference
    const currentTimeElement = document.getElementById('currentLocalTime');
    if (currentTimeElement) {
        const currentTime = new Date();
        const timeString = currentTime.toLocaleString('en-IN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true,
            timeZoneName: 'short'
        });
        currentTimeElement.textContent = timeString;
    }
    
    modals.reserveNow.show();
}

async function reserveNow() {
    const connectorId = parseInt(document.getElementById('reserveNowConnectorId').value);
    const idTag = document.getElementById('reserveNowIdTag').value;
    const reservationId = parseInt(document.getElementById('reserveNowReservationId').value);
    const expiryDate = document.getElementById('reserveNowExpiryDate').value;
    const parentIdTag = document.getElementById('reserveNowParentIdTag').value;
    
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    if (!idTag) {
        alert('Please select an ID tag');
        return;
    }
    
    if (!expiryDate) {
        alert('Please set an expiry date');
        return;
    }
    
    try {
        const requestBody = {
            connector_id: connectorId,
            expiry_date: new Date(expiryDate).toISOString(),
            id_tag: idTag,
            reservation_id: reservationId
        };
        
        if (parentIdTag) {
            requestBody.parent_id_tag = parentIdTag;
        }
        
        const response = await fetch(`/api/send/${selectedChargerId}/reserve_now`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (response.ok) {
            const result = await response.json();
            alert(`Reservation created successfully!\nReservation ID: ${reservationId}\nStatus: ${result.response?.status || 'Unknown'}`);
            modals.reserveNow.hide();
        } else {
            const error = await response.text();
            alert(`Failed to create reservation: ${error}`);
        }
    } catch (error) {
        console.error('Error creating reservation:', error);
        alert(`Error creating reservation: ${error.message}`);
    }
}

function showCancelReservationModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    modals.cancelReservation.show();
}

async function cancelReservation() {
    const reservationId = parseInt(document.getElementById('cancelReservationId').value);
    
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    if (!reservationId) {
        alert('Please enter a reservation ID');
        return;
    }
    
    try {
        const response = await fetch(`/api/send/${selectedChargerId}/cancel_reservation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                reservation_id: reservationId
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            alert(`Reservation cancelled successfully!\nReservation ID: ${reservationId}\nStatus: ${result.response?.status || 'Unknown'}`);
            modals.cancelReservation.hide();
        } else {
            const error = await response.text();
            alert(`Failed to cancel reservation: ${error}`);
        }
    } catch (error) {
        console.error('Error cancelling reservation:', error);
        alert(`Error cancelling reservation: ${error.message}`);
    }
}

async function showReservationsModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    await loadReservations();
    modals.reservations.show();
}

async function loadReservations() {
    try {
        const response = await fetch(`/api/reservations/${selectedChargerId}`);
        const data = await response.json();
        
        // Convert reservations object to array
        const reservationsArray = data.reservations ? Object.values(data.reservations) : [];
        displayReservations(reservationsArray);
    } catch (error) {
        console.error('Error loading reservations:', error);
        displayReservations([]);
    }
}

function displayReservations(reservations) {
    const list = document.getElementById('reservationsList');
    
    if (reservations.length === 0) {
        list.innerHTML = '<div class="alert alert-info">No active reservations found</div>';
        return;
    }
    
    list.innerHTML = '';
    
    reservations.forEach(reservation => {
        const item = document.createElement('div');
        item.className = 'list-group-item';
        
        const expiryDate = new Date(reservation.expiry_date);
        const isExpired = expiryDate < new Date();
        
        // Format expiry date as local time (the stored UTC time represents the intended local time)
        const expiryDisplay = expiryDate.toLocaleString('en-IN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true,
            timeZone: 'Asia/Kolkata'
        }) + ' IST';
        
        item.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <h6 class="mb-1">Reservation ID: ${reservation.reservation_id}</h6>
                    <p class="mb-1">
                        <strong>Connector:</strong> ${reservation.connector_id}<br>
                        <strong>ID Tag:</strong> ${reservation.id_tag}<br>
                        <strong>Expiry:</strong> ${expiryDisplay}
                        ${reservation.parent_id_tag ? `<br><strong>Parent ID Tag:</strong> ${reservation.parent_id_tag}` : ''}
                    </p>
                </div>
                <span class="badge ${isExpired ? 'bg-danger' : 'bg-success'}">
                    ${isExpired ? 'Expired' : 'Active'}
                </span>
            </div>
        `;
        
        list.appendChild(item);
    });
}

// === SMART CHARGING FUNCTIONS ===

// Charging periods are now managed dynamically without global counter

async function showSetChargingProfileModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Reset the form
    document.getElementById('setProfileConnectorId').value = '1';
    document.getElementById('setProfileId').value = '1';
    document.getElementById('setProfileStackLevel').value = '0';
    document.getElementById('setProfilePurpose').value = 'ChargePointMaxProfile';
    document.getElementById('setProfileKind').value = 'Absolute';
    document.getElementById('setProfileChargingRateUnit').value = 'W';
    document.getElementById('setProfileTransactionId').value = '';
    document.getElementById('setProfileDuration').value = '';
    
    // Reset charging periods to single period
    const periodsContainer = document.getElementById('chargingPeriods');
    periodsContainer.innerHTML = `
        <!-- Initial period -->
        <div class="charging-period border rounded p-3 mb-2" data-period-index="0">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h6 class="mb-0">Period 1</h6>
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeChargingPeriod(0)" style="display: none;">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
            <div class="row">
                <div class="col-md-4">
                    <label class="form-label">Start Period (seconds)</label>
                    <input type="number" class="form-control period-start" min="0" value="0" step="1">
                    <small class="form-text text-muted">Seconds from schedule start</small>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Limit (W or A)</label>
                    <input type="number" class="form-control period-limit" min="0.1" value="3200" step="0.1">
                    <small class="form-text text-muted">Maximum charging rate</small>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Number of Phases (optional)</label>
                    <input type="number" class="form-control period-phases" min="1" max="3" placeholder="Auto">
                    <small class="form-text text-muted">1, 2, or 3 phases</small>
                </div>
            </div>
        </div>
    `;
    
    // Set default times (1 hour from now for validFrom, 2 hours for validTo)
    const now = new Date();
    const validFrom = new Date(now.getTime() + 60 * 60 * 1000); // +1 hour
    const validTo = new Date(now.getTime() + 2 * 60 * 60 * 1000); // +2 hours
    
    document.getElementById('setProfileValidFrom').value = validFrom.toISOString().slice(0, 16);
    document.getElementById('setProfileValidTo').value = validTo.toISOString().slice(0, 16);
    
    // Set default start schedule to now
    document.getElementById('setProfileStartSchedule').value = now.toISOString().slice(0, 16);
    
    modals.setChargingProfile.show();
}

async function setChargingProfile() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    try {
        const connectorId = parseInt(document.getElementById('setProfileConnectorId').value);
        const profileId = parseInt(document.getElementById('setProfileId').value);
        const stackLevel = parseInt(document.getElementById('setProfileStackLevel').value);
        const purpose = document.getElementById('setProfilePurpose').value;
        const kind = document.getElementById('setProfileKind').value;
        const chargingRateUnit = document.getElementById('setProfileChargingRateUnit').value;
        
        // Collect all charging periods
        const chargingPeriods = [];
        const periodElements = document.querySelectorAll('.charging-period');
        
        for (let i = 0; i < periodElements.length; i++) {
            const periodEl = periodElements[i];
            const startPeriod = parseInt(periodEl.querySelector('.period-start').value);
            const limit = parseFloat(periodEl.querySelector('.period-limit').value);
            const numberPhases = periodEl.querySelector('.period-phases').value;
            
            if (isNaN(startPeriod) || isNaN(limit)) {
                alert(`Period ${i + 1}: Please enter valid start period and limit values`);
                return;
            }
            
            const period = {
                start_period: startPeriod,
                limit: limit
            };
            
            // Only add numberPhases if specified
            if (numberPhases && !isNaN(parseInt(numberPhases))) {
                period.number_phases = parseInt(numberPhases);
            }
            
            chargingPeriods.push(period);
        }
        
        // Sort periods by start_period to ensure correct order
        chargingPeriods.sort((a, b) => a.start_period - b.start_period);
        
        // Validate that periods are in ascending order and don't overlap
        for (let i = 1; i < chargingPeriods.length; i++) {
            if (chargingPeriods[i].start_period <= chargingPeriods[i-1].start_period) {
                alert(`Invalid period sequence: Period start times must be in ascending order and unique`);
                return;
            }
        }
        
        // Optional fields
        const transactionId = document.getElementById('setProfileTransactionId').value;
        const validFrom = document.getElementById('setProfileValidFrom').value;
        const validTo = document.getElementById('setProfileValidTo').value;
        const duration = document.getElementById('setProfileDuration').value;
        const startSchedule = document.getElementById('setProfileStartSchedule').value;
        
        const chargingProfile = {
            charging_profile_id: profileId,
            stack_level: stackLevel,
            charging_profile_purpose: purpose,
            charging_profile_kind: kind,
            charging_schedule: {
                charging_rate_unit: chargingRateUnit,
                charging_schedule_period: chargingPeriods
            }
        };
        
        // Add optional fields
        if (transactionId) chargingProfile.transaction_id = parseInt(transactionId);
        if (validFrom) chargingProfile.valid_from = new Date(validFrom).toISOString();
        if (validTo) chargingProfile.valid_to = new Date(validTo).toISOString();
        if (duration) chargingProfile.charging_schedule.duration = parseInt(duration);
        if (startSchedule) chargingProfile.charging_schedule.start_schedule = new Date(startSchedule).toISOString();
        
        const response = await fetch(`/api/send/${selectedChargerId}/set_charging_profile`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                connector_id: connectorId,
                cs_charging_profiles: chargingProfile
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            alert(`Charging profile set successfully!\nProfile ID: ${profileId}\nPeriods: ${chargingPeriods.length}\nStatus: ${result.response?.status || 'Unknown'}`);
            modals.setChargingProfile.hide();
        } else {
            const error = await response.text();
            alert(`Failed to set charging profile: ${error}`);
        }
    } catch (error) {
        console.error('Error setting charging profile:', error);
        alert(`Error setting charging profile: ${error.message}`);
    }
}

function addChargingPeriod() {
    const container = document.getElementById('chargingPeriods');
    
    // Get current number of periods to determine the next index
    const currentPeriods = container.querySelectorAll('.charging-period');
    const nextIndex = currentPeriods.length;
    const nextPeriodNumber = nextIndex + 1;
    
    const periodDiv = document.createElement('div');
    periodDiv.className = 'charging-period border rounded p-3 mb-2';
    periodDiv.setAttribute('data-period-index', nextIndex);
    
    // Get the last period's start time to suggest next start time
    let suggestedStart = 0;
    if (currentPeriods.length > 0) {
        const lastPeriod = currentPeriods[currentPeriods.length - 1];
        const lastStartInput = lastPeriod.querySelector('.period-start');
        const lastStartValue = parseInt(lastStartInput.value) || 0;
        suggestedStart = lastStartValue + 3600; // Add 1 hour (3600 seconds)
    }
    
    // Suggest a reasonable limit based on previous period
    let suggestedLimit = 1600; // Default
    if (currentPeriods.length > 0) {
        const lastPeriod = currentPeriods[currentPeriods.length - 1];
        const lastLimitInput = lastPeriod.querySelector('.period-limit');
        const lastLimitValue = parseFloat(lastLimitInput.value) || 3200;
        suggestedLimit = Math.max(800, lastLimitValue * 0.5); // Suggest half the previous limit, minimum 800W
    }
    
    periodDiv.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-2">
            <h6 class="mb-0">Period ${nextPeriodNumber}</h6>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeChargingPeriod(${nextIndex})">
                <i class="bi bi-trash"></i>
            </button>
        </div>
        <div class="row">
            <div class="col-md-4">
                <label class="form-label">Start Period (seconds)</label>
                <input type="number" class="form-control period-start" min="0" value="${suggestedStart}" step="1">
                <small class="form-text text-muted">Seconds from schedule start</small>
            </div>
            <div class="col-md-4">
                <label class="form-label">Limit (W or A)</label>
                <input type="number" class="form-control period-limit" min="0.1" value="${suggestedLimit}" step="0.1">
                <small class="form-text text-muted">Maximum charging rate</small>
            </div>
            <div class="col-md-4">
                <label class="form-label">Number of Phases (optional)</label>
                <input type="number" class="form-control period-phases" min="1" max="3" placeholder="Auto">
                <small class="form-text text-muted">1, 2, or 3 phases</small>
            </div>
        </div>
    `;
    
    container.appendChild(periodDiv);
    
    // Update remove button visibility for all periods
    updateRemoveButtons();
}

function removeChargingPeriod(index) {
    const periodToRemove = document.querySelector(`[data-period-index="${index}"]`);
    if (periodToRemove) {
        periodToRemove.remove();
        
        // Update period numbers and data-period-index for all remaining periods
        const remainingPeriods = document.querySelectorAll('.charging-period');
        remainingPeriods.forEach((period, idx) => {
            // Update the data-period-index attribute
            period.setAttribute('data-period-index', idx);
            
            // Update the period header text
            const header = period.querySelector('h6');
            header.textContent = `Period ${idx + 1}`;
            
            // Update the remove button onclick handler
            const removeBtn = period.querySelector('.btn-outline-danger');
            removeBtn.setAttribute('onclick', `removeChargingPeriod(${idx})`);
        });
        
        updateRemoveButtons();
    }
}

function updateRemoveButtons() {
    const periods = document.querySelectorAll('.charging-period');
    periods.forEach((period, index) => {
        const removeBtn = period.querySelector('.btn-outline-danger');
        if (periods.length <= 1) {
            removeBtn.style.display = 'none';
        } else {
            removeBtn.style.display = 'block';
        }
    });
}

function showClearChargingProfileModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    toggleClearFields(); // Initialize field visibility
    modals.clearChargingProfile.show();
}

function toggleClearFields() {
    const method = document.getElementById('clearProfileMethod').value;
    
    // Hide all fields first
    document.getElementById('clearProfileIdField').style.display = 'none';
    document.getElementById('clearProfileConnectorField').style.display = 'none';
    document.getElementById('clearProfilePurposeField').style.display = 'none';
    document.getElementById('clearProfileStackLevelField').style.display = 'none';
    
    // Show relevant fields based on method
    switch (method) {
        case 'by_id':
            document.getElementById('clearProfileIdField').style.display = 'block';
            break;
        case 'by_purpose':
            document.getElementById('clearProfilePurposeField').style.display = 'block';
            document.getElementById('clearProfileStackLevelField').style.display = 'block';
            break;
        case 'by_connector':
            document.getElementById('clearProfileConnectorField').style.display = 'block';
            document.getElementById('clearProfilePurposeField').style.display = 'block';
            document.getElementById('clearProfileStackLevelField').style.display = 'block';
            break;
        case 'all':
            // No additional fields needed
            break;
    }
}

async function clearChargingProfile() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    try {
        const method = document.getElementById('clearProfileMethod').value;
        const requestBody = {};
        
        switch (method) {
            case 'by_id':
                const profileId = document.getElementById('clearProfileId').value;
                if (!profileId) {
                    alert('Please enter a profile ID');
                    return;
                }
                requestBody.id = parseInt(profileId);
                break;
                
            case 'by_purpose':
                const purpose = document.getElementById('clearProfilePurpose').value;
                if (purpose) requestBody.charging_profile_purpose = purpose;
                
                const stackLevel = document.getElementById('clearProfileStackLevel').value;
                if (stackLevel) requestBody.stack_level = parseInt(stackLevel);
                break;
                
            case 'by_connector':
                const connectorId = document.getElementById('clearProfileConnectorId').value;
                if (!connectorId) {
                    alert('Please enter a connector ID');
                    return;
                }
                requestBody.connector_id = parseInt(connectorId);
                
                const connectorPurpose = document.getElementById('clearProfilePurpose').value;
                if (connectorPurpose) requestBody.charging_profile_purpose = connectorPurpose;
                
                const connectorStackLevel = document.getElementById('clearProfileStackLevel').value;
                if (connectorStackLevel) requestBody.stack_level = parseInt(connectorStackLevel);
                break;
                
            case 'all':
                // No parameters needed to clear all
                break;
        }
        
        const response = await fetch(`/api/send/${selectedChargerId}/clear_charging_profile`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (response.ok) {
            const result = await response.json();
            alert(`Charging profile(s) cleared successfully!\nStatus: ${result.response?.status || 'Unknown'}`);
            modals.clearChargingProfile.hide();
        } else {
            const error = await response.text();
            alert(`Failed to clear charging profile: ${error}`);
        }
    } catch (error) {
        console.error('Error clearing charging profile:', error);
        alert(`Error clearing charging profile: ${error.message}`);
    }
}

async function showChargingProfilesModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    await loadChargingProfiles();
    modals.chargingProfiles.show();
}

async function loadChargingProfiles() {
    try {
        const connectorId = document.getElementById('viewProfilesConnectorId').value;
        let url = `/api/charging_profiles/${selectedChargerId}`;
        if (connectorId) {
            url += `?connector_id=${connectorId}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        displayChargingProfiles(data.charging_profiles || []);
    } catch (error) {
        console.error('Error loading charging profiles:', error);
        displayChargingProfiles([]);
    }
}

function displayChargingProfiles(profiles) {
    const list = document.getElementById('chargingProfilesList');
    
    // Convert nested object structure to flat array
    const profilesArray = [];
    
    if (profiles && typeof profiles === 'object') {
        // Handle nested structure: { "connector_1": { "1": profile_data, "2": profile_data } }
        for (const connectorKey in profiles) {
            const connectorProfiles = profiles[connectorKey];
            if (connectorProfiles && typeof connectorProfiles === 'object') {
                for (const profileId in connectorProfiles) {
                    const profile = connectorProfiles[profileId];
                    if (profile) {
                        profilesArray.push(profile);
                    }
                }
            }
        }
    }
    
    if (profilesArray.length === 0) {
        list.innerHTML = '<div class="alert alert-info">No charging profiles found</div>';
        return;
    }
    
    list.innerHTML = '';
    
    profilesArray.forEach(profile => {
        const item = document.createElement('div');
        item.className = 'list-group-item';
        
        const schedule = profile.charging_schedule || {};
        const periods = schedule.charging_schedule_period || [];
        
        // Handle both snake_case and camelCase field names
        const profileId = profile.charging_profile_id || profile.chargingProfileId;
        const stackLevel = profile.stack_level || profile.stackLevel;
        const purpose = profile.charging_profile_purpose || profile.chargingProfilePurpose;
        const kind = profile.charging_profile_kind || profile.chargingProfileKind;
        const transactionId = profile.transaction_id || profile.transactionId;
        const validFrom = profile.valid_from || profile.validFrom;
        const validTo = profile.valid_to || profile.validTo;
        
        item.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="mb-1">Profile ID: ${profileId}</h6>
                    <p class="mb-1">
                        <strong>Connector:</strong> ${profile.connector_id || 'N/A'}<br>
                        <strong>Stack Level:</strong> ${stackLevel}<br>
                        <strong>Purpose:</strong> ${purpose}<br>
                        <strong>Kind:</strong> ${kind}<br>
                        ${transactionId ? `<strong>Transaction ID:</strong> ${transactionId}<br>` : ''}
                    </p>
                </div>
                <div class="col-md-6">
                    <p class="mb-1">
                        ${validFrom ? `<strong>Valid From:</strong> ${formatToIST(validFrom)}<br>` : ''}
                        ${validTo ? `<strong>Valid To:</strong> ${formatToIST(validTo)}<br>` : ''}
                        <strong>Rate Unit:</strong> ${schedule.charging_rate_unit || 'N/A'}<br>
                        ${schedule.duration ? `<strong>Duration:</strong> ${schedule.duration}s<br>` : ''}
                        <strong>Periods:</strong> ${periods.length}
                    </p>
                </div>
            </div>
            ${periods.length > 0 ? `
                <div class="mt-2">
                    <h6>Schedule Periods:</h6>
                    ${periods.map(period => `
                        <small class="badge bg-secondary me-1">
                            Start: ${period.start_period}s, Limit: ${period.limit}${schedule.charging_rate_unit || ''}
                            ${period.number_phases ? `, Phases: ${period.number_phases}` : ''}
                        </small>
                    `).join('')}
                </div>
            ` : ''}
            <div class="mt-2">
                <small class="text-muted">Created: ${profile.created_at ? formatToIST(profile.created_at) : 'Unknown'}</small>
            </div>
        `;
        
        list.appendChild(item);
    });
}

function showGetCompositeScheduleModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Hide result section
    document.getElementById('compositeScheduleResult').style.display = 'none';
    
    modals.getCompositeSchedule.show();
}

async function getCompositeSchedule() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    try {
        const connectorId = parseInt(document.getElementById('getScheduleConnectorId').value);
        const duration = parseInt(document.getElementById('getScheduleDuration').value);
        const chargingRateUnit = document.getElementById('getScheduleChargingRateUnit').value;
        
        const requestBody = {
            connector_id: connectorId,
            duration: duration
        };
        
        if (chargingRateUnit) {
            requestBody.charging_rate_unit = chargingRateUnit;
        }
        
        const response = await fetch(`/api/send/${selectedChargerId}/get_composite_schedule`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (response.ok) {
            const result = await response.json();
            displayCompositeScheduleResult(result.response);
        } else {
            const error = await response.text();
            alert(`Failed to get composite schedule: ${error}`);
        }
    } catch (error) {
        console.error('Error getting composite schedule:', error);
        alert(`Error getting composite schedule: ${error.message}`);
    }
}

function displayCompositeScheduleResult(scheduleResponse) {
    const resultDiv = document.getElementById('compositeScheduleResult');
    const detailsDiv = document.getElementById('scheduleDetails');
    
    if (!scheduleResponse) {
        detailsDiv.innerHTML = '<i class="bi bi-exclamation-triangle"></i> No schedule data received';
        resultDiv.style.display = 'block';
        return;
    }
    
    const schedule = scheduleResponse.charging_schedule;
    let html = `
        <h6><i class="bi bi-check-circle"></i> Composite Schedule Retrieved</h6>
        <p><strong>Status:</strong> ${scheduleResponse.status || 'Unknown'}</p>
        <p><strong>Connector ID:</strong> ${scheduleResponse.connector_id || 'N/A'}</p>
        ${scheduleResponse.schedule_start ? `<p><strong>Schedule Start:</strong> ${formatToIST(scheduleResponse.schedule_start)}</p>` : ''}
    `;
    
    if (schedule) {
        html += `
            <hr>
            <h6>Schedule Details:</h6>
            <p><strong>Rate Unit:</strong> ${schedule.charging_rate_unit || 'N/A'}</p>
            ${schedule.duration ? `<p><strong>Duration:</strong> ${schedule.duration} seconds</p>` : ''}
            ${schedule.start_schedule ? `<p><strong>Start Schedule:</strong> ${formatToIST(schedule.start_schedule)}</p>` : ''}
        `;
        
        if (schedule.charging_schedule_period && schedule.charging_schedule_period.length > 0) {
            html += `
                <h6>Schedule Periods:</h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Start (s)</th>
                                <th>Limit</th>
                                <th>Phases</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${schedule.charging_schedule_period.map(period => `
                                <tr>
                                    <td>${period.start_period}</td>
                                    <td>${period.limit} ${schedule.charging_rate_unit || ''}</td>
                                    <td>${period.number_phases || 'N/A'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            html += '<p><em>No schedule periods defined</em></p>';
        }
    } else {
        html += '<p><em>No schedule details available</em></p>';
    }
    
    detailsDiv.innerHTML = html;
    resultDiv.style.display = 'block';
}

// Helper function to load ID tags for dropdowns
async function loadIdTagsForDropdown(selectId) {
    try {
        const response = await fetch('/api/idtags');
        const data = await response.json();
        const select = document.getElementById(selectId);
        
        select.innerHTML = '';
        
        // Add "None" option for parent ID tag dropdown
        if (selectId === 'reserveNowParentIdTag') {
            select.innerHTML = '<option value="">None</option>';
        }
        
        // Convert the object format {tag_id: {tag_data}} to array format
        const idTagsArray = Object.values(data);
        
        if (idTagsArray && idTagsArray.length > 0) {
            // Sort ID tags: accepted first, then others
            const sortedTags = idTagsArray.sort((a, b) => {
                // First sort by status (accepted first)
                if (a.status !== b.status) {
                    if (a.status === 'Accepted') return -1;
                    if (b.status === 'Accepted') return 1;
                }
                // Then sort by ID tag name alphabetically
                return a.id_tag.localeCompare(b.id_tag);
            });
            
            sortedTags.forEach(tag => {
                const option = document.createElement('option');
                option.value = tag.id_tag;
                
                // Improve display format with status icons
                const statusIcon = tag.status === 'Accepted' ? '✅' : 
                                 tag.status === 'Blocked' ? '🚫' : 
                                 tag.status === 'Expired' ? '⏰' : 
                                 tag.status === 'Invalid' ? '❌' : '❓';
                
                option.textContent = `${statusIcon} ${tag.id_tag} (${tag.status})`;
                
                // Highlight accepted tags
                if (tag.status === 'Accepted') {
                    option.style.fontWeight = 'bold';
                    option.style.color = '#28a745'; // Green color for accepted
                } else if (tag.status === 'Blocked' || tag.status === 'Invalid') {
                    option.style.color = '#dc3545'; // Red color for blocked/invalid
                } else if (tag.status === 'Expired') {
                    option.style.color = '#ffc107'; // Yellow color for expired
                }
                
                select.appendChild(option);
            });
            
            // Add a hint to select an accepted tag if none selected
            if (selectId !== 'reserveNowParentIdTag') {
                const hintOption = document.createElement('option');
                hintOption.value = '';
                hintOption.textContent = '-- Select an ID Tag --';
                hintOption.disabled = true;
                hintOption.selected = true;
                hintOption.style.fontStyle = 'italic';
                hintOption.style.color = '#6c757d';
                select.insertBefore(hintOption, select.firstChild);
            }
        } else {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No ID tags available - Please add ID tags first';
            option.disabled = true;
            option.selected = true;
            option.style.fontStyle = 'italic';
            option.style.color = '#dc3545';
            select.appendChild(option);
        }
    } catch (error) {
        console.error('Error loading ID tags:', error);
        const select = document.getElementById(selectId);
        select.innerHTML = '<option value="" disabled selected>Error loading ID tags</option>';
    }
}

// === FIRMWARE UPDATE & DIAGNOSTICS FUNCTIONS ===

function showUpdateFirmwareModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Set default retrieve date to 5 minutes from now
    const now = new Date();
    now.setMinutes(now.getMinutes() + 5);
    const localISOTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    document.getElementById('firmwareRetrieveDate').value = localISOTime;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('updateFirmwareModal'));
    modal.show();
}

function showGetDiagnosticsModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Clear previous values
    document.getElementById('diagnosticsLocation').value = '';
    document.getElementById('diagnosticsStartTime').value = '';
    document.getElementById('diagnosticsStopTime').value = '';
    document.getElementById('diagnosticsRetries').value = '';
    document.getElementById('diagnosticsRetryInterval').value = '';
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('getDiagnosticsModal'));
    modal.show();
}

async function updateFirmware() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    const location = document.getElementById('firmwareLocation').value.trim();
    const retrieveDate = document.getElementById('firmwareRetrieveDate').value;
    const retries = document.getElementById('firmwareRetries').value;
    const retryInterval = document.getElementById('firmwareRetryInterval').value;
    
    if (!location) {
        alert('Please enter firmware location URL');
        return;
    }
    
    if (!retrieveDate) {
        alert('Please select retrieve date');
        return;
    }
    
    // Convert local datetime to ISO string
    const retrieveDateISO = new Date(retrieveDate).toISOString();
    
    try {
        const requestData = {
            location: location,
            retrieve_date: retrieveDateISO
        };
        
        if (retries) {
            requestData.retries = parseInt(retries);
        }
        if (retryInterval) {
            requestData.retry_interval = parseInt(retryInterval);
        }
        
        const response = await fetch(`/api/send/${selectedChargerId}/update_firmware`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`✅ UpdateFirmware command sent successfully!\n\nThe charger will download firmware from:\n${location}\n\nAt: ${new Date(retrieveDateISO).toLocaleString()}`);
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('updateFirmwareModal'));
            modal.hide();
            
            // Refresh logs to see the command
            await loadLogs();
        } else {
            alert(`❌ Error: ${result.detail || 'Failed to send UpdateFirmware command'}`);
        }
    } catch (error) {
        console.error('Error sending UpdateFirmware:', error);
        alert(`❌ Error sending UpdateFirmware command: ${error.message}`);
    }
}

async function getDiagnostics() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    const location = document.getElementById('diagnosticsLocation').value.trim();
    const startTime = document.getElementById('diagnosticsStartTime').value;
    const stopTime = document.getElementById('diagnosticsStopTime').value;
    const retries = document.getElementById('diagnosticsRetries').value;
    const retryInterval = document.getElementById('diagnosticsRetryInterval').value;
    
    if (!location) {
        alert('Please enter diagnostics upload location URL');
        return;
    }
    
    try {
        const requestData = {
            location: location
        };
        
        if (startTime) {
            requestData.start_time = new Date(startTime).toISOString();
        }
        if (stopTime) {
            requestData.stop_time = new Date(stopTime).toISOString();
        }
        if (retries) {
            requestData.retries = parseInt(retries);
        }
        if (retryInterval) {
            requestData.retry_interval = parseInt(retryInterval);
        }
        
        const response = await fetch(`/api/send/${selectedChargerId}/get_diagnostics`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            let message = `✅ GetDiagnostics command sent successfully!\n\nThe charger will upload diagnostics to:\n${location}`;
            
            if (result.response && result.response.fileName) {
                message += `\n\nExpected filename: ${result.response.fileName}`;
            }
            
            if (startTime) {
                message += `\n\nDiagnostic period start: ${new Date(startTime).toLocaleString()}`;
            }
            if (stopTime) {
                message += `\nDiagnostic period end: ${new Date(stopTime).toLocaleString()}`;
            }
            
            alert(message);
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('getDiagnosticsModal'));
            modal.hide();
            
            // Refresh logs to see the command
            await loadLogs();
        } else {
            alert(`❌ Error: ${result.detail || 'Failed to send GetDiagnostics command'}`);
        }
    } catch (error) {
        console.error('Error sending GetDiagnostics:', error);
        alert(`❌ Error sending GetDiagnostics command: ${error.message}`);
    }
}

function showUnlockConnectorModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Reset form
    document.getElementById('unlockConnectorId').value = '';
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('unlockConnectorModal'));
    modal.show();
}

async function unlockConnector() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    const connectorId = document.getElementById('unlockConnectorId').value;
    
    if (!connectorId) {
        alert('Please select a connector to unlock');
        return;
    }
    
    // Confirm the action
    if (!confirm(`Are you sure you want to unlock connector ${connectorId}?\n\nThis will physically unlock the connector and may interrupt any ongoing charging session.`)) {
        return;
    }
    
    try {
        const requestData = {
            connector_id: parseInt(connectorId)
        };
        
        const response = await fetch(`/api/send/${selectedChargerId}/unlock_connector`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            const status = result.response ? result.response.status : 'Unknown';
            let message = `✅ UnlockConnector command sent successfully!\n\nConnector: ${connectorId}\nStatus: ${status}`;
            
            // Add status explanation
            switch (status) {
                case 'Unlocked':
                    message += '\n\n🔓 The connector has been successfully unlocked.';
                    break;
                case 'UnlockFailed':
                    message += '\n\n❌ Failed to unlock the connector. Please check the charger status.';
                    break;
                case 'NotSupported':
                    message += '\n\n⚠️ This charger does not support remote connector unlocking.';
                    break;
                default:
                    message += '\n\n❓ Unknown response status.';
            }
            
            alert(message);
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('unlockConnectorModal'));
            modal.hide();
            
            // Refresh logs to see the command
            await loadLogs();
        } else {
            alert(`❌ Error: ${result.detail || 'Failed to send UnlockConnector command'}`);
        }
    } catch (error) {
        console.error('Error sending UnlockConnector:', error);
        alert(`❌ Error sending UnlockConnector command: ${error.message}`);
    }
}

// === JIO_BP DATA TRANSFER FUNCTIONS ===

async function showJioBpSettingsModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Load current settings
    await loadJioBpSettings();
    
    modals.jioBpSettings.show();
}

async function loadJioBpSettings() {
    try {
        const response = await fetch(`/api/jio_bp_settings/${selectedChargerId}`);
        const data = await response.json();
        
        const settings = data.settings;
        
        // Update form fields
        document.getElementById('stopEnergyEnabled').checked = settings.stop_energy_enabled;
        document.getElementById('stopEnergyValue').value = settings.stop_energy_value;
        document.getElementById('stopTimeEnabled').checked = settings.stop_time_enabled;
        document.getElementById('stopTimeValue').value = settings.stop_time_value;
        
        // Update field states
        toggleStopEnergyFields();
        toggleStopTimeFields();
        updatePreviews();
        
    } catch (error) {
        console.error('Error loading Jio_BP settings:', error);
        // Set defaults if loading fails
        document.getElementById('stopEnergyEnabled').checked = false;
        document.getElementById('stopEnergyValue').value = 10;
        document.getElementById('stopTimeEnabled').checked = false;
        document.getElementById('stopTimeValue').value = 10;
        toggleStopEnergyFields();
        toggleStopTimeFields();
        updatePreviews();
    }
}

function toggleStopEnergyFields() {
    const enabled = document.getElementById('stopEnergyEnabled').checked;
    const valueField = document.getElementById('stopEnergyValue');
    
    valueField.disabled = !enabled;
    
    if (enabled) {
        document.getElementById('stopEnergyFields').style.opacity = '1';
    } else {
        document.getElementById('stopEnergyFields').style.opacity = '0.5';
    }
    
    updatePreviews();
}

function toggleStopTimeFields() {
    const enabled = document.getElementById('stopTimeEnabled').checked;
    const valueField = document.getElementById('stopTimeValue');
    
    valueField.disabled = !enabled;
    
    if (enabled) {
        document.getElementById('stopTimeFields').style.opacity = '1';
    } else {
        document.getElementById('stopTimeFields').style.opacity = '0.5';
    }
    
    updatePreviews();
}

function updatePreviews() {
    const energyValue = document.getElementById('stopEnergyValue').value;
    const timeValue = document.getElementById('stopTimeValue').value;
    
    document.getElementById('stopEnergyPreview').textContent = `TransactionID_${energyValue}`;
    document.getElementById('stopTimePreview').textContent = `TransactionID_${timeValue}`;
}

async function saveJioBpSettings() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    const settings = {
        stop_energy_enabled: document.getElementById('stopEnergyEnabled').checked,
        stop_energy_value: parseFloat(document.getElementById('stopEnergyValue').value),
        stop_time_enabled: document.getElementById('stopTimeEnabled').checked,
        stop_time_value: parseInt(document.getElementById('stopTimeValue').value)
    };
    
    try {
        const response = await fetch(`/api/jio_bp_settings/${selectedChargerId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            const result = await response.json();
            alert('Jio_BP settings saved successfully!\n\nThese data transfer packets will now be sent automatically 500ms after StartTransaction responses.');
            modals.jioBpSettings.hide();
        } else {
            const error = await response.text();
            alert(`Failed to save Jio_BP settings: ${error}`);
        }
    } catch (error) {
        console.error('Error saving Jio_BP settings:', error);
        alert(`Error saving Jio_BP settings: ${error.message}`);
    }
}

async function clearJioBpSettings() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    if (!confirm('Are you sure you want to clear all Jio_BP settings for this charger?\n\nThis will disable automatic data transfer packets.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/jio_bp_settings/${selectedChargerId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Jio_BP settings cleared successfully!');
            
            // Reset form to defaults
            document.getElementById('stopEnergyEnabled').checked = false;
            document.getElementById('stopEnergyValue').value = 10;
            document.getElementById('stopTimeEnabled').checked = false;
            document.getElementById('stopTimeValue').value = 10;
            toggleStopEnergyFields();
            toggleStopTimeFields();
            updatePreviews();
            
            modals.jioBpSettings.hide();
        } else {
            const error = await response.text();
            alert(`Failed to clear Jio_BP settings: ${error}`);
        }
    } catch (error) {
        console.error('Error clearing Jio_BP settings:', error);
        alert(`Error clearing Jio_BP settings: ${error.message}`);
    }
}

// === MSIL DATA TRANSFER FUNCTIONS ===

async function showMsilSettingsModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Load current settings
    await loadMsilSettings();
    
    modals.msilSettings.show();
}

async function loadMsilSettings() {
    try {
        const response = await fetch(`/api/msil_settings/${selectedChargerId}`);
        const data = await response.json();
        
        const settings = data.settings;
        
        // Update form fields
        document.getElementById('msilAutoStopEnabled').checked = settings.auto_stop_enabled;
        document.getElementById('msilEnergyValue').value = settings.stop_energy_value;
        
        // Update field states
        toggleMsilFields();
        updateMsilPreview();
        
    } catch (error) {
        console.error('Error loading MSIL settings:', error);
        // Set defaults if loading fails
        document.getElementById('msilAutoStopEnabled').checked = false;
        document.getElementById('msilEnergyValue').value = 1000;
        toggleMsilFields();
        updateMsilPreview();
    }
}

function toggleMsilFields() {
    const enabled = document.getElementById('msilAutoStopEnabled').checked;
    const valueField = document.getElementById('msilEnergyValue');
    
    valueField.disabled = !enabled;
    
    if (enabled) {
        document.getElementById('msilFields').style.opacity = '1';
    } else {
        document.getElementById('msilFields').style.opacity = '0.5';
    }
    
    updateMsilPreview();
}

function updateMsilPreview() {
    const energyValue = document.getElementById('msilEnergyValue').value;
    document.getElementById('msilPreview').textContent = `{"transactionId": TransactionID, "parameter": "Stop_Energy", "value": ${energyValue}}`;
}

async function saveMsilSettings() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    const settings = {
        auto_stop_enabled: document.getElementById('msilAutoStopEnabled').checked,
        stop_energy_value: parseFloat(document.getElementById('msilEnergyValue').value)
    };
    
    try {
        const response = await fetch(`/api/msil_settings/${selectedChargerId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            alert('MSIL settings saved successfully!\n\nAutoStop packets will now be sent automatically 500ms after StartTransaction responses.');
            modals.msilSettings.hide();
        } else {
            const error = await response.text();
            alert(`Failed to save MSIL settings: ${error}`);
        }
    } catch (error) {
        console.error('Error saving MSIL settings:', error);
        alert(`Error saving MSIL settings: ${error.message}`);
    }
}

async function clearMsilSettings() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    if (!confirm('Are you sure you want to clear all MSIL settings for this charger?\n\nThis will disable automatic AutoStop packets.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/msil_settings/${selectedChargerId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('MSIL settings cleared successfully!');
            
            // Reset form to defaults
            document.getElementById('msilAutoStopEnabled').checked = false;
            document.getElementById('msilEnergyValue').value = 1000;
            toggleMsilFields();
            updateMsilPreview();
            
            modals.msilSettings.hide();
        } else {
            const error = await response.text();
            alert(`Failed to clear MSIL settings: ${error}`);
        }
    } catch (error) {
        console.error('Error clearing MSIL settings:', error);
        alert(`Error clearing MSIL settings: ${error.message}`);
    }
}

// === CZ DATA TRANSFER FUNCTIONS ===

async function showCzSettingsModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Load current settings
    await loadCzSettings();
    
    modals.czSettings.show();
}

async function loadCzSettings() {
    try {
        const response = await fetch(`/api/cz_settings/${selectedChargerId}`);
        const data = await response.json();
        
        const settings = data.settings;
        
        // Update form fields
        document.getElementById('czAutoStopEnabled').checked = settings.auto_stop_enabled;
        document.getElementById('czEnergyValue').value = settings.stop_energy_value;
        
        // Update field states
        toggleCzFields();
        updateCzPreview();
        
    } catch (error) {
        console.error('Error loading CZ settings:', error);
        // Set defaults if loading fails
        document.getElementById('czAutoStopEnabled').checked = false;
        document.getElementById('czEnergyValue').value = 2000;
        toggleCzFields();
        updateCzPreview();
    }
}

function toggleCzFields() {
    const enabled = document.getElementById('czAutoStopEnabled').checked;
    const valueField = document.getElementById('czEnergyValue');
    
    valueField.disabled = !enabled;
    
    if (enabled) {
        document.getElementById('czFields').style.opacity = '1';
    } else {
        document.getElementById('czFields').style.opacity = '0.5';
    }
    
    updateCzPreview();
}

function updateCzPreview() {
    const energyValue = document.getElementById('czEnergyValue').value;
    document.getElementById('czPreview').textContent = `"{\\"transactionId\\":TransactionID,\\"parameter\\":\\"Stop_Energy\\",\\"value\\":${energyValue}}"`;
}

async function saveCzSettings() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    const settings = {
        auto_stop_enabled: document.getElementById('czAutoStopEnabled').checked,
        stop_energy_value: parseFloat(document.getElementById('czEnergyValue').value)
    };
    
    try {
        const response = await fetch(`/api/cz_settings/${selectedChargerId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            alert('CZ settings saved successfully!\n\nAutoStop packets will now be sent automatically 500ms after StartTransaction responses.');
            modals.czSettings.hide();
        } else {
            const error = await response.text();
            alert(`Failed to save CZ settings: ${error}`);
        }
    } catch (error) {
        console.error('Error saving CZ settings:', error);
        alert(`Error saving CZ settings: ${error.message}`);
    }
}

async function clearCzSettings() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    if (!confirm('Are you sure you want to clear all CZ settings for this charger?\n\nThis will disable automatic AutoStop packets.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/cz_settings/${selectedChargerId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('CZ settings cleared successfully!');
            
            // Reset form to defaults
            document.getElementById('czAutoStopEnabled').checked = false;
            document.getElementById('czEnergyValue').value = 2000;
            toggleCzFields();
            updateCzPreview();
            
            modals.czSettings.hide();
        } else {
            const error = await response.text();
            alert(`Failed to clear CZ settings: ${error}`);
        }
    } catch (error) {
        console.error('Error clearing CZ settings:', error);
        alert(`Error clearing CZ settings: ${error.message}`);
    }
}

// Add event listeners for real-time preview updates
document.addEventListener('DOMContentLoaded', function() {
    // Add jioBpSettings modal to the modals object
    if (typeof modals !== 'undefined') {
        modals.jioBpSettings = new bootstrap.Modal(document.getElementById('jioBpSettingsModal'));
    }
    
    // Add event listeners for preview updates
    const stopEnergyValue = document.getElementById('stopEnergyValue');
    const stopTimeValue = document.getElementById('stopTimeValue');
    
    if (stopEnergyValue) {
        stopEnergyValue.addEventListener('input', updatePreviews);
    }
    
    if (stopTimeValue) {
        stopTimeValue.addEventListener('input', updatePreviews);
    }

    // Add event listeners for MSIL preview updates
    const msilEnergyValue = document.getElementById('msilEnergyValue');
    if (msilEnergyValue) {
        msilEnergyValue.addEventListener('input', updateMsilPreview);
    }

    // Add event listeners for CZ preview updates
    const czEnergyValue = document.getElementById('czEnergyValue');
    if (czEnergyValue) {
        czEnergyValue.addEventListener('input', updateCzPreview);
    }
});

// === UI CONFIGURATION FUNCTIONS ===

async function loadCurrentUIFeatures() {
    try {
        const response = await fetch('/api/config/ui-features');
        const data = await response.json();
        
        if (data.status === 'success') {
            // Update the checkboxes with current configuration
            const features = data.data;
            document.getElementById('showJioBpDataTransfer').checked = features.show_jio_bp_data_transfer || false;
            document.getElementById('showMsilDataTransfer').checked = features.show_msil_data_transfer || false;
            document.getElementById('showCzDataTransfer').checked = features.show_cz_data_transfer || false;
            
            // Show success message
            showToast('Configuration reloaded successfully!', 'success');
        } else {
            showToast('Error loading configuration: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error loading UI features:', error);
        showToast('Error loading configuration!', 'error');
    }
}

async function saveUIFeatures() {
    try {
        const features = {
            show_jio_bp_data_transfer: document.getElementById('showJioBpDataTransfer').checked,
            show_msil_data_transfer: document.getElementById('showMsilDataTransfer').checked,
            show_cz_data_transfer: document.getElementById('showCzDataTransfer').checked
        };
        
        const response = await fetch('/api/config/ui-features', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(features)
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showToast('Configuration saved successfully! Please refresh the page to see changes.', 'success');
            
            // Show reload button
            setTimeout(() => {
                const reloadConfirm = confirm('Configuration saved! Would you like to reload the page now to see the changes?');
                if (reloadConfirm) {
                    window.location.reload();
                }
            }, 1000);
        } else {
            showToast('Error saving configuration: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error saving UI features:', error);
        showToast('Error saving configuration!', 'error');
    }
}

// Simple toast notification function
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1055';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="bi bi-${type === 'success' ? 'check-circle text-success' : type === 'error' ? 'exclamation-triangle text-danger' : 'info-circle text-info'}"></i>
                <strong class="me-auto ms-2">Configuration</strong>
                <small>just now</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Show the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: type === 'success' ? 5000 : 3000
    });
    toast.show();
    
    // Remove the toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// === RAW MESSAGE FUNCTIONS ===

function showRawMessageModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Clear the textarea
    document.getElementById('rawMessageContent').value = '';
    
    modals.rawMessage.show();
}

function loadRawMessageExample(type) {
    const textarea = document.getElementById('rawMessageContent');
    const messageId = `msg-${Date.now()}`;
    let example = '';
    
    switch (type) {
        case 'dataTransfer':
            example = `[2, "${messageId}", "DataTransfer", {"vendorId": "Custom", "messageId": "TestMessage", "data": "test-data"}]`;
            break;
        case 'getConfiguration':
            example = `[2, "${messageId}", "GetConfiguration", {}]`;
            break;
        case 'reset':
            example = `[2, "${messageId}", "Reset", {"type": "Soft"}]`;
            break;
        case 'custom':
            example = `[2, "${messageId}", "CustomAction", {"customField": "customValue", "number": 123}]`;
            break;
        default:
            example = `[2, "${messageId}", "DataTransfer", {"vendorId": "Test", "data": "example"}]`;
    }
    
    textarea.value = example;
}

async function sendRawMessage() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    const rawMessage = document.getElementById('rawMessageContent').value.trim();
    
    if (!rawMessage) {
        alert('Please enter a raw message');
        return;
    }
    
    // Validate JSON format
    try {
        JSON.parse(rawMessage);
    } catch (e) {
        alert('Invalid JSON format. Please check your message syntax.');
        return;
    }
    
    // Confirm action due to potential risks
    const confirmed = confirm(
        `⚠️ WARNING ⚠️\n\n` +
        `You are about to send a raw WebSocket message without OCPP validation.\n\n` +
        `Message: ${rawMessage.substring(0, 100)}${rawMessage.length > 100 ? '...' : ''}\n\n` +
        `This could cause unexpected charger behavior. Continue?`
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch(`/api/send/${selectedChargerId}/raw_message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                raw_message: rawMessage
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            alert('✅ Raw message sent successfully!\n\nCheck the charger logs to see the response.');
            modals.rawMessage.hide();
        } else {
            const error = await response.text();
            alert(`❌ Failed to send raw message:\n${error}`);
        }
    } catch (error) {
        console.error('Error sending raw message:', error);
        alert(`❌ Error sending raw message:\n${error.message}`);
    }
}

// === DELETE CHARGER FUNCTIONALITY ===

function showDeleteChargerModal() {
    if (!selectedChargerId) {
        alert('Please select a charger first');
        return;
    }
    
    // Set the charger name in the modal
    document.getElementById('deleteChargerName').textContent = selectedChargerId;
    
    // Clear the confirmation checkbox
    const confirmCheckbox = document.getElementById('confirmDelete');
    confirmCheckbox.checked = false;
    
    // Disable the delete button initially
    document.getElementById('confirmDeleteBtn').disabled = true;
    
    // Remove any existing event listeners to prevent accumulation
    const newCheckbox = confirmCheckbox.cloneNode(true);
    confirmCheckbox.parentNode.replaceChild(newCheckbox, confirmCheckbox);
    
    // Add checkbox validation
    newCheckbox.addEventListener('change', function() {
        const deleteBtn = document.getElementById('confirmDeleteBtn');
        deleteBtn.disabled = !this.checked;
    });
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('deleteChargerModal'));
    modal.show();
}

async function deleteCharger() {
    if (!selectedChargerId) {
        alert('No charger selected');
        return;
    }
    
    // Validate checkbox
    const confirmCheckbox = document.getElementById('confirmDelete');
    if (!confirmCheckbox.checked) {
        alert('Please confirm that you understand this action is permanent');
        return;
    }
    
    // Final confirmation
    if (!confirm(`Are you absolutely sure you want to delete charger "${selectedChargerId}" and ALL its data? This action cannot be undone!`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/chargers/${selectedChargerId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            
            // Hide the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteChargerModal'));
            modal.hide();
            
            // Show success message
            showToast(`Charger "${selectedChargerId}" and all its data have been permanently deleted.`, 'success');
            
            // Clear selection and refresh the charger list
            selectedChargerId = null;
            const selectedChargerElement = document.getElementById('selectedCharger');
            if (selectedChargerElement) {
                selectedChargerElement.textContent = 'None';
            }
            
            // Clear logs
            const logContainer = document.getElementById('logContainer');
            if (logContainer) {
                logContainer.innerHTML = '<div class="alert alert-info">Select a charger to view logs</div>';
            }
            
            // Refresh the charger list
            await pollChargers();
            
        } else {
            const error = await response.text();
            showToast(`Failed to delete charger: ${error}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting charger:', error);
        showToast(`Error deleting charger: ${error.message}`, 'error');
    }
} 