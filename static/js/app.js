/**
 *Registration page JavaScript
 * Use the tool library in utils.js
 */

// state
let currentTask = null;
let currentBatch = null;
let logPollingInterval = null;
let batchPollingInterval = null;
let accountsPollingInterval = null;
let isBatchMode = false;
let isOutlookBatchMode = false;
let outlookAccounts = [];
let taskCompleted = false; // Mark whether the task is completed
let batchCompleted = false; // Mark whether the batch task has been completed
let taskFinalStatus = null; // Save the final status of the task
let batchFinalStatus = null; // Save the final status of the batch task
let displayedLogs = new Set(); // Used for log deduplication
let toastShown = false; // Mark whether toast has been shown
let availableServices = {
    tempmail: { available: true, services: [] },
    outlook: { available: false, services: [] },
    moe_mail: { available: false, services: [] },
    temp_mail: { available: false, services: [] },
    duck_mail: { available: false, services: [] },
    freemail: { available: false, services: [] }
};

// WebSocket related variables
let webSocket = null;
let batchWebSocket = null; // Batch task WebSocket
let useWebSocket = true; // Whether to use WebSocket
let wsHeartbeatInterval = null; // Heartbeat timer
let batchWsHeartbeatInterval = null; // Batch task heartbeat timer
let activeTaskUuid = null; // Currently active single task UUID (used for reconnection when the page becomes visible again)
let activeBatchId = null; // Currently active batch task ID (used for reconnection when the page becomes visible again)

// DOM element
const elements = {
    form: document.getElementById('registration-form'),
    emailService: document.getElementById('email-service'),
    regMode: document.getElementById('reg-mode'),
    regModeGroup: document.getElementById('reg-mode-group'),
    batchCountGroup: document.getElementById('batch-count-group'),
    batchCount: document.getElementById('batch-count'),
    batchOptions: document.getElementById('batch-options'),
    intervalMin: document.getElementById('interval-min'),
    intervalMax: document.getElementById('interval-max'),
    startBtn: document.getElementById('start-btn'),
    cancelBtn: document.getElementById('cancel-btn'),
    taskStatusRow: document.getElementById('task-status-row'),
    batchProgressSection: document.getElementById('batch-progress-section'),
    consoleLog: document.getElementById('console-log'),
    clearLogBtn: document.getElementById('clear-log-btn'),
    //Task status
    taskId: document.getElementById('task-id'),
    taskEmail: document.getElementById('task-email'),
    taskStatus: document.getElementById('task-status'),
    taskService: document.getElementById('task-service'),
    taskStatusBadge: document.getElementById('task-status-badge'),
    // batch status
    batchProgressText: document.getElementById('batch-progress-text'),
    batchProgressPercent: document.getElementById('batch-progress-percent'),
    progressBar: document.getElementById('progress-bar'),
    batchSuccess: document.getElementById('batch-success'),
    batchFailed: document.getElementById('batch-failed'),
    batchRemaining: document.getElementById('batch-remaining'),
    // Registered account
    recentAccountsTable: document.getElementById('recent-accounts-table'),
    refreshAccountsBtn: document.getElementById('refresh-accounts-btn'),
    // Outlook batch registration
    outlookBatchSection: document.getElementById('outlook-batch-section'),
    outlookAccountsContainer: document.getElementById('outlook-accounts-container'),
    outlookIntervalMin: document.getElementById('outlook-interval-min'),
    outlookIntervalMax: document.getElementById('outlook-interval-max'),
    outlookSkipRegistered: document.getElementById('outlook-skip-registered'),
    outlookConcurrencyMode: document.getElementById('outlook-concurrency-mode'),
    outlookConcurrencyCount: document.getElementById('outlook-concurrency-count'),
    outlookConcurrencyHint: document.getElementById('outlook-concurrency-hint'),
    outlookIntervalGroup: document.getElementById('outlook-interval-group'),
    // Batch concurrency control
    concurrencyMode: document.getElementById('concurrency-mode'),
    concurrencyCount: document.getElementById('concurrency-count'),
    concurrencyHint: document.getElementById('concurrency-hint'),
    intervalGroup: document.getElementById('interval-group'),
    // Automatic operation after registration
    autoUploadCpa: document.getElementById('auto-upload-cpa'),
    cpaServiceSelectGroup: document.getElementById('cpa-service-select-group'),
    cpaServiceSelect: document.getElementById('cpa-service-select'),
    autoUploadSub2api: document.getElementById('auto-upload-sub2api'),
    sub2apiServiceSelectGroup: document.getElementById('sub2api-service-select-group'),
    sub2apiServiceSelect: document.getElementById('sub2api-service-select'),
    autoUploadTm: document.getElementById('auto-upload-tm'),
    tmServiceSelectGroup: document.getElementById('tm-service-select-group'),
    tmServiceSelect: document.getElementById('tm-service-select'),
};

// initialization
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadAvailableServices();
    loadRecentAccounts();
    startAccountsPolling();
    initVisibilityReconnect();
    restoreActiveTask();
    initAutoUploadOptions();
});

// Automatic operation options after initialization registration (CPA/Sub2API/TM)
async function initAutoUploadOptions() {
    await Promise.all([
        loadServiceSelect('/cpa-services?enabled=true', elements.cpaServiceSelect, elements.autoUploadCpa, elements.cpaServiceSelectGroup),
        loadServiceSelect('/sub2api-services?enabled=true', elements.sub2apiServiceSelect, elements.autoUploadSub2api, elements.sub2apiServiceSelectGroup),
        loadServiceSelect('/tm-services?enabled=true', elements.tmServiceSelect, elements.autoUploadTm, elements.tmServiceSelectGroup),
    ]);
}

// General: Build a custom multi-select drop-down component and handle linkage
async function loadServiceSelect(apiPath, container, checkbox, selectGroup) {
    if (!checkbox || !container) return;
    let services = [];
    try {
        services = await api.get(apiPath);
    } catch (e) {}

    if (!services || services.length === 0) {
        checkbox.disabled = true;
        checkbox.title = 'Please add the corresponding service in the settings first';
        const label = checkbox.closest('label');
        if (label) label.style.opacity = '0.5';
        container.innerHTML = '<div class="msd-empty">No service available</div>';
    } else {
        const items = services.map(s =>
            `<label class="msd-item">
                <input type="checkbox" value="${s.id}" checked>
                <span>${escapeHtml(s.name)}</span>
            </label>`
        ).join('');
        container.innerHTML = `
            <div class="msd-dropdown" id="${container.id}-dd">
                <div class="msd-trigger" onclick="toggleMsd('${container.id}-dd')">
                    <span class="msd-label">All (${services.length})</span>
                    <span class="msd-arrow">▼</span>
                </div>
                <div class="msd-list">${items}</div>
            </div>`;
        // Monitor checkbox changes and update trigger text
        container.querySelectorAll('.msd-item input').forEach(cb => {
            cb.addEventListener('change', () => updateMsdLabel(container.id + '-dd'));
        });
        // Click outside to close
        document.addEventListener('click', (e) => {
            const dd = document.getElementById(container.id + '-dd');
            if (dd && !dd.contains(e.target)) dd.classList.remove('open');
        }, true);
    }

    // Linked display/hide service selection area
    checkbox.addEventListener('change', () => {
        if (selectGroup) selectGroup.style.display = checkbox.checked ? 'block' : 'none';
    });
}

