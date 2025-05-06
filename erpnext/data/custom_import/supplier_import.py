from erpnext.data.custom_import.data_import import DataImport


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