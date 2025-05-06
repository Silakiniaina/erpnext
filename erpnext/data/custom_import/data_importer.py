import json
import os
import frappe
from frappe import _
import csv
from typing import Dict, List, Tuple

from erpnext.data.custom_import.supplier_import import SupplierImport


class DataImporter:
    """
    Class for handling imports of various data types from CSV files
    """
    def __init__(self):
        self.supplier_csv_records = []
        self.rfq_csv_records = []
        self.sq_csv_records = []
        self.error_map = {}
        self.supplier_file_name = None
        self.rfq_file_name = None
        self.sq_file_name = None

    def load_supplier_csv(self, file_path: str) -> bool:
        self.supplier_file_name = file_path
        
        site_path = frappe.get_site_path()
        full_file_path = os.path.join(site_path, file_path.lstrip("/"))
        
        if not os.path.exists(full_file_path):
            error_msg = f"File not found at: {full_file_path}"
            self.error_map["supplier_import"] = [error_msg]
            return False
        
        if not os.access(full_file_path, os.R_OK):
            error_msg = f"No read permissions for file: {full_file_path}"
            self.error_map["supplier_import"] = [error_msg]
            return False
        
        try:
            with open(full_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.supplier_csv_records = list(reader)
                self.error_map.pop("supplier_import", None)
                return True
        except Exception as e:
            self.error_map["supplier_import"] = [f"Error loading CSV: {str(e)}"]
            return False

    def import_supplier(self) -> Tuple[bool, List[str]]:
        if not self.supplier_csv_records:
            return False, []
        
        created_suppliers = []
        all_errors = []
        
        # Remove this line - frappe.db.begin()
        
        try:
            for idx, record in enumerate(self.supplier_csv_records, 1):
                try:
                    supplier_name = record.get('supplier_name', '').strip()
                    country = record.get('country', '').strip()
                    supplier_type = record.get('type', record.get('supplier_type', '')).strip()
                    
                    importer = SupplierImport(
                        filename=self.supplier_file_name,
                        supplier_name=supplier_name,
                        country=country,
                        supplier_type=supplier_type
                    )
                    
                    importer.line_number = idx
                    importer.validate()
                    
                    if importer.valid:
                        supplier_name = importer.insert_data()
                        if supplier_name:
                            created_suppliers.append(supplier_name)
                        else:
                            all_errors.append(f"Line {idx}: Failed to create supplier (insert_data returned None)")
                    else:
                        all_errors.extend([f"{error}" for error in importer.errors])
                
                except Exception as e:
                    all_errors.append(str(e))
            
            if all_errors:
                self.error_map["supplier_import"] = all_errors
                frappe.db.rollback()
                return False, created_suppliers
            else:
                # Let the outer transaction handle the commit
                return True, created_suppliers
        
        except Exception as e:
            frappe.db.rollback()
            self.error_map["supplier_import"] = [f"Unexpected error: {str(e)}"]
            return False, created_suppliers
        
    def get_errors(self) -> Dict[str, List[str]]:
        return self.error_map
