/**
 * Set page JavaScript
 * Use the tool library in utils.js
 */

// DOM element
const elements = {
    tabs: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    registrationForm: document.getElementById('registration-settings-form'),
    backupBtn: document.getElementById('backup-btn'),
    cleanupBtn: document.getElementById('cleanup-btn'),
    addEmailServiceBtn: document.getElementById('add-email-service-btn'),
    addServiceModal: document.getElementById('add-service-modal'),
    addServiceForm: document.getElementById('add-service-form'),
    closeServiceModal: document.getElementById('close-service-modal'),
    cancelAddService: document.getElementById('cancel-add-service'),
    serviceType: document.getElementById('service-type'),
    serviceConfigFields: document.getElementById('service-config-fields'),
    emailServicesTable: document.getElementById('email-services-table'),
    // Outlook import
    toggleImportBtn: document.getElementById('toggle-import-btn'),
    outlookImportBody: document.getElementById('outlook-import-body'),
    outlookImportBtn: document.getElementById('outlook-import-btn'),
    clearImportBtn: document.getElementById('clear-import-btn'),
    outlookImportData: document.getElementById('outlook-import-data'),
    importResult: document.getElementById('import-result'),
    // batch operation
    selectAllServices: document.getElementById('select-all-services'),
    // proxy list
    proxiesTable: document.getElementById('proxies-table'),
    addProxyBtn: document.getElementById('add-proxy-btn'),
    testAllProxiesBtn: document.getElementById('test-all-proxies-btn'),
    addProxyModal: document.getElementById('add-proxy-modal'),
    proxyItemForm: document.getElementById('proxy-item-form'),
    closeProxyModal: document.getElementById('close-proxy-modal'),
    cancelProxyBtn: document.getElementById('cancel-proxy-btn'),
    proxyModalTitle: document.getElementById('proxy-modal-title'),
    //Dynamic proxy settings
    dynamicProxyForm: document.getElementById('dynamic-proxy-form'),
    testDynamicProxyBtn: document.getElementById('test-dynamic-proxy-btn'),
    // CPA service management
    addCpaServiceBtn: document.getElementById('add-cpa-service-btn'),
    cpaServicesTable: document.getElementById('cpa-services-table'),
    cpaServiceEditModal: document.getElementById('cpa-service-edit-modal'),
    closeCpaServiceModal: document.getElementById('close-cpa-service-modal'),
    cancelCpaServiceBtn: document.getElementById('cancel-cpa-service-btn'),
    cpaServiceForm: document.getElementById('cpa-service-form'),
    cpaServiceModalTitle: document.getElementById('cpa-service-modal-title'),
    testCpaServiceBtn: document.getElementById('test-cpa-service-btn'),
    // Sub2API service management
    addSub2ApiServiceBtn: document.getElementById('add-sub2api-service-btn'),
    sub2ApiServicesTable: document.getElementById('sub2api-services-table'),
    sub2ApiServiceEditModal: document.getElementById('sub2api-service-edit-modal'),
    closeSub2ApiServiceModal: document.getElementById('close-sub2api-service-modal'),
    cancelSub2ApiServiceBtn: document.getElementById('cancel-sub2api-service-btn'),
    sub2ApiServiceForm: document.getElementById('sub2api-service-form'),
    sub2ApiServiceModalTitle: document.getElementById('sub2api-service-modal-title'),
    testSub2ApiServiceBtn: document.getElementById('test-sub2api-service-btn'),
    // Team Manager service management
    addTmServiceBtn: document.getElementById('add-tm-service-btn'),
    tmServicesTable: document.getElementById('tm-services-table'),
    tmServiceEditModal: document.getElementById('tm-service-edit-modal'),
    closeTmServiceModal: document.getElementById('close-tm-service-modal'),
    cancelTmServiceBtn: document.getElementById('cancel-tm-service-btn'),
    tmServiceForm: document.getElementById('tm-service-form'),
    tmServiceModalTitle: document.getElementById('tm-service-modal-title'),
    testTmServiceBtn: document.getElementById('test-tm-service-btn'),
    // Verification code settings
    emailCodeForm: document.getElementById('email-code-form'),
    // Outlook settings
    outlookSettingsForm: document.getElementById('outlook-settings-form'),
    // Web UI access control
    webuiSettingsForm: document.getElementById('webui-settings-form')
};

// Selected service ID
let selectedServiceIds = new Set();

// initialization
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadSettings();
    loadEmailServices();
    loadDatabaseInfo();
    loadProxies();
    loadCpaServices();
    loadSub2ApiServices();
    loadTmServices();
    initEventListeners();
});

document.addEventListener('click', () => {
    document.querySelectorAll('.dropdown-menu.active').forEach(m => m.classList.remove('active'));
});

//Initialize tab page
function initTabs() {
    elements.tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;

            elements.tabs.forEach(b => b.classList.remove('active'));
            elements.tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(`${tab}-tab`).classList.add('active');
        });
    });
}

