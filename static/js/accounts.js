/**
 *Account management page JavaScript
 * Use the tool library in utils.js
 */

// state
let currentPage = 1;
let pageSize = 20;
let totalAccounts = 0;
let selectedAccounts = new Set();
let isLoading = false;
let selectAllPages = false; // Whether all pages are selected
let currentFilters = { status: '', email_service: '', search: '' }; // Current filter conditions

// DOM element
const elements = {
    table: document.getElementById('accounts-table'),
    totalAccounts: document.getElementById('total-accounts'),
    activeAccounts: document.getElementById('active-accounts'),
    expiredAccounts: document.getElementById('expired-accounts'),
    failedAccounts: document.getElementById('failed-accounts'),
    filterStatus: document.getElementById('filter-status'),
    filterService: document.getElementById('filter-service'),
    searchInput: document.getElementById('search-input'),
    refreshBtn: document.getElementById('refresh-btn'),
    batchRefreshBtn: document.getElementById('batch-refresh-btn'),
    batchValidateBtn: document.getElementById('batch-validate-btn'),
    batchUploadBtn: document.getElementById('batch-upload-btn'),
    batchCheckSubBtn: document.getElementById('batch-check-sub-btn'),
    batchDeleteBtn: document.getElementById('batch-delete-btn'),
    exportBtn: document.getElementById('export-btn'),
    exportMenu: document.getElementById('export-menu'),
    selectAll: document.getElementById('select-all'),
    prevPage: document.getElementById('prev-page'),
    nextPage: document.getElementById('next-page'),
    pageInfo: document.getElementById('page-info'),
    detailModal: document.getElementById('detail-modal'),
    modalBody: document.getElementById('modal-body'),
    closeModal: document.getElementById('close-modal')
};

// initialization
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadAccounts();
    initEventListeners();
    updateBatchButtons(); // Initialize button state
    renderSelectAllBanner();
});

//Event listening
function initEventListeners() {
    // filter
    elements.filterStatus.addEventListener('change', () => {
        currentPage = 1;
        resetSelectAllPages();
        loadAccounts();
    });

    elements.filterService.addEventListener('change', () => {
        currentPage = 1;
        resetSelectAllPages();
        loadAccounts();
    });

    //Search (anti-shake)
    elements.searchInput.addEventListener('input', debounce(() => {
        currentPage = 1;
        resetSelectAllPages();
        loadAccounts();
    }, 300));

    // Shortcut key focus search
    elements.searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            elements.searchInput.blur();
            elements.searchInput.value = '';
            resetSelectAllPages();
            loadAccounts();
        }
    });

    // refresh
    elements.refreshBtn.addEventListener('click', () => {
        loadStats();
        loadAccounts();
        toast.info('refreshed');
    });

    // Batch refresh Token
    elements.batchRefreshBtn.addEventListener('click', handleBatchRefresh);

    //Batch verification Token
    elements.batchValidateBtn.addEventListener('click', handleBatchValidate);

    // Batch detection subscription
    elements.batchCheckSubBtn.addEventListener('click', handleBatchCheckSubscription);

    //Upload drop-down menu
    const uploadMenu = document.getElementById('upload-menu');
    elements.batchUploadBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        uploadMenu.classList.toggle('active');
    });
    document.getElementById('batch-upload-cpa-item').addEventListener('click', (e) => { e.preventDefault(); uploadMenu.classList.remove('active'); handleBatchUploadCpa(); });
    document.getElementById('batch-upload-sub2api-item').addEventListener('click', (e) => { e.preventDefault(); uploadMenu.classList.remove('active'); handleBatchUploadSub2Api(); });
    document.getElementById('batch-upload-tm-item').addEventListener('click', (e) => { e.preventDefault(); uploadMenu.classList.remove('active'); handleBatchUploadTm(); });

    // Batch delete
    elements.batchDeleteBtn.addEventListener('click', handleBatchDelete);

    // Select all (current page)
    elements.selectAll.addEventListener('change', (e) => {
        const checkboxes = elements.table.querySelectorAll('input[type="checkbox"][data-id]');
        checkboxes.forEach(cb => {
            cb.checked = e.target.checked;
            const id = parseInt(cb.dataset.id);
            if (e.target.checked) {
                selectedAccounts.add(id);
            } else {
                selectedAccounts.delete(id);
            }
        });
        if (!e.target.checked) {
            selectAllPages = false;
        }
        updateBatchButtons();
        renderSelectAllBanner();
    });

    // paging
    elements.prevPage.addEventListener('click', () => {
        if (currentPage > 1 && !isLoading) {
            currentPage--;
            loadAccounts();
        }
    });

    elements.nextPage.addEventListener('click', () => {
        const totalPages = Math.ceil(totalAccounts / pageSize);
        if (currentPage < totalPages && !isLoading) {
            currentPage++;
            loadAccounts();
        }
    });

    //Export
    elements.exportBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        elements.exportMenu.classList.toggle('active');
    });

    delegate(elements.exportMenu, 'click', '.dropdown-item', (e, target) => {
        e.preventDefault();
        const format = target.dataset.format;
        exportAccounts(format);
        elements.exportMenu.classList.remove('active');
    });

    // Close the modal box
    elements.closeModal.addEventListener('click', () => {
        elements.detailModal.classList.remove('active');
    });

    elements.detailModal.addEventListener('click', (e) => {
        if (e.target === elements.detailModal) {
            elements.detailModal.classList.remove('active');
        }
    });

    // Click elsewhere to close the drop-down menu
    document.addEventListener('click', () => {
        elements.exportMenu.classList.remove('active');
        uploadMenu.classList.remove('active');
        document.querySelectorAll('#accounts-table .dropdown-menu.active').forEach(m => m.classList.remove('active'));
    });
}

