frappe.pages['data-import-page'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Data Import',
        single_column: true
    });

    // Create container for file inputs
    let $container = $(`<div class="file-import-container" style="padding: 20px;">
        <div class="file-upload-section" style="margin-bottom: 20px;">
            <h3>File 1 Upload</h3>
            <input type="file" id="file1" class="file-input" accept=".csv,.xlsx">
        </div>
        <div class="file-upload-section" style="margin-bottom: 20px;">
            <h3>Supplier File Upload</h3>
            <input type="file" id="file2" class="file-input" accept=".csv,.xlsx">
        </div>
        <div class="file-upload-section" style="margin-bottom: 20px;">
            <h3>File 3 Upload</h3>
            <input type="file" id="file3" class="file-input" accept=".csv,.xlsx">
        </div>
        <button class="btn btn-primary import-btn">Import Files</button>
        <div class="import-status" style="margin-top: 20px;"></div>
    </div>`).appendTo(page.body);

    // Import button click handler
    $container.find('.import-btn').on('click', function() {
        let files = {
            file1: $('#file1')[0].files[0],
            file2: $('#file2')[0].files[0],
            file3: $('#file3')[0].files[0]
        };

        // Validate if supplier file is selected
        if (!files.file2) {
            frappe.msgprint('Please select the supplier file (File 2) before importing.');
            return;
        }

        // Show loading status
        $container.find('.import-status').html('Uploading supplier file...');

        // Use frappe.new_doc to create a new file and attach it
        frappe.model.with_doctype('File', function() {
            var fileDoc = frappe.model.get_new_doc('File');
            
            // Read the file using FileReader
            var reader = new FileReader();
            reader.onload = function(e) {
                fileDoc.file_name = files.file2.name;
                fileDoc.file_size = files.file2.size;
                fileDoc.content = e.target.result.split(',')[1];
                fileDoc.is_private = 1;
                
                // Save the file
                frappe.db.insert(fileDoc).then(function(doc) {
                    if (doc && doc.name) {
                        const file_id = doc.name;
                    
                    // Call the backend import_files function with the file ID
                    $container.find('.import-status').html('Processing supplier file...');
                    
                    // Call the method directly using frappe.call
                    frappe.call({
                        method: 'erpnext.data.data_import.import_files',
                        args: {
                            file2_id: file_id
                        },
                        freeze: true,
                        freeze_message: 'Processing file import...',
                        callback: function(r) {
                            if (r.message) {
                                let status_html = '';
                                if (r.message.status === 'success') {
                                    status_html = `<div class="alert alert-success">
                                        ${r.message.message}
                                        <ul>
                                            ${r.message.results.map(result => `<li>Line ${result.line}: ${result.message}</li>`).join('')}
                                        </ul>
                                    </div>`;
                                } else {
                                    status_html = `<div class="alert alert-danger">
                                        ${r.message.message}
                                        <ul>
                                            ${r.message.results.map(result => `<li>Line ${result.line}: ${result.message}</li>`).join('')}
                                        </ul>
                                    </div>`;
                                }
                                $container.find('.import-status').html(status_html);
                            }
                        }
                    });
                    } else {
                        $container.find('.import-status').html(
                            `<div class="alert alert-danger">Error uploading supplier file: No file ID returned</div>`
                        );
                    }
                }).catch(function(error) {
                    $container.find('.import-status').html(
                        `<div class="alert alert-danger">Error uploading supplier file: ${error.message || 'Unknown error'}</div>`
                    );
                });
            };
            
            // Read the file as data URL
            reader.readAsDataURL(files.file2);
        });
    });
};