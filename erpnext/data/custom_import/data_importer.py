import json
import os
from erpnext.data.custom_import.rfq_importer import RFQImport
from erpnext.data.custom_import.sq_importer import SQImport
import frappe
from frappe import _
import csv
from typing import Dict, List, Tuple
from erpnext.data.custom_import.supplier_importer import SupplierImport

class DataImporter:
    def __init__(self):
        self.supplier_csv_records = []
        self.rfq_csv_records = []
        self.sq_csv_records = []
        self.error_map = {}
        self.created_docs = {
            'suppliers': [],
            'rfqs': [],
            'sqs': []
        }
        self._pending_rfq_refs = set()
        self._init_logging()

    def _init_logging(self):
        """Initialize logging counters"""
        self._log_counts = {
            'suppliers_processed': 0,
            'rfqs_processed': 0,
            'sqs_processed': 0,
            'suppliers_created': 0,
            'rfqs_created': 0,
            'sqs_created': 0
        }

    def _log_step(self, message):
        """Log a processing step"""
        frappe.log(message)
        print(f"LOG: {message}")

    def _rfq_exists(self, ref):
        """Check if RFQ exists in DB or in pending imports"""
        str_ref = str(ref)
        exists_in_db = frappe.db.exists("Request for Quotation", str_ref)
        exists_in_pending = str_ref in self._pending_rfq_refs
        self._log_step(f"Checking RFQ {str_ref} - DB: {exists_in_db}, Pending: {exists_in_pending}")
        return exists_in_db or exists_in_pending

    def import_all(self, supplier_file=None, rfq_file=None, sq_file=None):
        """Master import with proper reference tracking"""
        self._log_step("=== Starting import process ===")
        try:
            frappe.db.begin()
            self._reset_import_state()
            
            # 1. Import suppliers
            if supplier_file:
                self._log_step("Starting supplier import")
                if not self._safe_import_step('supplier', supplier_file, self.import_suppliers):
                    return self._handle_failure()
                self._log_step(f"Supplier import complete. Created: {self._log_counts['suppliers_created']}")
            
            # 2. Import RFQs
            if rfq_file:
                self._log_step("Starting RFQ import")
                if not self._safe_import_step('rfq', rfq_file, self.import_rfqs):
                    return self._handle_failure()
                self._log_step(f"RFQ import complete. Created: {self._log_counts['rfqs_created']}")
                self._log_step(f"Pending RFQ refs: {self._pending_rfq_refs}")
            
            # 3. Import SQs
            if sq_file:
                self._log_step("Starting SQ import")
                if not self._safe_import_step('sq', sq_file, self.import_sqs):
                    return self._handle_failure()
                self._log_step(f"SQ import complete. Created: {self._log_counts['sqs_created']}")
            
            if not self.error_map:
                frappe.db.commit()
                self._log_step("=== Import completed successfully ===")
                return {
                    'success': True,
                    'created': self._get_created_docs_summary(),
                    'stats': self._log_counts
                }
            
            return self._handle_failure()
            
        except Exception as e:
            frappe.db.rollback()
            self.error_map['transaction_error'] = str(e)
            self._log_step(f"!!! Import failed with error: {str(e)}")
            return self._handle_failure()

    def load_csv(self, doc_type, file_path):
        """Generic CSV loader with logging"""
        self._log_step(f"Loading {doc_type} CSV from {file_path}")
        try:
            site_path = frappe.get_site_path()
            full_path = os.path.join(site_path, file_path.lstrip('/'))
            
            if not os.path.exists(full_path):
                error_msg = f"File not found: {full_path}"
                self.error_map[f"{doc_type}_import"] = [error_msg]
                self._log_step(f"!!! {error_msg}")
                return False
                
            with open(full_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)
                
                if doc_type == 'supplier':
                    self.supplier_csv_records = records
                elif doc_type == 'rfq':
                    self.rfq_csv_records = records
                elif doc_type == 'sq':
                    self.sq_csv_records = records
                
                self._log_step(f"Loaded {len(records)} {doc_type} records")
                return True
                
        except Exception as e:
            error_msg = f"Error loading {doc_type} CSV: {str(e)}"
            self.error_map[f"{doc_type}_import"] = [error_msg]
            self._log_step(f"!!! {error_msg}")
            return False

    def import_suppliers(self):
        """Import suppliers with detailed logging"""
        self._log_step(f"Processing {len(self.supplier_csv_records)} supplier records")
        for record in self.supplier_csv_records:
            self._log_counts['suppliers_processed'] += 1
            try:
                supplier_name = record['supplier_name']
                if not frappe.db.exists("Supplier", supplier_name):
                    supplier = frappe.get_doc({
                        "doctype": "Supplier",
                        "supplier_name": supplier_name,
                        "country": record.get('country'),
                        "supplier_type": record.get('supplier_type', 'Company')
                    }).insert()
                    self.created_docs['suppliers'].append(supplier.name)
                    self._log_counts['suppliers_created'] += 1
                    self._log_step(f"Created supplier: {supplier_name}")
                else:
                    self._log_step(f"Supplier exists, skipping: {supplier_name}")
            except Exception as e:
                self._log_step(f"!!! Error creating supplier: {str(e)}")
                self._log_error('supplier', record, e)

    def import_rfqs(self):
        """Import RFQs with detailed logging"""
        self._log_step(f"Processing {len(self.rfq_csv_records)} RFQ records")
        for idx, record in enumerate(self.rfq_csv_records, 1):
            self._log_counts['rfqs_processed'] += 1
            try:
                ref = str(record['ref'])
                self._log_step(f"Processing RFQ line {idx} with ref: {ref}")
                
                rfq = RFQImport(
                    filename="RFQ Import",
                    date=record['date'],
                    item_name=record['item_name'],
                    item_group=record['item_group'],
                    required_by=record['required_by'],
                    quantity=record['quantity'],
                    purpose=record['purpose'],
                    target_warehouse=record['target_warehouse'],
                    ref=ref
                )
                rfq.line_number = idx
                
                if rfq.validate():
                    rfq_name = rfq.insert_data()
                    if rfq_name:
                        self.created_docs['rfqs'].append(rfq_name)
                        self._pending_rfq_refs.add(ref)
                        self._log_counts['rfqs_created'] += 1
                        self._log_step(f"Created RFQ: {rfq_name} (ref: {ref})")
                    else:
                        self._log_step(f"RFQ creation failed for ref: {ref}")
                else:
                    self._log_step(f"RFQ validation failed for ref: {ref}")
            except Exception as e:
                self._log_step(f"!!! Error processing RFQ line {idx}: {str(e)}")
                self._log_error('rfq', record, str(e))

    def import_sqs(self):
        """Import SQs with detailed logging"""
        self._log_step(f"Processing {len(self.sq_csv_records)} SQ records")
        self._log_step(f"Current pending RFQ refs: {self._pending_rfq_refs}")
        
        for idx, record in enumerate(self.sq_csv_records, 1):
            self._log_counts['sqs_processed'] += 1
            try:
                rfq_ref = str(record['ref_request_quotation'])
                supplier = record['supplier']
                self._log_step(f"Processing SQ line {idx} (RFQ: {rfq_ref}, Supplier: {supplier})")
                
                # Debug RFQ reference check
                db_exists = frappe.db.exists("Request for Quotation", rfq_ref)
                pending_exists = rfq_ref in self._pending_rfq_refs
                self._log_step(f"RFQ check - DB: {db_exists}, Pending: {pending_exists}")
                
                sq = SQImport(
                    filename="SQ Import",
                    rfq_name=rfq_ref,
                    supplier=supplier,
                    pending_rfq_refs=self._pending_rfq_refs
                )
                sq.line_number = idx
                
                if sq.validate():
                    sq_name = sq.insert_data()
                    if sq_name:
                        self.created_docs['sqs'].append(sq_name)
                        self._log_counts['sqs_created'] += 1
                        self._log_step(f"Created SQ: {sq_name}")
                    else:
                        self._log_step(f"SQ creation failed for RFQ: {rfq_ref}")
                else:
                    self._log_step(f"SQ validation failed for RFQ: {rfq_ref}")
            except Exception as e:
                self._log_step(f"!!! Error processing SQ line {idx}: {str(e)}")
                self._log_error('sq', record, str(e))

    # ... [keep all other existing methods unchanged] ...

    def _log_error(self, doc_type, record, error):
        """Standard error logging"""
        line_num = (self.supplier_csv_records if doc_type == 'supplier' else 
                   self.rfq_csv_records if doc_type == 'rfq' else 
                   self.sq_csv_records).index(record) + 1
                   
        err_msg = f"Line {line_num}: {str(error)}"
        self.error_map.setdefault(f"{doc_type}_import", []).append(err_msg)
        frappe.log_error(f"{doc_type.title()} Import Error", err_msg)

    def _reset_import_state(self):
        """Reset all tracking variables"""
        self.error_map = {}
        self.created_docs = {'suppliers': [], 'rfqs': [], 'sqs': []}
        self._pending_rfq_refs = set()

    def _safe_import_step(self, type, file, import_func):
        """Safe wrapper for each import step"""
        if not self.load_csv(type, file):
            return False
        import_func()
        return not bool(self.error_map)

    def _handle_failure(self):
        frappe.db.rollback()
        return {
            'success': False,
            'errors': self.error_map,
            'created': {}  # Nothing persisted due to rollback
        }

    def _get_created_docs_summary(self):
        """Get just the names of created docs for response"""
        return {
            'suppliers': [name for name in self.created_docs['suppliers']],
            'rfqs': [name for name in self.created_docs['rfqs']],
            'sqs': [name for name in self.created_docs['sqs']]
        }

    def get_errors(self):
        return self.error_map