//Event listening
function initEventListeners() {
    //Registration configuration form
    if (elements.registrationForm) {
        elements.registrationForm.addEventListener('submit', handleSaveRegistration);
    }

    // Back up database
    if (elements.backupBtn) {
        elements.backupBtn.addEventListener('click', handleBackup);
    }

    // clean data
    if (elements.cleanupBtn) {
        elements.cleanupBtn.addEventListener('click', handleCleanup);
    }

    //Add email service
    if (elements.addEmailServiceBtn) {
        elements.addEmailServiceBtn.addEventListener('click', () => {
            elements.addServiceModal.classList.add('active');
            loadServiceConfigFields(elements.serviceType.value);
        });
    }

    if (elements.closeServiceModal) {
        elements.closeServiceModal.addEventListener('click', () => {
            elements.addServiceModal.classList.remove('active');
        });
    }

    if (elements.cancelAddService) {
        elements.cancelAddService.addEventListener('click', () => {
            elements.addServiceModal.classList.remove('active');
        });
    }

    if (elements.addServiceModal) {
        elements.addServiceModal.addEventListener('click', (e) => {
            if (e.target === elements.addServiceModal) {
                elements.addServiceModal.classList.remove('active');
            }
        });
    }

    // Service type switching
    if (elements.serviceType) {
        elements.serviceType.addEventListener('change', (e) => {
            loadServiceConfigFields(e.target.value);
        });
    }

    //Add service form
    if (elements.addServiceForm) {
        elements.addServiceForm.addEventListener('submit', handleAddService);
    }

    // Outlook batch import expand/collapse
    if (elements.toggleImportBtn) {
        elements.toggleImportBtn.addEventListener('click', () => {
            const isHidden = elements.outlookImportBody.style.display === 'none';
            elements.outlookImportBody.style.display = isHidden ? 'block' : 'none';
            elements.toggleImportBtn.textContent = isHidden ? 'Collapse' : 'Expand';
        });
    }

    // Outlook batch import
    if (elements.outlookImportBtn) {
        elements.outlookImportBtn.addEventListener('click', handleOutlookBatchImport);
    }

    // Clear imported data
    if (elements.clearImportBtn) {
        elements.clearImportBtn.addEventListener('click', () => {
            elements.outlookImportData.value = '';
            elements.importResult.style.display = 'none';
        });
    }

    // Select all/Deselect all
    if (elements.selectAllServices) {
        elements.selectAllServices.addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('.service-checkbox');
            checkboxes.forEach(cb => cb.checked = e.target.checked);
            updateSelectedServices();
        });
    }

    //Related to proxy list
    if (elements.addProxyBtn) {
        elements.addProxyBtn.addEventListener('click', () => openProxyModal());
    }

    if (elements.testAllProxiesBtn) {
        elements.testAllProxiesBtn.addEventListener('click', handleTestAllProxies);
    }

    if (elements.closeProxyModal) {
        elements.closeProxyModal.addEventListener('click', closeProxyModal);
    }

    if (elements.cancelProxyBtn) {
        elements.cancelProxyBtn.addEventListener('click', closeProxyModal);
    }

    if (elements.addProxyModal) {
        elements.addProxyModal.addEventListener('click', (e) => {
            if (e.target === elements.addProxyModal) {
                closeProxyModal();
            }
        });
    }

    if (elements.proxyItemForm) {
        elements.proxyItemForm.addEventListener('submit', handleSaveProxyItem);
    }

    //Dynamic proxy settings
    if (elements.dynamicProxyForm) {
        elements.dynamicProxyForm.addEventListener('submit', handleSaveDynamicProxy);
    }
    if (elements.testDynamicProxyBtn) {
        elements.testDynamicProxyBtn.addEventListener('click', handleTestDynamicProxy);
    }

    // Verification code settings
    if (elements.emailCodeForm) {
        elements.emailCodeForm.addEventListener('submit', handleSaveEmailCode);
    }

    // Outlook settings
    if (elements.outlookSettingsForm) {
        elements.outlookSettingsForm.addEventListener('submit', handleSaveOutlookSettings);
    }

    if (elements.webuiSettingsForm) {
        elements.webuiSettingsForm.addEventListener('submit', handleSaveWebuiSettings);
    }
    // Team Manager service management
    if (elements.addTmServiceBtn) {
        elements.addTmServiceBtn.addEventListener('click', () => openTmServiceModal());
    }
    if (elements.closeTmServiceModal) {
        elements.closeTmServiceModal.addEventListener('click', closeTmServiceModal);
    }
    if (elements.cancelTmServiceBtn) {
        elements.cancelTmServiceBtn.addEventListener('click', closeTmServiceModal);
    }
    if (elements.tmServiceEditModal) {
        elements.tmServiceEditModal.addEventListener('click', (e) => {
            if (e.target === elements.tmServiceEditModal) closeTmServiceModal();
        });
    }
    if (elements.tmServiceForm) {
        elements.tmServiceForm.addEventListener('submit', handleSaveTmService);
    }
    if (elements.testTmServiceBtn) {
        elements.testTmServiceBtn.addEventListener('click', handleTestTmService);
    }

    // CPA service management
    if (elements.addCpaServiceBtn) {
        elements.addCpaServiceBtn.addEventListener('click', () => openCpaServiceModal());
    }
    if (elements.closeCpaServiceModal) {
        elements.closeCpaServiceModal.addEventListener('click', closeCpaServiceModal);
    }
    if (elements.cancelCpaServiceBtn) {
        elements.cancelCpaServiceBtn.addEventListener('click', closeCpaServiceModal);
    }
    if (elements.cpaServiceEditModal) {
        elements.cpaServiceEditModal.addEventListener('click', (e) => {
            if (e.target === elements.cpaServiceEditModal) closeCpaServiceModal();
        });
    }
    if (elements.cpaServiceForm) {
        elements.cpaServiceForm.addEventListener('submit', handleSaveCpaService);
    }
    if (elements.testCpaServiceBtn) {
        elements.testCpaServiceBtn.addEventListener('click', handleTestCpaService);
    }

    // Sub2API service management
    if (elements.addSub2ApiServiceBtn) {
        elements.addSub2ApiServiceBtn.addEventListener('click', () => openSub2ApiServiceModal());
    }
    if (elements.closeSub2ApiServiceModal) {
        elements.closeSub2ApiServiceModal.addEventListener('click', closeSub2ApiServiceModal);
    }
    if (elements.cancelSub2ApiServiceBtn) {
        elements.cancelSub2ApiServiceBtn.addEventListener('click', closeSub2ApiServiceModal);
    }
    if (elements.sub2ApiServiceEditModal) {
        elements.sub2ApiServiceEditModal.addEventListener('click', (e) => {
            if (e.target === elements.sub2ApiServiceEditModal) closeSub2ApiServiceModal();
        });
    }
    if (elements.sub2ApiServiceForm) {
        elements.sub2ApiServiceForm.addEventListener('submit', handleSaveSub2ApiService);
    }
    if (elements.testSub2ApiServiceBtn) {
        elements.testSub2ApiServiceBtn.addEventListener('click', handleTestSub2ApiService);
    }
}

