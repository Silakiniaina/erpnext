frappe.pages['data-import-page'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Data Import',
        single_column: true
    });

    // Create container for file inputs
    let $container = $(`<div class="file-import-container" style="padding: 20px;">
        <div class="file-upload-section" style="margin-bottom: 20px;">
            <h3>Supplier File Upload</h3>
            <input type="file" id="supplier_file" class="file-input" accept=".csv">
        </div>
        <div class="file-upload-section" style="margin-bottom: 20px;">
            <h3>RFQ File Upload</h3>
            <input type="file" id="rfq_file" class="file-input" accept=".csv">
        </div>
        <div class="file-upload-section" style="margin-bottom: 20px;">
            <h3>SQ File Upload</h3>
            <input type="file" id="sq_file" class="file-input" accept=".csv">
        </div>
        <button class="btn btn-primary import-btn">Import Files</button>
        <div class="import-status" style="margin-top: 20px;"></div>
    </div>`).appendTo(page.body);

    // Import button click handler
    $container.find('.import-btn').on('click', function() {
        let supplierFile = $('#supplier_file')[0].files[0];
        let rfqFile = $('#rfq_file')[0].files[0];
        let sqFile = $('#sq_file')[0].files[0];

        // Validate if at least one file is selected
        if (!supplierFile && !rfqFile && !sqFile) {
            frappe.msgprint('Please select at least one file to import.');
            return;
        }

        // Show loading status
        $container.find('.import-status').html(
            `<div class="alert alert-info">
                <i class="fa fa-spinner fa-spin"></i> Processing file import...
            </div>`
        );

        // Use frappe's form file reading method
        Promise.all([
            supplierFile ? readFileAsDataURL(supplierFile) : Promise.resolve(null),
            rfqFile ? readFileAsDataURL(rfqFile) : Promise.resolve(null),
            sqFile ? readFileAsDataURL(sqFile) : Promise.resolve(null)
        ]).then(([supplierContent, rfqContent, sqContent]) => {
            const args = {};
            
            if (supplierContent) {
                args.supplier_file = JSON.stringify({
                    filename: supplierFile.name,
                    dataurl: supplierContent
                });
            }
            
            if (rfqContent) {
                args.rfq_file = JSON.stringify({
                    filename: rfqFile.name,
                    dataurl: rfqContent
                });
            }
            
            if (sqContent) {
                args.sq_file = JSON.stringify({
                    filename: sqFile.name,
                    dataurl: sqContent
                });
            }
            
            frappe.call({
                method: 'erpnext.data.data_import.import_data',
                args: args,
                callback: function(r) {
                    if (r.exc) {
                        handleError(r, $container);
                    } else {
                        handleResponse(r, $container);
                    }
                }
            });
        }).catch(error => {
            $container.find('.import-status').html(
                `<div class="alert alert-danger">Error reading files: ${error.message || 'Unknown error'}</div>`
            );
        });
    });

    // Helper function to read file as data URL
    function readFileAsDataURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = e => resolve(e.target.result);
            reader.onerror = e => reject(new Error('Failed to read file'));
            reader.readAsDataURL(file);
        });
    }

    // Helper function to handle the API response
    function handleResponse(r, $container) {
        const response = r.message || {};
        
        // Check if there are any errors in the error_map
        const hasErrors = response && Object.keys(response).some(key => {
            return Array.isArray(response[key]) && response[key].length > 0;
        });

        if (hasErrors) {
            // Show errors if present
            $container.find('.import-status').html(
                `<div class="alert alert-danger">
                    <strong>Import completed with errors:</strong>
                    <ul>${formatErrors(response)}</ul>
                </div>`
            );
        } else {
            // Show success message if no errors
            $container.find('.import-status').html(
                `<div class="alert alert-success">
                    <i class="fa fa-check-circle"></i> Import completed successfully!
                </div>`
            );
        }
    }

    // Helper function to handle errors
    function handleError(r, $container) {
        let errorMessage = 'An error occurred during import';
        
        try {
            if (r._server_messages) {
                const messages = JSON.parse(r._server_messages);
                if (messages.length > 0) {
                    errorMessage = messages.join('<br>');
                }
            } else if (r.exc) {
                errorMessage = r.exc;
            }
        } catch (e) {
            console.error('Error parsing server messages:', e);
        }
        
        $container.find('.import-status').html(
            `<div class="alert alert-danger">
                ${errorMessage}
            </div>`
        );
    }

    // Helper function to format errors
    function formatErrors(error_map) {
        let html = '';
        for (let key in error_map) {
            if (Array.isArray(error_map[key]) && error_map[key].length > 0) {
                // Convert key to a more readable format
                const displayName = key.replace(/_/g, ' ')
                    .replace(/\b\w/g, l => l.toUpperCase());
                
                html += `<li><strong>${displayName}:</strong><ul>`;
                error_map[key].forEach(err => {
                    html += `<li>${err}</li>`;
                });
                html += `</ul></li>`;
            }
        }
        return html;
    }
};