function toggleMsd(ddId) {
    const dd = document.getElementById(ddId);
    if (dd) dd.classList.toggle('open');
}

function updateMsdLabel(ddId) {
    const dd = document.getElementById(ddId);
    if (!dd) return;
    const all = dd.querySelectorAll('.msd-item input');
    const checked = dd.querySelectorAll('.msd-item input:checked');
    const label = dd.querySelector('.msd-label');
    if (!label) return;
    if (checked.length === 0) label.textContent = 'Not selected';
    else if (checked.length === all.length) label.textContent = `all (${all.length})`;
    else label.textContent = Array.from(checked).map(c => c.nextElementSibling.textContent).join(', ');
}

// Get the list of service IDs selected in the custom multi-select drop-down
function getSelectedServiceIds(container) {
    if (!container) return [];
    return Array.from(container.querySelectorAll('.msd-item input:checked')).map(cb => parseInt(cb.value));
}

//Event listening
function initEventListeners() {
    //Registration form submission
    elements.form.addEventListener('submit', handleStartRegistration);

    //Switch registration mode
    elements.regMode.addEventListener('change', handleModeChange);

    // Email service switching
    elements.emailService.addEventListener('change', handleServiceChange);

    // Cancel button
    elements.cancelBtn.addEventListener('click', handleCancelTask);

    //Clear the log
    elements.clearLogBtn.addEventListener('click', () => {
        elements.consoleLog.innerHTML = '<div class="log-line info">[System] Log has been cleared</div>';
        displayedLogs.clear(); // Clear the log deduplication collection
    });

    // Refresh the account list
    elements.refreshAccountsBtn.addEventListener('click', () => {
        loadRecentAccounts();
        toast.info('refreshed');
    });

    // Concurrent mode switch
    elements.concurrencyMode.addEventListener('change', () => {
        handleConcurrencyModeChange(elements.concurrencyMode, elements.concurrencyHint, elements.intervalGroup);
    });
    elements.outlookConcurrencyMode.addEventListener('change', () => {
        handleConcurrencyModeChange(elements.outlookConcurrencyMode, elements.outlookConcurrencyHint, elements.outlookIntervalGroup);
    });
}

//Load available email services
async function loadAvailableServices() {
    try {
        const data = await api.get('/registration/available-services');
        availableServices = data;

        //Update the email service selection box
        updateEmailServiceOptions();

        addLog('info', '[System] Email service list has been loaded');
    } catch (error) {
        console.error('Failed to load email service list:', error);
        addLog('warning', '[Warning] Failed to load mailbox service list');
    }
}

//Update the email service selection box
function updateEmailServiceOptions() {
    const select = elements.emailService;
    select.innerHTML = '';

    // Tempmail
    if (availableServices.tempmail.available) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = '🌐 Temporary mailbox';

        availableServices.tempmail.services.forEach(service => {
            const option = document.createElement('option');
            option.value = `tempmail:${service.id || 'default'}`;
            option.textContent = service.name;
            option.dataset.type = 'tempmail';
            optgroup.appendChild(option);
        });

        select.appendChild(optgroup);
    }

    // Outlook
    if (availableServices.outlook.available) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = `📧 Outlook (${availableServices.outlook.count} accounts)`;

        availableServices.outlook.services.forEach(service => {
            const option = document.createElement('option');
            option.value = `outlook:${service.id}`;
            option.textContent = service.name + (service.has_oauth ? ' (OAuth)' : '');
            option.dataset.type = 'outlook';
            option.dataset.serviceId = service.id;
            optgroup.appendChild(option);
        });

        select.appendChild(optgroup);

        // Outlook bulk registration option
        const batchOption = document.createElement('option');
        batchOption.value = 'outlook_batch:all';
        batchOption.textContent = `📋 Outlook batch registration (${availableServices.outlook.count} accounts)`;
        batchOption.dataset.type = 'outlook_batch';
        optgroup.appendChild(batchOption);
    } else {
        const optgroup = document.createElement('optgroup');
        optgroup.label = '📧 Outlook (not configured)';

        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Please import the account on the email service page first';
        option.disabled = true;
        optgroup.appendChild(option);

        select.appendChild(optgroup);
    }

    // Custom domain name
    if (availableServices.moe_mail.available) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = `🔗 Custom domain name (${availableServices.moe_mail.count} services)`;

        availableServices.moe_mail.services.forEach(service => {
            const option = document.createElement('option');
            option.value = `moe_mail:${service.id || 'default'}`;
            option.textContent = service.name + (service.default_domain ? ` (@${service.default_domain})` : '');
            option.dataset.type = 'moe_mail';
            if (service.id) {
                option.dataset.serviceId = service.id;
            }
            optgroup.appendChild(option);
        });

        select.appendChild(optgroup);
    } else {
        const optgroup = document.createElement('optgroup');
        optgroup.label = '🔗 Custom domain name (not configured)';

        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Please add services on the email service page first';
        option.disabled = true;
        optgroup.appendChild(option);

        select.appendChild(optgroup);
    }

    // Temp-Mail (self-deployment)
    if (availableServices.temp_mail && availableServices.temp_mail.available) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = `📮 Temp-Mail self-deployment (${availableServices.temp_mail.count} services)`;

        availableServices.temp_mail.services.forEach(service => {
            const option = document.createElement('option');
            option.value = `temp_mail:${service.id}`;
            option.textContent = service.name + (service.domain ? ` (@${service.domain})` : '');
            option.dataset.type = 'temp_mail';
            option.dataset.serviceId = service.id;
            optgroup.appendChild(option);
        });

        select.appendChild(optgroup);
    }

    // DuckMail
    if (availableServices.duck_mail && availableServices.duck_mail.available) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = `🦆 DuckMail (${availableServices.duck_mail.count} services)`;

        availableServices.duck_mail.services.forEach(service => {
            const option = document.createElement('option');
            option.value = `duck_mail:${service.id}`;
            option.textContent = service.name + (service.default_domain ? ` (@${service.default_domain})` : '');
            option.dataset.type = 'duck_mail';
            option.dataset.serviceId = service.id;
            optgroup.appendChild(option);
        });

        select.appendChild(optgroup);
    }

    // Freemail
    if (availableServices.freemail && availableServices.freemail.available) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = `📧 Freemail (${availableServices.freemail.count} services)`;

        availableServices.freemail.services.forEach(service => {
            const option = document.createElement('option');
            option.value = `freemail:${service.id}`;
            option.textContent = service.name + (service.domain ? ` (@${service.domain})` : '');
            option.dataset.type = 'freemail';
            option.dataset.serviceId = service.id;
            optgroup.appendChild(option);
        });

        select.appendChild(optgroup);
    }
}

