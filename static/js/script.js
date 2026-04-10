/* ============================================================
   IntelliCredit Hub — script.js
   Vanilla JS: stage wizard, validation, simulations
   ============================================================ */

// ── Active sidebar link ───────────────────────────────────────
(function () {
  const links = document.querySelectorAll('.sidebar-link');
  links.forEach(link => {
    if (link.getAttribute('href') === window.location.pathname) {
      link.classList.add('active');
    }
  });
})();

// ── Utility ───────────────────────────────────────────────────
function formatCurrency(amount) {
  if (amount >= 10000000) return '₹' + (amount / 10000000).toFixed(1) + ' Cr';
  if (amount >= 100000)   return '₹' + (amount / 100000).toFixed(1) + ' L';
  return '₹' + amount.toLocaleString('en-IN');
}

function svgIcon(name) {
  const icons = {
    check: `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`,
    x:     `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`,
    ok:    `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`,
    alert: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`,
    warn:  `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`,
    file:  `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>`,
    shield:`<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>`,
    brain: `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.46 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.46 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/></svg>`,
    bar:   `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line><line x1="2" y1="20" x2="22" y2="20"></line></svg>`,
  };
  return icons[name] || '';
}

// ══════════════════════════════════════════════════════════════
// NEW CASE WIZARD
// ══════════════════════════════════════════════════════════════
if (document.getElementById('wizard')) {
  let currentStage = 1;
  let stage1Done = false;
  let stage2Done = false;
  let stage3Done = false;
  window.currentCaseId = new URLSearchParams(window.location.search).get('case_id');

  const STAGES = [
    { num: 1, label: 'Entity Onboarding' },
    { num: 2, label: 'Document Intelligence' },
    { num: 3, label: 'Financial Extraction' },
    { num: 4, label: 'AI Risk Analysis' },
  ];

  function renderStepper() {
    const el = document.getElementById('stepper');
    let html = '';
    STAGES.forEach((s, i) => {
      const isDone   = s.num < currentStage;
      const isActive = s.num === currentStage;
      const cls = isDone ? 'done' : isActive ? 'active' : 'pending';
      const numHTML = isDone
        ? `<span class="step-num">${svgIcon('check')}</span>`
        : `<span class="step-num">${s.num}</span>`;
      html += `<button class="step-btn ${cls}" onclick="${isDone ? `goStage(${s.num})` : ''}">${numHTML}${s.label}</button>`;
      if (i < STAGES.length - 1) {
        html += `<div class="step-connector ${isDone ? 'done' : 'pending'}"></div>`;
      }
    });
    el.innerHTML = html;
    document.getElementById('stage-num').textContent = currentStage;
  }

  window.goStage = function(n) {
    if (n <= currentStage) { currentStage = n; renderStepper(); showStage(n); }
  };

  function showStage(n) {
    document.querySelectorAll('.stage-panel').forEach(p => p.style.display = 'none');
    const panel = document.getElementById('stage-' + n);
    if (panel) panel.style.display = 'block';
  }

  function nextStage() {
    if (currentStage < 4) {
      currentStage++;
      renderStepper();
      showStage(currentStage);
      if (currentStage === 2) initStage2();
      if (currentStage === 3) initStage3();
      if (currentStage === 4) initStage4();
    }
  }

  // ── Stage 1: Entity Onboarding ──────────────────────────────
  let validationsPassed = false;
  let mcaVerified = false;

  window.runValidation = function() {
    const cn  = document.getElementById('f-company').value.trim();
    const cin = document.getElementById('f-cin').value.trim().toUpperCase();
    const pan = document.getElementById('f-pan').value.trim().toUpperCase();
    const loan = parseFloat(document.getElementById('f-loan').value) || 0;
    const tv   = parseFloat(document.getElementById('f-turnover').value) || 0;

    if (!cn || !cin || !pan) { alert('Please fill in Company Name, CIN, and PAN.'); return; }

    const btn = document.getElementById('btn-validate');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Validating...';

    setTimeout(() => {
      // CIN: [L/U] + [5-char alphanumeric NIC] + [2-letter state] + [4-digit year] + [3-letter type] + [6-digit serial]
      // NIC code can be alphanumeric (e.g. 2B920), so we use [A-Z0-9]{5}
      const cinRegex = /^[LU][A-Z0-9]{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$/;
      const panRegex = /^[A-Z]{5}\d{4}[A-Z]$/;

      // Year is always at positions 8-11 (0-indexed) in a valid CIN
      // CIN structure: [0]=L/U [1-5]=NIC(5chars) [6-7]=State [8-11]=Year [12-14]=CompType [15-20]=Serial
      const cinOk   = cinRegex.test(cin);
      const cinYear = cinOk ? parseInt(cin.slice(8, 12)) : NaN;
      const maxYear = new Date().getFullYear();
      const yearOk  = !isNaN(cinYear) && cinYear > 1900 && cinYear <= maxYear;

      // Loan-to-turnover: only meaningful when turnover > 0
      const ratioOk  = tv > 0 ? (loan / tv) <= 0.5 : false;
      const ratioMsg = tv <= 0
        ? 'Annual Turnover must be greater than ₹0'
        : `Ratio: ${((loan / tv) * 100).toFixed(1)}% ${ratioOk ? '(within 50% limit)' : '(exceeds 50% limit)'}`;

      // PAN 4th character denotes entity type:
      // C=Company, P=Person, H=HUF, F=Firm, A=AOP, T=Trust, B=Body, L=Local, J=AJP, G=Govt
      const validEntityTypes = ['C','P','H','F','A','T','B','L','J','G'];
      const panEntityChar = pan[3];
      const panEntityOk   = validEntityTypes.includes(panEntityChar);
      const entityLabels  = { C:'Company', P:'Individual', H:'HUF', F:'Firm', A:'AOP/BOI', T:'Trust', B:'Body of Individuals', L:'Local Authority', J:'Artificial Juridical Person', G:'Government' };
      const panEntityMsg  = panEntityOk
        ? `PAN entity type: "${panEntityChar}" — ${entityLabels[panEntityChar]}`
        : `PAN 4th char "${panEntityChar}" is not a valid entity code`;

      // Loan limit: ₹500 Cr = 5,000,000,000
      const loanLimit    = 5000000000;
      const loanLimitOk  = loan > 0 && loan <= loanLimit;
      const loanLimitMsg = loan <= 0
        ? 'Loan amount must be greater than ₹0'
        : loanLimitOk
          ? `Within ₹500 Cr limit (${formatCurrency(loan)})`
          : `Exceeds ₹500 Cr maximum (${formatCurrency(loan)})`;

      const checks = [
        { field: 'CIN Format',             pass: cinOk,        msg: cinOk   ? `Valid CIN format — ${cin}` : 'Invalid CIN (expected: L/U + 5 chars + 2-letter state + 4-digit year + 3-letter type + 6 digits)' },
        { field: 'PAN Format',             pass: panRegex.test(pan), msg: panRegex.test(pan) ? 'Valid PAN format' : 'Invalid PAN (expected: 5 letters + 4 digits + 1 letter)' },
        { field: 'PAN Entity Type',        pass: panEntityOk,  msg: panEntityMsg },
        { field: 'Incorporation Year',     pass: yearOk,       msg: yearOk  ? `Incorporated in ${cinYear} (${maxYear - cinYear} years ago)` : 'Could not extract a valid incorporation year from CIN' },
        { field: 'Loan-to-Turnover Ratio', pass: ratioOk,      msg: ratioMsg },
        { field: 'Loan Amount Limit',      pass: loanLimitOk,  msg: loanLimitMsg },
      ];

      const box = document.getElementById('validation-results');
      box.innerHTML = checks.map(c => `
        <div class="validation-item ${c.pass ? 'validation-pass' : 'validation-fail'}">
          <span style="color:${c.pass ? 'var(--success)' : 'var(--destructive)'}; flex-shrink:0; margin-top:1px">${c.pass ? svgIcon('ok') : svgIcon('alert')}</span>
          <div>
            <p class="validation-field">${c.field}</p>
            <p class="${c.pass ? 'validation-msg-pass' : 'validation-msg-fail'}">${c.msg}</p>
          </div>
        </div>`).join('');

      validationsPassed = checks.every(c => c.pass);
      updateMCABtn();
      btn.disabled = false;
      btn.innerHTML = 'Run Validation';
    }, 1500);
  };

  function updateMCABtn() {
    const mcaBtn = document.getElementById('btn-mca');
    if (mcaBtn) mcaBtn.disabled = !validationsPassed;
  }

  window.runMCA = async function() {
    const btn = document.getElementById('btn-mca');
    const resultDiv = document.getElementById('mca-result');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="border-top-color:var(--fg)"></span> Verifying...';
    resultDiv.innerHTML = '';

    const company = document.getElementById('f-company').value;
    const cin = document.getElementById('f-cin').value;
    const pan = document.getElementById('f-pan').value;

    try {
      const resp = await fetch('/api/verify-mca', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company, cin, pan })
      });
      const data = await resp.json();

      if (data.verified) {
        mcaVerified = true;
        resultDiv.innerHTML = `
          <div class="alert alert-success" style="margin-top:12px">
            <span>${svgIcon('ok')}</span>
            <div><p class="alert-title">MCA21 Verification Passed</p>
            <p class="alert-body">Verified against Ministry of Corporate Affairs records. Match found for ${data.company} (${data.sector}).</p></div>
          </div>`;
      } else {
        mcaVerified = false;
        resultDiv.innerHTML = `
          <div class="alert alert-danger" style="margin-top:12px; border-color:var(--red); background:rgba(239,68,68,0.1)">
            <span style="color:var(--red)">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            </span>
            <div><p class="alert-title" style="color:var(--red)">MCA Verification Error</p>
            <p class="alert-body" style="color:var(--red)">Error: Records not found in the MCA database.</p></div>
          </div>`;
      }
    } catch (err) {
      console.error(err);
      mcaVerified = false;
      resultDiv.innerHTML = `<div class="alert alert-danger" style="margin-top:12px"><p class="alert-title">API Connection Error</p></div>`;
    } finally {
      btn.innerHTML = 'MCA21 Verify';
      updateProceedBtn();
    }
  };

  function updateProceedBtn() {
    const pb = document.getElementById('btn-stage1-proceed');
    if (pb) pb.style.display = (validationsPassed && mcaVerified) ? 'flex' : 'none';
  }

  window.proceedStage1 = async function() {
    const payload = {
        company: document.getElementById('f-company').value.trim(),
        cin: document.getElementById('f-cin').value.trim().toUpperCase(),
        pan: document.getElementById('f-pan').value.trim().toUpperCase(),
        sector: document.getElementById('f-sector').value.trim(),
        loan_amount: parseFloat(document.getElementById('f-loan').value) || 0,
        annual_turnover: parseFloat(document.getElementById('f-turnover').value) || 0,
    };
    
    const btn = document.getElementById('btn-stage1-proceed');
    btn.disabled = true;
    try {
        if (!window.currentCaseId) {
            const resp = await fetch('/api/cases', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (data.ok) {
                window.currentCaseId = data.case_id;
                history.pushState(null, '', "?case_id=" + window.currentCaseId);
            }
        } else {
            await fetch(`/api/cases/${window.currentCaseId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }
    } catch(e) { console.error('Case save error', e); }
    
    btn.disabled = false;
    stage1Done = true; 
    nextStage();
  };

  document.getElementById('btn-validate').addEventListener('click', runValidation);
  document.getElementById('btn-mca').addEventListener('click', runMCA);
  document.getElementById('btn-stage1-proceed').addEventListener('click', window.proceedStage1);
  updateMCABtn();

  // ── Stage 2: Document Intelligence ─────────────────────────
  const DOCS = ['ALM Statement', 'Shareholding Pattern', 'Borrowing Profile', 'Annual Report', 'Portfolio Performance'];
  let docState = DOCS.map(name => ({ name, status: 'pending', fileType: null, fileSize: null, sha256: null, confidence: null, aiClassification: null }));

  function initStage2() {
    renderDocTable();
  }

  function renderDocTable() {
    const tbody = document.getElementById('doc-tbody');
    const processed = docState.filter(d => d.status === 'approved' || d.status === 'review').length;
    document.getElementById('doc-count').textContent = `${processed}/5 processed`;
    tbody.innerHTML = docState.map((doc, i) => {
      let statusHTML;
      if (doc.status === 'uploading')   statusHTML = `<span class="status-badge status-processing"><span class="spinner" style="width:10px;height:10px;border-width:1.5px"></span> Uploading</span>`;
      else if (doc.status === 'validating') statusHTML = `<span class="status-badge status-processing"><span class="spinner" style="width:10px;height:10px;border-width:1.5px"></span> AI Validating</span>`;
      else if (doc.status === 'approved')   statusHTML = `<span class="status-badge status-approved">${svgIcon('ok')} Approved</span>`;
      else if (doc.status === 'review')     statusHTML = `<span class="status-badge status-review">${svgIcon('warn')} Review</span>`;
      else statusHTML = `<span class="status-badge" style="background:var(--muted);color:var(--muted-fg)">Pending</span>`;

      let actionHTML = '';
      if (doc.status === 'pending')   actionHTML = `<button class="btn btn-primary btn-sm" onclick="uploadDoc(${i})">Upload</button>`;
      if (doc.status === 'review')    actionHTML = `<button class="btn btn-warning btn-sm" onclick="overrideDoc(${i})">Override</button>`;

      return `<tr>
        <td class="font-medium text-sm">${doc.name}</td>
        <td>${statusHTML}</td>
        <td class="mono text-xs">${doc.fileType || '—'}</td>
        <td class="mono text-xs">${doc.fileSize || '—'}</td>
        <td class="text-xs font-semibold" style="color:var(--primary)">${doc.aiClassification || '—'}</td>
        <td>${doc.confidence !== null ? `<span class="mono text-xs font-semibold ${doc.confidence >= 75 ? 'confidence-high' : 'confidence-low'}">${doc.confidence}%</span>` : '—'}</td>
        <td class="mono text-xs">${doc.sha256 ? doc.sha256.slice(0, 16) + '...' : '—'}</td>
        <td>${actionHTML}</td>
      </tr>`;
    }).join('');
    checkDocComplete();
  }

  window.uploadDoc = function(i) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.xlsx,.xls,.png,.jpg,.jpeg,.tiff';
    
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      docState[i].status = 'uploading';
      docState[i].fileType = file.name.split('.').pop().toUpperCase();
      docState[i].fileSize = (file.size / 1024 / 1024).toFixed(2) + ' MB';
      renderDocTable();

      const formData = new FormData();
      formData.append('file', file);
      formData.append('case_id', window.currentCaseId || '');
      formData.append('document_type', docState[i].name);

      try {
        docState[i].status = 'validating';
        renderDocTable();

        const resp = await fetch('/api/upload', {
          method: 'POST',
          body: formData
        });
        const data = await resp.json();

        if (resp.ok) {
          docState[i].confidence = Math.round(data.confidence * 100) || 85;
          docState[i].status = docState[i].confidence >= 75 ? 'approved' : 'review';
          docState[i].sha256 = data.file_hash || 'hash_unavailable';
          
          if (data.document_type && data.document_type !== 'Unknown') {
             docState[i].aiClassification = data.document_type;
          } else {
             docState[i].aiClassification = 'Unknown';
          }
          
          showToast(`✓ Uploaded and classified successfully!`, 'success');
        } else {
          docState[i].status = 'pending';
          docState[i].fileType = null;
          docState[i].fileSize = null;
          showToast(`Error: ${data.error}`, 'error');
          alert(`Upload failed: ${data.error}`);
        }
      } catch (err) {
        docState[i].status = 'pending';
        docState[i].fileType = null;
        docState[i].fileSize = null;
        showToast(`Connection error during upload.`, 'error');
        console.error(err);
      }
      renderDocTable();
      checkDocComplete();
    };
    input.click();
  };

  window.overrideDoc = function(i) {
    docState[i].status = 'approved';
    renderDocTable();
  };

  function checkDocComplete() {
    const allProcessed = docState.every(d => d.status === 'approved' || d.status === 'review');
    const hasReview = docState.some(d => d.status === 'review');
    const warnBox  = document.getElementById('doc-warn');
    const procBtn  = document.getElementById('btn-stage2-proceed');
    const verifyBox = document.getElementById('doc-verified');
    if (warnBox)  warnBox.style.display  = hasReview ? 'flex' : 'none';
    if (procBtn)  procBtn.style.display  = (allProcessed && !hasReview) ? 'flex' : 'none';
    if (verifyBox) verifyBox.style.display = (allProcessed && !hasReview) ? 'flex' : 'none';
  }

  document.getElementById('btn-stage2-proceed').addEventListener('click', () => { stage2Done = true; nextStage(); });

  // ── Stage 3: Financial Extraction ──────────────────────────
  function initStage3() { /* ready on render */ }

  const FIN = {
    revenue: 1500000000, ebitda: 375000000, pat: 225000000,
    debtEquity: 1.8, dscr: 1.45, interestCoverage: 3.2,
    gstBankDelta: 3.2, itcGap: 2.1,
  };

  const METRICS = [
    { label: 'Revenue',            key: 'revenue',          fmt: 'currency', rule: 'Positive revenue',       pass: true  },
    { label: 'EBITDA',             key: 'ebitda',           fmt: 'currency', rule: 'EBITDA ≤ Revenue',        pass: FIN.ebitda <= FIN.revenue },
    { label: 'PAT (Profit After Tax)', key: 'pat',          fmt: 'currency', rule: 'PAT ≤ EBITDA',           pass: FIN.pat <= FIN.ebitda },
    { label: 'Debt-Equity Ratio',  key: 'debtEquity',       fmt: 'ratio',    rule: 'D/E ≤ 3.0',              pass: FIN.debtEquity <= 3.0 },
    { label: 'DSCR',               key: 'dscr',             fmt: 'ratio',    rule: 'DSCR ≥ 1.0',             pass: FIN.dscr >= 1.0 },
    { label: 'Interest Coverage',  key: 'interestCoverage', fmt: 'ratio',    rule: 'ICR > 1.5',               pass: true  },
    { label: 'GST-Bank Delta',     key: 'gstBankDelta',     fmt: 'percent',  rule: 'GST Delta ≤ 5%',          pass: FIN.gstBankDelta <= 5 },
    { label: 'ITC Gap',            key: 'itcGap',           fmt: 'percent',  rule: 'ITC Gap within tolerance', pass: true  },
  ];

  function fmtVal(m) {
    if (m.fmt === 'currency') return formatCurrency(FIN[m.key]);
    if (m.fmt === 'percent')  return FIN[m.key] + '%';
    return FIN[m.key].toFixed(2);
  }

  let fraudOverride3 = false;

  window.runExtraction = async function() {
    const btn = document.getElementById('btn-extract');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Extracting Financial Data...';
    try {
      const res = await fetch(`/api/cases/${window.currentCaseId}/extract`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Unknown extraction error");
      
      const metrics = data.financial_metrics || {};
      const tbody = document.getElementById('extraction-tbody');
      if (tbody) {
        tbody.innerHTML = Object.entries(metrics).map(([k, v]) => `
          <tr>
            <td class="font-medium text-sm" style="text-transform: capitalize">${k}</td>
            <td class="mono text-sm">${v.toLocaleString()}</td>
            <td class="text-xs text-muted">Auto-Extracted</td>
            <td><span class="flex items-center gap-2 text-xs confidence-high font-semibold">${svgIcon('ok')} Extracted</span></td>
          </tr>`).join('');
      }

      document.getElementById('extraction-trigger').style.display = 'none';
      document.getElementById('extraction-result').style.display = 'block';
      document.getElementById('btn-stage3-proceed').style.display = 'inline-flex';
    } catch (e) {
      alert("Extraction failed: " + e.message);
      btn.disabled = false;
      btn.innerHTML = 'Scan & Extract Financial Data';
    }
  };

  window.applyFraudOverride = function() {
    fraudOverride3 = true;
    document.getElementById('override-info').style.display = 'block';
    document.getElementById('btn-override').style.display = 'none';
    document.getElementById('btn-stage3-proceed').style.display = 'inline-flex';
  };

  document.getElementById('btn-stage3-proceed').addEventListener('click', () => { stage3Done = true; nextStage(); });

  // Build extraction table HTML (hidden initially)
  (function buildExtractionTable() {
    const tbody = document.getElementById('extraction-tbody');
    if (!tbody) return;
    tbody.innerHTML = METRICS.map(m => `
      <tr>
        <td class="font-medium text-sm">${m.label}</td>
        <td class="mono text-sm">${fmtVal(m)}</td>
        <td class="text-xs text-muted">${m.rule}</td>
        <td>${m.pass
          ? `<span class="flex items-center gap-2 text-xs confidence-high font-semibold">${svgIcon('ok')} Pass</span>`
          : `<span class="flex items-center gap-2 text-xs text-destructive font-semibold">${svgIcon('alert')} Fail</span>`}</td>
      </tr>`).join('');
    document.getElementById('btn-extract').addEventListener('click', runExtraction);
  })();

  // ── Stage 4: AI Risk Analysis ───────────────────────────────
  const FIVE_CS = { character: 85, capacity: 78, capital: 82, collateral: 70, conditions: 75 };
  const WEIGHTS = { character: 0.25, capacity: 0.25, capital: 0.2, collateral: 0.15, conditions: 0.15 };
  const composite = Math.round(Object.keys(FIVE_CS).reduce((sum, k) => sum + FIVE_CS[k] * WEIGHTS[k], 0));
  const cts = 0.18, crs = 0.25;
  const ffs = +(0.6 * cts + 0.4 * crs).toFixed(2);
  const rejected = ffs > 0.75;
  const overallConf = Math.round(0.4 * 92 + 0.3 * 85 + 0.2 * 78 + 0.1 * (1 - ffs) * 100);

  const SWOT = {
    strengths:     ['Strong revenue growth (12% YoY)', 'Diversified product portfolio', 'Low debt-equity ratio (1.8x)', 'Established market presence (15+ years)'],
    weaknesses:    ['Declining EBITDA margin trend', 'High working capital cycle (95 days)', 'Concentrated customer base (top 5 = 60%)'],
    opportunities: ['Government infrastructure spending boost', 'Export market expansion potential', 'Green energy transition alignment'],
    threats:       ['Raw material price volatility', 'Regulatory changes in sector', 'Increasing competitive pressure from imports'],
  };

  const RESEARCH = [
    { source: 'MCA Filings',      finding: 'No director disqualifications found', status: 'clear', date: '2026-03-12' },
    { source: 'SEBI Database',    finding: 'No enforcement actions on record',     status: 'clear', date: '2026-03-12' },
    { source: 'CIBIL Rating',     finding: 'Credit rating: AA+ (Stable outlook)',  status: 'clear', date: '2026-03-11' },
    { source: 'News Intelligence',finding: '2 articles flagged — capacity expansion plans', status: 'review', date: '2026-03-13' },
    { source: 'Litigation Records',finding: '1 minor pending case (₹2.3Cr dispute)',status: 'review', date: '2026-03-10' },
  ];

  function scoreColor(s) { return s >= 75 ? 'hsl(160,84%,39%)' : s >= 50 ? 'hsl(38,92%,50%)' : 'hsl(0,72%,51%)'; }

  function initStage4() {
    document.getElementById('stage4-trigger').style.display = 'block';
    document.getElementById('stage4-result').style.display = 'none';
  }

  window.runRiskAnalysis = async function() {
    const btn = document.getElementById('btn-analyze');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Running AI Analysis...';
    const log = document.getElementById('analysis-log');
    log.innerHTML = '<p class="pulse text-xs text-muted">→ Cross-Triangulating Data Intelligence Engines...</p>';
    try {
      const res = await fetch(`/api/cases/${window.currentCaseId}/analyze`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Analysis error");

      const analysis = data.analysis;
      document.getElementById('stage4-trigger').style.display = 'none';
      buildStage4Results(analysis);
      document.getElementById('stage4-result').style.display = 'block';
    } catch (e) {
      alert("Analysis failed: " + e.message);
      btn.disabled = false;
      btn.innerHTML = 'Execute AI Appraisal Engine';
      log.innerHTML = '';
    }
  };

  function buildStage4Results(analysis) {
    if (!analysis) return;
    const FIVE_CS = analysis.scoring?.five_cs || {};
    const composite = analysis.composite_score || 0;
    const recommendation = analysis.scoring?.recommendation || 'Review';
    const SWOT = analysis.swot || {};

    // Five Cs
    const fiveCsGrid = document.getElementById('five-cs-grid');
    fiveCsGrid.innerHTML = Object.entries(FIVE_CS).map(([k, v]) => `
      <div class="cs-item">
        <div class="cs-chart">
          <svg viewBox="0 0 36 36">
            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none" stroke="hsl(214,32%,91%)" stroke-width="3"/>
            <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none" stroke="${scoreColor(v)}" stroke-width="3" stroke-dasharray="${Math.round(v)}, 100"/>
          </svg>
          <div class="cs-label" style="font-family:'Roboto Mono',monospace">${Math.round(v)}</div>
        </div>
        <p class="cs-name">${k}</p>
      </div>`).join('');

    // Composite
    const compColor = composite >= 70 ? 'var(--success)' : composite >= 50 ? 'var(--warning)' : 'var(--destructive)';
    const compBadge = composite >= 70 ? 'status-approved' : composite >= 50 ? 'status-review' : 'status-rejected';
    document.getElementById('composite-display').innerHTML = `
      <p class="text-xs text-muted" style="text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Composite Score</p>
      <div class="composite-number" style="color:${compColor}">${composite}</div>
      <p class="composite-sub">/ 100</p>
      <div class="status-badge ${compBadge}" style="margin-top:12px">${recommendation.toUpperCase()}</div>`;

    // Triangulation (reusing fraud panel UI to display these critical warnings instead)
    const fraudPanel = document.getElementById('fraud-panel');
    const triangulation = analysis.triangulation || [];
    fraudPanel.className = 'fraud-panel ' + (composite < 50 ? 'danger' : 'safe');
    fraudPanel.innerHTML = `
      <div class="fraud-panel-title">${svgIcon('expand')} Triangulation Intelligence Engine</div>
      <div style="margin-top: 12px">
        ${triangulation.map(t => `<p style="margin-bottom: 6px; font-size: 13px; color: ${t.flag==='Critical'?'var(--destructive)':t.flag==='Warning'?'var(--warning)':'var(--success)'}"><strong>[${t.flag}]</strong> ${t.message}</p>`).join('')}
      </div>`;

    // SWOT
    const swotEl = document.getElementById('swot-grid');
    const swotIcons = { strengths: ['↑', 'var(--success)'], weaknesses: ['↓', 'var(--destructive)'], opportunities: ['◆', 'var(--primary)'], threats: ['⚠', 'var(--warning)'] };
    swotEl.innerHTML = Object.entries(SWOT).map(([k, items]) => `
      <div>
        <div class="swot-section-title" style="color:${swotIcons[k][1]}">${swotIcons[k][0]} ${k.charAt(0).toUpperCase()+k.slice(1)}</div>
        ${items.map(item => `<div class="swot-item">${item}</div>`).join('')}
      </div>`).join('');

    // Research (from secondary API failures/sources used list to simulate tracking)
    const resEl = document.getElementById('research-list');
    const intel = analysis.intelligence || {};
    const sources = intel.data_sources_used || [];
    resEl.innerHTML = sources.map(s => `
      <div class="research-item clear">
        <div class="research-item-header">
          <span class="research-source">${s}</span>
          <span class="status-badge status-approved">Hit</span>
        </div>
      </div>`).join('');

    document.getElementById('confidence-display').innerHTML = `
      <span class="text-xs text-muted">System Recommendation:</span>
      <span class="mono font-semibold confidence-high" style="font-size:14px;margin-left:8px">${analysis.scoring.recommendation}</span>`;
  }

  // NOTE: generateReport is defined here as a base; the MongoDB submit layer
  // in case_new.html wraps this to persist data first, then calls this.
  window.generateReport = function() {
    const banner = document.createElement('div');
    banner.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:9998;background:hsl(214,90%,25%);color:hsl(214,90%,90%);border:1px solid hsl(214,70%,45%);padding:10px 24px;border-radius:8px;font-size:13px;font-weight:500;box-shadow:0 4px 20px rgba(0,0,0,0.2)';
    banner.textContent = '✓ Credit report generated — downloading PDF and redirecting...';
    document.body.appendChild(banner);
    
    // Download the PDF
    window.open(`/api/cases/${window.currentCaseId}/report.pdf`, '_blank');
    
    setTimeout(() => { window.location.href = '/cases'; }, 2000);
  };

  // Init Resume Logic
  async function loadCase(caseId) {
    try {
      const resp = await fetch(`/api/cases/${caseId}`);
      if (!resp.ok) return;
      const data = await resp.json();
      
      // Rehydrate Stage 1
      if (data.company) document.getElementById('f-company').value = data.company;
      if (data.cin) document.getElementById('f-cin').value = data.cin;
      if (data.pan) document.getElementById('f-pan').value = data.pan;
      if (data.sector) document.getElementById('f-sector').value = data.sector;
      if (data.loan_amount) document.getElementById('f-loan').value = data.loan_amount;
      if (data.annual_turnover) document.getElementById('f-turnover').value = data.annual_turnover;
      
      if (data.status === 'ENTITY_COMPLETED' || data.status === 'DOCUMENTS_UPLOADED' || data.status === 'REPORT_GENERATED') {
          stage1Done = true;
          validationsPassed = true;
          mcaVerified = true;
          updateProceedBtn();
          goStage(2);
      }
      
      // Rehydrate Stage 2
      if (data.documents && data.documents.length > 0) {
         data.documents.forEach(d => {
            const idx = docState.findIndex(ds => ds.name === d.document_type);
            if (idx !== -1) {
                docState[idx].status = d.status.toLowerCase();
                docState[idx].fileType = d.file_type;
                docState[idx].fileSize = (d.file_size / 1024 / 1024).toFixed(2) + ' MB';
                docState[idx].aiClassification = d.ai_classification;
                docState[idx].confidence = Math.round(d.confidence * 100);
                docState[idx].sha256 = d.sha256_hash;
            }
         });
         renderDocTable();
         checkDocComplete();
         
         if (data.status === 'DOCUMENTS_UPLOADED' || data.status === 'REPORT_GENERATED') {
             stage2Done = true;
             goStage(3);
         }
      }
      
      if (data.status === 'REPORT_GENERATED') {
          stage3Done = true;
          goStage(4);
      }
    } catch(err) { console.error('Error loading case', err); }
  }

  renderStepper();
  if (window.currentCaseId) {
      document.getElementById('stage-num').textContent = currentStage;
      loadCase(window.currentCaseId);
  } else {
      showStage(1);
  }
}
