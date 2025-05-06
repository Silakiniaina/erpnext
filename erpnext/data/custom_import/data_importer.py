import csv


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