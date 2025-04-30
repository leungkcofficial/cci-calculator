/**
 * API.js - Handles all API interactions for the CCI Calculator
 */

class CCIApi {
    constructor() {
        this.baseUrl = '/api/v1';
    }

    /**
     * Upload a file to the predict endpoint
     * @param {File} file - The file to upload
     * @param {Object} options - Upload options
     * @returns {Promise} - Promise resolving to the API response
     */
    async uploadFile(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('format', options.format || 'csv');
        formData.append('return_format', options.returnFormat || 'json');
        formData.append('include_details', options.includeDetails !== false);

        try {
            const response = await fetch(`${this.baseUrl}/predict`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Error uploading file');
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    /**
     * Get results by ID
     * @param {string} resultId - The ID of the result to fetch
     * @param {Object} options - Options for fetching results
     * @returns {Promise} - Promise resolving to the results
     */
    async getResults(resultId, options = {}) {
        const params = new URLSearchParams({
            format: options.format || 'json',
            include_errors: options.includeErrors || false
        });

        try {
            const response = await fetch(`${this.baseUrl}/results/${resultId}?${params}`);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Error fetching results');
            }

            // If format is CSV, return the blob for download
            if (options.format === 'csv') {
                return await response.blob();
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    /**
     * Download results as a file
     * @param {string} resultId - The ID of the result to download
     * @param {string} format - The format to download (csv or json)
     */
    async downloadResults(resultId, format = 'csv') {
        try {
            let data;
            let filename;
            let mimeType;

            if (format === 'csv') {
                // Get CSV blob
                data = await this.getResults(resultId, { format: 'csv' });
                filename = `cci_results_${resultId}.csv`;
                mimeType = 'text/csv';
            } else {
                // Get JSON and convert to blob
                const jsonData = await this.getResults(resultId);
                data = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
                filename = `cci_results_${resultId}.json`;
                mimeType = 'application/json';
            }

            // Create download link
            const url = window.URL.createObjectURL(data);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Download Error:', error);
            throw error;
        }
    }

    /**
     * Check API health
     * @returns {Promise} - Promise resolving to the health status
     */
    async checkHealth() {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            
            if (!response.ok) {
                throw new Error('API health check failed');
            }

            return await response.json();
        } catch (error) {
            console.error('Health Check Error:', error);
            throw error;
        }
    }

    /**
     * Get API information
     * @returns {Promise} - Promise resolving to the API info
     */
    async getApiInfo() {
        try {
            const response = await fetch(`${this.baseUrl}/info`);
            
            if (!response.ok) {
                throw new Error('Failed to get API info');
            }

            return await response.json();
        } catch (error) {
            console.error('API Info Error:', error);
            throw error;
        }
    }
}

// Create and export a singleton instance
const api = new CCIApi();