// Handle mailbox service switching
function handleServiceChange(e) {
    const value = e.target.value;
    if (!value) return;

    const [type, id] = value.split(':');
    // Handle Outlook bulk registration mode
    if (type === 'outlook_batch') {
        isOutlookBatchMode = true;
        elements.outlookBatchSection.style.display = 'block';
        elements.regModeGroup.style.display = 'none';
        elements.batchCountGroup.style.display = 'none';
        elements.batchOptions.style.display = 'none';
        loadOutlookAccounts();
        addLog('info', '[System] has switched to Outlook batch registration mode');
        return;
    } else {
        isOutlookBatchMode = false;
        elements.outlookBatchSection.style.display = 'none';
        elements.regModeGroup.style.display = 'block';
    }

    //Display service information
    if (type === 'outlook') {
        const service = availableServices.outlook.services.find(s => s.id == id);
        if (service) {
            addLog('info', `[System] Outlook account selected: ${service.name}`);
        }
    } else if (type === 'moe_mail') {
        const service = availableServices.moe_mail.services.find(s => s.id == id);
        if (service) {
            addLog('info', `[System] Custom domain name service selected: ${service.name}`);
        }
    } else if (type === 'temp_mail') {
        const service = availableServices.temp_mail.services.find(s => s.id == id);
        if (service) {
            addLog('info', `[System] Temp-Mail self-deployment service selected: ${service.name}`);
        }
    } else if (type === 'duck_mail') {
        const service = availableServices.duck_mail.services.find(s => s.id == id);
        if (service) {
            addLog('info', `[System] DuckMail service selected: ${service.name}`);
        }
    } else if (type === 'freemail') {
        const service = availableServices.freemail.services.find(s => s.id == id);
        if (service) {
            addLog('info', `[System] Freemail service selected: ${service.name}`);
        }
    }
}

//Mode switch
function handleModeChange(e) {
    const mode = e.target.value;
    isBatchMode = mode === 'batch';

    elements.batchCountGroup.style.display = isBatchMode ? 'block' : 'none';
    elements.batchOptions.style.display = isBatchMode ? 'block' : 'none';
}

// Concurrent mode switching (batch)
function handleConcurrencyModeChange(selectEl, hintEl, intervalGroupEl) {
    const mode = selectEl.value;
    if (mode === 'parallel') {
        hintEl.textContent = 'All tasks are divided into N concurrent batches and executed simultaneously';
        intervalGroupEl.style.display = 'none';
    } else {
        hintEl.textContent = 'Run up to N tasks at the same time and start new tasks every interval seconds';
        intervalGroupEl.style.display = 'block';
    }
}

// Start registration
async function handleStartRegistration(e) {
    e.preventDefault();

    const selectedValue = elements.emailService.value;
    if (!selectedValue) {
        toast.error('Please select an email service');
        return;
    }

    // Handle Outlook bulk registration mode
    if (isOutlookBatchMode) {
        await handleOutlookBatchRegistration();
        return;
    }

    const [emailServiceType, serviceId] = selectedValue.split(':');

    // Disable start button
    elements.startBtn.disabled = true;
    elements.cancelBtn.disabled = false;

    //Clear the log
    elements.consoleLog.innerHTML = '';

    // Build request data (the proxy automatically gets it from settings)
    const requestData = {
        email_service_type: emailServiceType,
        auto_upload_cpa: elements.autoUploadCpa ? elements.autoUploadCpa.checked : false,
        cpa_service_ids: elements.autoUploadCpa && elements.autoUploadCpa.checked ? getSelectedServiceIds(elements.cpaServiceSelect) : [],
        auto_upload_sub2api: elements.autoUploadSub2api ? elements.autoUploadSub2api.checked : false,
        sub2api_service_ids: elements.autoUploadSub2api && elements.autoUploadSub2api.checked ? getSelectedServiceIds(elements.sub2apiServiceSelect) : [],
        auto_upload_tm: elements.autoUploadTm ? elements.autoUploadTm.checked : false,
        tm_service_ids: elements.autoUploadTm && elements.autoUploadTm.checked ? getSelectedServiceIds(elements.tmServiceSelect) : [],
    };

    // If a service in the database is selected, pass service_id
    if (serviceId && serviceId !== 'default') {
        requestData.email_service_id = parseInt(serviceId);
    }

    if (isBatchMode) {
        await handleBatchRegistration(requestData);
    } else {
        await handleSingleRegistration(requestData);
    }
}

//Single registration
async function handleSingleRegistration(requestData) {
    //Reset task status
    taskCompleted = false;
    taskFinalStatus = null;
    displayedLogs.clear(); // Clear the log deduplication collection
    toastShown = false; //Reset toast flag

    addLog('info', '[System] is starting the registration task...');

    try {
        const data = await api.post('/registration/start', requestData);

        currentTask = data;
        activeTaskUuid = data.task_uuid; // Save for reconnection
        // Persist to sessionStorage and can be restored after cross-page navigation
        sessionStorage.setItem('activeTask', JSON.stringify({ task_uuid: data.task_uuid, mode: 'single' }));
        addLog('info', `[System] task has been created: ${data.task_uuid}`);
        showTaskStatus(data);
        updateTaskStatus('running');

        // Prefer using WebSocket
        connectWebSocket(data.task_uuid);

    } catch (error) {
        addLog('error', `[Error] Startup failed: ${error.message}`);
        toast.error(error.message);
        resetButtons();
    }
}


// ============== WebSocket functions ==============

