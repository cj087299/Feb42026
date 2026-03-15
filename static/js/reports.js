document.addEventListener('DOMContentLoaded', () => {
    // Set default dates (Today and 1 month ago)
    const today = new Date();
    const oneMonthAgo = new Date();
    oneMonthAgo.setMonth(today.getMonth() - 1);

    // Format date as YYYY-MM-DD
    const formatDate = (date) => date.toISOString().split('T')[0];

    if(document.getElementById('endDateA')) document.getElementById('endDateA').value = formatDate(today);
    if(document.getElementById('startDateA')) document.getElementById('startDateA').value = formatDate(oneMonthAgo);

    // Default B dates (Previous year)
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(today.getFullYear() - 1);
    const oneYearAgoMonth = new Date();
    oneYearAgoMonth.setFullYear(today.getFullYear() - 1);
    oneYearAgoMonth.setMonth(today.getMonth() - 1);

    if(document.getElementById('endDateB')) document.getElementById('endDateB').value = formatDate(oneYearAgo);
    if(document.getElementById('startDateB')) document.getElementById('startDateB').value = formatDate(oneYearAgoMonth);

    // Toggle Comparison
    const compareToggle = document.getElementById('compareToggle');
    if(compareToggle) {
        compareToggle.addEventListener('change', (e) => {
            const reportBControls = document.getElementById('reportBControls');
            reportBControls.style.display = e.target.checked ? 'block' : 'none';
        });
    }

    // Run Report
    const runBtn = document.getElementById('runReportBtn');
    if(runBtn) {
        runBtn.addEventListener('click', fetchReport);
    }

    // Export Buttons
    const exportExcelBtn = document.getElementById('exportExcelBtn');
    if (exportExcelBtn) {
        exportExcelBtn.addEventListener('click', () => exportReport('excel'));
    }

    const exportPDFBtn = document.getElementById('exportPDFBtn');
    if (exportPDFBtn) {
        exportPDFBtn.addEventListener('click', () => exportReport('pdf'));
    }

    // Save View Logic
    const saveViewBtn = document.getElementById('saveViewBtn');
    if (saveViewBtn) {
        saveViewBtn.addEventListener('click', openSaveModal);
    }
    const confirmSaveBtn = document.getElementById('confirmSaveViewBtn');
    if (confirmSaveBtn) {
        confirmSaveBtn.addEventListener('click', saveCurrentView);
    }
    const savedReportsSelect = document.getElementById('savedReports');
    if (savedReportsSelect) {
        savedReportsSelect.addEventListener('change', loadSavedReport);
    }

    // Load Saved Reports
    fetchSavedReports();

    // Auto-run if type param is present
    const urlParams = new URLSearchParams(window.location.search);
    const type = urlParams.get('type');
    if (type) {
        const reportTypeSelect = document.getElementById('reportType');
        if (reportTypeSelect) {
            // Find option matching value (case-insensitive if needed, but exact match for now)
            reportTypeSelect.value = type;
            // Trigger fetch
            fetchReport();
        }
    }
});

let currentReportData = null; // Store fetched data for export

