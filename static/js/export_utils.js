// Export Utilities for CSV, Excel, and PDF
// Dependencies: SheetJS (xlsx), jsPDF, jsPDF-AutoTable

// Get formatted date string for filenames (YYYY-MM-DD)
function getFormattedDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Check if libraries are loaded
function checkLibraries() {
    if (typeof XLSX === 'undefined') {
        alert('SheetJS (XLSX) library is not loaded. Please include it.');
        return false;
    }
    if (typeof jspdf === 'undefined') {
        alert('jsPDF library is not loaded. Please include it.');
        return false;
    }
    return true;
}

// Helper to add professional header to PDF
function addPDFHeader(doc, title) {
    const pageWidth = doc.internal.pageSize.width;

    // Add "VZT Solutions"
    doc.setFontSize(18);
    doc.setFont(undefined, 'bold');
    doc.text('VZT Solutions', pageWidth / 2, 15, { align: 'center' });

    // Add Report Title
    doc.setFontSize(14);
    doc.setFont(undefined, 'normal');
    // Replace underscores with spaces for title and capitalize words
    const formattedTitle = title.replace(/_/g, ' ');
    doc.text(formattedTitle, pageWidth / 2, 25, { align: 'center' });

    // Add Date
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(`Generated on: ${getFormattedDate()}`, pageWidth / 2, 32, { align: 'center' });
    doc.setTextColor(0); // Reset color

    return 40; // Return Y position for table start
}

// Export HTML Table to CSV
function exportTableToCSV(tableSelector, filename) {
    if (!checkLibraries()) return;

    // Handle string selector or element
    let table = tableSelector;
    if (typeof tableSelector === 'string') {
        table = document.querySelector(tableSelector);
    }

    if (!table) {
        alert('Table not found.');
        return;
    }

    const ws = XLSX.utils.table_to_sheet(table);
    const csv = XLSX.utils.sheet_to_csv(ws);

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `${filename}_${getFormattedDate()}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Export HTML Table to Excel
function exportTableToExcel(tableSelector, filename) {
    if (!checkLibraries()) return;

    let table = tableSelector;
    if (typeof tableSelector === 'string') {
        table = document.querySelector(tableSelector);
    }

    if (!table) {
        alert('Table not found.');
        return;
    }

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.table_to_sheet(table);
    XLSX.utils.book_append_sheet(wb, ws, "Sheet1");
    XLSX.writeFile(wb, `${filename}_${getFormattedDate()}.xlsx`);
}

// Export HTML Table to PDF
function exportTableToPDF(tableSelector, filename) {
    if (!checkLibraries()) return;

    // Ensure jsPDF constructor is available
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    // Use autoTable plugin
    if (typeof doc.autoTable === 'undefined') {
        alert('jsPDF-AutoTable plugin is not loaded.');
        return;
    }

    let table = tableSelector;
    if (typeof tableSelector === 'string') {
        table = document.querySelector(tableSelector);
    }

    if (!table) {
        alert('Table not found.');
        return;
    }

    const startY = addPDFHeader(doc, filename);

    doc.autoTable({
        html: table,
        startY: startY,
        theme: 'striped',
        headStyles: { fillColor: [44, 62, 80] }, // Dark blue header
        styles: { fontSize: 8 }
    });
    doc.save(`${filename}_${getFormattedDate()}.pdf`);
}

// Export Data Array to CSV
function exportDataToCSV(data, headers, filename) {
    if (!checkLibraries()) return;

    const ws = XLSX.utils.json_to_sheet(data, { header: headers });
    const csv = XLSX.utils.sheet_to_csv(ws);

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `${filename}_${getFormattedDate()}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Export Data Array to Excel
function exportDataToExcel(data, headers, filename) {
    if (!checkLibraries()) return;

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(data, { header: headers });
    XLSX.utils.book_append_sheet(wb, ws, "Sheet1");
    XLSX.writeFile(wb, `${filename}_${getFormattedDate()}.xlsx`);
}

// Export Data Array to PDF
function exportDataToPDF(data, headers, filename) {
    if (!checkLibraries()) return;

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    if (typeof doc.autoTable === 'undefined') {
        alert('jsPDF-AutoTable plugin is not loaded.');
        return;
    }

    const startY = addPDFHeader(doc, filename);

    // Prepare body data for autoTable
    // Handle case where data items might not have all headers
    const body = data.map(row => headers.map(header => {
        const val = row[header];
        return val === undefined || val === null ? '' : String(val);
    }));

    doc.autoTable({
        head: [headers],
        body: body,
        startY: startY,
        theme: 'striped',
        headStyles: { fillColor: [44, 62, 80] },
        styles: { fontSize: 8 }
    });
    doc.save(`${filename}_${getFormattedDate()}.pdf`);
}
