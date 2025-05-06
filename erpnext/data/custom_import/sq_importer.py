import frappe
from frappe import _
from erpnext.data.custom_import.base_importer import BaseImport
from frappe.utils import getdate, nowdate, flt, formatdate, today
from datetime import datetime

class SQImport(BaseImport):
    def __init__(self, filename, rfq_name, supplier, pending_rfq_refs=None, pending_suppliers=None, rfq_docs=None, rfq_ref_to_name=None):
        super().__init__(filename)
        self.rfq_name = str(rfq_name)
        self.supplier = supplier
        self.pending_rfq_refs = pending_rfq_refs or set()
        self.pending_suppliers = pending_suppliers or set()
        self.rfq_docs = rfq_docs or {}  # Store uncommitted RFQ docs
        self.rfq_ref_to_name = rfq_ref_to_name or {}  # Map references to actual names
        self.created_sq = None
        self.actual_rfq_name = None  # Will store the actual RFQ document name if found

    def check_integrity(self):
        self.check_required_value(self.rfq_name, "RFQ Reference")
        self.check_required_value(self.supplier, "Supplier")
        
        if self.valid:
            # First check if we have a mapping for this reference
            if self.rfq_name in self.rfq_ref_to_name:
                self.actual_rfq_name = self.rfq_ref_to_name[self.rfq_name]
                self.log(f"Found RFQ mapping: {self.rfq_name} -> {self.actual_rfq_name}")
            
            # Check if RFQ exists by reference or actual name
            rfq_exists = self.validate_rfq_exists()
            
            if not rfq_exists:
                self.errors.append(f"Line {self.line_number}: RFQ {self.rfq_name} not found")
                self.valid = False
            
            # Check supplier exists in either database or pending suppliers
            supplier_exists = (frappe.db.exists("Supplier", self.supplier) or 
                              self.supplier in self.pending_suppliers)
            
            if not supplier_exists:
                self.errors.append(f"Line {self.line_number}: Supplier {self.supplier} not found")
                self.valid = False
                
            self.log(f"Integrity check - RFQ exists: {rfq_exists}, Supplier exists: {supplier_exists}")

        return self.valid
    
    def validate_rfq_exists(self):
        """Dedicated method to validate RFQ existence with better error handling"""
        # First check direct match by name
        if self.actual_rfq_name and frappe.db.exists("Request for Quotation", self.actual_rfq_name):
            self.log(f"Found RFQ by actual name: {self.actual_rfq_name}")
            return True
            
        # Then check direct match by reference
        if frappe.db.exists("Request for Quotation", self.rfq_name):
            self.actual_rfq_name = self.rfq_name
            self.log(f"Found RFQ by direct reference: {self.rfq_name}")
            return True
            
        # Try lookup by reference in name
        rfq_docs = frappe.get_all("Request for Quotation", 
                                filters={"name": ("like", f"%{self.rfq_name}")})
        if rfq_docs:
            self.actual_rfq_name = rfq_docs[0].name
            self.log(f"Found RFQ by searching: {self.actual_rfq_name}")
            return True
        
        # Check pending refs as last resort
        if self.rfq_name in self.pending_rfq_refs:
            self.log(f"Found RFQ in pending references: {self.rfq_name}")
            return True
        
        self.log(f"RFQ not found: {self.rfq_name}")
        return False

    def insert_data(self):
        if not self.valid:
            self.log("Validation failed, skipping SQ creation")
            return None

        try:
            self.log(f"Starting SQ creation for RFQ: {self.rfq_name}, Supplier: {self.supplier}")
            
            # Try to get RFQ using the actual document name if we found it
            rfq = None
            if self.actual_rfq_name:
                self.log(f"Looking up RFQ by actual name: {self.actual_rfq_name}")
                rfq = frappe.get_doc("Request for Quotation", self.actual_rfq_name)
            else:
                # If we don't have the actual name, try direct lookup
                if frappe.db.exists("Request for Quotation", self.rfq_name):
                    self.log(f"Looking up RFQ by reference: {self.rfq_name}")
                    rfq = frappe.get_doc("Request for Quotation", self.rfq_name)
                else:
                    # Try to find RFQ by reference in name
                    rfq_docs = frappe.get_all("Request for Quotation", 
                                           filters={"name": ("like", f"%{self.rfq_name}")})
                    if rfq_docs:
                        self.log(f"Found RFQ by search: {rfq_docs[0].name}")
                        rfq = frappe.get_doc("Request for Quotation", rfq_docs[0].name)
                    else:
                        # Check uncommitted docs 
                        rfq = self.rfq_docs.get(self.rfq_name)
                        if not rfq:
                            raise Exception(f"RFQ {self.rfq_name} not found in database or pending documents")
            
            self.log(f"Retrieved RFQ: {rfq.name if rfq else 'None'}")

            # Add supplier to RFQ if not present
            if not any(s.supplier == self.supplier for s in rfq.suppliers):
                supplier_name = (frappe.db.get_value("Supplier", self.supplier, "supplier_name") or 
                                self.supplier)
                rfq.append("suppliers", {
                    "supplier": self.supplier,
                    "supplier_name": supplier_name
                })
                rfq.save(ignore_permissions=True)
                self.log(f"Added supplier {self.supplier} to RFQ")

            # Create SQ items
            items = [{
                "item_code": item.item_code,
                "qty": item.qty,
                "uom": item.uom,
                "conversion_factor": 1.0,
                "request_for_quotation": rfq.name,
                "rfq_item": item.name
            } for item in rfq.items]

            self.log(f"Prepared {len(items)} items for SQ")

            # Create SQ
            sq = frappe.get_doc({
                "doctype": "Supplier Quotation",
                "supplier": self.supplier,
                "transaction_date": today(),
                "status": "Draft",
                "items": items
            })
            
            sq.insert(ignore_permissions=True)
            self.log(f"Created SQ: {sq.name}")

            # Link SQ to RFQ
            for supplier in rfq.suppliers:
                if supplier.supplier == self.supplier:
                    supplier.supplier_quotation = sq.name
                    break
            rfq.save(ignore_permissions=True)
            self.log(f"Linked SQ {sq.name} to RFQ")

            self.created_sq = sq.name
            return sq.name

        except Exception as e:
            self.log(f"SQ creation failed: {str(e)}")
            frappe.db.rollback()
            self.errors.append(f"Line {self.line_number}: {str(e)}")
            return None

    def log(self, message):
        """Enhanced logging method"""
        full_message = f"SQ Import [Line {self.line_number}]: {message}"
        frappe.log(full_message)
        print(f"LOG: {full_message}")