/* ==========================================================================
   GeM AI Bid Compliance Verification Platform - Main App Logic & Auth
   ========================================================================== */

let tendersState = [];
let submissionsState = [];
let currentUser = null;

document.addEventListener('DOMContentLoaded', () => {
    checkSession();
});

// ---------------------------------------------------------
// AUTHENTICATION & SESSION MANAGEMENT
// ---------------------------------------------------------
async function checkSession() {
    try {
        const res = await fetch('/api/me');
        const data = await res.json();
        if (data.status === 'success' && data.authenticated) {
            currentUser = data.user;
            showAuthenticatedUI();
        } else {
            showLoginView();
        }
    } catch (err) {
        showLoginView();
    }
}

function showLoginView() {
    document.getElementById('loginView').style.display = 'flex';
    document.getElementById('appContainer').style.display = 'none';
}

function showAuthenticatedUI() {
    document.getElementById('loginView').style.display = 'none';
    document.getElementById('appContainer').style.display = 'block';

    // Update Profile Badge in Navbar
    if (currentUser) {
        document.getElementById('userNameBadge').textContent = currentUser.name;
        document.getElementById('userRoleBadge').textContent = currentUser.role;
        const icon = document.getElementById('userRoleIcon');
        if (currentUser.role === 'ADMIN') {
            icon.className = 'fa-solid fa-user-shield text-cyan';
        } else {
            icon.className = 'fa-solid fa-building-user text-emerald';
        }
    }

    applyRolePermissions();
    initAppData();
}

function applyRolePermissions() {
    if (!currentUser) return;

    const isAdmin = currentUser.role === 'ADMIN';
    const adminElements = document.querySelectorAll('.nav-admin-only');

    adminElements.forEach(el => {
        el.style.display = isAdmin ? 'inline-flex' : 'none';
    });

    // Default tab based on role
    if (isAdmin) {
        switchTab('dashboard');
    } else {
        switchTab('precheck');
    }
}

function switchLoginRole(role) {
    document.getElementById('loginRole').value = role;
    const adminBtn = document.getElementById('roleAdminBtn');
    const vendorBtn = document.getElementById('roleVendorBtn');
    const uInput = document.getElementById('loginUsername');
    const pInput = document.getElementById('loginPassword');

    if (role === 'ADMIN') {
        adminBtn.classList.add('active');
        vendorBtn.classList.remove('active');
        uInput.value = 'admin';
        pInput.value = 'admin123';
    } else {
        vendorBtn.classList.add('active');
        adminBtn.classList.remove('active');
        uInput.value = 'vendor';
        pInput.value = 'vendor123';
    }
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (data.status === 'success') {
            currentUser = data.user;
            showAlert('success', data.message);
            showAuthenticatedUI();
        } else {
            alert(data.message || 'Login failed. Please check credentials.');
        }
    } catch (err) {
        alert('Server error logging in.');
    }
}

function quickLogin(username, password) {
    document.getElementById('loginUsername').value = username;
    document.getElementById('loginPassword').value = password;
    handleLoginSubmit(new Event('submit'));
}

async function handleLogout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        currentUser = null;
        showLoginView();
    } catch (err) {
        showLoginView();
    }
}

function initAppData() {
    if (currentUser.role === 'ADMIN') {
        loadAnalytics();
        loadDashboardSubmissions();
        loadAuditHistory();
    }
    loadTenders();
}

// ---------------------------------------------------------
// TAB NAVIGATION
// ---------------------------------------------------------
function switchTab(tabName) {
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));

    const targetPane = document.getElementById(`tab-${tabName}`);
    if (targetPane) targetPane.classList.add('active');

    const btn = Array.from(document.querySelectorAll('.nav-btn')).find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(tabName));
    if (btn) btn.classList.add('active');

    // Refresh tab specific data
    if (tabName === 'dashboard' && currentUser && currentUser.role === 'ADMIN') {
        loadAnalytics();
        loadDashboardSubmissions();
    } else if (tabName === 'tenders') {
        loadTenders();
    } else if (tabName === 'audit' && currentUser && currentUser.role === 'ADMIN') {
        loadAuditHistory();
    }
}