// Connect WebSocket
function connectWebSocket(taskUuid) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/task/${taskUuid}`;

    try {
        webSocket = new WebSocket(wsUrl);

        webSocket.onopen = () => {
            console.log('WebSocket connection successful');
            useWebSocket = true;
            // Stop polling (if any)
            stopLogPolling();
            // Start heartbeat
            startWebSocketHeartbeat();
        };

        webSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'log') {
                const logType = getLogType(data.message);
                addLog(logType, data.message);
            } else if (data.type === 'status') {
                updateTaskStatus(data.status);

                // Check if completed
                if (['completed', 'failed', 'cancelled', 'cancelling'].includes(data.status)) {
                    //Save the final state for onclose judgment
                    taskFinalStatus = data.status;
                    taskCompleted = true;

                    // Disconnect WebSocket (asynchronous operation)
                    disconnectWebSocket();

                    //Reset the button after the task is completed
                    resetButtons();

                    // Show toast only once
                    if (!toastShown) {
                        toastShown = true;
                        if (data.status === 'completed') {
                            addLog('success', '[Success] Registration successful!');
                            toast.success('Registration successful!');
                            // Refresh the account list
                            loadRecentAccounts();
                        } else if (data.status === 'failed') {
                            addLog('error', '[Error] Registration failed');
                            toast.error('Registration failed');
                        } else if (data.status === 'cancelled' || data.status === 'cancelling') {
                            addLog('warning', '[Warning] Task has been canceled');
                        }
                    }
                }
            } else if (data.type === 'pong') {
                // Heartbeat response, ignored
            }
        };

        webSocket.onclose = (event) => {
            console.log('WebSocket connection closed:', event.code);
            stopWebSocketHeartbeat();

            // Only switch to polling if the task is not completed and the final status is not completed
            // Use taskFinalStatus instead of currentTask.status because currentTask may have been reset
            const shouldPoll = !taskCompleted &&
                               taskFinalStatus === null; // If taskFinalStatus has a value, the task has been completed

            if (shouldPoll && currentTask) {
                console.log('Switch to polling mode');
                useWebSocket = false;
                startLogPolling(currentTask.task_uuid);
            }
        };

        webSocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            // switch to polling
            useWebSocket = false;
            stopWebSocketHeartbeat();
            startLogPolling(taskUuid);
        };

    } catch (error) {
        console.error('WebSocket connection failed:', error);
        useWebSocket = false;
        startLogPolling(taskUuid);
    }
}

// Disconnect WebSocket
function disconnectWebSocket() {
    stopWebSocketHeartbeat();
    if (webSocket) {
        webSocket.close();
        webSocket = null;
    }
}

// Start heartbeat
function startWebSocketHeartbeat() {
    stopWebSocketHeartbeat();
    wsHeartbeatInterval = setInterval(() => {
        if (webSocket && webSocket.readyState === WebSocket.OPEN) {
            webSocket.send(JSON.stringify({ type: 'ping' }));
        }
    }, 25000); // Send a heartbeat every 25 seconds
}

// Stop heartbeat
function stopWebSocketHeartbeat() {
    if (wsHeartbeatInterval) {
        clearInterval(wsHeartbeatInterval);
        wsHeartbeatInterval = null;
    }
}

//Send cancellation request
function cancelViaWebSocket() {
    if (webSocket && webSocket.readyState === WebSocket.OPEN) {
        webSocket.send(JSON.stringify({ type: 'cancel' }));
    }
}

//Batch registration
async function handleBatchRegistration(requestData) {
    //Reset batch task status
    batchCompleted = false;
    batchFinalStatus = null;
    displayedLogs.clear(); // Clear the log deduplication collection
    toastShown = false; //Reset toast flag

    const count = parseInt(elements.batchCount.value) || 5;
    const intervalMin = parseInt(elements.intervalMin.value) || 5;
    const intervalMax = parseInt(elements.intervalMax.value) || 30;
    const concurrency = parseInt(elements.concurrencyCount.value) || 3;
    const mode = elements.concurrencyMode.value || 'pipeline';

    requestData.count = count;
    requestData.interval_min = intervalMin;
    requestData.interval_max = intervalMax;
    requestData.concurrency = Math.min(50, Math.max(1, concurrency));
    requestData.mode = mode;

    addLog('info', `[System] is starting batch registration tasks (Quantity: ${count})...`);

    try {
        const data = await api.post('/registration/batch', requestData);

        currentBatch = data;
        activeBatchId = data.batch_id; // Save for reconnection
        // Persist to sessionStorage and can be restored after cross-page navigation
        sessionStorage.setItem('activeTask', JSON.stringify({ batch_id: data.batch_id, mode: 'batch', total: data.count }));
        addLog('info', `[System] Batch task has been created: ${data.batch_id}`);
        addLog('info', `[System] A total of ${data.count} tasks have been added to the queue`);
        showBatchStatus(data);

        // Prefer using WebSocket
        connectBatchWebSocket(data.batch_id);

    } catch (error) {
        addLog('error', `[Error] Startup failed: ${error.message}`);
        toast.error(error.message);
        resetButtons();
    }
}

//Cancel task
async function handleCancelTask() {
    // Disable the cancel button to prevent repeated clicks
    elements.cancelBtn.disabled = true;
    addLog('info', '[System] is submitting a cancellation request...');

    try {
        // Batch task cancellation (including normal batch mode and Outlook batch mode)
        if (currentBatch && (isBatchMode || isOutlookBatchMode)) {
            // Cancel via WebSocket first
            if (batchWebSocket && batchWebSocket.readyState === WebSocket.OPEN) {
                batchWebSocket.send(JSON.stringify({ type: 'cancel' }));
                addLog('warning', '[Warning] Batch task cancellation request has been submitted');
                toast.info('Task cancellation request has been submitted');
            } else {
                //Downgrade to REST API
                const endpoint = isOutlookBatchMode
                    ? `/registration/outlook-batch/${currentBatch.batch_id}/cancel`
                    : `/registration/batch/${currentBatch.batch_id}/cancel`;

                await api.post(endpoint);
                addLog('warning', '[Warning] Batch task cancellation request has been submitted');
                toast.info('Task cancellation request has been submitted');
                stopBatchPolling();
                resetButtons();
            }
        }
        //Single task cancellation
        else if (currentTask) {
            // Cancel via WebSocket first
            if (webSocket && webSocket.readyState === WebSocket.OPEN) {
                webSocket.send(JSON.stringify({ type: 'cancel' }));
                addLog('warning', '[Warning] Task cancellation request has been submitted');
                toast.info('Task cancellation request has been submitted');
            } else {
                //Downgrade to REST API
                await api.post(`/registration/tasks/${currentTask.task_uuid}/cancel`);
                addLog('warning', '[Warning] Task has been canceled');
                toast.info('Task canceled');
                stopLogPolling();
                resetButtons();
            }
        }
        // No active tasks
        else {
            addLog('warning', '[Warning] There are no active tasks to cancel');
            toast.warning('No active tasks');
            resetButtons();
        }
    } catch (error) {
        addLog('error', `[Error] Cancellation failed: ${error.message}`);
        toast.error(error.message);
        //Restore the cancel button and allow retries
        elements.cancelBtn.disabled = false;
    }
}

//Start polling logs
function startLogPolling(taskUuid) {
    let lastLogIndex = 0;

    logPollingInterval = setInterval(async () => {
        try {
            const data = await api.get(`/registration/tasks/${taskUuid}/logs`);

            //Update task status
            updateTaskStatus(data.status);

            //Update email information
            if (data.email) {
                elements.taskEmail.textContent = data.email;
            }
            if (data.email_service) {
                elements.taskService.textContent = getServiceTypeText(data.email_service);
            }

            //Add new log
            const logs = data.logs || [];
            for (let i = lastLogIndex; i < logs.length; i++) {
                const log = logs[i];
                const logType = getLogType(log);
                addLog(logType, log);
            }
            lastLogIndex = logs.length;

            // Check if the task is completed
            if (['completed', 'failed', 'cancelled'].includes(data.status)) {
                stopLogPolling();
                resetButtons();

                // Show toast only once
                if (!toastShown) {
                    toastShown = true;
                    if (data.status === 'completed') {
                        addLog('success', '[Success] Registration successful!');
                        toast.success('Registration successful!');
                        // Refresh the account list
                        loadRecentAccounts();
                    } else if (data.status === 'failed') {
                        addLog('error', '[Error] Registration failed');
                        toast.error('Registration failed');
                    } else if (data.status === 'cancelled') {
                        addLog('warning', '[Warning] Task has been canceled');
                    }
                }
            }
        } catch (error) {
            console.error('Polling log failed:', error);
        }
    }, 1000);
}

// Stop polling logs
function stopLogPolling() {
    if (logPollingInterval) {
        clearInterval(logPollingInterval);
        logPollingInterval = null;
    }
}

// Start polling batch status
function startBatchPolling(batchId) {
    batchPollingInterval = setInterval(async () => {
        try {
            const data = await api.get(`/registration/batch/${batchId}`);
            updateBatchProgress(data);

            // Check if completed
            if (data.finished) {
                stopBatchPolling();
                resetButtons();

                // Show toast only once
                if (!toastShown) {
                    toastShown = true;
                    addLog('info', `[Complete] The batch task is completed! Success: ${data.success}, Failure: ${data.failed}`);
                    if (data.success > 0) {
                        toast.success(`Batch registration completed, ${data.success} successful`);
                        // Refresh the account list
                        loadRecentAccounts();
                    } else {
                        toast.warning('Batch registration completed, but no account was successfully registered');
                    }
                }
            }
        } catch (error) {
            console.error('Polling batch status failed:', error);
        }
    }, 2000);
}

// Stop polling batch status
function stopBatchPolling() {
    if (batchPollingInterval) {
        clearInterval(batchPollingInterval);
        batchPollingInterval = null;
    }
}

//Display task status
function showTaskStatus(task) {
    elements.taskStatusRow.style.display = 'grid';
    elements.batchProgressSection.style.display = 'none';
    elements.taskStatusBadge.style.display = 'inline-flex';
    elements.taskId.textContent = task.task_uuid.substring(0, 8) + '...';
    elements.taskEmail.textContent = '-';
    elements.taskService.textContent = '-';
}

//Update task status
function updateTaskStatus(status) {
    const statusInfo = {
        pending: { text: 'Waiting', class: 'pending' },
        running: { text: 'running', class: 'running' },
        completed: { text: 'Completed', class: 'completed' },
        failed: { text: 'failed', class: 'failed' },
        canceled: { text: 'Cancelled', class: 'disabled' }
    };

    const info = statusInfo[status] || { text: status, class: '' };
    elements.taskStatusBadge.textContent = info.text;
    elements.taskStatusBadge.className = `status-badge ${info.class}`;
    elements.taskStatus.textContent = info.text;
}

//Display batch status
function showBatchStatus(batch) {
    elements.batchProgressSection.style.display = 'block';
    elements.taskStatusRow.style.display = 'none';
    elements.taskStatusBadge.style.display = 'none';
    elements.batchProgressText.textContent = `0/${batch.count}`;
    elements.batchProgressPercent.textContent = '0%';
    elements.progressBar.style.width = '0%';
    elements.batchSuccess.textContent = '0';
    elements.batchFailed.textContent = '0';
    elements.batchRemaining.textContent = batch.count;

    //Reset counter
    elements.batchSuccess.dataset.last = '0';
    elements.batchFailed.dataset.last = '0';
}

//Update batch progress
function updateBatchProgress(data) {
    const progress = ((data.completed / data.total) * 100).toFixed(0);
    elements.batchProgressText.textContent = `${data.completed}/${data.total}`;
    elements.batchProgressPercent.textContent = `${progress}%`;
    elements.progressBar.style.width = `${progress}%`;
    elements.batchSuccess.textContent = data.success;
    elements.batchFailed.textContent = data.failed;
    elements.batchRemaining.textContent = data.total - data.completed;

    // Log (avoid duplication)
    if (data.completed > 0) {
        const lastSuccess = parseInt(elements.batchSuccess.dataset.last || '0');
        const lastFailed = parseInt(elements.batchFailed.dataset.last || '0');

        if (data.success > lastSuccess) {
            addLog('success', `[Success] The ${data.success} account was successfully registered`);
        }
        if (data.failed > lastFailed) {
            addLog('error', `[Failed] The registration of the ${data.failed} account failed`);
        }

        elements.batchSuccess.dataset.last = data.success;
        elements.batchFailed.dataset.last = data.failed;
    }
}

//Load the recently registered account
async function loadRecentAccounts() {
    try {
        const data = await api.get('/accounts?page=1&page_size=10');

        if (data.accounts.length === 0) {
            elements.recentAccountsTable.innerHTML = `
                <tr>
                    <td colspan="5">
                        <div class="empty-state" style="padding: var(--spacing-md);">
                            <div class="empty-state-icon">📭</div>
                            <div class="empty-state-title">No registered account yet</div>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        elements.recentAccountsTable.innerHTML = data.accounts.map(account => `
            <tr data-id="${account.id}">
                <td>${account.id}</td>
                <td>
                    <span style="display:inline-flex;align-items:center;gap:4px;">
                        <span title="${escapeHtml(account.email)}">${escapeHtml(account.email)}</span>
                        <button class="btn-copy-icon copy-email-btn" data-email="${escapeHtml(account.email)}" title="Copy Email">📋</button>
                    </span>
                </td>
                <td class="password-cell">
                    ${account.password
                        ? `<span style="display:inline-flex;align-items:center;gap:4px;">
                            <span class="password-hidden" title="Click to view">${escapeHtml(account.password.substring(0, 8))}...</span>
                            <button class="btn-copy-icon copy-pwd-btn" data-pwd="${escapeHtml(account.password)}" title="Copy password">📋</button>
                           </span>`
                        : '-'}
                </td>
                <td>
                    ${getStatusIcon(account.status)}
                </td>
            </tr>
        `).join('');

        //Bind copy button event
        elements.recentAccountsTable.querySelectorAll('.copy-email-btn').forEach(btn => {
            btn.addEventListener('click', (e) => { e.stopPropagation(); copyToClipboard(btn.dataset.email); });
        });
        elements.recentAccountsTable.querySelectorAll('.copy-pwd-btn').forEach(btn => {
            btn.addEventListener('click', (e) => { e.stopPropagation(); copyToClipboard(btn.dataset.pwd); });
        });

    } catch (error) {
        console.error('Failed to load account list:', error);
    }
}

