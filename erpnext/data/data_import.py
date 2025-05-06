import frappe
from frappe import _
import csv
import io
import openpyxl
from erpnext.data.custom_import.supplier_import import SupplierImport

@frappe.whitelist(allow_guest=False)
def import_files(file2_id):
    """
    Handle the import of the supplier file (file2).
    If any row has an error, no data is inserted.
    """
    try:
        # Get the supplier file from file ID
        file_doc = frappe.get_doc("File", file2_id)
        file_content = file_doc.get_content()
        file_name = file_doc.file_name

        # Validate that supplier file exists
        if not file_content:
            frappe.throw(_("Supplier file (file2) is required"))

        # Process supplier file
        results = process_supplier_file(file_content, file_name)

        # Check if any errors exist in results
        has_errors = any(result['status'] == 'error' for result in results)

        if has_errors:
            frappe.response['message'] = {
                'status': 'error',
                'message': 'Import failed due to errors in one or more rows',
                'results': results
            }
        else:
            # Commit all insertions if no errors
            for result in results:
                if result.get('supplier_import'):
                    supplier_id = result['supplier_import'].insert_data()
                    result['supplier_id'] = supplier_id
                    result['status'] = 'success'
                    result['message'] = f"Supplier {result['supplier_name']} created successfully"
            frappe.db.commit()
            frappe.response['message'] = {
                'status': 'success',
                'message': 'Supplier file processed successfully',
                'results': results
            }

        return frappe.response['message']

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"File import error: {str(e)}")
        frappe.response['message'] = {
            'status': 'error',
            'message': f"Error processing files: {str(e)}",
            'results': []
        }
        return frappe.response['message']

def process_supplier_file(file_content, file_name):
    """
    Process the supplier file using SupplierImport class, validating all rows first.
    Uses csv module instead of pandas.
    """
    results = []
    
    try:
        # Read file based on extension
        file_extension = file_name.split('.')[-1].lower()

        if file_extension == 'csv':
            if isinstance(file_content, bytes):
                csv_content = io.StringIO(file_content.decode('utf-8'))
            else:
                csv_content = io.StringIO(file_content)
            csv_reader = csv.DictReader(csv_content)
            rows = list(csv_reader)
        else:
            frappe.throw(_("Unsupported file format. Please use CSV or Excel files"))

        # First pass: Validate all rows
        for index, row in enumerate(rows):
            try:
                # Initialize SupplierImport with row data
                supplier_import = SupplierImport(
                    filename=file_name,
                    supplier_name=str(row.get('supplier_name', '')),
                    country=str(row.get('country', '')),
                    supplier_type=str(row.get('supplier_type', ''))
                )
                
                # Set line number for error reporting
                supplier_import.line_number = index + 2  # Account for header row

                # Validate the data
                supplier_import.validate()

                # Store result
                if supplier_import.valid:
                    results.append({
                        'line': supplier_import.line_number,
                        'status': 'pending',  # Will be updated after insertion
                        'supplier_name': row.get('supplier_name'),
                        'supplier_import': supplier_import,  # Store instance for later insertion
                        'message': 'Validation successful, pending insertion'
                    })
                else:
                    results.append({
                        'line': supplier_import.line_number,
                        'status': 'error',
                        'message': f"Validation failed: {', '.join(supplier_import.errors)}"
                    })

            except Exception as e:
                results.append({
                    'line': index + 2,
                    'status': 'error',
                    'message': f"Error processing row: {str(e)}"
                })

        print(results)

    except Exception as e:
        frappe.db.rollback()
        frappe.throw(_("Error processing supplier file: {0}").format(str(e)))