// ---------------------------------------------------------
// ANALYTICS & DASHBOARD
// ---------------------------------------------------------
async function loadAnalytics() {
    try {
        const res = await fetch('/api/analytics');
        const data = await res.json();
        if (data.status === 'success') {
            const stats = data.analytics;
            document.getElementById('statTotalTenders').textContent = stats.total_tenders;
            document.getElementById('statTotalBids').textContent = stats.total_bids;
            document.getElementById('statPassRate').textContent = `${stats.pass_rate}%`;
            document.getElementById('statTimeSaved').textContent = `${stats.time_saved_hours} hrs`;
            document.getElementById('statQualifiedRatio').textContent = `${stats.qualified_bids} Qualified / ${stats.disqualified_bids} Disqualified`;
        }
    } catch (err) {
        console.error('Error loading analytics:', err);
    }
}

async function loadDashboardSubmissions() {
    const tbody = document.getElementById('recentSubmissionsBody');
    if (!tbody) return;

    try {
        const res = await fetch('/api/submissions');
        const data = await res.json();
        if (data.status === 'success') {
            submissionsState = data.submissions;
            if (submissionsState.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" class="text-center p-4 text-muted">No evaluated bids found. Upload a bid to get started.</td></tr>`;
                return;
            }

            tbody.innerHTML = submissionsState.slice(0, 5).map(s => `
                <tr>
                    <td><strong class="font-mono text-cyan">#BID-${s.id}</strong></td>
                    <td><strong>${escapeHtml(s.vendor_name)}</strong></td>
                    <td><span class="tender-ref">${escapeHtml(s.tender_ref)}</span></td>
                    <td>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <strong>${s.compliance_score}%</strong>
                        </div>
                    </td>
                    <td><span class="badge badge-${s.status}">${s.status}</span></td>
                    <td><span class="badge badge-${s.risk_level === 'HIGH' ? 'danger' : s.risk_level === 'MEDIUM' ? 'amber' : 'success'}">${s.risk_level} RISK</span></td>
                    <td class="text-xs text-muted">${s.verified_at}</td>
                    <td>
                        <button class="btn btn-sm btn-outline" onclick="openSubmissionDetail(${s.id})"><i class="fa-solid fa-eye"></i> Matrix</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center p-4 text-red">Failed to load submissions.</td></tr>`;
    }
}

// ---------------------------------------------------------
// TENDERS MANAGEMENT
// ---------------------------------------------------------
async function loadTenders() {
    try {
        const res = await fetch('/api/tenders');
        const data = await res.json();
        if (data.status === 'success') {
            tendersState = data.tenders;
            populateTenderDropdowns(tendersState);
            renderTendersGrid(tendersState);
        }
    } catch (err) {
        console.error('Error loading tenders:', err);
    }
}

function populateTenderDropdowns(tenders) {
    const selects = ['verifyTenderSelect', 'precheckTenderSelect'];
    selects.forEach(id => {
        const sel = document.getElementById(id);
        if (!sel) return;
        const currentVal = sel.value;
        sel.innerHTML = `<option value="">-- Select GeM Tender --</option>` +
            tenders.map(t => `<option value="${t.id}">${t.tender_ref} - ${escapeHtml(t.title)}</option>`).join('');
        if (currentVal) sel.value = currentVal;
    });

    if (tenders.length > 0) {
        const verifySel = document.getElementById('verifyTenderSelect');
        if (verifySel && !verifySel.value) {
            verifySel.value = tenders[0].id;
            updateSelectedTenderInfo();
        }
        const precheckSel = document.getElementById('precheckTenderSelect');
        if (precheckSel && !precheckSel.value) {
            precheckSel.value = tenders[0].id;
        }
    }
}

function renderTendersGrid(tenders) {
    const grid = document.getElementById('tendersListGrid');
    if (!grid) return;

    if (tenders.length === 0) {
        grid.innerHTML = `<div class="col-span-3 text-center p-6 text-muted">No GeM Tenders created yet.</div>`;
        return;
    }

    const isAdmin = currentUser && currentUser.role === 'ADMIN';

    grid.innerHTML = tenders.map(t => `
        <div class="card glass-card tender-card">
            <div class="card-body">
                <div class="tender-header">
                    <span class="tender-ref">${t.tender_ref}</span>
                    <span class="badge badge-info"><i class="fa-solid fa-building"></i> ${escapeHtml(t.department.split('/')[0])}</span>
                </div>
                <h3 class="mb-2" style="font-size: 1.05rem;">${escapeHtml(t.title)}</h3>
                <p class="text-xs text-muted mb-3"><i class="fa-solid fa-landmark"></i> ${escapeHtml(t.department)}</p>
                
                <div class="tender-specs">
                    <div><strong>Min Turnover:</strong> ₹${t.min_turnover_lakhs} Lakhs</div>
                    <div><strong>Min Exp:</strong> ${t.min_experience_years} Years</div>
                    <div><strong>MII Content:</strong> >= ${t.min_mii_percent}%</div>
                    <div><strong>EMD Amount:</strong> ₹${t.emd_amount.toLocaleString()}</div>
                </div>

                <div class="mt-3">
                    <span class="text-xs font-semibold text-secondary">Required Certs:</span>
                    <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px;">
                        ${(t.required_certs || []).map(c => `<span class="badge badge-amber text-xs">${c}</span>`).join('')}
                    </div>
                </div>
            </div>
            <div class="card-header" style="border-top: 1px solid var(--border-color); border-bottom: none; padding: 0.8rem 1.25rem;">
                <span class="text-xs text-muted">Closes: ${t.closing_date}</span>
                ${isAdmin ? `<button class="btn btn-sm btn-primary" onclick="selectTenderForScan(${t.id})"><i class="fa-solid fa-robot"></i> Scan Bid</button>` : `<button class="btn btn-sm btn-success" onclick="selectTenderForPrecheck(${t.id})"><i class="fa-solid fa-user-check"></i> Pre-Check</button>`}
            </div>
        </div>
    `).join('');
}

function updateSelectedTenderInfo() {
    const sel = document.getElementById('verifyTenderSelect');
    const box = document.getElementById('tenderCriteriaSummary');
    if (!sel || !box) return;

    const tId = parseInt(sel.value);
    const t = tendersState.find(x => x.id === tId);

    if (!t) {
        box.innerHTML = `<span class="text-xs text-muted">Select a tender to view required criteria.</span>`;
        return;
    }

    box.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 3px;">
            <strong class="text-cyan">${t.tender_ref}</strong>
            <span><strong>Turnover:</strong> >= ₹${t.min_turnover_lakhs} Lakhs/yr</span>
            <span><strong>Experience:</strong> >= ${t.min_experience_years} Years</span>
            <span><strong>MII Local Content:</strong> >= ${t.min_mii_percent}%</span>
            <span><strong>Certs:</strong> ${(t.required_certs || []).join(', ')}</span>
        </div>
    `;
}

function selectTenderForScan(tenderId) {
    switchTab('verifier');
    const sel = document.getElementById('verifyTenderSelect');
    if (sel) {
        sel.value = tenderId;
        updateSelectedTenderInfo();
    }
}

function selectTenderForPrecheck(tenderId) {
    switchTab('precheck');
    const sel = document.getElementById('precheckTenderSelect');
    if (sel) {
        sel.value = tenderId;
    }
}

// ---------------------------------------------------------
// MODAL CONTROLLERS
// ---------------------------------------------------------
function openNewTenderModal() {
    document.getElementById('createTenderModal').style.display = 'flex';
}

function closeNewTenderModal() {
    document.getElementById('createTenderModal').style.display = 'none';
}

async function handleCreateTender(e) {
    e.preventDefault();
    const payload = {
        tender_ref: document.getElementById('newTenderRef').value.trim(),
        title: document.getElementById('newTenderTitle').value.trim(),
        department: document.getElementById('newTenderDept').value.trim(),
        min_turnover_lakhs: parseFloat(document.getElementById('newMinTurnover').value),
        min_experience_years: parseInt(document.getElementById('newMinExp').value),
        min_mii_percent: parseFloat(document.getElementById('newMinMii').value),
        emd_amount: parseFloat(document.getElementById('newEmdAmt').value),
        required_certs: document.getElementById('newRequiredCerts').value.split(',').map(s => s.trim()).filter(Boolean)
    };

    try {
        const res = await fetch('/api/tenders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.status === 'success') {
            showAlert('success', 'GeM Tender created successfully!');
            closeNewTenderModal();
            loadTenders();
            if (currentUser && currentUser.role === 'ADMIN') loadAnalytics();
        } else {
            showAlert('danger', data.message || 'Failed to create tender');
        }
    } catch (err) {
        showAlert('danger', 'Server error creating tender');
    }
}

async function openSubmissionDetail(subId) {
    const modal = document.getElementById('detailModal');
    const container = document.getElementById('modalSubContent');
    document.getElementById('modalSubId').textContent = subId;
    modal.style.display = 'flex';
    container.innerHTML = `<div class="p-6 text-center text-muted">Loading compliance breakdown...</div>`;

    try {
        const res = await fetch(`/api/submissions/${subId}`);
        const data = await res.json();
        if (data.status === 'success') {
            const sub = data.submission;
            const matrix = data.compliance_matrix;

            container.innerHTML = `
                <div class="result-summary-bar mb-4">
                    <div class="summary-score-box">
                        <div class="score-circle"><span>${sub.compliance_score}%</span></div>
                    </div>
                    <div class="summary-details">
                        <div class="summary-badge-group">
                            <span class="badge badge-${sub.status}">${sub.status}</span>
                            <span class="badge badge-${sub.risk_level === 'HIGH' ? 'danger' : 'success'}">${sub.risk_level} RISK</span>
                        </div>
                        <h4>${escapeHtml(sub.vendor_name)} (GSTIN: ${escapeHtml(sub.vendor_gstin)})</h4>
                        <p class="text-xs text-muted">Tender Ref: ${sub.tender_ref} - ${escapeHtml(sub.tender_title)}</p>
                    </div>
                </div>

                <h4 class="mb-2">Compliance Matrix</h4>
                <div class="table-responsive">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Clause</th>
                                <th>Required</th>
                                <th>Extracted</th>
                                <th>Status</th>
                                <th>Evidence Snippet</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${matrix.map(c => `
                                <tr>
                                    <td><strong>${c.clause_name}</strong></td>
                                    <td class="text-xs">${c.required_value}</td>
                                    <td class="text-xs text-cyan"><strong>${c.extracted_value}</strong></td>
                                    <td><span class="badge badge-${c.status}">${c.status}</span></td>
                                    <td class="text-xs font-mono text-muted" style="max-width: 250px;">${escapeHtml(c.evidence_snippet || '')}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
    } catch (err) {
        container.innerHTML = `<div class="p-4 text-red">Failed to load details.</div>`;
    }
}

function closeDetailModal() {
    document.getElementById('detailModal').style.display = 'none';
}

// ---------------------------------------------------------
// AUDIT HISTORY LOG
// ---------------------------------------------------------
async function loadAuditHistory() {
    const tbody = document.getElementById('auditHistoryTableBody');
    if (!tbody) return;

    try {
        const res = await fetch('/api/submissions');
        const data = await res.json();
        if (data.status === 'success') {
            const list = data.submissions;
            if (list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" class="text-center p-4 text-muted">No history found.</td></tr>`;
                return;
            }
            tbody.innerHTML = list.map(s => `
                <tr>
                    <td><strong class="font-mono text-cyan">#${s.id}</strong></td>
                    <td><strong>${escapeHtml(s.vendor_name)}</strong></td>
                    <td class="font-mono text-xs">${escapeHtml(s.vendor_gstin)}</td>
                    <td><span class="tender-ref">${s.tender_ref}</span></td>
                    <td><strong>${s.compliance_score}%</strong></td>
                    <td><span class="badge badge-${s.status}">${s.status}</span></td>
                    <td><span class="badge badge-${s.risk_level === 'HIGH' ? 'danger' : 'success'}">${s.risk_level} RISK</span></td>
                    <td class="text-xs text-muted">${s.verified_at}</td>
                    <td>
                        <button class="btn btn-sm btn-outline" onclick="openSubmissionDetail(${s.id})"><i class="fa-solid fa-file-lines"></i> Report</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="9" class="text-center p-4 text-red">Error loading audit history.</td></tr>`;
    }
}

// ---------------------------------------------------------
// UTILS & NOTIFICATIONS
// ---------------------------------------------------------
function showAlert(type, message) {
    const container = document.getElementById('alertContainer');
    if (!container) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type === 'success' ? 'info' : 'danger'}`;
    alert.style.cssText = `
        background: ${type === 'success' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'};
        border: 1px solid ${type === 'success' ? 'var(--accent-emerald)' : 'var(--accent-red)'};
        color: #fff;
        padding: 0.75rem 1rem;
        border-radius: var(--radius-sm);
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    `;
    alert.innerHTML = `<span>${message}</span> <button class="btn-icon" onclick="this.parentElement.remove()"><i class="fa-solid fa-xmark"></i></button>`;

    container.appendChild(alert);
    setTimeout(() => { if (alert.parentNode) alert.remove(); }, 5000);
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#039;");
}
