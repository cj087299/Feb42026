// ── Global state ────────────────────────────────────────────
let currentReportData = null;
let currentReportType = 'BalanceSheet';
let agedPivotAllLabels = [];
let agedPivotChecked   = new Set();

// ── Initialisation ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Default dates
    const today = new Date();
    const oneMonthAgo = new Date();
    oneMonthAgo.setMonth(today.getMonth() - 1);
    const fmtDate = d => d.toISOString().split('T')[0];

    if (document.getElementById('endDateA'))   document.getElementById('endDateA').value   = fmtDate(today);
    if (document.getElementById('startDateA')) document.getElementById('startDateA').value = fmtDate(oneMonthAgo);

    const oneYearAgo  = new Date(); oneYearAgo.setFullYear(today.getFullYear() - 1);
    const oneYearAgoM = new Date(); oneYearAgoM.setFullYear(today.getFullYear() - 1); oneYearAgoM.setMonth(today.getMonth() - 1);
    if (document.getElementById('endDateB'))   document.getElementById('endDateB').value   = fmtDate(oneYearAgo);
    if (document.getElementById('startDateB')) document.getElementById('startDateB').value = fmtDate(oneYearAgoM);

    // Compare toggle
    const compareToggle = document.getElementById('compareToggle');
    if (compareToggle) {
        compareToggle.addEventListener('change', e => {
            document.getElementById('reportBControls').style.display = e.target.checked ? 'block' : 'none';
        });
    }

    // Run report
    const runBtn = document.getElementById('runReportBtn');
    if (runBtn) runBtn.addEventListener('click', fetchReport);

    // Export buttons
    const excelBtn = document.getElementById('exportExcelBtn');
    if (excelBtn) excelBtn.addEventListener('click', () => exportReport('excel'));
    const pdfBtn = document.getElementById('exportPDFBtn');
    if (pdfBtn) pdfBtn.addEventListener('click', () => exportReport('pdf'));

    // Save view
    const saveViewBtn = document.getElementById('saveViewBtn');
    if (saveViewBtn) saveViewBtn.addEventListener('click', openSaveModal);
    const confirmSaveBtn = document.getElementById('confirmSaveViewBtn');
    if (confirmSaveBtn) confirmSaveBtn.addEventListener('click', saveCurrentView);
    const savedReportsSelect = document.getElementById('savedReports');
    if (savedReportsSelect) savedReportsSelect.addEventListener('change', loadSavedReport);

    fetchSavedReports();

    // Close aged pivot dropdown when clicking outside it
    document.addEventListener('click', () => {
        const dd = document.getElementById('agedPivotDropdown');
        if (dd) dd.style.display = 'none';
    });

    // Auto-run if type param present in URL
    const urlParams = new URLSearchParams(window.location.search);
    const type = urlParams.get('type');
    if (type) {
        const sel = document.getElementById('reportType');
        if (sel) { sel.value = type; fetchReport(); }
    }
});

// ── Fetch & render report ────────────────────────────────────