//Load statistics
async function loadStats() {
    try {
        const data = await api.get('/accounts/stats/summary');

        elements.totalAccounts.textContent = format.number(data.total || 0);
        elements.activeAccounts.textContent = format.number(data.by_status?.active || 0);
        elements.expiredAccounts.textContent = format.number(data.by_status?.expired || 0);
        elements.failedAccounts.textContent = format.number(data.by_status?.failed || 0);

        //Add animation effects
        animateValue(elements.totalAccounts, data.total || 0);
    } catch (error) {
        console.error('Loading statistics failed:', error);
    }
}

// digital animation
function animateValue(element, value) {
    element.style.transition = 'transform 0.2s ease';
    element.style.transform = 'scale(1.1)';
    setTimeout(() => {
        element.style.transform = 'scale(1)';
    }, 200);
}

//Load the account list
async function loadAccounts() {
    if (isLoading) return;
    isLoading = true;

    //Show loading status
    elements.table.innerHTML = `
        <tr>
            <td colspan="9">
                <div class="empty-state">
                    <div class="skeleton skeleton-text" style="width: 60%;"></div>
                    <div class="skeleton skeleton-text" style="width: 80%;"></div>
                    <div class="skeleton skeleton-text" style="width: 40%;"></div>
                </div>
            </td>
        </tr>
    `;

    //Record the current filter conditions
    currentFilters.status = elements.filterStatus.value;
    currentFilters.email_service = elements.filterService.value;
    currentFilters.search = elements.searchInput.value.trim();

    const params = new URLSearchParams({
        page: currentPage,
        page_size: pageSize,
    });

    if (currentFilters.status) {
        params.append('status', currentFilters.status);
    }

    if (currentFilters.email_service) {
        params.append('email_service', currentFilters.email_service);
    }

    if (currentFilters.search) {
        params.append('search', currentFilters.search);
    }

    try {
        const data = await api.get(`/accounts?${params}`);
        totalAccounts = data.total;
        renderAccounts(data.accounts);
        updatePagination();
    } catch (error) {
        console.error('Failed to load account list:', error);
        elements.table.innerHTML = `
            <tr>
                <td colspan="9">
                    <div class="empty-state">
                        <div class="empty-state-icon">❌</div>
                        <div class="empty-state-title">Loading failed</div>
                        <div class="empty-state-description">Please check the network connection and try again</div>
                    </div>
                </td>
            </tr>
        `;
    } finally {
        isLoading = false;
    }
}

