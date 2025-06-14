// Global variables
let selectedChargerId = null;
let logPollingInterval = null;
let autoScrollEnabled = true;
let currentLogs = []; // Store current logs for CSV download
const POLLING_INTERVAL = 2000; // 2 seconds

// Store packets data for easy access
let packetsData = [];

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
    dataTransferPackets: new bootstrap.Modal(document.getElementById('dataTransferPacketsModal'))
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
});

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

// Update charger list in UI
function updateChargerList(chargers) {
    const list = document.getElementById('chargerList');
    
    if (!list) {
        console.error('Charger list element not found');
        return;
    }
    
    list.innerHTML = '';

    // Show all chargers in the list
    chargers.forEach(charger => {
        const item = document.createElement('div');
        item.className = `list-group-item list-group-item-action ${charger.id === selectedChargerId ? 'active' : ''}`;
        item.style.cursor = 'pointer';
        
        // Get connector status
        let connectorStatus = 'Available';
        if (charger.connector_status && typeof charger.connector_status === 'object') {
            // Find the first connector status
            for (const [key, value] of Object.entries(charger.connector_status)) {
                if (key.startsWith('connector_') && value && typeof value === 'object' && value.status) {
                    connectorStatus = value.status;
                    break;
                }
            }
        }
        
        // Get status display and charging indicator
        let statusDisplay = charger.connected ? (connectorStatus || 'Connected') : 'Disconnected';
        let statusClass = charger.connected ? 'bg-success' : 'bg-danger';
        
        const isCharging = connectorStatus && ['charging', 'preparing'].includes(connectorStatus.toLowerCase());
        const chargingIndicator = isCharging ? '<i class="bi bi-lightning-charge-fill text-warning"></i> ' : '';
        const transactionInfo = isCharging ? '<br><small class="text-warning"><i class="bi bi-info-circle"></i> Active transaction</small>' : '';
        
        item.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">${chargingIndicator}${charger.id}</h6>
                    <small class="text-muted">Status: ${statusDisplay}</small>
                    <br>
                    <small class="text-muted">Last seen: ${charger.last_seen ? new Date(charger.last_seen).toLocaleString() : 'Never'}</small>
                    ${transactionInfo}
                </div>
                <span class="badge ${statusClass}">
                    ${charger.connected ? 'Connected' : 'Disconnected'}
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
    container.innerHTML = '';
    
    // Store logs for CSV download
    currentLogs = logs;

    logs.forEach(log => {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        
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

    // Auto-scroll to bottom if enabled
    if (autoScrollEnabled) {
        container.scrollTop = container.scrollHeight;
    }
}

// Clear logs
function clearLogs() {
    document.getElementById('logContainer').innerHTML = '';
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
    const csvHeaders = ['Charger ID', 'IST Time', 'UTC Time', 'Message Path', 'Payload'];
    let csvContent = csvHeaders.join(',') + '\n';
    
    currentLogs.forEach(log => {
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
        
        // Format IST time (UTC + 5:30)
        const istTime = timestamp.toLocaleString('en-IN', { 
            timeZone: 'Asia/Kolkata',
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        
        // Format UTC time
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
        
        // Determine message path from log message
        let messagePath = '';
        let payload = '';
        
        // Parse the log message to extract direction and payload
        const message = log.message;
        if (message.includes('send [')) {
            messagePath = 'CMS->Charger';
            // Extract JSON payload from send message
            const match = message.match(/send \[(.*)\]/);
            if (match) {
                payload = match[1];
            }
        } else if (message.includes('receive message [')) {
            messagePath = 'Charger->CMS';
            // Extract JSON payload from receive message
            const match = message.match(/receive message \[(.*)\]/);
            if (match) {
                payload = match[1];
            }
        } else {
            // For other messages (like responses), try to extract any JSON-like content
            messagePath = 'System';
            payload = message;
        }
        
        // Escape CSV values (handle commas and quotes)
        const escapeCSV = (value) => {
            if (typeof value !== 'string') value = String(value);
            if (value.includes(',') || value.includes('"') || value.includes('\n')) {
                return '"' + value.replace(/"/g, '""') + '"';
            }
            return value;
        };
        
        const row = [
            escapeCSV(selectedChargerId),
            escapeCSV(istTime),
            escapeCSV(utcTime),
            escapeCSV(messagePath),
            escapeCSV(payload)
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
                        <div>
                            <h6 class="card-title">${idTag}</h6>
                            ${expiryText}
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
}

// Add new ID tag
async function addIdTag() {
    const idTag = document.getElementById('newIdTag').value.trim();
    const expiryDateTime = document.getElementById('newIdTagExpiry').value;
    
    if (!idTag) {
        alert('Please enter an ID tag');
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
    await loadActiveTransactions();
    modals.remoteStop.show();
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
        const response = await fetch(`/api/active_transactions/${selectedChargerId}`);
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

async function sendLocalList() {
    const updateType = document.getElementById('localListUpdateType').value;
    const data = document.getElementById('localListData').value;

    try {
        const response = await fetch(`/api/send/${selectedChargerId}/send_local_list`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                update_type: updateType,
                local_authorization_list: data ? JSON.parse(data) : null
            })
        });

        if (response.ok) {
            modals.sendLocalList.hide();
            alert('Local list sent successfully');
        } else {
            alert('Error sending local list');
        }
    } catch (error) {
        console.error('Error sending local list:', error);
        alert('Error sending local list');
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