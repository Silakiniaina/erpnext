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