import frappe
from frappe import _
from erpnext.data.custom_import.base_importer import BaseImport
from frappe.utils import getdate, nowdate, flt, formatdate
from datetime import datetime

class SupplierImport(BaseImport):
    def __init__(self, filename, supplier_name, country=None, supplier_type="Company"):
        super().__init__(filename)
        self.supplier_name = supplier_name
        self.country = country
        self.supplier_type = supplier_type
        self.valid_types = ["Company", "Individual", "Partnership", "Proprietorship"]

    def check_integrity(self):
        self.check_required_value(self.supplier_name, "Supplier Name")
        
        if self.supplier_type and self.supplier_type not in self.valid_types:
            self.errors.append(f"Line {self.line_number}: Invalid supplier type")
            self.valid = False

        if self.country and not frappe.db.exists("Country", self.country):
            self.errors.append(f"Line {self.line_number}: Country does not exist")
            self.valid = False

        # Don't check existence here - let the orchestrator handle it
        return self.valid

    def insert_data(self):
        if not self.valid:
            return None
            
        try:
            doc = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": self.supplier_name,
                "country": self.country,
                "supplier_type": self.supplier_type,
                "supplier_group": frappe.db.get_single_value("Buying Settings", "supplier_group") or "All Supplier Groups"
            })
            doc.insert(ignore_permissions=True)
            return doc.name
        except Exception as e:
            self.errors.append(f"Line {self.line_number}: {str(e)}")
            return None