async function fetchReport() {
    const reportType = document.getElementById('reportType').value;
    const compare    = document.getElementById('compareToggle').checked;
    currentReportType = reportType;

    const startDateA = document.getElementById('startDateA').value;
    const endDateA   = document.getElementById('endDateA').value;

    let params = new URLSearchParams({ start_date: startDateA, end_date: endDateA });

    if (compare) {
        const startDateB = document.getElementById('startDateB').value;
        const endDateB   = document.getElementById('endDateB').value;
        params = new URLSearchParams({ compare: 'true', start_date_a: startDateA, end_date_a: endDateA, start_date_b: startDateB, end_date_b: endDateB });
    }

    document.getElementById('loading').style.display = 'block';
    document.getElementById('reportContainer').innerHTML = '';
    currentReportData = null;

    try {
        const response = await fetch(`/api/reports/${reportType}?${params.toString()}`);
        const data     = await response.json();

        if (data.error) {
            document.getElementById('reportContainer').innerHTML =
                `<div style="color:#dc2626;padding:20px;text-align:center;">Error: ${escapeHTML(data.error)}</div>`;
            return;
        }

        currentReportData = data;

        if (compare) {
            renderComparison(data);
        } else {
            const container = document.getElementById('reportContainer');
            container.innerHTML = '';
            renderReport(data, container, reportType);
        }
    } catch (err) {
        console.error(err);
        document.getElementById('reportContainer').innerHTML =
            '<div style="color:#dc2626;padding:20px;text-align:center;">Failed to fetch report. See console for details.</div>';
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

// ── Aged report column title mapping ─────────────────────────

function mapAgedColumnTitle(title) {
    const t = (title || '').trim().toLowerCase();
    if (t === 'current')                              return 'Not Due';
    if (/^1\s*[-–]\s*30/.test(t))                    return '1-30 Days';
    if (/^31\s*[-–]\s*60/.test(t))                   return '31-60 Days';
    if (/^61\s*[-–]\s*90/.test(t))                   return '61-90 Days';
    if (/^91\s*[-–]\s*120/.test(t))                  return '91-120 Days';
    if (/^(>|over|121|120\+)/.test(t) || t.includes('over')) return '120+ Days';
    return title;
}

// ── Aged pivot filter ─────────────────────────────────────────

function buildAgedPivotDropdown(treeContainer) {
    // Collect labels from rendered data rows (skip section headers and totals)
    const labels = [];
    treeContainer.querySelectorAll('.report-tree-node').forEach(node => {
        if (node.querySelector('.report-section-header') || node.querySelector('.summary-row')) return;
        const cell = node.querySelector('.report-cell');
        if (cell) { const t = cell.textContent.trim(); if (t) labels.push(t); }
    });
    agedPivotAllLabels = labels;
    agedPivotChecked   = new Set(labels);

    const existing = document.getElementById('agedPivotDropdown');
    if (existing) existing.remove();

    const dropdown = document.createElement('div');
    dropdown.id = 'agedPivotDropdown';
    dropdown.className = 'aged-pivot-dropdown';
    dropdown.style.display = 'none';
    dropdown.addEventListener('click', e => e.stopPropagation());

    // Search input
    const searchDiv = document.createElement('div');
    searchDiv.className = 'aged-pivot-search';
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.id = 'agedPivotSearch';
    searchInput.placeholder = 'Search…';
    searchInput.addEventListener('input', () => renderAgedPivotOptions(searchInput.value));
    searchDiv.appendChild(searchInput);
    dropdown.appendChild(searchDiv);

    // Select All row
    const saDiv = document.createElement('div');
    saDiv.className = 'aged-pivot-selectall';
    const saLabel = document.createElement('label');
    const saCb = document.createElement('input');
    saCb.type = 'checkbox'; saCb.id = 'agedPivotSelectAll'; saCb.checked = true;
    saCb.addEventListener('change', () => toggleAgedPivotAll(saCb.checked));
    saLabel.appendChild(saCb);
    saLabel.appendChild(document.createTextNode(' Select All'));
    saDiv.appendChild(saLabel);
    dropdown.appendChild(saDiv);

    // Options list
    const optsList = document.createElement('div');
    optsList.id = 'agedPivotList';
    optsList.className = 'aged-pivot-list';
    dropdown.appendChild(optsList);

    const trigger = treeContainer.querySelector('.aged-filter-trigger');
    if (trigger) trigger.appendChild(dropdown);

    renderAgedPivotOptions('');
}

function toggleAgedPivotDropdown() {
    const dd = document.getElementById('agedPivotDropdown');
    if (!dd) return;
    dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
}

function renderAgedPivotOptions(search) {
    const list = document.getElementById('agedPivotList');
    if (!list) return;
    const lower    = search.toLowerCase().trim();
    const filtered = lower ? agedPivotAllLabels.filter(l => l.toLowerCase().includes(lower)) : agedPivotAllLabels;
    list.innerHTML = '';
    filtered.forEach(label => {
        const opt = document.createElement('label');
        opt.className = 'aged-pivot-option';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = agedPivotChecked.has(label);
        cb.addEventListener('change', () => {
            if (cb.checked) agedPivotChecked.add(label);
            else            agedPivotChecked.delete(label);
            applyAgedPivotFilter();
            updateAgedPivotSelectAll();
        });
        const span = document.createElement('span');
        span.textContent = label; span.title = label;
        opt.appendChild(cb); opt.appendChild(span);
        list.appendChild(opt);
    });
    updateAgedPivotSelectAll();
}

function toggleAgedPivotAll(checked) {
    if (checked) agedPivotAllLabels.forEach(l => agedPivotChecked.add(l));
    else         agedPivotChecked.clear();
    const si = document.getElementById('agedPivotSearch');
    renderAgedPivotOptions(si ? si.value : '');
    applyAgedPivotFilter();
}

function updateAgedPivotSelectAll() {
    const sa = document.getElementById('agedPivotSelectAll');
    if (!sa) return;
    const n = agedPivotAllLabels.filter(l => agedPivotChecked.has(l)).length;
    if (n === 0)                          { sa.indeterminate = false; sa.checked = false; }
    else if (n >= agedPivotAllLabels.length) { sa.indeterminate = false; sa.checked = true;  }
    else                                  { sa.indeterminate = true; }
}

function applyAgedPivotFilter() {
    document.querySelectorAll('#reportContainer .report-tree-node').forEach(node => {
        if (node.querySelector('.report-section-header') || node.querySelector('.summary-row')) return;
        const cell = node.querySelector('.report-cell');
        if (!cell) return;
        node.style.display = agedPivotChecked.has(cell.textContent.trim()) ? '' : 'none';
    });
}

// ── Report rendering ─────────────────────────────────────────

function renderReport(reportData, container, reportType) {
    reportType = reportType || currentReportType;

    if (!reportData || !reportData.Header) {
        container.innerHTML = '<div class="report-placeholder">No data available or invalid response format.</div>';
        return;
    }

    // Header block
    const headerBlock = document.createElement('div');
    headerBlock.className = 'report-header-block';
    const titleEl = document.createElement('h2');
    titleEl.className = 'report-title';
    titleEl.textContent = reportData.Header.ReportName || 'Report';
    headerBlock.appendChild(titleEl);
    if (reportData.Header.StartPeriod || reportData.Header.EndPeriod) {
        const periodEl = document.createElement('div');
        periodEl.className = 'report-period';
        if (reportData.Header.StartPeriod && reportData.Header.EndPeriod) {
            periodEl.textContent = `${reportData.Header.StartPeriod} — ${reportData.Header.EndPeriod}`;
        } else {
            periodEl.textContent = `As of ${reportData.Header.EndPeriod || reportData.Header.StartPeriod}`;
        }
        headerBlock.appendChild(periodEl);
    }
    container.appendChild(headerBlock);

    // Column header row
    const treeContainer = document.createElement('div');
    treeContainer.className = 'report-tree';

    if (reportData.Columns && reportData.Columns.Column) {
        const headerRow = document.createElement('div');
        headerRow.className = 'report-header-row';

        const isAged = (reportType === 'AgedPayables' || reportType === 'AgedReceivables');
        const labelCol = document.createElement('div');
        if (isAged) {
            labelCol.className = 'report-cell aged-filter-trigger';
            labelCol.innerHTML = 'Account / Item <span class="aged-filter-arrow">&#9660;</span>';
            labelCol.addEventListener('click', e => { e.stopPropagation(); toggleAgedPivotDropdown(); });
        } else {
            labelCol.className = 'report-cell';
            labelCol.textContent = 'Account / Item';
        }
        headerRow.appendChild(labelCol);

        reportData.Columns.Column.forEach(col => {
            if (col.ColType === 'Money') {
                const cell = document.createElement('div');
                cell.className = 'report-cell report-cell-value';
                cell.textContent = isAged ? mapAgedColumnTitle(col.ColTitle) : (col.ColTitle || 'Amount');
                headerRow.appendChild(cell);
            }
        });
        treeContainer.appendChild(headerRow);
    }

    // Rows
    if (reportData.Rows && reportData.Rows.Row) {
        renderRows(reportData.Rows.Row, treeContainer, 0, reportData.Header, reportType);
    }

    // Aged reports: build pivot filter dropdown after rows exist in DOM
    if (reportType === 'AgedPayables' || reportType === 'AgedReceivables') {
        buildAgedPivotDropdown(treeContainer);
    }

    container.appendChild(treeContainer);
}

function renderRows(rows, container, level, header, reportType) {
    if (!Array.isArray(rows)) rows = [rows];

    rows.forEach(row => {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'report-tree-node';
        if (level > 0) rowDiv.classList.add('report-indent');

        if (row.type === 'Section' || (row.Header && row.Header.ColData)) {
            const sectionTitle = row.Header && row.Header.ColData && row.Header.ColData.length > 0
                ? row.Header.ColData[0].value
                : 'Section';

            const sectionHeader = document.createElement('div');
            sectionHeader.className = 'report-section-header';
            sectionHeader.textContent = sectionTitle;
            sectionHeader.style.marginLeft = (level * 20) + 'px';
            rowDiv.appendChild(sectionHeader);

            if (row.Rows && row.Rows.Row) {
                renderRows(row.Rows.Row, rowDiv, level + 1, header, reportType);
            }
            if (row.Summary && row.Summary.ColData) {
                renderDataRow(row.Summary, rowDiv, level, header, true, reportType);
            }
        } else if (row.ColData) {
            renderDataRow(row, rowDiv, level, header, false, reportType);
        }

        container.appendChild(rowDiv);
    });
}

function renderDataRow(row, container, level, header, isSummary, reportType) {
    const rowDiv = document.createElement('div');
    rowDiv.className = 'report-row' + (isSummary ? ' summary-row' : '');

    // Label cell
    const labelDiv = document.createElement('div');
    labelDiv.className = 'report-cell';
    labelDiv.textContent = row.ColData[0].value;
    labelDiv.style.paddingLeft = (level * 14) + 'px';
    rowDiv.appendChild(labelDiv);

    // Determine drilldown filter type based on report type
    let drilldownType = 'account';
    if (reportType === 'AgedPayables')    drilldownType = 'vendor';
    else if (reportType === 'AgedReceivables') drilldownType = 'customer';

    // Date range for drilldown
    let startDate = header.StartPeriod;
    let endDate   = header.EndPeriod;
    // For aging reports, StartPeriod may be absent — use a 2-year lookback
    if (!startDate && endDate) {
        const d = new Date(endDate);
        d.setFullYear(d.getFullYear() - 2);
        startDate = d.toISOString().split('T')[0];
    }

    // Value cells
    for (let i = 1; i < row.ColData.length; i++) {
        const valDiv = document.createElement('div');
        valDiv.className = 'report-cell report-cell-value';

        const rawVal = row.ColData[i].value;
        const id     = row.ColData[0].id;
        const isNeg  = rawVal && parseFloat(rawVal) < 0;
        if (isNeg) valDiv.classList.add('is-negative');

        const displayVal = formatReportValue(rawVal);

        if (displayVal && rawVal !== '' && id && !isSummary) {
            const link = document.createElement('span');
            link.className = 'report-value-link';
            link.textContent = displayVal;
            link.onclick = () => showDrillDown(id, startDate, endDate, row.ColData[0].value, drilldownType);
            valDiv.appendChild(link);
        } else {
            valDiv.textContent = displayVal;
        }

        rowDiv.appendChild(valDiv);
    }

    container.appendChild(rowDiv);
}

function renderComparison(data) {
    const container = document.getElementById('reportContainer');
    container.innerHTML = '';

    const wrapper = document.createElement('div');
    wrapper.className = 'comparison-container';

    const colA = document.createElement('div');
    colA.className = 'report-column';
    colA.innerHTML = '<div class="comparison-label">Report Period</div>';
    renderReport(data.report_a, colA, currentReportType);

    const colB = document.createElement('div');
    colB.className = 'report-column';
    colB.innerHTML = '<div class="comparison-label period-b">Comparison Period</div>';
    renderReport(data.report_b, colB, currentReportType);

    wrapper.appendChild(colA);
    wrapper.appendChild(colB);
    container.appendChild(wrapper);
}

// ── Drill-down modal ─────────────────────────────────────────

async function showDrillDown(entityId, startDate, endDate, entityName, drilldownType) {
    drilldownType = drilldownType || 'account';

    const modal      = document.getElementById('drillDownModal');
    const modalBody  = document.getElementById('modalContent');
    const modalTitle = document.getElementById('modalTitle');

    // Build a readable title
    const typeLabel = drilldownType === 'vendor' ? 'Vendor' : drilldownType === 'customer' ? 'Customer' : 'Account';
    const datePart  = startDate && endDate ? ` · ${startDate} – ${endDate}` : endDate ? ` · As of ${endDate}` : '';
    const title     = `${entityName}${datePart}`;
    modalTitle.textContent = title;
    currentDrillDownTitle  = title;
    document.getElementById('drillDownExportBtns').style.display = 'none';
    modalBody.innerHTML = '<div style="text-align:center;padding:30px;color:#94a3b8;">Loading transactions…</div>';
    modal.style.display = 'block';

    try {
        const params = new URLSearchParams({ end_date: endDate || '' });
        if (startDate) params.append('start_date', startDate);
        params.append(drilldownType, entityId);

        const response = await fetch(`/api/reports/drilldown?${params.toString()}`);
        const data     = await response.json();

        if (data.error) {
            modalBody.innerHTML = `<div style="color:#dc2626;padding:20px;">${escapeHTML(data.error)}</div>`;
            return;
        }

        renderTransactionList(data, modalBody);
        document.getElementById('drillDownExportBtns').style.display = 'flex';
    } catch (e) {
        console.error(e);
        modalBody.innerHTML = '<div style="color:#dc2626;padding:20px;">Error loading transactions.</div>';
    }
}

function renderTransactionList(data, container) {
    if (!data || !data.Rows || !data.Rows.Row || data.Rows.Row.length === 0) {
        container.innerHTML = '<div class="drilldown-empty">No transactions found for this period.</div>';
        return;
    }

    // Flatten rows — TransactionList is flat; GeneralLedger nests data rows inside Section rows
    const flatRows = [];
    data.Rows.Row.forEach(row => {
        if (row.ColData) {
            flatRows.push(row);
        } else if (row.Rows && row.Rows.Row) {
            row.Rows.Row.forEach(inner => { if (inner.ColData) flatRows.push(inner); });
        }
    });

    if (flatRows.length === 0) {
        container.innerHTML = '<div class="drilldown-empty">No transactions found for this period.</div>';
        return;
    }

    // Detect amount-like columns (by title or ColType)
    const amountKeywords = ['amount', 'debit', 'credit', 'balance', 'total'];
    const columns = (data.Columns && data.Columns.Column) ? data.Columns.Column : [];
    const isAmountCol = columns.map(col => {
        const title = (col.ColTitle || '').toLowerCase();
        return amountKeywords.some(k => title.includes(k)) || col.ColType === 'Money';
    });

    const table  = document.createElement('table');
    table.className = 'drilldown-table';

    // Header
    const thead     = document.createElement('thead');
    const headerRow = document.createElement('tr');
    columns.forEach((col, i) => {
        const th = document.createElement('th');
        th.textContent = col.ColTitle || '';
        if (isAmountCol[i]) th.classList.add('col-amount');
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Body
    const tbody = document.createElement('tbody');
    flatRows.forEach(row => {
        const tr = document.createElement('tr');
        row.ColData.forEach((cell, i) => {
            const td = document.createElement('td');
            const isAmt = isAmountCol[i];
            if (isAmt) {
                td.classList.add('col-amount');
                const num = parseFloat(cell.value);
                if (!isNaN(num)) {
                    if (num < 0) td.classList.add('is-negative');
                    td.textContent = formatReportValue(cell.value);
                } else {
                    td.textContent = cell.value || '';
                }
            } else {
                td.textContent = cell.value || '';
            }
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    container.innerHTML = '';
    container.appendChild(table);
}

function formatReportValue(val) {
    if (val === null || val === undefined || val === '') return '';
    const num = parseFloat(val);
    if (isNaN(num)) return val;
    const abs = Math.abs(num).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return num < 0 ? `(${abs})` : abs;
}

let currentDrillDownTitle = 'Transactions';

function exportDrillDown(format) {
    const table = document.querySelector('#modalContent .drilldown-table');
    if (!table) { alert('No data to export.'); return; }
    // Sanitize title for use as a filename
    const filename = currentDrillDownTitle.replace(/[^\w\s–-]/g, '').replace(/\s+/g, '_');
    if (format === 'csv')   exportTableToCSV(table, filename);
    else if (format === 'excel') exportTableToExcel(table, filename);
    else if (format === 'pdf')   exportTableToPDF(table, filename);
}

function closeModal() {
    document.getElementById('drillDownModal').style.display = 'none';
}

window.addEventListener('click', e => {
    const ddModal   = document.getElementById('drillDownModal');
    const saveModal = document.getElementById('saveViewModal');
    if (e.target === ddModal)   ddModal.style.display   = 'none';
    if (e.target === saveModal) saveModal.style.display = 'none';
});

// ── Export ───────────────────────────────────────────────────

function exportReport(format) {
    if (!currentReportData) { alert('Please run a report first.'); return; }

    let reportDataToExport = currentReportData;
    let filename = 'Report';

    if (currentReportData.report_a && currentReportData.report_b) {
        alert('Exporting comparison reports — exporting primary report period only.');
        reportDataToExport = currentReportData.report_a;
        filename = 'Comparison_Report_A';
    } else {
        filename = reportDataToExport.Header.ReportName || 'Report';
    }

    const flatData = flattenReportData(reportDataToExport);

    const headers = ['Account / Item'];
    if (reportDataToExport.Columns && reportDataToExport.Columns.Column) {
        reportDataToExport.Columns.Column.forEach(col => {
            if (col.ColType === 'Money') headers.push(col.ColTitle || 'Amount');
        });
    }

    if (format === 'excel') exportDataToExcel(flatData, headers, filename);
    else if (format === 'pdf') exportDataToPDF(flatData, headers, filename);
}

function flattenReportData(reportData) {
    const rows   = [];
    const headers = ['Account / Item'];
    if (reportData.Columns && reportData.Columns.Column) {
        reportData.Columns.Column.forEach(col => {
            if (col.ColType === 'Money') headers.push(col.ColTitle || 'Amount');
        });
    }

    function processRows(reportRows, indent) {
        if (!Array.isArray(reportRows)) reportRows = [reportRows];
        reportRows.forEach(row => {
            if (row.type === 'Section' || (row.Header && row.Header.ColData)) {
                const label = row.Header && row.Header.ColData && row.Header.ColData.length > 0
                    ? row.Header.ColData[0].value : 'Section';
                const obj = { 'Account / Item': '  '.repeat(indent) + label };
                headers.slice(1).forEach(h => obj[h] = '');
                rows.push(obj);
                if (row.Rows && row.Rows.Row) processRows(row.Rows.Row, indent + 1);
                if (row.Summary && row.Summary.ColData) processDataRow(row.Summary, indent);
            } else if (row.ColData) {
                processDataRow(row, indent);
            }
        });
    }

    function processDataRow(row, indent) {
        const obj = { 'Account / Item': '  '.repeat(indent) + (row.ColData[0].value || '') };
        for (let i = 1; i < row.ColData.length; i++) {
            const key = headers[i];
            if (key) obj[key] = row.ColData[i].value;
        }
        rows.push(obj);
    }

    if (reportData.Rows && reportData.Rows.Row) processRows(reportData.Rows.Row, 0);
    return rows;
}

// ── Saved reports ────────────────────────────────────────────

let savedReports = [];

async function fetchSavedReports() {
    try {
        const response = await fetch('/api/reports/saved');
        savedReports = await response.json();
        const select = document.getElementById('savedReports');
        if (!select) return;
        while (select.options.length > 1) select.remove(1);
        savedReports.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.id;
            opt.textContent = r.name;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to fetch saved reports', e);
    }
}

function loadSavedReport() {
    const select   = document.getElementById('savedReports');
    const reportId = parseInt(select.value);
    if (!reportId) return;
    const report = savedReports.find(r => r.id === reportId);
    if (!report) return;

    const params = report.params;
    document.getElementById('reportType').value = report.report_type;
    currentReportType = report.report_type;

    if (params.start_date_a) document.getElementById('startDateA').value = params.start_date_a;
    if (params.end_date_a)   document.getElementById('endDateA').value   = params.end_date_a;

    const compareToggle = document.getElementById('compareToggle');
    const compare = params.compare === 'true' || params.compare === true;
    if (compareToggle.checked !== compare) {
        compareToggle.checked = compare;
        compareToggle.dispatchEvent(new Event('change'));
    }
    if (compare) {
        if (params.start_date_b) document.getElementById('startDateB').value = params.start_date_b;
        if (params.end_date_b)   document.getElementById('endDateB').value   = params.end_date_b;
    }

    fetchReport();
}

function openSaveModal() {
    document.getElementById('saveViewModal').style.display = 'block';
    document.getElementById('saveViewName').value = '';
    document.getElementById('saveViewName').focus();
}

function closeSaveModal() {
    document.getElementById('saveViewModal').style.display = 'none';
}

async function saveCurrentView() {
    const name = document.getElementById('saveViewName').value.trim();
    if (!name) { alert('Please enter a name for this view.'); return; }

    const reportType = document.getElementById('reportType').value;
    const compare    = document.getElementById('compareToggle').checked;

    const params = {
        start_date_a: document.getElementById('startDateA').value,
        end_date_a:   document.getElementById('endDateA').value,
        compare,
    };

    if (compare) {
        params.start_date_b = document.getElementById('startDateB').value;
        params.end_date_b   = document.getElementById('endDateB').value;
    }

    try {
        const response = await fetch('/api/reports/saved', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, report_type: reportType, params })
        });
        if (response.ok) {
            closeSaveModal();
            fetchSavedReports();
            alert('View saved successfully!');
        } else {
            const err = await response.json();
            alert('Error saving view: ' + (err.error || 'Unknown error'));
        }
    } catch (e) {
        console.error(e);
        alert('Failed to save view.');
    }
}