//Start account list polling
function startAccountsPolling() {
    // Refresh the account list every 30 seconds
    accountsPollingInterval = setInterval(() => {
        loadRecentAccounts();
    }, 30000);
}

//Add log
function addLog(type, message) {
    // Log deduplication: use the hash of the message content as the key
    const logKey = `${type}:${message}`;
    if (displayedLogs.has(logKey)) {
        return; // Already displayed, skip
    }
    displayedLogs.add(logKey);

    // Limit the size of the deduplication set to avoid memory leaks
    if (displayedLogs.size > 1000) {
        // Clear half of the records
        const keys = Array.from(displayedLogs);
        keys.slice(0, 500).forEach(k => displayedLogs.delete(k));
    }

    const line = document.createElement('div');
    line.className = `log-line ${type}`;

    //Add timestamp
    const timestamp = new Date().toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });

    line.innerHTML = `<span class="timestamp">[${timestamp}]</span>${escapeHtml(message)}`;
    elements.consoleLog.appendChild(line);

    //Automatically scroll to the bottom
    elements.consoleLog.scrollTop = elements.consoleLog.scrollHeight;

    //Limit the number of log lines
    const lines = elements.consoleLog.querySelectorAll('.log-line');
    if (lines.length > 500) {
        lines[0].remove();
    }
}