//Load settings
async function loadSettings() {
    try {
        const data = await api.get('/settings');

        //Dynamic proxy settings
        document.getElementById('dynamic-proxy-enabled').checked = data.proxy?.dynamic_enabled || false;
        document.getElementById('dynamic-proxy-api-url').value = data.proxy?.dynamic_api_url || '';
        document.getElementById('dynamic-proxy-api-key-header').value = data.proxy?.dynamic_api_key_header || 'X-API-Key';
        document.getElementById('dynamic-proxy-result-field').value = data.proxy?.dynamic_result_field || '';

        //Register configuration
        document.getElementById('max-retries').value = data.registration?.max_retries || 3;
        document.getElementById('timeout').value = data.registration?.timeout || 120;
        document.getElementById('password-length').value = data.registration?.default_password_length || 12;
        document.getElementById('sleep-min').value = data.registration?.sleep_min || 5;
        document.getElementById('sleep-max').value = data.registration?.sleep_max || 30;

        //Verification code waiting for configuration
        if (data.email_code) {
            document.getElementById('email-code-timeout').value = data.email_code.timeout || 120;
            document.getElementById('email-code-poll-interval').value = data.email_code.poll_interval || 3;
        }

        // Load Outlook settings
        loadOutlookSettings();

        // Web UI access password prompt
        if (data.webui?.has_access_password) {
            const input = document.getElementById('webui-access-password');
            if (input) {
                input.value = '';
                input.placeholder = 'Configured, leave blank to remain unchanged';
            }
        }

    } catch (error) {
        console.error('Loading settings failed:', error);
        toast.error('Loading settings failed');
    }
}

//Save Web UI settings
async function handleSaveWebuiSettings(e) {
    e.preventDefault();

    const accessPassword = document.getElementById('webui-access-password').value;
    const payload = {
        access_password: accessPassword || null
    };

    try {
        await api.post('/settings/webui', payload);
        toast.success('Web UI settings updated');
        document.getElementById('webui-access-password').value = '';
    } catch (error) {
        console.error('Failed to save Web UI settings:', error);
        toast.error('Failed to save Web UI settings');
    }
}

//Load the mailbox service
async function loadEmailServices() {
    // Check if the element exists
    if (!elements.emailServicesTable) return;

    try {
        const data = await api.get('/email-services');
        renderEmailServices(data.services);
    } catch (error) {
        console.error('Failed to load email service:', error);
        if (elements.emailServicesTable) {
            elements.emailServicesTable.innerHTML = `
                <tr>
                    <td colspan="7">
                        <div class="empty-state">
                            <div class="empty-state-icon">❌</div>
                            <div class="empty-state-title">Loading failed</div>
                        </div>
                    </td>
                </tr>
            `;
        }
    }
}

