from erpnext.data.custom_import.data_import import DataImport

from frappe import _

class SupplierImport(DataImport):
    """
    Class to handle importing supplier data
    """
    def __init__(self, filename, supplier_name, country, supplier_type):
        super().__init__(filename)
        self.supplier_name = supplier_name
        self.country = country
        self.supplier_type = supplier_type
        self.additional_data = {}

    def check_type(self):
        """
        Check if supplier type exists in the system
        
        Returns:
            bool: True if valid, False otherwise
        """
        if not self.check_required_value(self.supplier_type, "supplier_name"):
            self.errors.append(f"Line {self.line_number}: Supplier Type is required")
            self.valid = False
            return
            
        supplier_type_exists = frappe.db.exists("Supplier Type", self.supplier_type)
        if not supplier_type_exists:
            self.errors.append(f"Line {self.line_number}: Supplier Type '{self.supplier_type}' does not exist")
            self.valid = False
            pass
        pass