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

# ---------------------------------------------------------------------------- #
#                                Integrity check                               #
# ---------------------------------------------------------------------------- #
    def check_type(self):
        """
        Check if supplier type exists in the system
        """
        if self.supplier_type :   
            supplier_type_exists = frappe.db.exists("Supplier Type", self.supplier_type)
            if not supplier_type_exists:
                self.errors.append(f"Line {self.line_number}: Supplier Type '{self.supplier_type}' does not exist")
                self.valid = False

    def check_country(self):
        """
        Check if country exists in the system
        """
        if self.country :
            country_exists = frappe.db.exists("Country", self.country)
            if not country_exists:
                self.errors.append(f"Line {self.line_number}: Country '{self.country}' does not exist")
                self.valid = False

    def check_supplier(self):
        """
        Check if supplier exists in the system
        """
        if self.supplier_name and frappe.db.exists("Supplier", {"supplier_name": self.supplier_name}):
            self.errors.append(f"Line {self.line_number}: Supplier '{self.supplier_name}' already exists")
            is_valid = False

# ---------------------------------------------------------------------------- #
#                                   Override                                   #
# ---------------------------------------------------------------------------- #
    def check_integrity(self):
        """
        Check integrity of supplier data
        """
        self.check_required_value(self.supplier_name, "supplier_name")
        self.check_required_value(self.country, "country")
        self.check_required_value(self.supplier_type, "type")

        self.check_type()
        self.check_country()
        self.check_supplier()

# ---------------------------------------------------------------------------- #
#                                Data generation                               #
# ---------------------------------------------------------------------------- #
    def generate_additional_data(self):
        """
        Generate additional data needed for creating a supplier
        """
        # Generate a unique supplier ID if needed
        supplier_id = f"SUPP-{frappe.utils.now_datetime().strftime('%Y%m%d')}-{frappe.utils.random_string(5)}"
        
        # Set default values for other required fields
        self.additional_data = {
            "supplier_group": frappe.db.get_single_value("Buying Settings", "supplier_group") or "All Supplier Groups",
            "supplier_id": supplier_id,
            "is_internal_supplier": 0,
            "represents_company": "",
            "tax_id": "",
            "default_currency": frappe.db.get_default("Currency"),
            "default_price_list": "",
            "payment_terms": "",
            "doctype": "Supplier"
        }