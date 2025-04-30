/**
 * Main.js - Main functionality for the CCI Calculator frontend
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const formatSelect = document.getElementById('format-select');
    const returnFormatSelect = document.getElementById('return-format');
    const includeDetailsCheckbox = document.getElementById('include-details');
    const submitBtn = document.getElementById('submit-btn');
    
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    const errorDetails = document.getElementById('error-details');
    
    const processingContainer = document.getElementById('processing-container');
    const processingStatus = document.getElementById('processing-status');
    
    const resultsContainer = document.getElementById('results-container');
    const resultsSummary = document.getElementById('results-summary');
    const viewDetailsBtn = document.getElementById('view-details-btn');
    const downloadResultsBtn = document.getElementById('download-results-btn');
    const resultsDetails = document.getElementById('results-details');
    const resultsTableBody = document.getElementById('results-table-body');
    
    // Current result ID
    let currentResultId = null;

    // Auto-detect file format based on file extension
    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        if (!file) return;
        
        const fileName = file.name.toLowerCase();
        if (fileName.endsWith('.csv')) {
            formatSelect.value = 'csv';
        } else if (fileName.endsWith('.xlsx') || fileName.endsWith('.xls')) {
            formatSelect.value = 'excel';
        } else if (fileName.endsWith('.json')) {
            formatSelect.value = 'json';
        }
    });

    // Form submission handler
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Validate file input
        const file = fileInput.files[0];
        if (!file) {
            showError('Please select a file to upload.');
            return;
        }
        
        // Validate file size (10MB max)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            showError(`File size exceeds the maximum limit of 10MB. Your file is ${(file.size / (1024 * 1024)).toFixed(2)}MB.`);
            return;
        }
        
        // Validate file type based on selected format
        const format = formatSelect.value;
        if (format === 'csv' && !file.name.toLowerCase().endsWith('.csv')) {
            showError('Selected format is CSV but the file does not have a .csv extension.');
            return;
        } else if (format === 'excel' && !file.name.toLowerCase().match(/\.(xlsx|xls)$/)) {
            showError('Selected format is Excel but the file does not have a .xlsx or .xls extension.');
            return;
        } else if (format === 'json' && !file.name.toLowerCase().endsWith('.json')) {
            showError('Selected format is JSON but the file does not have a .json extension.');
            return;
        }
        
        // Hide any previous errors and results
        hideError();
        hideResults();
        
        // Show processing status
        showProcessing();
        
        try {
            // Upload file
            const response = await api.uploadFile(file, {
                format: formatSelect.value,
                returnFormat: returnFormatSelect.value,
                includeDetails: includeDetailsCheckbox.checked
            });
            
            // Hide processing status
            hideProcessing();
            
            // Store result ID
            currentResultId = response.result_id;
            
            // Show results summary
            showResultsSummary(response);
            
        } catch (error) {
            hideProcessing();
            showError('Error uploading file', error.message);
        }
    });

    // View details button handler
    viewDetailsBtn.addEventListener('click', async () => {
        if (!currentResultId) return;
        
        try {
            // Toggle details visibility
            if (resultsDetails.classList.contains('d-none')) {
                // Show loading state
                viewDetailsBtn.disabled = true;
                viewDetailsBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
                
                // Fetch results
                const results = await api.getResults(currentResultId);
                
                // Populate results table
                populateResultsTable(results);
                
                // Show details
                resultsDetails.classList.remove('d-none');
                viewDetailsBtn.textContent = 'Hide Detailed Results';
            } else {
                // Hide details
                resultsDetails.classList.add('d-none');
                viewDetailsBtn.textContent = 'View Detailed Results';
            }
        } catch (error) {
            showError('Error fetching results', error.message);
        } finally {
            viewDetailsBtn.disabled = false;
        }
    });

    // Download results button handler
    downloadResultsBtn.addEventListener('click', async () => {
        if (!currentResultId) return;
        
        try {
            // Show loading state
            downloadResultsBtn.disabled = true;
            downloadResultsBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Downloading...';
            
            // Download results
            await api.downloadResults(currentResultId, returnFormatSelect.value);
        } catch (error) {
            showError('Error downloading results', error.message);
        } finally {
            downloadResultsBtn.disabled = false;
            downloadResultsBtn.textContent = 'Download Results';
        }
    });

    // Helper function to show error message
    function showError(message, details = '') {
        errorMessage.textContent = message;
        
        if (details) {
            errorDetails.textContent = details;
            errorDetails.classList.remove('d-none');
        } else {
            errorDetails.classList.add('d-none');
        }
        
        errorContainer.classList.remove('d-none');
    }

    // Helper function to hide error message
    function hideError() {
        errorContainer.classList.add('d-none');
    }

    // Helper function to show processing status
    function showProcessing() {
        processingContainer.classList.remove('d-none');
        submitBtn.disabled = true;
    }

    // Helper function to hide processing status
    function hideProcessing() {
        processingContainer.classList.add('d-none');
        submitBtn.disabled = false;
    }

    // Helper function to hide results
    function hideResults() {
        resultsContainer.classList.add('d-none');
        resultsDetails.classList.add('d-none');
    }

    // Helper function to show results summary
    function showResultsSummary(data) {
        // Create summary HTML
        const summaryHtml = `
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Records Processed:</strong> ${data.records_processed}</p>
                    <p><strong>Records with Errors:</strong> ${data.records_with_errors}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Processing Time:</strong> ${data.processing_time_ms.toFixed(2)} ms</p>
                    <p><strong>Status:</strong> <span class="badge bg-success">Success</span></p>
                </div>
            </div>
            ${data.summary ? `
            <div class="mt-3">
                <h6>Summary Statistics</h6>
                <div class="row">
                    <div class="col-md-4">
                        <p><strong>Average CCI:</strong> ${data.summary.average_cci?.toFixed(2) || 'N/A'}</p>
                    </div>
                    <div class="col-md-4">
                        <p><strong>Median CCI:</strong> ${data.summary.median_cci || 'N/A'}</p>
                    </div>
                    <div class="col-md-4">
                        <p><strong>Max CCI:</strong> ${data.summary.max_cci || 'N/A'}</p>
                    </div>
                </div>
            </div>
            ` : ''}
        `;
        
        // Update summary section
        resultsSummary.innerHTML = summaryHtml;
        
        // Show results container
        resultsContainer.classList.remove('d-none');
        
        // Reset view details button
        viewDetailsBtn.textContent = 'View Detailed Results';
    }

    // Helper function to populate results table
    function populateResultsTable(results) {
        // Clear existing rows
        resultsTableBody.innerHTML = '';
        
        // Check if results exist
        if (!results || !results.results || !Array.isArray(results.results)) {
            resultsTableBody.innerHTML = '<tr><td colspan="4">No results available</td></tr>';
            return;
        }
        
        // Add rows for each result
        results.results.forEach(result => {
            const row = document.createElement('tr');
            
            // Create patient ID cell
            const patientIdCell = document.createElement('td');
            patientIdCell.textContent = result.patient_id || 'N/A';
            row.appendChild(patientIdCell);
            
            // Create age cell
            const ageCell = document.createElement('td');
            ageCell.textContent = result.age || 'N/A';
            row.appendChild(ageCell);
            
            // Create CCI score cell
            const cciCell = document.createElement('td');
            cciCell.textContent = result.cci_score || 'N/A';
            row.appendChild(cciCell);
            
            // Create details cell with button to show conditions
            const detailsCell = document.createElement('td');
            const detailsBtn = document.createElement('button');
            detailsBtn.className = 'btn btn-sm btn-outline-secondary';
            detailsBtn.textContent = 'View Conditions';
            detailsBtn.addEventListener('click', () => {
                showPatientDetails(result);
            });
            detailsCell.appendChild(detailsBtn);
            row.appendChild(detailsCell);
            
            // Add row to table
            resultsTableBody.appendChild(row);
        });
    }

    // Helper function to show patient details in a modal
    function showPatientDetails(patient) {
        // Create modal HTML
        const modalHtml = `
            <div class="modal fade" id="patientDetailsModal" tabindex="-1" aria-labelledby="patientDetailsModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="patientDetailsModalLabel">Patient Details: ${patient.patient_id || 'N/A'}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-3">
                                <div class="col-6">
                                    <p><strong>Age:</strong> ${patient.age || 'N/A'}</p>
                                </div>
                                <div class="col-6">
                                    <p><strong>CCI Score:</strong> ${patient.cci_score || 'N/A'}</p>
                                </div>
                            </div>
                            
                            <h6>Conditions</h6>
                            <ul class="condition-list">
                                ${patient.conditions && typeof patient.conditions === 'object' ? 
                                    Object.entries(patient.conditions)
                                        .map(([condition, value]) => `
                                            <li>
                                                <span class="${value ? 'condition-present' : 'condition-absent'}">
                                                    ${formatConditionName(condition)}: ${value ? 'Yes' : 'No'}
                                                </span>
                                            </li>
                                        `).join('') : 
                                    '<li>No condition data available</li>'
                                }
                            </ul>
                            
                            ${patient.icd_codes && patient.icd_codes.length ? `
                                <h6 class="mt-3">ICD-10 Codes</h6>
                                <div class="icd-codes">
                                    ${patient.icd_codes.map(code => `
                                        <span class="badge bg-secondary me-1 mb-1">${code}</span>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to document
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHtml;
        document.body.appendChild(modalContainer);
        
        // Initialize and show modal
        const modal = new bootstrap.Modal(document.getElementById('patientDetailsModal'));
        modal.show();
        
        // Remove modal from DOM when hidden
        document.getElementById('patientDetailsModal').addEventListener('hidden.bs.modal', function () {
            document.body.removeChild(modalContainer);
        });
    }

    // Helper function to format condition names
    function formatConditionName(condition) {
        return condition
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    // Check API health on page load
    (async function checkApiHealth() {
        try {
            await api.checkHealth();
        } catch (error) {
            showError('API is not available. Please try again later or contact support.');
        }
    })();
});