// Render mailbox service
function renderEmailServices(services) {
    // Check if the element exists
    if (!elements.emailServicesTable) return;

    if (services.length === 0) {
        elements.emailServicesTable.innerHTML = `
            <tr>
                <td colspan="7">
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <div class="empty-state-title">No configuration yet</div>
                        <div class="empty-state-description">Click the "Add Service" button above to add an email service</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    elements.emailServicesTable.innerHTML = services.map(service => `
        <tr data-service-id="${service.id}">
            <td>
                <input type="checkbox" class="service-checkbox" data-id="${service.id}"
                    onchange="updateSelectedServices()">
            </td>
            <td>${escapeHtml(service.name)}</td>
            <td>${getServiceTypeText(service.service_type)}</td>
            <td title="${service.enabled ? 'Enabled' : 'Disabled'}">${service.enabled ? '✅' : '⭕'}</td>
            <td>${service.priority}</td>
            <td>${format.date(service.last_used)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn btn-ghost btn-sm" onclick="testService(${service.id})" title="Test">
                        🔌
                    </button>
                    <button class="btn btn-ghost btn-sm" onclick="toggleService(${service.id}, ${!service.enabled})" title="${service.enabled ? 'Disable' : 'Enable'}">
                        ${service.enabled ? '🔒' : '🔓'}
                    </button>
                    <button class="btn btn-ghost btn-sm" onclick="deleteService(${service.id})" title="Delete">
                        🗑️
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

//Load database information
async function loadDatabaseInfo() {
    try {
        const data = await api.get('/settings/database');

        document.getElementById('db-size').textContent = `${data.database_size_mb} MB`;
        document.getElementById('db-accounts').textContent = format.number(data.accounts_count);
        document.getElementById('db-services').textContent = format.number(data.email_services_count);
        document.getElementById('db-tasks').textContent = format.number(data.tasks_count);

    } catch (error) {
        console.error('Failed to load database information:', error);
    }
}

//Save registration configuration
async function handleSaveRegistration(e) {
    e.preventDefault();

    const data = {
        max_retries: parseInt(document.getElementById('max-retries').value),
        timeout: parseInt(document.getElementById('timeout').value),
        default_password_length: parseInt(document.getElementById('password-length').value),
        sleep_min: parseInt(document.getElementById('sleep-min').value),
        sleep_max: parseInt(document.getElementById('sleep-max').value),
    };

    try {
        await api.post('/settings/registration', data);
        toast.success('Registration configuration has been saved');
    } catch (error) {
        toast.error('Save failed: ' + error.message);
    }
}

//Save the verification code and wait for configuration
async function handleSaveEmailCode(e) {
    e.preventDefault();

    const timeout = parseInt(document.getElementById('email-code-timeout').value);
    const pollInterval = parseInt(document.getElementById('email-code-poll-interval').value);

    // Client verification
    if (timeout < 30 || timeout > 600) {
        toast.error('Waiting timeout must be between 30-600 seconds');
        return;
    }
    if (pollInterval < 1 || pollInterval > 30) {
        toast.error('Polling interval must be between 1-30 seconds');
        return;
    }

    const data = {
        timeout: timeout,
        poll_interval: pollInterval
    };

    try {
        await api.post('/settings/email-code', data);
        toast.success('Verification code configuration has been saved');
    } catch (error) {
        toast.error('Save failed: ' + error.message);
    }
}

// Back up database
async function handleBackup() {
    elements.backupBtn.disabled = true;
    elements.backupBtn.innerHTML = '<span class="loading-spinner"></span> Backing up...';

    try {
        const data = await api.post('/settings/database/backup');
        toast.success(`Backup successful: ${data.backup_path}`);
    } catch (error) {
        toast.error('Backup failed: ' + error.message);
    } finally {
        elements.backupBtn.disabled = false;
        elements.backupBtn.textContent = '💾 Backup database';
    }
}

// clean data
async function handleCleanup() {
    const confirmed = await confirm('Are you sure you want to clean up expired data? This operation is not reversible.');
    if (!confirmed) return;

    elements.cleanupBtn.disabled = true;
    elements.cleanupBtn.innerHTML = '<span class="loading-spinner"></span> Cleaning...';

    try {
        const data = await api.post('/settings/database/cleanup?days=30');
        toast.success(data.message);
        loadDatabaseInfo();
    } catch (error) {
        toast.error('Cleaning failed: ' + error.message);
    } finally {
        elements.cleanupBtn.disabled = false;
        elements.cleanupBtn.textContent = '🧹 Clean up expired data';
    }
}

//Load service configuration fields
async function loadServiceConfigFields(serviceType) {
    try {
        const data = await api.get('/email-services/types');
        const typeInfo = data.types.find(t => t.value === serviceType);

        if (!typeInfo) {
            elements.serviceConfigFields.innerHTML = '';
            return;
        }

        elements.serviceConfigFields.innerHTML = typeInfo.config_fields.map(field => `
            <div class="form-group">
                <label for="config-${field.name}">${field.label}</label>
                <input type="${field.name.includes('password') || field.name.includes('token') ? 'password' : 'text'}"
                       id="config-${field.name}"
                       name="${field.name}"
                       value="${field.default || ''}"
                       placeholder="${field.label}"
                       ${field.required ? 'required' : ''}>
            </div>
        `).join('');

    } catch (error) {
        console.error('Failed to load configuration fields:', error);
    }
}

//Add email service
async function handleAddService(e) {
    e.preventDefault();

    const formData = new FormData(elements.addServiceForm);
    const config = {};

    elements.serviceConfigFields.querySelectorAll('input').forEach(input => {
        config[input.name] = input.value;
    });

    const data = {
        service_type: formData.get('service_type'),
        name: formData.get('name'),
        config: config,
        enabled: true,
        priority: 0,
    };

    try {
        await api.post('/email-services', data);
        toast.success('Mailbox service has been added');
        elements.addServiceModal.classList.remove('active');
        elements.addServiceForm.reset();
        loadEmailServices();
    } catch (error) {
        toast.error('Add failed: ' + error.message);
    }
}

// test service
async function testService(id) {
    try {
        const data = await api.post(`/email-services/${id}/test`);
        if (data.success) {
            toast.success('Service connection is normal');
        } else {
            toast.warning('Service connection failed: ' + data.message);
        }
    } catch (error) {
        toast.error('Test failed: ' + error.message);
    }
}

//Switch service status
async function toggleService(id, enabled) {
    try {
        const endpoint = enabled ? 'enable' : 'disable';
        await api.post(`/email-services/${id}/${endpoint}`);
        toast.success(enabled ? 'Service is enabled' : 'Service is disabled');
        loadEmailServices();
    } catch (error) {
        toast.error('Operation failed: ' + error.message);
    }
}

// Delete service
async function deleteService(id) {
    const confirmed = await confirm('Are you sure you want to delete this email service configuration?');
    if (!confirmed) return;

    try {
        await api.delete(`/email-services/${id}`);
        toast.success('Service has been deleted');
        loadEmailServices();
    } catch (error) {
        toast.error('Deletion failed: ' + error.message);
    }
}

//Update the selected service
function updateSelectedServices() {
    selectedServiceIds.clear();
    document.querySelectorAll('.service-checkbox:checked').forEach(cb => {
        selectedServiceIds.add(parseInt(cb.dataset.id));
    });
}

// Outlook batch import
async function handleOutlookBatchImport() {
    const data = elements.outlookImportData.value.trim();
    if (!data) {
        toast.warning('Please enter the data to be imported');
        return;
    }

    const enabled = document.getElementById('outlook-import-enabled').checked;
    const priority = parseInt(document.getElementById('outlook-import-priority').value) || 0;

    // parse data
    const lines = data.split('\n').filter(line => line.trim() && !line.trim().startsWith('#'));
    const accounts = [];
    const errors = [];

    lines.forEach((line, index) => {
        const parts = line.split('----').map(p => p.trim());
        if (parts.length < 2) {
            errors.push(`Line ${index + 1} is formatted incorrectly`);
            return;
        }

        const account = {
            email: parts[0],
            password: parts[1],
            client_id: parts[2] || null,
            refresh_token: parts[3] || null,
            enabled: enabled,
            priority: priority
        };

        if (!account.email.includes('@')) {
            errors.push(`Email format error in line ${index + 1}: ${account.email}`);
            return;
        }

        accounts.push(account);
    });

    if (errors.length > 0) {
        elements.importResult.style.display = 'block';
        elements.importResult.innerHTML = `
            <div class="import-errors">${errors.map(e => `<div>${e}</div>`).join('')}</div>
        `;
        return;
    }

    elements.outlookImportBtn.disabled = true;
    elements.outlookImportBtn.innerHTML = '<span class="loading-spinner"></span> Importing...';

    let successCount = 0;
    let failCount = 0;

    try {
        for (const account of accounts) {
            try {
                await api.post('/email-services', {
                    service_type: 'outlook',
                    name: account.email,
                    config: {
                        email: account.email,
                        password: account.password,
                        client_id: account.client_id,
                        refresh_token: account.refresh_token
                    },
                    enabled: account.enabled,
                    priority: account.priority
                });
                successCount++;
            } catch {
                failCount++;
            }
        }

        elements.importResult.style.display = 'block';
        elements.importResult.innerHTML = `
            <div class="import-stats">
                <span>✅ Success: ${successCount}</span>
                <span>❌ Failed: ${failCount}</span>
            </div>
        `;

        toast.success(`Import completed, ${successCount} successful`);
        loadEmailServices();

    } catch (error) {
        toast.error('Import failed: ' + error.message);
    } finally {
        elements.outlookImportBtn.disabled = false;
        elements.outlookImportBtn.textContent = '📥 Start importing';
    }
}

//HTML escaping
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// ============================================================================
//Agent list management
// ============================================================================

//Load proxy list
async function loadProxies() {
    try {
        const data = await api.get('/settings/proxies');
        renderProxies(data.proxies);
    } catch (error) {
        console.error('Failed to load proxy list:', error);
        elements.proxiesTable.innerHTML = `
            <tr>
                <td colspan="7">
                    <div class="empty-state">
                        <div class="empty-state-icon">❌</div>
                        <div class="empty-state-title">Loading failed</div>
                    </div>
                </td>
            </tr>
        `;
    }
}

// Render proxy list
function renderProxies(proxies) {
    if (!proxies || proxies.length === 0) {
        elements.proxiesTable.innerHTML = `
            <tr>
                <td colspan="7">
                    <div class="empty-state">
                        <div class="empty-state-icon">🌐</div>
                        <div class="empty-state-title">No agent yet</div>
                        <div class="empty-state-description">Click the "Add Proxy" button to add a proxy server</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    elements.proxiesTable.innerHTML = proxies.map(proxy => `
        <tr data-proxy-id="${proxy.id}">
            <td>${proxy.id}</td>
            <td>${escapeHtml(proxy.name)}</td>
            <td><span class="badge">${proxy.type.toUpperCase()}</span></td>
            <td><code>${escapeHtml(proxy.host)}:${proxy.port}</code></td>
            <td>
                ${proxy.is_default
                    ? '<span class="status-badge active">Default</span>'
                    : `<button class="btn btn-ghost btn-sm" onclick="handleSetProxyDefault(${proxy.id})" title="Set as default">Set as default</button>`
                }
            </td>
            <td title="${proxy.enabled ? 'Enabled' : 'Disabled'}">${proxy.enabled ? '✅' : '⭕'}</td>
            <td>${format.date(proxy.last_used)}</td>
            <td>
                <div style="display:flex;gap:4px;align-items:center;white-space:nowrap;">
                    <button class="btn btn-secondary btn-sm" onclick="editProxyItem(${proxy.id})">Edit</button>
                    <div class="dropdown" style="position:relative;">
                        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();toggleSettingsMoreMenu(this)">More</button>
                        <div class="dropdown-menu" style="min-width:80px;">
                            <a href="#" class="dropdown-item" onclick="event.preventDefault();closeSettingsMoreMenu(this);testProxyItem(${proxy.id})">Test</a>
                            <a href="#" class="dropdown-item" onclick="event.preventDefault();closeSettingsMoreMenu(this);toggleProxyItem(${proxy.id}, ${!proxy.enabled})">${proxy.enabled ? 'Disable' : 'Enable'}</a>
                            ${!proxy.is_default ? `<a href="#" class="dropdown-item" onclick="event.preventDefault();closeSettingsMoreMenu(this);handleSetProxyDefault(${proxy.id})">Set as default</a>` : ''}
                        </div>
                    </div>
                    <button class="btn btn-danger btn-sm" onclick="deleteProxyItem(${proxy.id})">Delete</button>
                </div>
            </td>
        </tr>
    `).join('');
}

function toggleSettingsMoreMenu(btn) {
    const menu = btn.nextElementSibling;
    const isActive = menu.classList.contains('active');
    document.querySelectorAll('.dropdown-menu.active').forEach(m => m.classList.remove('active'));
    if (!isActive) menu.classList.add('active');
}

function closeSettingsMoreMenu(el) {
    const menu = el.closest('.dropdown-menu');
    if (menu) menu.classList.remove('active');
}

//Set as default proxy
async function handleSetProxyDefault(id) {
    try {
        await api.post(`/settings/proxies/${id}/set-default`);
        toast.success('set as default proxy');
        loadProxies();
    } catch (error) {
        toast.error('Operation failed: ' + error.message);
    }
}

//Open the agent modal box
function openProxyModal(proxy = null) {
    elements.proxyModalTitle.textContent = proxy ? 'Edit proxy' : 'Add proxy';
    elements.proxyItemForm.reset();

    document.getElementById('proxy-item-id').value = proxy ? proxy.id : '';

    if (proxy) {
        document.getElementById('proxy-item-name').value = proxy.name || '';
        document.getElementById('proxy-item-type').value = proxy.type || 'http';
        document.getElementById('proxy-item-host').value = proxy.host || '';
        document.getElementById('proxy-item-port').value = proxy.port || '';
        document.getElementById('proxy-item-username').value = proxy.username || '';
        document.getElementById('proxy-item-password').value = '';
    }

    elements.addProxyModal.classList.add('active');
}

// Close the agent modal box
function closeProxyModal() {
    elements.addProxyModal.classList.remove('active');
    elements.proxyItemForm.reset();
}

// save proxy
async function handleSaveProxyItem(e) {
    e.preventDefault();

    const proxyId = document.getElementById('proxy-item-id').value;
    const data = {
        name: document.getElementById('proxy-item-name').value,
        type: document.getElementById('proxy-item-type').value,
        host: document.getElementById('proxy-item-host').value,
        port: parseInt(document.getElementById('proxy-item-port').value),
        username: document.getElementById('proxy-item-username').value || null,
        password: document.getElementById('proxy-item-password').value || null,
        enabled: true
    };

    try {
        if (proxyId) {
            await api.patch(`/settings/proxies/${proxyId}`, data);
            toast.success('Agent has been updated');
        } else {
            await api.post('/settings/proxies', data);
            toast.success('Agent has been added');
        }
        closeProxyModal();
        loadProxies();
    } catch (error) {
        toast.error('Save failed: ' + error.message);
    }
}

//edit agent
async function editProxyItem(id) {
    try {
        const proxy = await api.get(`/settings/proxies/${id}`);
        openProxyModal(proxy);
    } catch (error) {
        toast.error('Failed to obtain agent information');
    }
}

//Test a single agent
async function testProxyItem(id) {
    try {
        const result = await api.post(`/settings/proxies/${id}/test`);
        if (result.success) {
            toast.success(result.message);
        } else {
            toast.error(result.message);
        }
    } catch (error) {
        toast.error('Test failed: ' + error.message);
    }
}

//Switch agent status
async function toggleProxyItem(id, enabled) {
    try {
        const endpoint = enabled ? 'enable' : 'disable';
        await api.post(`/settings/proxies/${id}/${endpoint}`);
        toast.success(enabled ? 'Agent is enabled' : 'Agent is disabled');
        loadProxies();
    } catch (error) {
        toast.error('Operation failed: ' + error.message);
    }
}

// Delete proxy
async function deleteProxyItem(id) {
    const confirmed = await confirm('Are you sure you want to delete this agent?');
    if (!confirmed) return;

    try {
        await api.delete(`/settings/proxies/${id}`);
        toast.success('Agent has been deleted');
        loadProxies();
    } catch (error) {
        toast.error('Deletion failed: ' + error.message);
    }
}

// Test all proxies
async function handleTestAllProxies() {
    elements.testAllProxiesBtn.disabled = true;
    elements.testAllProxiesBtn.innerHTML = '<span class="loading-spinner"></span> Testing...';

    try {
        const result = await api.post('/settings/proxies/test-all');
        toast.info(`Test completed: successful ${result.success}, failed ${result.failed}`);
        loadProxies();
    } catch (error) {
        toast.error('Test failed: ' + error.message);
    } finally {
        elements.testAllProxiesBtn.disabled = false;
        elements.testAllProxiesBtn.textContent = '🔌 Test all';
    }
}


// ============================================================================
// Outlook settings management
// ============================================================================

// Load Outlook settings
async function loadOutlookSettings() {
    try {
        const data = await api.get('/settings/outlook');
        const el = document.getElementById('outlook-default-client-id');
        if (el) el.value = data.default_client_id || '';
    } catch (error) {
        console.error('Failed to load Outlook settings:', error);
    }
}

//Save Outlook settings
async function handleSaveOutlookSettings(e) {
    e.preventDefault();
    const data = {
        default_client_id: document.getElementById('outlook-default-client-id').value
    };
    try {
        await api.post('/settings/outlook', data);
        toast.success('Outlook settings saved');
    } catch (error) {
        toast.error('Save failed: ' + error.message);
    }
}

// ============== Dynamic proxy settings ==============

async function handleSaveDynamicProxy(e) {
    e.preventDefault();
    const data = {
        enabled: document.getElementById('dynamic-proxy-enabled').checked,
        api_url: document.getElementById('dynamic-proxy-api-url').value.trim(),
        api_key: document.getElementById('dynamic-proxy-api-key').value || null,
        api_key_header: document.getElementById('dynamic-proxy-api-key-header').value.trim() || 'X-API-Key',
        result_field: document.getElementById('dynamic-proxy-result-field').value.trim()
    };
    try {
        await api.post('/settings/proxy/dynamic', data);
        toast.success('Dynamic proxy settings saved');
        document.getElementById('dynamic-proxy-api-key').value = '';
    } catch (error) {
        toast.error('Save failed: ' + error.message);
    }
}

async function handleTestDynamicProxy() {
    const apiUrl = document.getElementById('dynamic-proxy-api-url').value.trim();
    if (!apiUrl) {
        toast.warning('Please fill in the dynamic proxy API address first');
        return;
    }
    const btn = elements.testDynamicProxyBtn;
    btn.disabled = true;
    btn.textContent = 'Testing...';
    try {
        const result = await api.post('/settings/proxy/dynamic/test', {
            api_url: apiUrl,
            api_key: document.getElementById('dynamic-proxy-api-key').value || null,
            api_key_header: document.getElementById('dynamic-proxy-api-key-header').value.trim() || 'X-API-Key',
            result_field: document.getElementById('dynamic-proxy-result-field').value.trim()
        });
        if (result.success) {
            toast.success(result.message);
        } else {
            toast.error(result.message);
        }
    } catch (error) {
        toast.error('Test failed: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🔌 Test dynamic proxy';
    }
}

// ============== Team Manager Service Management ==============

async function loadTmServices() {
    if (!elements.tmServicesTable) return;
    try {
        const services = await api.get('/tm-services');
        renderTmServicesTable(services);
    } catch (e) {
        elements.tmServicesTable.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--danger-color);">${e.message}</td></tr>`;
    }
}

function renderTmServicesTable(services) {
    if (!services || services.length === 0) {
        elements.tmServicesTable.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px;">There is currently no Team Manager service, click "Add Service" to add one</td></tr>';
        return;
    }
    elements.tmServicesTable.innerHTML = services.map(s => `
        <tr>
            <td>${escapeHtml(s.name)}</td>
            <td style="font-size:0.85rem;color:var(--text-muted);">${escapeHtml(s.api_url)}</td>
            <td style="text-align:center;" title="${s.enabled ? 'Enabled' : 'Disabled'}">${s.enabled ? '✅' : '⭕'}</td>
            <td style="text-align:center;">${s.priority}</td>
            <td style="white-space:nowrap;">
                <button class="btn btn-secondary btn-sm" onclick="editTmService(${s.id})">Edit</button>
                <button class="btn btn-secondary btn-sm" onclick="testTmServiceById(${s.id})">Test</button>
                <button class="btn btn-danger btn-sm" onclick="deleteTmService(${s.id}, '${escapeHtml(s.name)}')">Delete</button>
            </td>
        </tr>
    `).join('');
}

function openTmServiceModal(service = null) {
    document.getElementById('tm-service-id').value = service ? service.id : '';
    document.getElementById('tm-service-name').value = service ? service.name : '';
    document.getElementById('tm-service-url').value = service ? service.api_url : '';
    document.getElementById('tm-service-key').value = '';
    document.getElementById('tm-service-priority').value = service ? service.priority : 0;
    document.getElementById('tm-service-enabled').checked = service ? service.enabled : true;
    if (service) {
        document.getElementById('tm-service-key').placeholder = service.has_key ? 'Configured, leave blank to remain unchanged' : 'Please enter API Key';
    } else {
        document.getElementById('tm-service-key').placeholder = 'Please enter API Key';
    }
    elements.tmServiceModalTitle.textContent = service ? 'Edit Team Manager service' : 'Add Team Manager service';
    elements.tmServiceEditModal.classList.add('active');
}

function closeTmServiceModal() {
    elements.tmServiceEditModal.classList.remove('active');
}

async function editTmService(id) {
    try {
        const service = await api.get(`/tm-services/${id}`);
        openTmServiceModal(service);
    } catch (e) {
        toast.error('Failed to obtain service information: ' + e.message);
    }
}

async function handleSaveTmService(e) {
    e.preventDefault();
    const id = document.getElementById('tm-service-id').value;
    const name = document.getElementById('tm-service-name').value.trim();
    const apiUrl = document.getElementById('tm-service-url').value.trim();
    const apiKey = document.getElementById('tm-service-key').value.trim();
    const priority = parseInt(document.getElementById('tm-service-priority').value) || 0;
    const enabled = document.getElementById('tm-service-enabled').checked;

    if (!name || !apiUrl) {
        toast.error('Name and API URL cannot be empty');
        return;
    }
    if (!id && !apiKey) {
        toast.error('API Key cannot be empty when adding a service');
        return;
    }

    try {
        const payload = { name, api_url: apiUrl, priority, enabled };
        if (apiKey) payload.api_key = apiKey;

        if (id) {
            await api.patch(`/tm-services/${id}`, payload);
            toast.success('Service has been updated');
        } else {
            payload.api_key = apiKey;
            await api.post('/tm-services', payload);
            toast.success('Service has been added');
        }
        closeTmServiceModal();
        loadTmServices();
    } catch (e) {
        toast.error('Save failed: ' + e.message);
    }
}

async function deleteTmService(id, name) {
    const confirmed = await confirm(`Are you sure you want to delete the Team Manager service "${name}"?`);
    if (!confirmed) return;
    try {
        await api.delete(`/tm-services/${id}`);
        toast.success('deleted');
        loadTmServices();
    } catch (e) {
        toast.error('Deletion failed: ' + e.message);
    }
}

async function testTmServiceById(id) {
    try {
        const result = await api.post(`/tm-services/${id}/test`);
        if (result.success) {
            toast.success(result.message);
        } else {
            toast.error(result.message);
        }
    } catch (e) {
        toast.error('Test failed: ' + e.message);
    }
}

async function handleTestTmService() {
    const apiUrl = document.getElementById('tm-service-url').value.trim();
    const apiKey = document.getElementById('tm-service-key').value.trim();
    const id = document.getElementById('tm-service-id').value;

    if (!apiUrl) {
        toast.error('Please fill in the API URL first');
        return;
    }
    if (!id && !apiKey) {
        toast.error('Please fill in the API Key first');
        return;
    }

    elements.testTmServiceBtn.disabled = true;
    elements.testTmServiceBtn.textContent = 'Testing...';

    try {
        let result;
        if (id && !apiKey) {
            result = await api.post(`/tm-services/${id}/test`);
        } else {
            result = await api.post('/tm-services/test-connection', { api_url: apiUrl, api_key: apiKey });
        }
        if (result.success) {
            toast.success(result.message);
        } else {
            toast.error(result.message);
        }
    } catch (e) {
        toast.error('Test failed: ' + e.message);
    } finally {
        elements.testTmServiceBtn.disabled = false;
        elements.testTmServiceBtn.textContent = '🔌 Test connection';
    }
}


// ============== CPA Service Management ==============

async function loadCpaServices() {
    if (!elements.cpaServicesTable) return;
    try {
        const services = await api.get('/cpa-services');
        renderCpaServicesTable(services);
    } catch (e) {
        elements.cpaServicesTable.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--danger-color);">${e.message}</td></tr>`;
    }
}

function renderCpaServicesTable(services) {
    if (!services || services.length === 0) {
        elements.cpaServicesTable.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px;">There is currently no CPA service, click "Add Service" to add one</td></tr>';
        return;
    }
    elements.cpaServicesTable.innerHTML = services.map(s => `
        <tr>
            <td>${escapeHtml(s.name)}</td>
            <td style="font-size:0.85rem;color:var(--text-muted);">${escapeHtml(s.api_url)}</td>
            <td style="text-align:center;" title="${s.enabled ? 'Enabled' : 'Disabled'}">${s.enabled ? '✅' : '⭕'}</td>
            <td style="text-align:center;">${s.priority}</td>
            <td style="white-space:nowrap;">
                <button class="btn btn-secondary btn-sm" onclick="editCpaService(${s.id})">Edit</button>
                <button class="btn btn-secondary btn-sm" onclick="testCpaServiceById(${s.id})">Test</button>
                <button class="btn btn-danger btn-sm" onclick="deleteCpaService(${s.id}, '${escapeHtml(s.name)}')">Delete</button>
            </td>
        </tr>
    `).join('');
}

function openCpaServiceModal(service = null) {
    document.getElementById('cpa-service-id').value = service ? service.id : '';
    document.getElementById('cpa-service-name').value = service ? service.name : '';
    document.getElementById('cpa-service-url').value = service ? service.api_url : '';
    document.getElementById('cpa-service-token').value = '';
    document.getElementById('cpa-service-priority').value = service ? service.priority : 0;
    document.getElementById('cpa-service-enabled').checked = service ? service.enabled : true;
    elements.cpaServiceModalTitle.textContent = service ? 'Edit CPA service' : 'Add CPA service';
    elements.cpaServiceEditModal.classList.add('active');
}

function closeCpaServiceModal() {
    elements.cpaServiceEditModal.classList.remove('active');
}

async function editCpaService(id) {
    try {
        const service = await api.get(`/cpa-services/${id}`);
        openCpaServiceModal(service);
    } catch (e) {
        toast.error('Failed to obtain service information: ' + e.message);
    }
}

async function handleSaveCpaService(e) {
    e.preventDefault();
    const id = document.getElementById('cpa-service-id').value;
    const name = document.getElementById('cpa-service-name').value.trim();
    const apiUrl = document.getElementById('cpa-service-url').value.trim();
    const apiToken = document.getElementById('cpa-service-token').value.trim();
    const priority = parseInt(document.getElementById('cpa-service-priority').value) || 0;
    const enabled = document.getElementById('cpa-service-enabled').checked;

    if (!name || !apiUrl) {
        toast.error('Name and API URL cannot be empty');
        return;
    }
    if (!id && !apiToken) {
        toast.error('API Token cannot be empty when adding a service');
        return;
    }

    try {
        const payload = { name, api_url: apiUrl, priority, enabled };
        if (apiToken) payload.api_token = apiToken;

        if (id) {
            await api.patch(`/cpa-services/${id}`, payload);
            toast.success('Service has been updated');
        } else {
            payload.api_token = apiToken;
            await api.post('/cpa-services', payload);
            toast.success('Service has been added');
        }
        closeCpaServiceModal();
        loadCpaServices();
    } catch (e) {
        toast.error('Save failed: ' + e.message);
    }
}

async function deleteCpaService(id, name) {
    const confirmed = await confirm(`Are you sure you want to delete the CPA service "${name}"?`);
    if (!confirmed) return;
    try {
        await api.delete(`/cpa-services/${id}`);
        toast.success('deleted');
        loadCpaServices();
    } catch (e) {
        toast.error('Deletion failed: ' + e.message);
    }
}

async function testCpaServiceById(id) {
    try {
        const result = await api.post(`/cpa-services/${id}/test`);
        if (result.success) {
            toast.success(result.message);
        } else {
            toast.error(result.message);
        }
    } catch (e) {
        toast.error('Test failed: ' + e.message);
    }
}

async function handleTestCpaService() {
    const apiUrl = document.getElementById('cpa-service-url').value.trim();
    const apiToken = document.getElementById('cpa-service-token').value.trim();
    const id = document.getElementById('cpa-service-id').value;

    if (!apiUrl) {
        toast.error('Please fill in the API URL first');
        return;
    }
    // There must be a token when adding a new one, and the token can be empty when editing (use the saved one)
    if (!id && !apiToken) {
        toast.error('Please fill in the API Token first');
        return;
    }

    elements.testCpaServiceBtn.disabled = true;
    elements.testCpaServiceBtn.textContent = 'Testing...';

    try {
        let result;
        if (id && !apiToken) {
            // If the token is not filled in when editing, test the saved service directly.
            result = await api.post(`/cpa-services/${id}/test`);
        } else {
            result = await api.post('/cpa-services/test-connection', { api_url: apiUrl, api_token: apiToken });
        }
        if (result.success) {
            toast.success(result.message);
        } else {
            toast.error(result.message);
        }
    } catch (e) {
        toast.error('Test failed: ' + e.message);
    } finally {
        elements.testCpaServiceBtn.disabled = false;
        elements.testCpaServiceBtn.textContent = '🔌 Test connection';
    }
}

// ============================================================================
// Sub2API service management
// ============================================================================

let _sub2apiEditingId = null;

async function loadSub2ApiServices() {
    try {
        const services = await api.get('/sub2api-services');
        renderSub2ApiServices(services);
    } catch (e) {
        if (elements.sub2ApiServicesTable) {
            elements.sub2ApiServicesTable.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px;">Loading failed</td></tr>';
        }
    }
}

function renderSub2ApiServices(services) {
    if (!elements.sub2ApiServicesTable) return;
    if (!services || services.length === 0) {
        elements.sub2ApiServicesTable.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:20px;">There is currently no Sub2API service, click "Add Service" to add one</td></tr>';
        return;
    }
    elements.sub2ApiServicesTable.innerHTML = services.map(s => `
        <tr>
            <td>${escapeHtml(s.name)}</td>
            <td style="font-size:0.85rem;color:var(--text-muted);">${escapeHtml(s.api_url)}</td>
            <td style="text-align:center;" title="${s.enabled ? 'Enabled' : 'Disabled'}">${s.enabled ? '✅' : '⭕'}</td>
            <td style="text-align:center;">${s.priority}</td>
            <td style="white-space:nowrap;">
                <button class="btn btn-secondary btn-sm" onclick="editSub2ApiService(${s.id})">Edit</button>
                <button class="btn btn-secondary btn-sm" onclick="testSub2ApiServiceById(${s.id})">Test</button>
                <button class="btn btn-danger btn-sm" onclick="deleteSub2ApiService(${s.id}, '${escapeHtml(s.name)}')">Delete</button>
            </td>
        </tr>
    `).join('');
}

function openSub2ApiServiceModal(svc = null) {
    _sub2apiEditingId = svc ? svc.id : null;
    elements.sub2ApiServiceModalTitle.textContent = svc ? 'Edit Sub2API service' : 'Add Sub2API service';
    elements.sub2ApiServiceForm.reset();
    document.getElementById('sub2api-service-id').value = svc ? svc.id : '';
    if (svc) {
        document.getElementById('sub2api-service-name').value = svc.name || '';
        document.getElementById('sub2api-service-url').value = svc.api_url || '';
        document.getElementById('sub2api-service-priority').value = svc.priority ?? 0;
        document.getElementById('sub2api-service-enabled').checked = svc.enabled !== false;
        document.getElementById('sub2api-service-key').placeholder = svc.has_key ? 'Already configured, leave blank to remain unchanged' : 'Please enter API Key';
    }
    elements.sub2ApiServiceEditModal.classList.add('active');
}

function closeSub2ApiServiceModal() {
    elements.sub2ApiServiceEditModal.classList.remove('active');
    elements.sub2ApiServiceForm.reset();
    _sub2apiEditingId = null;
}

async function editSub2ApiService(id) {
    try {
        const svc = await api.get(`/sub2api-services/${id}`);
        openSub2ApiServiceModal(svc);
    } catch (e) {
        toast.error('Loading failed: ' + e.message);
    }
}

async function deleteSub2ApiService(id, name) {
    if (!confirm(`Confirm to delete Sub2API service "${name}"?`)) return;
    try {
        await api.delete(`/sub2api-services/${id}`);
        toast.success('Service has been deleted');
        loadSub2ApiServices();
    } catch (e) {
        toast.error('Deletion failed: ' + e.message);
    }
}

async function handleSaveSub2ApiService(e) {
    e.preventDefault();
    const id = document.getElementById('sub2api-service-id').value;
    const data = {
        name: document.getElementById('sub2api-service-name').value,
        api_url: document.getElementById('sub2api-service-url').value,
        api_key: document.getElementById('sub2api-service-key').value || undefined,
        priority: parseInt(document.getElementById('sub2api-service-priority').value) || 0,
        enabled: document.getElementById('sub2api-service-enabled').checked,
    };
    if (!id && !data.api_key) {
        toast.error('Please fill in the API Key');
        return;
    }
    if (!data.api_key) delete data.api_key;

    try {
        if (id) {
            await api.patch(`/sub2api-services/${id}`, data);
            toast.success('Service has been updated');
        } else {
            await api.post('/sub2api-services', data);
            toast.success('Service has been added');
        }
        closeSub2ApiServiceModal();
        loadSub2ApiServices();
    } catch (e) {
        toast.error('Save failed: ' + e.message);
    }
}

async function testSub2ApiServiceById(id) {
    try {
        const result = await api.post(`/sub2api-services/${id}/test`);
        if (result.success) {
            toast.success(result.message);
        } else {
            toast.error(result.message);
        }
    } catch (e) {
        toast.error('Test failed: ' + e.message);
    }
}

async function handleTestSub2ApiService() {
    const apiUrl = document.getElementById('sub2api-service-url').value.trim();
    const apiKey = document.getElementById('sub2api-service-key').value.trim();
    const id = document.getElementById('sub2api-service-id').value;

    if (!apiUrl) {
        toast.error('Please fill in the API URL first');
        return;
    }
    if (!id && !apiKey) {
        toast.error('Please fill in the API Key first');
        return;
    }

    elements.testSub2ApiServiceBtn.disabled = true;
    elements.testSub2ApiServiceBtn.textContent = 'Testing...';

    try {
        let result;
        if (id && !apiKey) {
            result = await api.post(`/sub2api-services/${id}/test`);
        } else {
            result = await api.post('/sub2api-services/test-connection', { api_url: apiUrl, api_key: apiKey });
        }
        if (result.success) {
            toast.success(result.message);
        } else {
            toast.error(result.message);
        }
    } catch (e) {
        toast.error('Test failed: ' + e.message);
    } finally {
        elements.testSub2ApiServiceBtn.disabled = false;
        elements.testSub2ApiServiceBtn.textContent = '🔌 Test connection';
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}
