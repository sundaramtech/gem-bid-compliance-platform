/* ==========================================================================
   GeM AI Bid Compliance Verification Platform - Verifier & Matrix Engine
   ========================================================================== */

let selectedBidFile = null;

// ---------------------------------------------------------
// FILE SELECTION & DROPZONE HANDLERS
// ---------------------------------------------------------
function handleFileSelect(input) {
    if (input.files && input.files[0]) {
        selectedBidFile = input.files[0];
        showSelectedFileBadge(selectedBidFile.name);
    }
}

function showSelectedFileBadge(fileName) {
    document.getElementById('selectedFileName').textContent = fileName;
    document.getElementById('fileSelectedBadge').style.display = 'flex';
}

function clearSelectedFile() {
    selectedBidFile = null;
    document.getElementById('bidFileInput').value = '';
    document.getElementById('fileSelectedBadge').style.display = 'none';
}

// Drag and drop event listeners
document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('bidDropzone');
    if (!dropzone) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.remove('dragover'), false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            selectedBidFile = files[0];
            showSelectedFileBadge(selectedBidFile.name);
        }
    });
});

// ---------------------------------------------------------
// RUN BID VERIFICATION (OFFICER PORTAL)
// ---------------------------------------------------------
async function handleBidVerification(e) {
    e.preventDefault();

    const tenderId = document.getElementById('verifyTenderSelect').value;
    const vendorName = document.getElementById('vendorNameInput').value.trim();
    const vendorGstin = document.getElementById('vendorGstinInput').value.trim();

    if (!tenderId) {
        showAlert('danger', 'Please select a target GeM tender.');
        return;
    }

    if (!selectedBidFile) {
        showAlert('danger', 'Please upload a technical bid PDF or TXT file.');
        return;
    }

    // Show Scanning Loader Animation
    showScanningState();

    const formData = new FormData();
    formData.append('tender_id', tenderId);
    formData.append('vendor_name', vendorName || 'Vendor Bidder');
    formData.append('vendor_gstin', vendorGstin || '07AAAAA0000A1Z5');
    formData.append('bid_file', selectedBidFile);

    try {
        const response = await fetch('/api/verify-bid', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'success') {
            setTimeout(() => {
                renderVerificationResults(data.result);
                loadAnalytics();
                loadDashboardSubmissions();
                loadAuditHistory();
            }, 1200); // Smooth transition after scanner animation
        } else {
            hideScanningState();
            showAlert('danger', data.message || 'Verification failed');
        }
    } catch (err) {
        hideScanningState();
        showAlert('danger', 'Network error executing AI verification engine.');
    }
}

// ---------------------------------------------------------
// QUICK HACKATHON DEMO PRESETS
// ---------------------------------------------------------
async function loadDemoPreset(presetKey) {
    switchTab('verifier');
    showScanningState();

    try {
        const res = await fetch(`/api/sample-bids/load/${presetKey}`, {
            method: 'POST'
        });
        const data = await res.json();
        if (data.status === 'success') {
            setTimeout(() => {
                renderVerificationResults(data.result);
                loadAnalytics();
                loadDashboardSubmissions();
                loadAuditHistory();
            }, 1200);
        } else {
            hideScanningState();
            showAlert('danger', data.message || 'Failed to load demo preset.');
        }
    } catch (err) {
        hideScanningState();
        showAlert('danger', 'Server error loading demo bid.');
    }
}

// ---------------------------------------------------------
// UI RENDERERS FOR SCANNING & MATRIX
// ---------------------------------------------------------
function showScanningState() {
    document.getElementById('verifierPlaceholder').style.display = 'none';
    document.getElementById('verifierResults').style.display = 'none';
    document.getElementById('verifierLoader').style.display = 'block';

    const stepText = document.getElementById('scannerStepText');
    const progressBar = document.getElementById('scannerProgressBar');

    let step = 0;
    const stages = [
        { text: "Parsing document text & page metadata...", progress: "25%" },
        { text: "Extracting Financial Turnover & CA Audit snippets...", progress: "50%" },
        { text: "Evaluating Make in India (MII) local value addition %...", progress: "75%" },
        { text: "Cross-checking ISO 9001/27001 & EMD exemption validity...", progress: "95%" }
    ];

    const interval = setInterval(() => {
        step++;
        if (step < stages.length) {
            stepText.textContent = stages[step].text;
            progressBar.style.width = stages[step].progress;
        } else {
            clearInterval(interval);
        }
    }, 300);
}

function hideScanningState() {
    document.getElementById('verifierLoader').style.display = 'none';
}

