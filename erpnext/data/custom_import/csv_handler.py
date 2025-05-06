import base64
import os
import csv
import frappe
from frappe.utils.file_manager import save_file

class CSVHandler:
    @staticmethod
    def save_uploaded_file(file_data):
        """Save uploaded file and return file path"""
        try:
            file_content = base64.b64decode(file_data['dataurl'].split(",")[1])
            file_doc = save_file(
                fname=file_data['filename'],
                content=file_content,
                is_private=1,
                dt=None,
                dn=None
            )
            return file_doc.file_url
        except Exception as e:
            raise Exception(f"File save failed: {str(e)}")

    @staticmethod
    def load_csv_records(file_path):
        """Load records from CSV file"""
        try:
            site_path = frappe.get_site_path()
            full_path = os.path.join(site_path, file_path.lstrip('/'))
            
            with open(full_path, 'r', encoding='utf-8') as f:
                return list(csv.DictReader(f))
        except Exception as e:
            raise Exception(f"CSV load failed: {str(e)}")

    @staticmethod
    def cleanup_file(file_path):
        """Delete temporary file"""
        if file_path and frappe.db.exists("File", {"file_url": file_path}):
            frappe.delete_doc("File", {"file_url": file_path})