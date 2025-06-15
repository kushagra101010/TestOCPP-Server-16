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
        
        // Use the main charger status (from StatusNotification) - this is the primary status
        let statusDisplay = charger.status || 'Unknown';
        let statusClass = charger.connected ? 'bg-success' : 'bg-danger';
        
        // Check if charger is in a charging state based on the main status
        const isCharging = statusDisplay && ['charging', 'preparing'].includes(statusDisplay.toLowerCase());
        const chargingIndicator = isCharging ? '<i class="bi bi-lightning-charge-fill text-warning"></i> ' : '';
        const transactionInfo = isCharging ? '<br><small class="text-warning"><i class="bi bi-info-circle"></i> Active transaction</small>' : '';
        
        item.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">${chargingIndicator}${charger.id}</h6>
                    <small class="text-muted">Status: ${statusDisplay}</small>
                    <br>
                    <small class="text-muted">Last seen: ${charger.last_seen ? formatToIST(charger.last_seen) : 'Never'}</small>
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
    modals.triggerMessage = new bootstrap.Modal(document.getElementById('triggerMessageModal'));
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