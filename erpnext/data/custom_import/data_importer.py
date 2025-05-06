import csv
from typing import List, Tuple

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
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.supplier_csv_records = list(reader)
            return True
        except Exception as e:
            self.error_map["supplier_import"] = [f"Error loading CSV: {str(e)}"]
            return False
        
    def import_supplier(self) -> Tuple[bool, List[str]]:
        if not self.supplier_csv_records:
            return False, []
        
        created_suppliers = []
        all_errors = []
        
        for idx, record in enumerate(self.supplier_csv_records, 1):
            try:
                # Extract required fields
                supplier_name = record.get('supplier_name', '').strip()
                country = record.get('country', '').strip()
                supplier_type = record.get('supplier_type', '').strip()
                
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
                    all_errors.extend(importer.errors)
            
            except Exception as e:
                all_errors.append(f"Line {idx}: {str(e)}")
        
        if all_errors:
            self.error_map["supplier_import"] = all_errors
            return False, created_suppliers
        
        return True, created_suppliers

    def get_errors(self) -> Dict[str, List[str]]:
        return self.error_map