// Get the log type
function getLogType(log) {
    if (typeof log !== 'string') return 'info';

    const lowerLog = log.toLowerCase();
    if (lowerLog.includes('error') || lowerLog.includes('failure') || lowerLog.includes('error')) {
        return 'error';
    }
    if (lowerLog.includes('warning') || lowerLog.includes('warning')) {
        return 'warning';
    }
    if (lowerLog.includes('success') || lowerLog.includes('success') || lowerLog.includes('completion')) {
        return 'success';
    }
    return 'info';
}

//Reset button state
function resetButtons() {
    elements.startBtn.disabled = false;
    elements.cancelBtn.disabled = true;
    currentTask = null;
    currentBatch = null;
    isBatchMode = false;
    //Reset completion flag
    taskCompleted = false;
    batchCompleted = false;
    //Reset final status flag
    taskFinalStatus = null;
    batchFinalStatus = null;
    // Clear active task ID
    activeTaskUuid = null;
    activeBatchId = null;
    // Clear sessionStorage persistence state
    sessionStorage.removeItem('activeTask');
    // Disconnect WebSocket
    disconnectWebSocket();
    disconnectBatchWebSocket();
    // NOTE: Do not reset isOutlookBatchMode as the user may want to continue using Outlook batch mode
}

//HTML escaping
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// ============== Outlook batch registration function ==============

//Load Outlook account list
async function loadOutlookAccounts() {
    try {
        elements.outlookAccountsContainer.innerHTML = '<div class="loading-placeholder" style="text-align: center; padding: var(--spacing-md); color: var(--text-muted);">Loading...</div>';

        const data = await api.get('/registration/outlook-accounts');
        outlookAccounts = data.accounts || [];

        renderOutlookAccountsList();

        addLog('info', `[System] Loaded ${data.total} Outlook accounts (registered: ${data.registered_count}, unregistered: ${data.unregistered_count})`);

    } catch (error) {
        console.error('Failed to load Outlook account list:', error);
        elements.outlookAccountsContainer.innerHTML = `<div style="text-align: center; padding: var(--spacing-md); color: var(--text-muted);">Loading failed: ${error.message}</div>`;
        addLog('error', `[Error] Failed to load Outlook account list: ${error.message}`);
    }
}

// Render the Outlook account list
function renderOutlookAccountsList() {
    if (outlookAccounts.length === 0) {
        elements.outlookAccountsContainer.innerHTML = '<div style="text-align: center; padding: var(--spacing-md); color: var(--text-muted);">No Outlook accounts available</div>';
        return;
    }

    const html = outlookAccounts.map(account => `
        <label class="outlook-account-item" style="display: flex; align-items: center; padding: var(--spacing-sm); border-bottom: 1px solid var(--border-light); cursor: pointer; ${account.is_registered ? 'opacity: 0.6;' : ''}" data-id="${account.id}" data-registered="${account.is_registered}">
            <input type="checkbox" class="outlook-account-checkbox" value="${account.id}" ${account.is_registered ? '' : 'checked'} style="margin-right: var(--spacing-sm);">
            <div style="flex: 1;">
                <div style="font-weight: 500;">${escapeHtml(account.email)}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">
                    ${account.is_registered
                        ? `<span style="color: var(--success-color);">✓ Registered</span>`
                        : '<span style="color: var(--primary-color);">Not registered</span>'
                    }
                    ${account.has_oauth ? ' | OAuth' : ''}
                </div>
            </div>
        </label>
    `).join('');

    elements.outlookAccountsContainer.innerHTML = html;
}

// Select all
function selectAllOutlookAccounts() {
    const checkboxes = document.querySelectorAll('.outlook-account-checkbox');
    checkboxes.forEach(cb => cb.checked = true);
}

