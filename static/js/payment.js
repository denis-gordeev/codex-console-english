/**
 * Payment page JavaScript
 */

const COUNTRY_CURRENCY_MAP = {
    SG: 'SGD', US: 'USD', TR: 'TRY', JP: 'JPY',
    HK: 'HKD', GB: 'GBP', EU: 'EUR', AU: 'AUD',
    CA: 'CAD', IN: 'INR', BR: 'BRL', MX: 'MXN',
};

let selectedPlan = 'plus';
let generatedLink = '';

// initialization
document.addEventListener('DOMContentLoaded', () => {
    loadAccounts();
});

//Load the account list
async function loadAccounts() {
    try {
        const resp = await fetch('/api/accounts?page=1&page_size=100&status=active');
        const data = await resp.json();
        const sel = document.getElementById('account-select');
        sel.innerHTML = '<option value="">-- Please select an account --</option>';
        (data.accounts || []).forEach(acc => {
            const opt = document.createElement('option');
            opt.value = acc.id;
            opt.textContent = acc.email;
            sel.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load account:', e);
    }
}

// Country switch
function onCountryChange() {
    const country = document.getElementById('country-select').value;
    const currency = COUNTRY_CURRENCY_MAP[country] || 'USD';
    document.getElementById('currency-display').value = currency;
}

//Select a package
function selectPlan(plan) {
    selectedPlan = plan;
    document.getElementById('plan-plus').classList.toggle('selected', plan === 'plus');
    document.getElementById('plan-team').classList.toggle('selected', plan === 'team');
    document.getElementById('team-options').classList.toggle('show', plan === 'team');
    //Hide generated links
    document.getElementById('link-box').classList.remove('show');
    generatedLink = '';
}

// Generate payment link
async function generateLink() {
    const accountId = document.getElementById('account-select').value;
    if (!accountId) {
        ui.showToast('Please select an account first', 'warning');
        return;
    }

    const country = document.getElementById('country-select').value || 'SG';

    const body = {
        account_id: parseInt(accountId),
        plan_type: selectedPlan,
        country: country,
    };

    if (selectedPlan === 'team') {
        body.workspace_name = document.getElementById('workspace-name').value || 'MyTeam';
        body.seat_quantity = parseInt(document.getElementById('seat-quantity').value) || 5;
        body.price_interval = document.getElementById('price-interval').value;
    }

    const btn = document.querySelector('.form-actions .btn-primary');
    if (btn) { btn.disabled = true; btn.textContent = 'Generating...'; }

    try {
        const resp = await fetch('/api/payment/generate-link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (data.success && data.link) {
            generatedLink = data.link;
            document.getElementById('link-text').value = data.link;
            document.getElementById('link-box').classList.add('show');
            document.getElementById('open-status').textContent = '';
            ui.showToast('Payment link generated successfully', 'success');
        } else {
            ui.showToast(data.detail || 'Failed to generate link', 'error');
        }
    } catch (e) {
        ui.showToast('Request failed: ' + e.message, 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Generate payment link'; }
    }
}

// copy link
function copyLink() {
    if (!generatedLink) return;
    navigator.clipboard.writeText(generatedLink).then(() => {
        ui.showToast('Copied to clipboard', 'success');
    }).catch(() => {
        const ta = document.getElementById('link-text');
        ta.select();
        document.execCommand('copy');
        ui.showToast('Copied to clipboard', 'success');
    });
}

// Open the browser without trace (carry account cookie)
async function openIncognito() {
    if (!generatedLink) {
        ui.showToast('Please generate a link first', 'warning');
        return;
    }
    const accountId = document.getElementById('account-select').value;
    const statusEl = document.getElementById('open-status');
    statusEl.textContent = 'Opening...';
    try {
        const body = { url: generatedLink };
        if (accountId) body.account_id = parseInt(accountId);

        const resp = await fetch('/api/payment/open-incognito', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (data.success) {
            statusEl.textContent = 'Browser opened in incognito mode';
            ui.showToast('Incognito browser is opened', 'success');
        } else {
            statusEl.textContent = data.message || 'No available browser found, please copy the link manually';
            ui.showToast(data.message || 'Browser not found', 'warning');
        }
    } catch (e) {
        statusEl.textContent = 'Request failed: ' + e.message;
        ui.showToast('Request failed', 'error');
    }
}