// Render account list
function renderAccounts(accounts) {
    if (accounts.length === 0) {
        elements.table.innerHTML = `
            <tr>
                <td colspan="9">
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <div class="empty-state-title">No data</div>
                        <div class="empty-state-description">No matching account record found</div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    elements.table.innerHTML = accounts.map(account => `
        <tr data-id="${account.id}">
            <td>
                <input type="checkbox" data-id="${account.id}"
                    ${selectedAccounts.has(account.id) ? 'checked' : ''}>
            </td>
            <td>${account.id}</td>
            <td>
                <span style="display:inline-flex;align-items:center;gap:4px;">
                    <span class="email-cell" title="${escapeHtml(account.email)}">${escapeHtml(account.email)}</span>
                    <button class="btn-copy-icon copy-email-btn" data-email="${escapeHtml(account.email)}" title="Copy Email">📋</button>
                </span>
            </td>
            <td class="password-cell">
                ${account.password
                    ? `<span style="display:inline-flex;align-items:center;gap:4px;">
                        <span class="password-hidden" data-pwd="${escapeHtml(account.password)}" onclick="togglePassword(this, this.dataset.pwd)" title="Click to view">${escapeHtml(account.password.substring(0, 4) + '****')}</span>
                        <button class="btn-copy-icon copy-pwd-btn" data-pwd="${escapeHtml(account.password)}" title="Copy password">📋</button>
                       </span>`
                    : '-'}
            </td>
            <td>${getServiceTypeText(account.email_service)}</td>
            <td>${getStatusIcon(account.status)}</td>
            <td>
                <div class="cpa-status">
                    ${account.cpa_uploaded
                        ? `<span class="badge uploaded" title="Uploaded on ${format.date(account.cpa_uploaded_at)}">✓</span>`
                        : `<span class="badge pending">-</span>`}
                </div>
            </td>
            <td>
                <div class="cpa-status">
                    ${account.subscription_type
                        ? `<span class="badge uploaded" title="${account.subscription_type}">${account.subscription_type}</span>`
                        : `<span class="badge pending">-</span>`}
                </div>
            </td>
            <td>${format.date(account.last_refresh) || '-'}</td>
            <td>
                <div style="display:flex;gap:4px;align-items:center;white-space:nowrap;">
                    <button class="btn btn-secondary btn-sm" onclick="viewAccount(${account.id})">Details</button>
                    <div class="dropdown" style="position:relative;">
                        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation();toggleMoreMenu(this)">More</button>
                        <div class="dropdown-menu" style="min-width:100px;">
                            <a href="#" class="dropdown-item" onclick="event.preventDefault();closeMoreMenu(this);refreshToken(${account.id})">Refresh</a>
                            <a href="#" class="dropdown-item" onclick="event.preventDefault();closeMoreMenu(this);uploadAccount(${account.id})">Upload</a>
                            <a href="#" class="dropdown-item" onclick="event.preventDefault();closeMoreMenu(this);markSubscription(${account.id})">mark</a>
                            <a href="#" class="dropdown-item" onclick="event.preventDefault();closeMoreMenu(this);checkInboxCode(${account.id})">Inbox</a>
                        </div>
                    </div>
                    <button class="btn btn-danger btn-sm" onclick="deleteAccount(${account.id}, '${escapeHtml(account.email)}')">Delete</button>
                </div>
            </td>
        </tr>
    `).join('');

    //Bind checkbox event
    elements.table.querySelectorAll('input[type="checkbox"][data-id]').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const id = parseInt(e.target.dataset.id);
            if (e.target.checked) {
                selectedAccounts.add(id);
            } else {
                selectedAccounts.delete(id);
                selectAllPages = false;
            }
            //Synchronize all selection box status
            const allChecked = elements.table.querySelectorAll('input[type="checkbox"][data-id]');
            const checkedCount = elements.table.querySelectorAll('input[type="checkbox"][data-id]:checked').length;
            elements.selectAll.checked = allChecked.length > 0 && checkedCount === allChecked.length;
            elements.selectAll.indeterminate = checkedCount > 0 && checkedCount < allChecked.length;
            updateBatchButtons();
            renderSelectAllBanner();
        });
    });

    // Bind the copy mailbox button
    elements.table.querySelectorAll('.copy-email-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            copyToClipboard(btn.dataset.email);
        });
    });

    // Bind the copy password button
    elements.table.querySelectorAll('.copy-pwd-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            copyToClipboard(btn.dataset.pwd);
        });
    });

    //Synchronize the full selection box state after rendering
    const allCbs = elements.table.querySelectorAll('input[type="checkbox"][data-id]');
    const checkedCbs = elements.table.querySelectorAll('input[type="checkbox"][data-id]:checked');
    elements.selectAll.checked = allCbs.length > 0 && checkedCbs.length === allCbs.length;
    elements.selectAll.indeterminate = checkedCbs.length > 0 && checkedCbs.length < allCbs.length;
    renderSelectAllBanner();
}

//Switch password display
function togglePassword(element, password) {
    if (element.dataset.revealed === 'true') {
        element.textContent = password.substring(0, 4) + '****';
        element.classList.add('password-hidden');
        element.dataset.revealed = 'false';
    } else {
        element.textContent = password;
        element.classList.remove('password-hidden');
        element.dataset.revealed = 'true';
    }
}

//Update pagination
function updatePagination() {
    const totalPages = Math.max(1, Math.ceil(totalAccounts / pageSize));

    elements.prevPage.disabled = currentPage <= 1;
    elements.nextPage.disabled = currentPage >= totalPages;

    elements.pageInfo.textContent = `Page ${currentPage} / Total Page ${totalPages}`;
}

//Reset the status of all selected pages
function resetSelectAllPages() {
    selectAllPages = false;
    selectedAccounts.clear();
    updateBatchButtons();
    renderSelectAllBanner();
}

// Build a batch request body (including select_all and filter parameters)
function buildBatchPayload(extraFields = {}) {
    if (selectAllPages) {
        return {
            ids: [],
            select_all: true,
            status_filter: currentFilters.status || null,
            email_service_filter: currentFilters.email_service || null,
            search_filter: currentFilters.search || null,
            ...extraFields
        };
    }
    return { ids: Array.from(selectedAccounts), ...extraFields };
}

// Get the effective number of selections (use the total number when selecting_all)
function getEffectiveCount() {
    return selectAllPages ? totalAccounts : selectedAccounts.size;
}

//Render the select all banner
function renderSelectAllBanner() {
    let banner = document.getElementById('select-all-banner');
    const totalPages = Math.ceil(totalAccounts / pageSize);
    const currentPageSize = elements.table.querySelectorAll('input[type="checkbox"][data-id]').length;
    const checkedOnPage = elements.table.querySelectorAll('input[type="checkbox"][data-id]:checked').length;
    const allPageSelected = currentPageSize > 0 && checkedOnPage === currentPageSize;

    // Only display the banner when the current page is fully selected and there are multiple pages
    if (!allPageSelected || totalPages <= 1 || totalAccounts <= pageSize) {
        if (banner) banner.remove();
        return;
    }

    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'select-all-banner';
        banner.style.cssText = 'background:var(--primary-light,#e8f0fe);color:var(--primary-color,#1a73e8);padding:8px 16px;text-align:center;font-size:0.875rem;border-bottom:1px solid var(--border-color);';
        const tableContainer = document.querySelector('.table-container');
        if (tableContainer) tableContainer.insertAdjacentElement('beforebegin', banner);
    }

    if (selectAllPages) {
        banner.innerHTML = `All <strong>${totalAccounts}</strong> records selected. <button onclick="resetSelectAllPages()" style="margin-left:8px;color:var(--primary-color,#1a73e8);background:none;border:none;cursor:pointer;text-decoration:underline;">Cancel all selection</button>`;
    } else {
        banner.innerHTML = `All <strong>${checkedOnPage}</strong> items on the current page have been selected. <button onclick="selectAllPagesAction()" style="margin-left:8px;color:var(--primary-color,#1a73e8);background:none;border:none;cursor:pointer;text-decoration:underline;">Select all ${totalAccounts} items</button>`;
    }
}

// Select all pages
function selectAllPagesAction() {
    selectAllPages = true;
    updateBatchButtons();
    renderSelectAllBanner();
}

//Update batch operation button
function updateBatchButtons() {
    const count = getEffectiveCount();
    elements.batchDeleteBtn.disabled = count === 0;
    elements.batchRefreshBtn.disabled = count === 0;
    elements.batchValidateBtn.disabled = count === 0;
    elements.batchUploadBtn.disabled = count === 0;
    elements.batchCheckSubBtn.disabled = count === 0;
    elements.exportBtn.disabled = count === 0;

    elements.batchDeleteBtn.textContent = count > 0 ? `🗑️ Delete (${count})` : '🗑️ Batch delete';
    elements.batchRefreshBtn.textContent = count > 0 ? `🔄 Refresh (${count})` : '🔄 Refresh Tokens';
    elements.batchValidateBtn.textContent = count > 0 ? `✅ Validate (${count})` : '✅ Validate Tokens';
    elements.batchUploadBtn.textContent = count > 0 ? `☁️ Upload (${count})` : '☁️ Upload';
    elements.batchCheckSubBtn.textContent = count > 0 ? `🔍 Check (${count})` : '🔍 Check Subscription';
}

// Refresh a single account Token
async function refreshToken(id) {
    try {
        toast.info('Refreshing token...');
        const result = await api.post(`/accounts/${id}/refresh`);

        if (result.success) {
            toast.success('Token refreshed successfully');
            loadAccounts();
        } else {
            toast.error('Refresh failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        toast.error('Refresh failed: ' + error.message);
    }
}

// Batch refresh Token
async function handleBatchRefresh() {
    const count = getEffectiveCount();
    if (count === 0) return;

    const confirmed = await confirm(`Are you sure you want to refresh the tokens for the selected ${count} accounts?`);
    if (!confirmed) return;

    elements.batchRefreshBtn.disabled = true;
    elements.batchRefreshBtn.textContent = 'Refreshing...';

    try {
        const result = await api.post('/accounts/batch-refresh', buildBatchPayload());
        toast.success(`Successfully refreshed ${result.success_count} items, failed ${result.failed_count} items`);
        loadAccounts();
    } catch (error) {
        toast.error('Batch refresh failed: ' + error.message);
    } finally {
        updateBatchButtons();
    }
}

// Batch token validation
async function handleBatchValidate() {
    if (getEffectiveCount() === 0) return;

    elements.batchValidateBtn.disabled = true;
    elements.batchValidateBtn.textContent = 'Validating...';

    try {
        const result = await api.post('/accounts/batch-validate', buildBatchPayload());
        toast.info(`Valid: ${result.valid_count}, invalid: ${result.invalid_count}`);
        loadAccounts();
    } catch (error) {
        toast.error('Batch validation failed: ' + error.message);
    } finally {
        updateBatchButtons();
    }
}

// View account details
async function viewAccount(id) {
    try {
        const account = await api.get(`/accounts/${id}`);
        const tokens = await api.get(`/accounts/${id}/tokens`);

        elements.modalBody.innerHTML = `
            <div class="info-grid">
                <div class="info-item">
                    <span class="label">Email</span>
                    <span class="value">
                        ${escapeHtml(account.email)}
                        <button class="btn btn-ghost btn-sm" onclick="copyToClipboard('${escapeHtml(account.email)}')" title="Copy">
                            📋
                        </button>
                    </span>
                </div>
                <div class="info-item">
                    <span class="label">Password</span>
                    <span class="value">
                        ${account.password
                            ? `<code style="font-size: 0.75rem;">${escapeHtml(account.password)}</code>
                               <button class="btn btn-ghost btn-sm" onclick="copyToClipboard('${escapeHtml(account.password)}')" title="Copy">📋</button>`
                            : '-'}
                    </span>
                </div>
                <div class="info-item">
                    <span class="label">Mailbox service</span>
                    <span class="value">${getServiceTypeText(account.email_service)}</span>
                </div>
                <div class="info-item">
                    <span class="label">Status</span>
                    <span class="value">
                        <span class="status-badge ${getStatusClass('account', account.status)}">
                            ${getStatusText('account', account.status)}
                        </span>
                    </span>
                </div>
                <div class="info-item">
                    <span class="label">Registration time</span>
                    <span class="value">${format.date(account.registered_at)}</span>
                </div>
                <div class="info-item">
                    <span class="label">Last refresh</span>
                    <span class="value">${format.date(account.last_refresh) || '-'}</span>
                </div>
                <div class="info-item" style="grid-column: span 2;">
                    <span class="label">Account ID</span>
                    <span class="value" style="font-size: 0.75rem; word-break: break-all;">
                        ${escapeHtml(account.account_id || '-')}
                    </span>
                </div>
                <div class="info-item" style="grid-column: span 2;">
                    <span class="label">Workspace ID</span>
                    <span class="value" style="font-size: 0.75rem; word-break: break-all;">
                        ${escapeHtml(account.workspace_id || '-')}
                    </span>
                </div>
                <div class="info-item" style="grid-column: span 2;">
                    <span class="label">Client ID</span>
                    <span class="value" style="font-size: 0.75rem; word-break: break-all;">
                        ${escapeHtml(account.client_id || '-')}
                    </span>
                </div>
                <div class="info-item" style="grid-column: span 2;">
                    <span class="label">Access Token</span>
                    <div class="value" style="font-size: 0.7rem; word-break: break-all; font-family: var(--font-mono); background: var(--surface-hover); padding: 8px; border-radius: 4px;">
                        ${escapeHtml(tokens.access_token || '-')}
                        ${tokens.access_token ? `<button class="btn btn-ghost btn-sm" onclick="copyToClipboard('${escapeHtml(tokens.access_token)}')" style="margin-left: 8px;">📋</button>` : ''}
                    </div>
                </div>
                <div class="info-item" style="grid-column: span 2;">
                    <span class="label">Refresh Token</span>
                    <div class="value" style="font-size: 0.7rem; word-break: break-all; font-family: var(--font-mono); background: var(--surface-hover); padding: 8px; border-radius: 4px;">
                        ${escapeHtml(tokens.refresh_token || '-')}
                        ${tokens.refresh_token ? `<button class="btn btn-ghost btn-sm" onclick="copyToClipboard('${escapeHtml(tokens.refresh_token)}')" style="margin-left: 8px;">📋</button>` : ''}
                    </div>
                </div>
                <div class="info-item" style="grid-column: span 2;">
                    <span class="label">Cookies (for payment)</span>
                    <div class="value">
                        <textarea id="cookies-input-${id}" rows="3"
                            style="width:100%;font-size:0.7rem;font-family:var(--font-mono);background:var(--surface-hover);border:1px solid var(--border);border-radius:4px;padding:6px;color:var(--text-primary);resize:vertical;"
                            placeholder="Paste complete cookie string, leave blank to clear">${escapeHtml(account.cookies || '')}</textarea>
                        <button class="btn btn-secondary btn-sm" style="margin-top:4px" onclick="saveCookies(${id})">
                            Save Cookies
                        </button>
                    </div>
                </div>
            </div>
            <div style="margin-top: var(--spacing-lg); display: flex; gap: var(--spacing-sm);">
                <button class="btn btn-primary" onclick="refreshToken(${id}); elements.detailModal.classList.remove('active');">
                    🔄 Refresh Token
                </button>
            </div>
        `;

        elements.detailModal.classList.add('active');
    } catch (error) {
        toast.error('Failed to load account details: ' + error.message);
    }
}

//Copy email
function copyEmail(email) {
    copyToClipboard(email);
}

// Delete account
async function deleteAccount(id, email) {
    const confirmed = await confirm(`Are you sure you want to delete account ${email}? This operation is irreversible.`);
    if (!confirmed) return;

    try {
        await api.delete(`/accounts/${id}`);
        toast.success('Account has been deleted');
        selectedAccounts.delete(id);
        loadStats();
        loadAccounts();
    } catch (error) {
        toast.error('Deletion failed: ' + error.message);
    }
}

// Batch delete
async function handleBatchDelete() {
    const count = getEffectiveCount();
    if (count === 0) return;

    const confirmed = await confirm(`Are you sure you want to delete the selected ${count} accounts? This operation is irreversible.`);
    if (!confirmed) return;

    try {
        const result = await api.post('/accounts/batch-delete', buildBatchPayload());
        toast.success(`Successfully deleted ${result.deleted_count} accounts`);
        selectedAccounts.clear();
        selectAllPages = false;
        loadStats();
        loadAccounts();
    } catch (error) {
        toast.error('Deletion failed: ' + error.message);
    }
}

//Export account
async function exportAccounts(format) {
    const count = getEffectiveCount();
    if (count === 0) {
        toast.warning('Select at least one account to export');
        return;
    }

    toast.info(`Exporting ${count} accounts...`);

    try {
        const response = await fetch('/api/accounts/export/' + format, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(buildBatchPayload())
        });

        if (!response.ok) {
            throw new Error(`Export failed: HTTP ${response.status}`);
        }

        // Get file content
        const blob = await response.blob();

        // Get the file name from Content-Disposition
        const disposition = response.headers.get('Content-Disposition');
        let filename = `accounts_${Date.now()}.${(format === 'cpa' || format === 'sub2api') ? 'json' : format}`;
        if (disposition) {
            const match = disposition.match(/filename=(.+)/);
            if (match) {
                filename = match[1];
            }
        }

        //Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        toast.success('Export successful');
    } catch (error) {
        console.error('Export failed:', error);
        toast.error('Export failed: ' + error.message);
    }
}

//HTML escaping
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============== CPA Service Selection ==============

// Pop up the CPA service selection box and return Promise<{cpa_service_id: number|null}|null>
// null means user cancellation, {cpa_service_id: null} means use global configuration
function selectCpaService() {
    return new Promise(async (resolve) => {
        const modal = document.getElementById('cpa-service-modal');
        const listEl = document.getElementById('cpa-service-list');
        const closeBtn = document.getElementById('close-cpa-modal');
        const cancelBtn = document.getElementById('cancel-cpa-modal-btn');
        const globalBtn = document.getElementById('cpa-use-global-btn');

        //Load service list
        listEl.innerHTML = '<div style="text-align:center;color:var(--text-muted)">Loading...</div>';
        modal.classList.add('active');

        let services = [];
        try {
            services = await api.get('/cpa-services?enabled=true');
        } catch (e) {
            services = [];
        }

        if (services.length === 0) {
            listEl.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:12px;">No enabled CPA services are available. The global configuration will be used.</div>';
        } else {
            listEl.innerHTML = services.map(s => `
                <div class="cpa-service-item" data-id="${s.id}" style="
                    padding: 10px 14px;
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    cursor: pointer;
                    transition: background 0.15s;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div>
                        <div style="font-weight:500;">${escapeHtml(s.name)}</div>
                        <div style="font-size:0.8rem;color:var(--text-muted);">${escapeHtml(s.api_url)}</div>
                    </div>
                    <span class="badge" style="background:var(--success-color);color:#fff;font-size:0.7rem;padding:2px 8px;border-radius:10px;">Select</span>
                </div>
            `).join('');

            listEl.querySelectorAll('.cpa-service-item').forEach(item => {
                item.addEventListener('mouseenter', () => item.style.background = 'var(--surface-hover)');
                item.addEventListener('mouseleave', () => item.style.background = '');
                item.addEventListener('click', () => {
                    cleanup();
                    resolve({ cpa_service_id: parseInt(item.dataset.id) });
                });
            });
        }

        function cleanup() {
            modal.classList.remove('active');
            closeBtn.removeEventListener('click', onCancel);
            cancelBtn.removeEventListener('click', onCancel);
            globalBtn.removeEventListener('click', onGlobal);
        }
        function onCancel() { cleanup(); resolve(null); }
        function onGlobal() { cleanup(); resolve({ cpa_service_id: null }); }

        closeBtn.addEventListener('click', onCancel);
        cancelBtn.addEventListener('click', onCancel);
        globalBtn.addEventListener('click', onGlobal);
    });
}

//Unified upload entrance: popup target selection
async function uploadAccount(id) {
    const targets = [
        { label: '☁️ Upload to CPA', value: 'cpa' },
        { label: '🔗 Upload to Sub2API', value: 'sub2api' },
        { label: '🚀 Upload to Team Manager', value: 'tm' },
    ];

    const choice = await new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'modal active';
        modal.innerHTML = `
            <div class="modal-content" style="max-width:360px;">
                <div class="modal-header">
                    <h3>☁️ Select upload target</h3>
                    <button class="modal-close" id="_upload-close">&times;</button>
                </div>
                <div class="modal-body" style="display:flex;flex-direction:column;gap:8px;">
                    ${targets.map(t => `
                        <button class="btn btn-secondary" data-val="${t.value}" style="text-align:left;">${t.label}</button>
                    `).join('')}
                </div>
            </div>`;
        document.body.appendChild(modal);
        modal.querySelector('#_upload-close').addEventListener('click', () => { modal.remove(); resolve(null); });
        modal.addEventListener('click', (e) => { if (e.target === modal) { modal.remove(); resolve(null); } });
        modal.querySelectorAll('button[data-val]').forEach(btn => {
            btn.addEventListener('click', () => { modal.remove(); resolve(btn.dataset.val); });
        });
    });

    if (!choice) return;
    if (choice === 'cpa') return uploadToCpa(id);
    if (choice === 'sub2api') return uploadToSub2Api(id);
    if (choice === 'tm') return uploadToTm(id);
}

// Upload a single account to CPA
async function uploadToCpa(id) {
    const choice = await selectCpaService();
    if (choice === null) return; // User cancels

    try {
        toast.info('Uploading to CPA...');
        const payload = {};
        if (choice.cpa_service_id != null) payload.cpa_service_id = choice.cpa_service_id;
        const result = await api.post(`/accounts/${id}/upload-cpa`, payload);

        if (result.success) {
            toast.success('Upload successful');
            loadAccounts();
        } else {
            toast.error('Upload failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        toast.error('Upload failed: ' + error.message);
    }
}

//Batch upload to CPA
async function handleBatchUploadCpa() {
    const count = getEffectiveCount();
    if (count === 0) return;

    const choice = await selectCpaService();
    if (choice === null) return; // User cancels

    const confirmed = await confirm(`Are you sure you want to upload the selected ${count} accounts to CPA?`);
    if (!confirmed) return;

    elements.batchUploadBtn.disabled = true;
    elements.batchUploadBtn.textContent = 'Uploading...';

    try {
        const payload = buildBatchPayload();
        if (choice.cpa_service_id != null) payload.cpa_service_id = choice.cpa_service_id;
        const result = await api.post('/accounts/batch-upload-cpa', payload);

        let message = `Success: ${result.success_count}`;
        if (result.failed_count > 0) message += `, failed: ${result.failed_count}`;
        if (result.skipped_count > 0) message += `, skip: ${result.skipped_count}`;

        toast.success(message);
        loadAccounts();
    } catch (error) {
        toast.error('Batch upload failed: ' + error.message);
    } finally {
        updateBatchButtons();
    }
}

// ============== Subscription status ==============

// Manually mark subscription type
async function markSubscription(id) {
    const type = prompt('Please enter the subscription type (plus / team / free):', 'plus');
    if (!type) return;
    if (!['plus', 'team', 'free'].includes(type.trim().toLowerCase())) {
        toast.error('Invalid subscription type, please enter plus, team or free');
        return;
    }
    try {
        await api.post(`/payment/accounts/${id}/mark-subscription`, {
            subscription_type: type.trim().toLowerCase()
        });
        toast.success('Subscription status has been updated');
        loadAccounts();
    } catch (e) {
        toast.error('Mark failed: ' + e.message);
    }
}

// Check subscription status in batches
async function handleBatchCheckSubscription() {
    const count = getEffectiveCount();
    if (count === 0) return;
    const confirmed = await confirm(`Are you sure you want to check the subscription status of the selected ${count} accounts?`);
    if (!confirmed) return;

    elements.batchCheckSubBtn.disabled = true;
    elements.batchCheckSubBtn.textContent = 'Checking...';

    try {
        const result = await api.post('/payment/accounts/batch-check-subscription', buildBatchPayload());
        let message = `Success: ${result.success_count}`;
        if (result.failed_count > 0) message += `, failed: ${result.failed_count}`;
        toast.success(message);
        loadAccounts();
    } catch (e) {
        toast.error('Batch detection failed: ' + e.message);
    } finally {
        updateBatchButtons();
    }
}

// ============== Sub2API upload ==============

// Pop up the Sub2API service selection box and return Promise<{service_id: number|null}|null>
// null means user cancellation, {service_id: null} means automatic selection
function selectSub2ApiService() {
    return new Promise(async (resolve) => {
        const modal = document.getElementById('sub2api-service-modal');
        const listEl = document.getElementById('sub2api-service-list');
        const closeBtn = document.getElementById('close-sub2api-modal');
        const cancelBtn = document.getElementById('cancel-sub2api-modal-btn');
        const autoBtn = document.getElementById('sub2api-use-auto-btn');

        listEl.innerHTML = '<div style="text-align:center;color:var(--text-muted)">Loading...</div>';
        modal.classList.add('active');

        let services = [];
        try {
            services = await api.get('/sub2api-services?enabled=true');
        } catch (e) {
            services = [];
        }

        if (services.length === 0) {
            listEl.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:12px;">There is currently no enabled Sub2API service, the first one will be automatically selected</div>';
        } else {
            listEl.innerHTML = services.map(s => `
                <div class="sub2api-service-item" data-id="${s.id}" style="
                    padding: 10px 14px;
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    cursor: pointer;
                    transition: background 0.15s;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div>
                        <div style="font-weight:500;">${escapeHtml(s.name)}</div>
                        <div style="font-size:0.8rem;color:var(--text-muted);">${escapeHtml(s.api_url)}</div>
                    </div>
                    <span class="badge" style="background:var(--primary);color:#fff;font-size:0.7rem;padding:2px 8px;border-radius:10px;">Select</span>
                </div>
            `).join('');

            listEl.querySelectorAll('.sub2api-service-item').forEach(item => {
                item.addEventListener('mouseenter', () => item.style.background = 'var(--surface-hover)');
                item.addEventListener('mouseleave', () => item.style.background = '');
                item.addEventListener('click', () => {
                    cleanup();
                    resolve({ service_id: parseInt(item.dataset.id) });
                });
            });
        }

        function cleanup() {
            modal.classList.remove('active');
            closeBtn.removeEventListener('click', onCancel);
            cancelBtn.removeEventListener('click', onCancel);
            autoBtn.removeEventListener('click', onAuto);
        }
        function onCancel() { cleanup(); resolve(null); }
        function onAuto() { cleanup(); resolve({ service_id: null }); }

        closeBtn.addEventListener('click', onCancel);
        cancelBtn.addEventListener('click', onCancel);
        autoBtn.addEventListener('click', onAuto);
    });
}

//Batch upload to Sub2API
async function handleBatchUploadSub2Api() {
    const count = getEffectiveCount();
    if (count === 0) return;

    const choice = await selectSub2ApiService();
    if (choice === null) return; // User cancels

    const confirmed = await confirm(`Are you sure you want to upload the selected ${count} accounts to Sub2API?`);
    if (!confirmed) return;

    elements.batchUploadBtn.disabled = true;
    elements.batchUploadBtn.textContent = 'Uploading...';

    try {
        const payload = buildBatchPayload();
        if (choice.service_id != null) payload.service_id = choice.service_id;
        const result = await api.post('/accounts/batch-upload-sub2api', payload);

        let message = `Success: ${result.success_count}`;
        if (result.failed_count > 0) message += `, failed: ${result.failed_count}`;
        if (result.skipped_count > 0) message += `, skip: ${result.skipped_count}`;

        toast.success(message);
        loadAccounts();
    } catch (error) {
        toast.error('Batch upload failed: ' + error.message);
    } finally {
        updateBatchButtons();
    }
}

// ============== Team Manager upload ==============

// Upload a single account to Sub2API
async function uploadToSub2Api(id) {
    const choice = await selectSub2ApiService();
    if (choice === null) return;
    try {
        toast.info('Uploading to Sub2API...');
        const payload = {};
        if (choice.service_id != null) payload.service_id = choice.service_id;
        const result = await api.post(`/accounts/${id}/upload-sub2api`, payload);
        if (result.success) {
            toast.success('Upload successful');
            loadAccounts();
        } else {
            toast.error('Upload failed: ' + (result.error || result.message || 'Unknown error'));
        }
    } catch (e) {
        toast.error('Upload failed: ' + e.message);
    }
}

// Pop up the Team Manager service selection box and return Promise<{service_id: number|null}|null>
// null means user cancellation, {service_id: null} means automatic selection
function selectTmService() {
    return new Promise(async (resolve) => {
        const modal = document.getElementById('tm-service-modal');
        const listEl = document.getElementById('tm-service-list');
        const closeBtn = document.getElementById('close-tm-modal');
        const cancelBtn = document.getElementById('cancel-tm-modal-btn');
        const autoBtn = document.getElementById('tm-use-auto-btn');

        listEl.innerHTML = '<div style="text-align:center;color:var(--text-muted)">Loading...</div>';
        modal.classList.add('active');

        let services = [];
        try {
            services = await api.get('/tm-services?enabled=true');
        } catch (e) {
            services = [];
        }

        if (services.length === 0) {
            listEl.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:12px;">There is no enabled Team Manager service, the first one will be automatically selected</div>';
        } else {
            listEl.innerHTML = services.map(s => `
                <div class="tm-service-item" data-id="${s.id}" style="
                    padding: 10px 14px;
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    cursor: pointer;
                    transition: background 0.15s;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div>
                        <div style="font-weight:500;">${escapeHtml(s.name)}</div>
                        <div style="font-size:0.8rem;color:var(--text-muted);">${escapeHtml(s.api_url)}</div>
                    </div>
                    <span class="badge" style="background:var(--primary);color:#fff;font-size:0.7rem;padding:2px 8px;border-radius:10px;">Select</span>
                </div>
            `).join('');

            listEl.querySelectorAll('.tm-service-item').forEach(item => {
                item.addEventListener('mouseenter', () => item.style.background = 'var(--surface-hover)');
                item.addEventListener('mouseleave', () => item.style.background = '');
                item.addEventListener('click', () => {
                    cleanup();
                    resolve({ service_id: parseInt(item.dataset.id) });
                });
            });
        }

        function cleanup() {
            modal.classList.remove('active');
            closeBtn.removeEventListener('click', onCancel);
            cancelBtn.removeEventListener('click', onCancel);
            autoBtn.removeEventListener('click', onAuto);
        }
        function onCancel() { cleanup(); resolve(null); }
        function onAuto() { cleanup(); resolve({ service_id: null }); }

        closeBtn.addEventListener('click', onCancel);
        cancelBtn.addEventListener('click', onCancel);
        autoBtn.addEventListener('click', onAuto);
    });
}

// Upload a single account to Team Manager
async function uploadToTm(id) {
    const choice = await selectTmService();
    if (choice === null) return;
    try {
        toast.info('Uploading to Team Manager...');
        const payload = {};
        if (choice.service_id != null) payload.service_id = choice.service_id;
        const result = await api.post(`/accounts/${id}/upload-tm`, payload);
        if (result.success) {
            toast.success('Upload successful');
        } else {
            toast.error('Upload failed: ' + (result.message || 'Unknown error'));
        }
    } catch (e) {
        toast.error('Upload failed: ' + e.message);
    }
}

//Batch upload to Team Manager
async function handleBatchUploadTm() {
    const count = getEffectiveCount();
    if (count === 0) return;

    const choice = await selectTmService();
    if (choice === null) return; // User cancels

    const confirmed = await confirm(`Are you sure you want to upload the selected ${count} accounts to Team Manager?`);
    if (!confirmed) return;

    elements.batchUploadBtn.disabled = true;
    elements.batchUploadBtn.textContent = 'Uploading...';

    try {
        const payload = buildBatchPayload();
        if (choice.service_id != null) payload.service_id = choice.service_id;
        const result = await api.post('/accounts/batch-upload-tm', payload);
        let message = `Success: ${result.success_count}`;
        if (result.failed_count > 0) message += `, failed: ${result.failed_count}`;
        if (result.skipped_count > 0) message += `, skip: ${result.skipped_count}`;
        toast.success(message);
        loadAccounts();
    } catch (e) {
        toast.error('Batch upload failed: ' + e.message);
    } finally {
        updateBatchButtons();
    }
}

//More menu switches
function toggleMoreMenu(btn) {
    const menu = btn.nextElementSibling;
    const isActive = menu.classList.contains('active');
    // Close all other more menus
    document.querySelectorAll('.dropdown-menu.active').forEach(m => m.classList.remove('active'));
    if (!isActive) menu.classList.add('active');
}

function closeMoreMenu(el) {
    const menu = el.closest('.dropdown-menu');
    if (menu) menu.classList.remove('active');
}

//Save account Cookies
async function saveCookies(id) {
    const textarea = document.getElementById(`cookies-input-${id}`);
    if (!textarea) return;
    const cookiesValue = textarea.value.trim();
    try {
        await api.patch(`/accounts/${id}`, { cookies: cookiesValue });
        toast.success('Cookies saved');
    } catch (e) {
        toast.error('Failed to save Cookies: ' + e.message);
    }
}

// Query the inbox verification code
async function checkInboxCode(id) {
    toast.info('Querying inbox...');
    try {
        const result = await api.post(`/accounts/${id}/inbox-code`);
        if (result.success) {
            showInboxCodeResult(result.code, result.email);
        } else {
            toast.error('Query failed: ' + (result.error || 'Verification code not received'));
        }
    } catch (error) {
        toast.error('Query failed: ' + error.message);
    }
}

function showInboxCodeResult(code, email) {
    elements.modalBody.innerHTML = `
        <div style="text-align:center; padding:24px 16px;">
            <div style="font-size:13px;color:var(--text-muted);margin-bottom:12px;">
                ${escapeHtml(email)} latest verification code
            </div>
            <div style="font-size:36px;font-weight:700;letter-spacing:8px;
                        color:var(--primary);font-family:monospace;margin-bottom:20px;">
                ${escapeHtml(code)}
            </div>
            <button class="btn btn-primary" onclick="copyToClipboard('${escapeHtml(code)}')">Copy verification code</button>
        </div>
    `;
    elements.detailModal.classList.add('active');
}