// Only select unregistered
function selectUnregisteredOutlook() {
    const items = document.querySelectorAll('.outlook-account-item');
    items.forEach(item => {
        const checkbox = item.querySelector('.outlook-account-checkbox');
        const isRegistered = item.dataset.registered === 'true';
        checkbox.checked = !isRegistered;
    });
}

//Cancel select all
function deselectAllOutlookAccounts() {
    const checkboxes = document.querySelectorAll('.outlook-account-checkbox');
    checkboxes.forEach(cb => cb.checked = false);
}

// Handle Outlook batch registration
async function handleOutlookBatchRegistration() {
    //Reset batch task status
    batchCompleted = false;
    batchFinalStatus = null;
    displayedLogs.clear(); // Clear the log deduplication collection
    toastShown = false; //Reset toast flag

    // Get the selected account
    const selectedIds = [];
    document.querySelectorAll('.outlook-account-checkbox:checked').forEach(cb => {
        selectedIds.push(parseInt(cb.value));
    });

    if (selectedIds.length === 0) {
        toast.error('Please select at least one Outlook account');
        return;
    }

    const intervalMin = parseInt(elements.outlookIntervalMin.value) || 5;
    const intervalMax = parseInt(elements.outlookIntervalMax.value) || 30;
    const skipRegistered = elements.outlookSkipRegistered.checked;
    const concurrency = parseInt(elements.outlookConcurrencyCount.value) || 3;
    const mode = elements.outlookConcurrencyMode.value || 'pipeline';

    // Disable start button
    elements.startBtn.disabled = true;
    elements.cancelBtn.disabled = false;

    //Clear the log
    elements.consoleLog.innerHTML = '';

    const requestData = {
        service_ids: selectedIds,
        skip_registered: skipRegistered,
        interval_min: intervalMin,
        interval_max: intervalMax,
        concurrency: Math.min(50, Math.max(1, concurrency)),
        mode: mode,
        auto_upload_cpa: elements.autoUploadCpa ? elements.autoUploadCpa.checked : false,
        cpa_service_ids: elements.autoUploadCpa && elements.autoUploadCpa.checked ? getSelectedServiceIds(elements.cpaServiceSelect) : [],
        auto_upload_sub2api: elements.autoUploadSub2api ? elements.autoUploadSub2api.checked : false,
        sub2api_service_ids: elements.autoUploadSub2api && elements.autoUploadSub2api.checked ? getSelectedServiceIds(elements.sub2apiServiceSelect) : [],
        auto_upload_tm: elements.autoUploadTm ? elements.autoUploadTm.checked : false,
        tm_service_ids: elements.autoUploadTm && elements.autoUploadTm.checked ? getSelectedServiceIds(elements.tmServiceSelect) : [],
    };

    addLog('info', `[System] is starting Outlook batch registration (${selectedIds.length} accounts)...`);

    try {
        const data = await api.post('/registration/outlook-batch', requestData);

        if (data.to_register === 0) {
            addLog('warning', '[Warning] All selected email addresses have been registered, no need to register again');
            toast.warning('All selected email addresses have been registered');
            resetButtons();
            return;
        }

        currentBatch = { batch_id: data.batch_id, ...data };
        activeBatchId = data.batch_id; // Save for reconnection
        // Persist to sessionStorage and can be restored after cross-page navigation
        sessionStorage.setItem('activeTask', JSON.stringify({ batch_id: data.batch_id, mode: isOutlookBatchMode ? 'outlook_batch' : 'batch', total: data.to_register }));
        addLog('info', `[System] Batch task has been created: ${data.batch_id}`);
        addLog('info', `[System] Total: ${data.total}, Skip registered: ${data.skipped}, To be registered: ${data.to_register}`);

        //Initialize batch status display
        showBatchStatus({ count: data.to_register });

        // Prefer using WebSocket
        connectBatchWebSocket(data.batch_id);

    } catch (error) {
        addLog('error', `[Error] Startup failed: ${error.message}`);
        toast.error(error.message);
        resetButtons();
    }
}

// ============== Batch task WebSocket function ==============

