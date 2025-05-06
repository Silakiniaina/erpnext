from erpnext.data.custom_import.data_importer import DataImporter
import frappe
from frappe import _
from frappe.utils.file_manager import save_file
from typing import Dict, List, Optional, Union, Any
import json
import base64
import re

def get_base64_content(dataurl: str) -> bytes:
    match = re.match(r"data:.*?;base64,(.*)", dataurl)
    if not match:
        raise ValueError("Invalid dataurl format")
    return base64.b64decode(match.group(1))

@frappe.whitelist(allow_guest=False)
def import_data(supplier_file: Union[Dict[str, Any], str, None] = None, 
                rfq_file: Union[Dict[str, Any], str, None] = None, 
                sq_file: Union[Dict[str, Any], str, None] = None) -> Dict[str, List[str]]:
    current_user = frappe.get_doc("User", frappe.session.user)
    data_importer = DataImporter()
    file_paths = {}
    error_map = {}

    def parse_arg(arg):
        if isinstance(arg, str):
            try:
                return json.loads(arg)
            except json.JSONDecodeError:
                return None
        return arg

    supplier_file = parse_arg(supplier_file)
    rfq_file = parse_arg(rfq_file)
    sq_file = parse_arg(sq_file)

    try:
        frappe.db.begin()
        if supplier_file:
            if not isinstance(supplier_file, dict) or 'filename' not in supplier_file or 'dataurl' not in supplier_file:
                error_map.setdefault('supplier_file', []).append("Invalid supplier file data. Expected a dictionary with 'filename' and 'dataurl' keys.")
            else:
                try:
                    file_content = get_base64_content(supplier_file['dataurl'])
                    supplier_file_doc = save_file(
                        fname=supplier_file['filename'],
                        content=file_content,
                        dt=None,
                        dn=None,
                        decode=False,
                        is_private=1
                    )
                    file_paths['supplier_file'] = supplier_file_doc.file_url
                except Exception as e:
                    error_map.setdefault('supplier_file', []).append(f"Error processing supplier file: {str(e)}")

        if rfq_file:
            if not isinstance(rfq_file, dict) or 'filename' not in rfq_file or 'dataurl' not in rfq_file:
                error_map.setdefault('rfq_file', []).append("Invalid RFQ file data. Expected a dictionary with 'filename' and 'dataurl' keys.")
            else:
                try:
                    file_content = get_base64_content(rfq_file['dataurl'])
                    rfq_file_doc = save_file(
                        fname=rfq_file['filename'],
                        content=file_content,
                        dt=None,
                        dn=None,
                        decode=False,
                        is_private=1
                    )
                    file_paths['rfq_file'] = rfq_file_doc.file_url
                except Exception as e:
                    error_map.setdefault('rfq_file', []).append(f"Error processing RFQ file: {str(e)}")

        if sq_file:
            if not isinstance(sq_file, dict) or 'filename' not in sq_file or 'dataurl' not in sq_file:
                error_map.setdefault('sq_file', []).append("Invalid SQ file data. Expected a dictionary with 'filename' and 'dataurl' keys.")
            else:
                try:
                    file_content = get_base64_content(sq_file['dataurl'])
                    sq_file_doc = save_file(
                        fname=sq_file['filename'],
                        content=file_content,
                        dt=None,
                        dn=None,
                        decode=False,
                        is_private=1
                    )
                    file_paths['sq_file'] = sq_file_doc.file_url
                except Exception as e:
                    error_map.setdefault('sq_file', []).append(f"Error processing SQ file: {str(e)}")

        if 'supplier_file' in file_paths and not error_map:
            try:
                if data_importer.load_supplier_csv(file_paths['supplier_file']):
                    success, created_suppliers = data_importer.import_supplier()
                    if data_importer.get_errors().get('supplier_import'):
                        error_map['supplier_file'] = data_importer.get_errors()['supplier_import']
                        frappe.log(error_map['supplier_file'])
            except Exception as e:
                error_map.setdefault('supplier_file', []).append(f"Error importing supplier data: {str(e)}")

    finally:
        for file_path in file_paths.values():
            if file_path:
                try:
                    frappe.delete_doc("File", file_path, ignore_permissions=True)
                except Exception as e:
                    frappe.log_error(f"Error deleting file {file_path}: {str(e)}")
    return error_map
