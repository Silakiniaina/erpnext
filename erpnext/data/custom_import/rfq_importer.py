import frappe
from frappe import _
from erpnext.data.custom_import.base_importer import BaseImport
from frappe.utils import getdate, nowdate, flt, formatdate
from datetime import datetime

class RFQImport(BaseImport):
    def __init__(self, filename, date, item_name, item_group, required_by, quantity, purpose, target_warehouse, ref, pending_suppliers=None):
        super().__init__(filename)
        self.date = date
        self.item_name = item_name
        self.item_group = item_group
        self.required_by = required_by
        self.quantity = quantity
        self.purpose = purpose
        self.target_warehouse = target_warehouse
        self.ref = str(ref)  # Ensure string type
        self.uom = "Nos"
        self.pending_suppliers = pending_suppliers or set()

    def check_integrity(self):
        required_fields = [
            ("date", "Date"),
            ("item_name", "Item Name"),
            ("item_group", "Item Group"),
            ("required_by", "Required By Date"),
            ("quantity", "Quantity"),
            ("purpose", "Purpose"),
            ("target_warehouse", "Target Warehouse")
        ]
        
        for field, name in required_fields:
            self.check_required_value(getattr(self, field), name)

        if self.valid:
            self.validate_date(self.date)
            self.validate_date(self.required_by)
            self.validate_number(self.quantity, min_value=0.1)
            
            if getdate(self.required_by) < getdate(self.date):
                self.errors.append(f"Line {self.line_number}: Required by date cannot be before RFQ date")
                self.valid = False

        if self.valid:
            self.check_foreign_key()

        return self.valid

    def check_foreign_key(self):
        if not self.valid:
            return

        # Check/create item group
        if not frappe.db.exists("Item Group", self.item_group):
            try:
                frappe.get_doc({
                    "doctype": "Item Group",
                    "item_group_name": self.item_group,
                    "parent_item_group": "All Item Groups"
                }).insert(ignore_permissions=True)
            except Exception as e:
                self.errors.append(f"Line {self.line_number}: Failed to create Item Group: {str(e)}")
                self.valid = False

        # Check/create item
        if not frappe.db.exists("Item", {"item_name": self.item_name}):
            try:
                self.create_item()
            except Exception as e:
                self.errors.append(f"Line {self.line_number}: Failed to create Item: {str(e)}")
                self.valid = False

        # Check/create warehouse
        warehouse_name = f"{self.target_warehouse} - ITU"
        if not frappe.db.exists("Warehouse", warehouse_name):
            try:
                frappe.get_doc({
                    "doctype": "Warehouse",
                    "warehouse_name": warehouse_name,
                    "parent_warehouse": "All Warehouses - ITU"
                }).insert(ignore_permissions=True)
            except Exception as e:
                self.errors.append(f"Line {self.line_number}: Failed to create Warehouse: {str(e)}")
                self.valid = False

    def insert_data(self):
        if not self.valid:
            return None

        try:
            transaction_date = formatdate(self.date, "yyyy-mm-dd")
            schedule_date = formatdate(self.required_by, "yyyy-mm-dd")

            # Check if RFQ exists
            rfq = None
            if self.ref and frappe.db.exists("Request for Quotation", self.ref):
                rfq = frappe.get_doc("Request for Quotation", self.ref)
            
            if rfq:
                # RFQ exists - add item to it
                rfq.append("items", {
                    "item_code": self.item_name,
                    "item_name": self.item_name,
                    "description": self.item_name,
                    "qty": flt(self.quantity),
                    "uom": self.uom,
                    "conversion_factor": 1.0,
                    "warehouse": f"{self.target_warehouse} - ITU",
                    "schedule_date": schedule_date,
                    "material_request": self._create_material_request().name
                })
                rfq.save(ignore_permissions=True)
                
                # Submit the RFQ if it's in Draft status
                if rfq.status == "Draft":
                    rfq.submit()
            else:
                # Create new RFQ
                mr = self._create_material_request()
                
                # Get suppliers from both DB and pending imports
                suppliers = []
                db_suppliers = frappe.get_all("Supplier", fields=["name", "supplier_name"])
                for s in db_suppliers:
                    suppliers.append({
                        "supplier": s["name"],
                        "supplier_name": s["supplier_name"]
                    })
                
                # Add pending suppliers that aren't in DB yet
                for supplier_name in self.pending_suppliers:
                    if not any(s['supplier_name'] == supplier_name for s in db_suppliers):
                        suppliers.append({
                            "supplier": supplier_name,
                            "supplier_name": supplier_name
                        })

                rfq_data = {
                    "doctype": "Request for Quotation",
                    "name": self.ref,
                    "transaction_date": transaction_date,
                    "schedule_date": schedule_date,
                    "message_for_supplier": "Please provide your quotation",
                    "status": "Draft",  # Initially create as draft
                    "items": [{
                        "item_code": self.item_name,
                        "item_name": self.item_name,
                        "description": self.item_name,
                        "qty": flt(self.quantity),
                        "uom": self.uom,
                        "conversion_factor": 1.0,
                        "warehouse": f"{self.target_warehouse} - ITU",
                        "schedule_date": schedule_date,
                        "material_request": mr.name,
                        "material_request_item": mr.items[0].name
                    }],
                    "suppliers": suppliers
                }
                rfq = frappe.get_doc(rfq_data)
                rfq.insert(ignore_permissions=True)
                
                # Submit the RFQ
                rfq.submit()

            return rfq.name

        except Exception as e:
            frappe.db.rollback()
            self.errors.append(f"Line {self.line_number}: {str(e)}")
            return None

    def create_item(self):
        try:
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": self.item_name,
                "item_name": self.item_name,
                "item_group": self.item_group,
                "stock_uom": self.uom,
                "is_stock_item": 1,
                "uoms": [{
                    "uom": self.uom,
                    "conversion_factor": 1.0
                }],
                "description": self.item_name,
                "valuation_rate": 0,
                "standard_rate": 0
            })
            item.insert(ignore_permissions=True)
            return True
        except Exception as e:
            frappe.db.rollback()
            raise e
        
    def _create_material_request(self):
        mr = frappe.get_doc({
            "doctype": "Material Request",
            "material_request_type": "Purchase",
            "transaction_date": formatdate(self.date, "yyyy-mm-dd"),
            "schedule_date": formatdate(self.required_by, "yyyy-mm-dd"),
            "items": [{
                "item_code": self.item_name,
                "item_name": self.item_name,
                "qty": flt(self.quantity),
                "uom": self.uom,
                "conversion_factor": 1.0,
                "warehouse": f"{self.target_warehouse} - ITU",
                "schedule_date": formatdate(self.required_by, "yyyy-mm-dd")
            }],
            "purpose": self.purpose
        })
        mr.insert(ignore_permissions=True)
        mr.submit()
        return mr