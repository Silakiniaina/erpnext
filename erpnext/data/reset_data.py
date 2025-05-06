import frappe
from frappe import _
import json

@frappe.whitelist()
def reset_selected(doctypes):
    if frappe.session.user != "Administrator":
        frappe.throw(_("Only Administrator can perform this action."))

    if isinstance(doctypes, str):
        doctypes = json.loads(doctypes)

    if not doctypes or not isinstance(doctypes, list):
        frappe.throw(_("Invalid doctype list."))

    deleted = []

    for doctype in doctypes:
        if frappe.get_meta(doctype, cached=True).issingle:
            continue  # skip singleton Doctypes
        try:
            frappe.db.delete(doctype)
            deleted.append(doctype)
        except Exception as e:
            frappe.log_error(f"Failed to delete {doctype}: {str(e)}")

    return {"message": "Done", "deleted": deleted}