async function fetchReport() {
    const reportType = document.getElementById('reportType').value;
    const compare = document.getElementById('compareToggle').checked;

    const startDateA = document.getElementById('startDateA').value;
    const endDateA = document.getElementById('endDateA').value;

    const customer = document.getElementById('filterCustomer').value;
    const vendor = document.getElementById('filterVendor').value;

    let params = new URLSearchParams({
        start_date: startDateA,
        end_date: endDateA
    });

    if (customer) params.append('customer', customer);
    if (vendor) params.append('vendor', vendor);

    if (compare) {
        const startDateB = document.getElementById('startDateB').value;
        const endDateB = document.getElementById('endDateB').value;

        // Rebuild params for comparison
        const compareParams = new URLSearchParams();
        compareParams.append('compare', 'true');
        compareParams.append('start_date_a', startDateA);
        compareParams.append('end_date_a', endDateA);
        compareParams.append('start_date_b', startDateB);
        compareParams.append('end_date_b', endDateB);

        if (customer) compareParams.append('customer', customer);
        if (vendor) compareParams.append('vendor', vendor);

        params = compareParams;
    }

    // Show loading
    document.getElementById('loading').style.display = 'block';
    document.getElementById('reportContainer').innerHTML = '';
    currentReportData = null;

    try {
        const response = await fetch(`/api/reports/${reportType}?${params.toString()}`);
        const data = await response.json();
        console.log('Report Data:', JSON.stringify(data));

        if (data.error) {
            console.log('escapeHTML type:', typeof escapeHTML);
            try {
                 const escaped = escapeHTML(data.error);
                 console.log('Escaped error:', escaped);
                 document.getElementById('reportContainer').innerHTML = `<div style="color:red; text-align:center;">Error: ${escaped}</div>`;
            } catch (e) {
                 console.log('Error in escapeHTML block:', e);
            }
            return;
        }

        currentReportData = data; // Store for export

        if (compare) {
            renderComparison(data);
        } else {
            renderReport(data, document.getElementById('reportContainer'));
        }

    } catch (error) {
        console.error(error);
        document.getElementById('reportContainer').innerHTML = '<div style="color:red; text-align:center;">Failed to fetch report. See console for details.</div>';
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

function renderReport(reportData, container) {
    if (!reportData || !reportData.Header) {
        container.innerHTML = '<div class="alert alert-info">No data available or invalid response format.</div>';
        return;
    }

    const title = document.createElement('h3');
    title.textContent = reportData.Header.ReportName;
    if (reportData.Header.StartPeriod && reportData.Header.EndPeriod) {
        title.textContent += ` (${reportData.Header.StartPeriod} to ${reportData.Header.EndPeriod})`;
    }
    container.appendChild(title);

    const treeContainer = document.createElement('div');
    treeContainer.className = 'report-tree';

    // Render Header Row (Columns)
    const headerRow = document.createElement('div');
    headerRow.className = 'report-row report-header-row';
    // First col is label (implicit)
    const labelCol = document.createElement('div');
    labelCol.className = 'report-cell';
    labelCol.textContent = 'Account / Item';
    headerRow.appendChild(labelCol);

    if (reportData.Columns && reportData.Columns.Column) {
        reportData.Columns.Column.forEach(col => {
            if (col.ColType === 'Money') {
                const cell = document.createElement('div');
                cell.className = 'report-cell report-cell-value';
                cell.textContent = col.ColTitle || 'Amount';
                headerRow.appendChild(cell);
            }
        });
    }
    treeContainer.appendChild(headerRow);

    // Recursively render Rows
    if (reportData.Rows && reportData.Rows.Row) {
        renderRows(reportData.Rows.Row, treeContainer, 0, reportData.Header);
    }

    container.appendChild(treeContainer);
}

function renderRows(rows, container, level, header) {
    if (!Array.isArray(rows)) rows = [rows];

    rows.forEach(row => {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'report-tree-node';
        if (level > 0) rowDiv.classList.add('report-indent');

        // If it's a section
        if (row.type === 'Section' || (row.Header && row.Header.ColData)) {
            const sectionTitle = row.Header && row.Header.ColData && row.Header.ColData.length > 0
                ? row.Header.ColData[0].value
                : 'Section';

             // Render section header
            const headerDiv = document.createElement('div');
            headerDiv.className = 'report-section-header';
            headerDiv.textContent = sectionTitle;
            headerDiv.style.paddingLeft = (level * 10) + 'px';
            rowDiv.appendChild(headerDiv);

            if (row.Rows && row.Rows.Row) {
                renderRows(row.Rows.Row, rowDiv, level + 1, header);
            }
             // Render Summary if any
            if (row.Summary && row.Summary.ColData) {
                 renderDataRow(row.Summary, rowDiv, level, header, true);
            }
        } else if (row.ColData) {
            // It's a data row
            renderDataRow(row, rowDiv, level, header, false);
        }

        container.appendChild(rowDiv);
    });
}

function renderDataRow(row, container, level, header, isSummary) {
    const rowDiv = document.createElement('div');
    rowDiv.className = 'report-row';
    if (isSummary) rowDiv.style.fontWeight = 'bold';

    // First column is the label
    const labelDiv = document.createElement('div');
    labelDiv.className = 'report-cell';
    labelDiv.textContent = row.ColData[0].value;
    labelDiv.style.paddingLeft = (level * 10) + 'px';
    rowDiv.appendChild(labelDiv);

    // Other columns are values
    for (let i = 1; i < row.ColData.length; i++) {
        const valDiv = document.createElement('div');
        valDiv.className = 'report-cell report-cell-value';
        const val = row.ColData[i].value;
        const id = row.ColData[0].id; // Usually ID is in first col data

        if (val && val !== "" && id && !isSummary) {
            // Make clickable
            const link = document.createElement('span');
            link.className = 'report-value-link';
            link.textContent = val;
            link.onclick = () => showDrillDown(id, header.StartPeriod, header.EndPeriod, row.ColData[0].value);
            valDiv.appendChild(link);
        } else {
            valDiv.textContent = val;
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
    colA.innerHTML = '<div style="background:#eef; padding:5px; text-align:center; margin-bottom:10px; font-weight:bold;">Report Period</div>';
    renderReport(data.report_a, colA);

    const colB = document.createElement('div');
    colB.className = 'report-column';
    colB.innerHTML = '<div style="background:#fee; padding:5px; text-align:center; margin-bottom:10px; font-weight:bold;">Comparison Period</div>';
    renderReport(data.report_b, colB);

    wrapper.appendChild(colA);
    wrapper.appendChild(colB);
}

async function showDrillDown(accountId, startDate, endDate, accountName) {
    const modal = document.getElementById('drillDownModal');
    const modalContent = document.getElementById('modalContent');
    const modalTitle = document.getElementById('modalTitle');

    modalTitle.textContent = `Transactions for ${accountName} (${startDate} - ${endDate})`;
    modalContent.innerHTML = '<div style="text-align:center; padding:20px;">Loading transactions...</div>';
    modal.style.display = 'block';

    try {
        const params = new URLSearchParams({
            account: accountId,
            start_date: startDate,
            end_date: endDate
        });

        const response = await fetch(`/api/reports/drilldown?${params.toString()}`);
        const data = await response.json();

        renderTransactionList(data, modalContent);
    } catch (e) {
        console.error(e);
        modalContent.textContent = 'Error loading transactions.';
    }
}

function renderTransactionList(data, container) {
    if (!data || !data.Rows || !data.Rows.Row || data.Rows.Row.length === 0) {
        container.innerHTML = '<div style="text-align:center; padding:20px;">No transactions found.</div>';
        return;
    }

    const table = document.createElement('table');
    table.className = 'drilldown-table';

    // Headers
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    if (data.Columns && data.Columns.Column) {
        data.Columns.Column.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col.ColTitle;
            headerRow.appendChild(th);
        });
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Body
    const tbody = document.createElement('tbody');
    data.Rows.Row.forEach(row => {
        const tr = document.createElement('tr');
        if (row.ColData) {
            row.ColData.forEach(cell => {
                const td = document.createElement('td');
                td.textContent = cell.value;
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        }
    });
    table.appendChild(tbody);

    container.innerHTML = '';
    container.appendChild(table);
}

function closeModal() {
    document.getElementById('drillDownModal').style.display = 'none';
}

window.onclick = function(event) {
    const modal = document.getElementById('drillDownModal');
    if (event.target == modal) {
        modal.style.display = "none";
    }
}

// ---------------------------------------------------------
// Export Logic
// ---------------------------------------------------------

function exportReport(format) {
    if (!currentReportData) {
        alert('Please run a report first.');
        return;
    }

    let reportDataToExport = currentReportData;
    let filename = 'Report';

    // Check if comparison mode (contains report_a and report_b)
    if (currentReportData.report_a && currentReportData.report_b) {
        // For simplicity, export both as separate sheets or combined?
        // Let's just alert for now or implement export for report A
        alert("Exporting comparison reports is complex. Exporting primary report only.");
        reportDataToExport = currentReportData.report_a;
        filename = 'Comparison_Report_A';
    } else {
        filename = reportDataToExport.Header.ReportName || 'Report';
    }

    const flatData = flattenReportData(reportDataToExport);

    // Determine headers from report columns
    const headers = [];
    if (reportDataToExport.Columns && reportDataToExport.Columns.Column) {
        // Label column
        headers.push('Account / Item');

        reportDataToExport.Columns.Column.forEach(col => {
            if (col.ColType === 'Money') {
                headers.push(col.ColTitle || 'Amount');
            }
        });
    }

    if (format === 'excel') {
        // For Excel, we can pass the data array directly if we format it right
        // exportDataToExcel expects array of objects with keys matching headers
        // But our flatData is array of objects { 'Account / Item': ..., 'Total': ... }
        exportDataToExcel(flatData, headers, filename);
    } else if (format === 'pdf') {
        exportDataToPDF(flatData, headers, filename);
    }
}

function flattenReportData(reportData) {
    const rows = [];
    const headers = ['Account / Item'];

    // Extract headers for money columns
    const moneyColIndices = [];
    if (reportData.Columns && reportData.Columns.Column) {
        reportData.Columns.Column.forEach((col, index) => {
            if (col.ColType === 'Money') {
                headers.push(col.ColTitle || 'Amount');
                moneyColIndices.push(index); // Index in ColData array (which starts after label)
            }
        });
    }

    // Recursive function to process rows
    function processRows(reportRows, indentLevel) {
        if (!Array.isArray(reportRows)) reportRows = [reportRows];

        reportRows.forEach(row => {
            let label = "";

            // Section Header
            if (row.type === 'Section' || (row.Header && row.Header.ColData)) {
                label = row.Header && row.Header.ColData && row.Header.ColData.length > 0
                    ? row.Header.ColData[0].value
                    : 'Section';

                // Add Section Header Row (values empty)
                const rowObj = {};
                rowObj['Account / Item'] = "  ".repeat(indentLevel) + label;
                headers.slice(1).forEach(h => rowObj[h] = "");
                rows.push(rowObj);

                if (row.Rows && row.Rows.Row) {
                    processRows(row.Rows.Row, indentLevel + 1);
                }

                // Summary Row
                if (row.Summary && row.Summary.ColData) {
                    processDataRow(row.Summary, indentLevel, true);
                }
            } else if (row.ColData) {
                processDataRow(row, indentLevel, false);
            }
        });
    }

    function processDataRow(row, indentLevel, isSummary) {
        const rowObj = {};
        let label = row.ColData[0].value;
        // if (isSummary) label = "Total " + label; // QBO usually provides the "Total" prefix

        rowObj['Account / Item'] = "  ".repeat(indentLevel) + label;

        // Map values
        // ColData[0] is label. ColData[1..N] are values corresponding to columns.
        // moneyColIndices contains indices of money columns in the report definition.
        // But row.ColData contains ALL columns defined.
        // Assuming simple mapping: ColData[i] corresponds to Column[i-1] in definition?

        // Actually, let's just iterate headers starting at 1
        for (let i = 1; i < row.ColData.length; i++) {
             // Find header name for this index
             // Money columns start at index 1 in ColData
             // In headers array, they start at index 1
             const headerName = headers[i];
             if (headerName) {
                 rowObj[headerName] = row.ColData[i].value;
             }
        }
        rows.push(rowObj);
    }

    if (reportData.Rows && reportData.Rows.Row) {
        processRows(reportData.Rows.Row, 0);
    }

    return rows;
}

// ---------------------------------------------------------
// Saved Reports Logic
// ---------------------------------------------------------

let savedReports = [];

async function fetchSavedReports() {
    try {
        const response = await fetch('/api/reports/saved');
        savedReports = await response.json();

        const select = document.getElementById('savedReports');
        if (!select) return;

        // Clear except first option
        while (select.options.length > 1) {
            select.remove(1);
        }

        savedReports.forEach(report => {
            const option = document.createElement('option');
            option.value = report.id;
            option.textContent = report.name;
            select.appendChild(option);
        });
    } catch (e) {
        console.error('Failed to fetch saved reports', e);
    }
}

function loadSavedReport() {
    const select = document.getElementById('savedReports');
    const reportId = parseInt(select.value);
    if (!reportId) return;

    const report = savedReports.find(r => r.id === reportId);
    if (!report) return;

    // Apply Params
    const params = report.params;

    document.getElementById('reportType').value = report.report_type;

    if (params.start_date_a) document.getElementById('startDateA').value = params.start_date_a;
    if (params.end_date_a) document.getElementById('endDateA').value = params.end_date_a;

    // Handle Compare
    const compareToggle = document.getElementById('compareToggle');
    const compare = params.compare === 'true' || params.compare === true;

    if (compareToggle.checked !== compare) {
        compareToggle.checked = compare;
        // Trigger change event manually to show/hide controls
        compareToggle.dispatchEvent(new Event('change'));
    }

    if (compare) {
        if (params.start_date_b) document.getElementById('startDateB').value = params.start_date_b;
        if (params.end_date_b) document.getElementById('endDateB').value = params.end_date_b;
    }

    if (params.customer) document.getElementById('filterCustomer').value = params.customer;
    else document.getElementById('filterCustomer').value = '';

    if (params.vendor) document.getElementById('filterVendor').value = params.vendor;
    else document.getElementById('filterVendor').value = '';

    // Run Report
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
    const name = document.getElementById('saveViewName').value;
    if (!name) {
        alert('Please enter a name for this view.');
        return;
    }

    const reportType = document.getElementById('reportType').value;
    const compare = document.getElementById('compareToggle').checked;

    const params = {
        start_date_a: document.getElementById('startDateA').value,
        end_date_a: document.getElementById('endDateA').value,
        compare: compare,
        customer: document.getElementById('filterCustomer').value,
        vendor: document.getElementById('filterVendor').value
    };

    if (compare) {
        params.start_date_b = document.getElementById('startDateB').value;
        params.end_date_b = document.getElementById('endDateB').value;
    }

    try {
        const response = await fetch('/api/reports/saved', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                report_type: reportType,
                params: params
            })
        });

        if (response.ok) {
            closeSaveModal();
            fetchSavedReports(); // Refresh list
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