function renderVerificationResults(res) {
    hideScanningState();
    document.getElementById('verifierResults').style.display = 'block';
    document.getElementById('resultActions').style.display = 'block';

    // Set Header Summary Values
    const scoreVal = document.getElementById('resultScoreVal');
    const scoreCircle = document.getElementById('resultScoreCircle');
    const statusBadge = document.getElementById('resultStatusBadge');
    const riskBadge = document.getElementById('resultRiskBadge');

    scoreVal.textContent = `${res.compliance_score}%`;
    
    // Circle Border & Badge Colors based on status
    if (res.status === 'QUALIFIED') {
        scoreCircle.style.borderColor = 'var(--accent-emerald)';
        scoreCircle.style.boxShadow = '0 0 15px var(--accent-emerald-glow)';
        statusBadge.className = 'badge badge-QUALIFIED';
        statusBadge.innerHTML = '<i class="fa-solid fa-circle-check"></i> QUALIFIED';
    } else if (res.status === 'DISQUALIFIED') {
        scoreCircle.style.borderColor = 'var(--accent-red)';
        scoreCircle.style.boxShadow = '0 0 15px var(--accent-red-glow)';
        statusBadge.className = 'badge badge-DISQUALIFIED';
        statusBadge.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> DISQUALIFIED';
    } else {
        scoreCircle.style.borderColor = 'var(--accent-amber)';
        scoreCircle.style.boxShadow = '0 0 15px var(--accent-amber-glow)';
        statusBadge.className = 'badge badge-CONDITIONALLY_QUALIFIED';
        statusBadge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> CONDITIONAL';
    }

    riskBadge.className = `badge badge-${res.risk_level === 'HIGH' ? 'danger' : res.risk_level === 'MEDIUM' ? 'amber' : 'success'}`;
    riskBadge.textContent = `${res.risk_level} RISK`;

    document.getElementById('resultVendorName').textContent = res.vendor_name || 'Vendor Bidder';
    document.getElementById('resultTenderRef').textContent = `Tender Reference: ${res.tender_ref}`;
    document.getElementById('resultSummaryNotes').textContent = res.summary_notes || '';

    // Render Matrix Rows
    const matrixBody = document.getElementById('complianceMatrixBody');
    matrixBody.innerHTML = res.clauses.map(c => `
        <tr>
            <td>
                <strong>${escapeHtml(c.clause_name)}</strong>
                <div class="text-xs text-muted">Confidence: ${(c.confidence * 100).toFixed(0)}%</div>
            </td>
            <td><span class="text-xs">${escapeHtml(c.required_value)}</span></td>
            <td><strong class="text-cyan text-xs">${escapeHtml(c.extracted_value)}</strong></td>
            <td><span class="badge badge-${c.status}">${c.status}</span></td>
            <td>
                <div class="text-xs font-mono text-muted" style="max-width: 280px; word-break: break-word;">
                    "${escapeHtml(c.evidence_snippet || 'No snippet extracted')}"
                </div>
                ${c.remarks ? `<div class="text-xs text-amber mt-1"><i class="fa-solid fa-info-circle"></i> ${escapeHtml(c.remarks)}</div>` : ''}
            </td>
        </tr>
    `).join('');
}

// ---------------------------------------------------------
// VENDOR PRE-CHECK PORTAL HANDLER
// ---------------------------------------------------------
async function handleVendorPrecheck(e) {
    e.preventDefault();

    const tenderId = document.getElementById('precheckTenderSelect').value;
    const fileInput = document.getElementById('precheckFileInput');
    const rawText = document.getElementById('precheckRawText').value.trim();

    if (!tenderId) {
        showAlert('danger', 'Select a target tender to pre-check your bid against.');
        return;
    }

    if (!rawText && (!fileInput.files || fileInput.files.length === 0)) {
        showAlert('danger', 'Please upload a draft document file OR paste technical bid text.');
        return;
    }

    const formData = new FormData();
    formData.append('tender_id', tenderId);
    if (fileInput.files && fileInput.files[0]) {
        formData.append('bid_file', fileInput.files[0]);
    }
    if (rawText) {
        formData.append('raw_text', rawText);
    }

    try {
        const res = await fetch('/api/vendor-precheck', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.status === 'success') {
            renderVendorPrecheckResults(data.result);
        } else {
            showAlert('danger', data.message || 'Pre-check failed.');
        }
    } catch (err) {
        showAlert('danger', 'Server error running vendor pre-check.');
    }
}

function renderVendorPrecheckResults(res) {
    document.getElementById('precheckPlaceholder').style.display = 'none';
    document.getElementById('precheckResults').style.display = 'block';

    const msg = document.getElementById('precheckStatusMsg');
    const heading = document.getElementById('precheckStatusHeading');
    const recList = document.getElementById('precheckRecommendations');

    heading.textContent = `Technical Health Score: ${res.compliance_score}% (${res.status})`;
    msg.textContent = res.summary_notes;

    // Generate actionable advice
    const recs = [];
    res.clauses.forEach(c => {
        if (c.status === 'NON_COMPLIANT') {
            recs.push({
                type: 'danger',
                text: `CRITICAL DISQUALIFICATION RISK in '${c.clause_name}': Required ${c.required_value}, but extracted ${c.extracted_value}. Action: ${c.remarks}`
            });
        } else if (c.status === 'WARNING' || c.status === 'MANUAL_CHECK') {
            recs.push({
                type: 'warning',
                text: `WARNING in '${c.clause_name}': Extracted ${c.extracted_value}. Action: Ensure formal certificate/affidavit is clearly legible.`
            });
        }
    });

    if (recs.length === 0) {
        recs.push({
            type: 'success',
            text: 'Your bid meets all technical compliance criteria! Ready for official submission on GeM.'
        });
    }

    recList.innerHTML = recs.map(r => `
        <div style="background: ${r.type === 'danger' ? 'rgba(239, 68, 68, 0.1)' : r.type === 'warning' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(16, 185, 129, 0.1)'}; border: 1px solid ${r.type === 'danger' ? 'var(--accent-red)' : r.type === 'warning' ? 'var(--accent-amber)' : 'var(--accent-emerald)'}; padding: 0.8rem; border-radius: var(--radius-sm); margin-bottom: 0.6rem; font-size: 0.85rem;">
            <i class="fa-solid ${r.type === 'danger' ? 'fa-circle-xmark text-red' : r.type === 'warning' ? 'fa-triangle-exclamation text-amber' : 'fa-circle-check text-emerald'}"></i> ${escapeHtml(r.text)}
        </div>
    `).join('');
}