//Connect batch task WebSocket
function connectBatchWebSocket(batchId) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/batch/${batchId}`;

    try {
        batchWebSocket = new WebSocket(wsUrl);

        batchWebSocket.onopen = () => {
            console.log('Batch task WebSocket connection successful');
            // Stop polling (if any)
            stopBatchPolling();
            // Start heartbeat
            startBatchWebSocketHeartbeat();
        };

        batchWebSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'log') {
                const logType = getLogType(data.message);
                addLog(logType, data.message);
            } else if (data.type === 'status') {
                // update progress
                if (data.total !== undefined) {
                    updateBatchProgress({
                        total: data.total,
                        completed: data.completed || 0,
                        success: data.success || 0,
                        failed: data.failed || 0
                    });
                }

                // Check if completed
                if (['completed', 'failed', 'cancelled', 'cancelling'].includes(data.status)) {
                    //Save the final state for onclose judgment
                    batchFinalStatus = data.status;
                    batchCompleted = true;

                    // Disconnect WebSocket (asynchronous operation)
                    disconnectBatchWebSocket();

                    //Reset the button after the task is completed
                    resetButtons();

                    // Show toast only once
                    if (!toastShown) {
                        toastShown = true;
                        if (data.status === 'completed') {
                            addLog('success', `[Complete] Outlook batch task completed! Success: ${data.success}, Failure: ${data.failed}, Skip: ${data.skipped || 0}`);
                            if (data.success > 0) {
                                toast.success(`Outlook batch registration completed, ${data.success} successful`);
                                loadRecentAccounts();
                            } else {
                                toast.warning('Outlook batch registration completed, but no account was successfully registered');
                            }
                        } else if (data.status === 'failed') {
                            addLog('error', '[Error] Batch task execution failed');
                            toast.error('Batch task execution failed');
                        } else if (data.status === 'cancelled' || data.status === 'cancelling') {
                            addLog('warning', '[Warning] The batch task has been canceled');
                        }
                    }
                }
            } else if (data.type === 'pong') {
                // Heartbeat response, ignored
            }
        };

        batchWebSocket.onclose = (event) => {
            console.log('Batch task WebSocket connection closed:', event.code);
            stopBatchWebSocketHeartbeat();

            // Only switch to polling if the task is not completed and the final status is not completed
            // Use batchFinalStatus instead of currentBatch.status because currentBatch may have been reset
            const shouldPoll = !batchCompleted &&
                               batchFinalStatus === null; // If batchFinalStatus has a value, the task has been completed

            if (shouldPoll && currentBatch) {
                console.log('Switch to polling mode');
                startOutlookBatchPolling(currentBatch.batch_id);
            }
        };

        batchWebSocket.onerror = (error) => {
            console.error('Batch task WebSocket error:', error);
            stopBatchWebSocketHeartbeat();
            // switch to polling
            startOutlookBatchPolling(batchId);
        };

    } catch (error) {
        console.error('Batch task WebSocket connection failed:', error);
        startOutlookBatchPolling(batchId);
    }
}

//Disconnect batch task WebSocket
function disconnectBatchWebSocket() {
    stopBatchWebSocketHeartbeat();
    if (batchWebSocket) {
        batchWebSocket.close();
        batchWebSocket = null;
    }
}

//Start batch task heartbeat
function startBatchWebSocketHeartbeat() {
    stopBatchWebSocketHeartbeat();
    batchWsHeartbeatInterval = setInterval(() => {
        if (batchWebSocket && batchWebSocket.readyState === WebSocket.OPEN) {
            batchWebSocket.send(JSON.stringify({ type: 'ping' }));
        }
    }, 25000); // Send a heartbeat every 25 seconds
}

// Stop batch task heartbeat
function stopBatchWebSocketHeartbeat() {
    if (batchWsHeartbeatInterval) {
        clearInterval(batchWsHeartbeatInterval);
        batchWsHeartbeatInterval = null;
    }
}

//Send batch task cancellation request
function cancelBatchViaWebSocket() {
    if (batchWebSocket && batchWebSocket.readyState === WebSocket.OPEN) {
        batchWebSocket.send(JSON.stringify({ type: 'cancel' }));
    }
}

// Start polling Outlook batch status (downgrade scenario)
function startOutlookBatchPolling(batchId) {
    batchPollingInterval = setInterval(async () => {
        try {
            const data = await api.get(`/registration/outlook-batch/${batchId}`);

            // update progress
            updateBatchProgress({
                total: data.total,
                completed: data.completed,
                success: data.success,
                failed: data.failed
            });

            //output log
            if (data.logs && data.logs.length > 0) {
                const lastLogIndex = batchPollingInterval.lastLogIndex || 0;
                for (let i = lastLogIndex; i < data.logs.length; i++) {
                    const log = data.logs[i];
                    const logType = getLogType(log);
                    addLog(logType, log);
                }
                batchPollingInterval.lastLogIndex = data.logs.length;
            }

            // Check if completed
            if (data.finished) {
                stopBatchPolling();
                resetButtons();

                // Show toast only once
                if (!toastShown) {
                    toastShown = true;
                    addLog('info', `[Complete] Outlook batch task completed! Success: ${data.success}, Failure: ${data.failed}, Skip: ${data.skipped || 0}`);
                    if (data.success > 0) {
                        toast.success(`Outlook batch registration completed, ${data.success} successful`);
                        loadRecentAccounts();
                    } else {
                        toast.warning('Outlook batch registration completed, but no account was successfully registered');
                    }
                }
            }
        } catch (error) {
            console.error('Polling Outlook batch status failed:', error);
        }
    }, 2000);

    batchPollingInterval.lastLogIndex = 0;
}

// ============== Page visibility reconnection mechanism ==============

function initVisibilityReconnect() {
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState !== 'visible') return;

        // When the page becomes visible again, check whether reconnection is required (for the scenario of label switching on the same page)
        const wsDisconnected = !webSocket || webSocket.readyState === WebSocket.CLOSED;
        const batchWsDisconnected = !batchWebSocket || batchWebSocket.readyState === WebSocket.CLOSED;

        //Single task reconnection
        if (activeTaskUuid && !taskCompleted && wsDisconnected) {
            console.log('[Reconnect] The page is visible again, reconnect the single task WebSocket:', activeTaskUuid);
            addLog('info', '[System] page has been reactivated and task monitoring is being reconnected...');
            connectWebSocket(activeTaskUuid);
        }

        //Batch task reconnection
        if (activeBatchId && !batchCompleted && batchWsDisconnected) {
            console.log('[Reconnect] The page is visible again, reconnect the batch task WebSocket:', activeBatchId);
            addLog('info', '[System] page has been reactivated, reconnecting to batch task monitoring...');
            connectBatchWebSocket(activeBatchId);
        }
    });
}

//Resume ongoing tasks when the page loads (handling the situation of returning to the registration page after cross-page navigation)
async function restoreActiveTask() {
    const saved = sessionStorage.getItem('activeTask');
    if (!saved) return;

    let state;
    try {
        state = JSON.parse(saved);
    } catch {
        sessionStorage.removeItem('activeTask');
        return;
    }

    const { mode, task_uuid, batch_id, total } = state;

    if (mode === 'single' && task_uuid) {
        // Check whether the task is still running
        try {
            const data = await api.get(`/registration/tasks/${task_uuid}`);
            if (['completed', 'failed', 'cancelled'].includes(data.status)) {
                sessionStorage.removeItem('activeTask');
                return;
            }
            // The task is still running, restore the state
            currentTask = data;
            activeTaskUuid = task_uuid;
            taskCompleted = false;
            taskFinalStatus = null;
            toastShown = false;
            displayedLogs.clear();
            elements.startBtn.disabled = true;
            elements.cancelBtn.disabled = false;
            showTaskStatus(data);
            updateTaskStatus(data.status);
            addLog('info', `[System] detected a task in progress and is reconnecting to monitor... (${task_uuid.substring(0, 8)})`);
            connectWebSocket(task_uuid);
        } catch {
            sessionStorage.removeItem('activeTask');
        }
    } else if ((mode === 'batch' || mode === 'outlook_batch') && batch_id) {
        //Query whether the batch task is still running
        const endpoint = mode === 'outlook_batch'
            ? `/registration/outlook-batch/${batch_id}`
            : `/registration/batch/${batch_id}`;
        try {
            const data = await api.get(endpoint);
            if (data.finished) {
                sessionStorage.removeItem('activeTask');
                return;
            }
            // The batch task is still running, restore the status
            currentBatch = { batch_id, ...data };
            activeBatchId = batch_id;
            isOutlookBatchMode = (mode === 'outlook_batch');
            batchCompleted = false;
            batchFinalStatus = null;
            toastShown = false;
            displayedLogs.clear();
            elements.startBtn.disabled = true;
            elements.cancelBtn.disabled = false;
            showBatchStatus({ count: total || data.total });
            updateBatchProgress(data);
            addLog('info', `[System] has detected batch tasks in progress and is reconnecting to monitor... (${batch_id.substring(0, 8)})`);
            connectBatchWebSocket(batch_id);
        } catch {
            sessionStorage.removeItem('activeTask');
        }
    }
}
