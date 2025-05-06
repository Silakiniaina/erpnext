from .csv_handler import CSVHandler
from erpnext.data.custom_import.supplier_importer import SupplierImport
from erpnext.data.custom_import.rfq_importer import RFQImport
from erpnext.data.custom_import.sq_importer import SQImport
import frappe

class ImportOrchestrator:
    def __init__(self):
        self.error_map = {}
        self.created_docs = {
            'suppliers': [],
            'rfqs': [],
            'sqs': []
        }
        self._pending_suppliers = set()  # Track created suppliers
        self._pending_rfq_refs = set()   # Track created RFQs
        self._rfq_ref_to_name = {}       # NEW: Track mapping of ref to actual name
        self._log_counts = {
            'suppliers_processed': 0,
            'rfqs_processed': 0,
            'sqs_processed': 0,
            'suppliers_created': 0,
            'rfqs_created': 0,
            'sqs_created': 0
        }

    def _log_step(self, message):
        frappe.log(message)
        print(f"LOG: {message}")

    def _supplier_exists(self, supplier_name):
        """Check if supplier exists in DB or pending imports"""
        return (frappe.db.exists("Supplier", supplier_name) or
                supplier_name in self._pending_suppliers)

    def process_all(self, supplier_file=None, rfq_file=None, sq_file=None):
        self._log_step("=== Starting import process ===")
        
        try:
            # 1. Process Suppliers
            if supplier_file:
                self._log_step("Starting supplier import")
                self.process_file('supplier', supplier_file, self.process_supplier)
                self._log_step(f"Supplier import complete. Created: {self._log_counts['suppliers_created']}")
                self._log_step(f"Pending suppliers: {self._pending_suppliers}")
            
            # 2. Process RFQs if no supplier errors
            if rfq_file and 'supplier_file' not in self.error_map:
                self._log_step("Starting RFQ import")
                self.process_file('rfq', rfq_file, self.process_rfq)
                self._log_step(f"RFQ import complete. Created: {self._log_counts['rfqs_created']}")
                self._log_step(f"Pending RFQ refs: {self._pending_rfq_refs}")
            
            # 3. Process SQs if no previous errors
            if sq_file and not any(k in self.error_map for k in ['supplier_file', 'rfq_file']):
                self._log_step("Starting SQ import")
                self.process_file('sq', sq_file, self.process_sq)
                self._log_step(f"SQ import complete. Created: {self._log_counts['sqs_created']}")
            
            return {
                'errors': self.error_map,
                'created': self.created_docs
            }
            
        except Exception as e:
            self._log_step(f"!!! Import failed: {str(e)}")
            self.error_map['system'] = [str(e)]
            return {
                'errors': self.error_map,
                'created': self.created_docs
            }

    def process_file(self, file_type, file_data, processor):
        try:
            file_path = CSVHandler.save_uploaded_file(file_data)
            records = CSVHandler.load_csv_records(file_path)
            self._log_step(f"Processing {len(records)} {file_type} records")
            
            for idx, record in enumerate(records, 1):
                processor(record, idx)
                
            CSVHandler.cleanup_file(file_path)
        except Exception as e:
            self._log_step(f"!!! Error processing {file_type} file: {str(e)}")
            self.error_map[f"{file_type}_file"] = [str(e)]

    def process_supplier(self, record, line_num):
        self._log_counts['suppliers_processed'] += 1
        try:
            supplier_name = record['supplier_name']
            self._log_step(f"Processing supplier line {line_num}: {supplier_name}")
            
            if not self._supplier_exists(supplier_name):
                importer = SupplierImport(
                    filename="Supplier Import",
                    supplier_name=supplier_name,
                    country=record.get('country'),
                    supplier_type=record.get('supplier_type', 'Company')
                )
                importer.line_number = line_num
                
                if importer.validate():
                    docname = importer.insert_data()
                    if docname:
                        self.created_docs['suppliers'].append(docname)
                        self._pending_suppliers.add(supplier_name)
                        self._log_counts['suppliers_created'] += 1
                        self._log_step(f"Created supplier: {supplier_name}")
                self.collect_errors('supplier', importer.errors)
            else:
                self._log_step(f"Supplier exists, skipping: {supplier_name}")
                
        except Exception as e:
            error_msg = f"Line {line_num}: {str(e)}"
            self._log_step(f"!!! {error_msg}")
            self.error_map.setdefault('supplier_file', []).append(error_msg)

    def process_rfq(self, record, line_num):
        self._log_counts['rfqs_processed'] += 1
        try:
            ref = str(record['ref'])
            self._log_step(f"Processing RFQ line {line_num} with ref: {ref}")
            
            importer = RFQImport(
                filename="RFQ Import",
                date=record['date'],
                item_name=record['item_name'],
                item_group=record['item_group'],
                required_by=record['required_by'],
                quantity=record['quantity'],
                purpose=record['purpose'],
                target_warehouse=record['target_warehouse'],
                ref=ref,
                pending_suppliers=self._pending_suppliers  # Pass the suppliers list
            )
            importer.line_number = line_num
            
            if importer.validate():
                docname = importer.insert_data()
                if docname:
                    self.created_docs['rfqs'].append(docname)
                    self._pending_rfq_refs.add(ref)
                    # Store the mapping between reference and actual document name
                    self._rfq_ref_to_name[ref] = docname
                    self._log_counts['rfqs_created'] += 1
                    self._log_step(f"Created RFQ: {docname} (ref: {ref})")
                    self._log_step(f"Added mapping: ref {ref} -> doc {docname}")
            self.collect_errors('rfq', importer.errors)
            
        except Exception as e:
            error_msg = f"Line {line_num}: {str(e)}"
            self._log_step(f"!!! {error_msg}")
            self.error_map.setdefault('rfq_file', []).append(error_msg)

    def process_sq(self, record, line_num):
        self._log_counts['sqs_processed'] += 1
        try:
            rfq_ref = str(record['ref_request_quotation'])
            supplier = record['supplier']
            self._log_step(f"Processing SQ line {line_num} (RFQ: {rfq_ref}, Supplier: {supplier})")
            
            # Get the actual RFQ document name if we have a mapping
            rfq_name = self._rfq_ref_to_name.get(rfq_ref, rfq_ref)
            self._log_step(f"Using RFQ name: {rfq_name} (from ref: {rfq_ref})")
            
            # Check both DB and pending references
            rfq_exists = False
            if frappe.db.exists("Request for Quotation", rfq_name):
                rfq_exists = True
            elif rfq_ref in self._pending_rfq_refs:
                rfq_exists = True
            
            supplier_exists = self._supplier_exists(supplier)
            
            self._log_step(f"Checks - RFQ: {rfq_exists}, Supplier: {supplier_exists}")
            
            if not rfq_exists:
                raise Exception(f"RFQ {rfq_ref} not found")
            if not supplier_exists:
                raise Exception(f"Supplier {supplier} not found")
            
            importer = SQImport(
                filename="SQ Import",
                rfq_name=rfq_name,  # Use the actual document name if available
                supplier=supplier,
                pending_rfq_refs=self._pending_rfq_refs,
                pending_suppliers=self._pending_suppliers,  # Pass the suppliers list
                rfq_ref_to_name=self._rfq_ref_to_name  # Pass the reference mapping
            )
            importer.line_number = line_num
            
            if importer.validate():
                docname = importer.insert_data()
                if docname:
                    self.created_docs['sqs'].append(docname)
                    self._log_counts['sqs_created'] += 1
                    self._log_step(f"Created SQ: {docname}")
            self.collect_errors('sq', importer.errors)
            
        except Exception as e:
            error_msg = f"Line {line_num}: {str(e)}"
            self._log_step(f"!!! {error_msg}")
            self.error_map.setdefault('sq_file', []).append(error_msg)

    def collect_errors(self, file_type, errors):
        if errors:
            self.error_map.setdefault(f"{file_type}_file", []).extend(errors)