from typing import Any, Dict, List, Union
import frappe
from frappe import _
import json
from erpnext.data.custom_import.import_orchestrator import ImportOrchestrator

@frappe.whitelist(allow_guest=False)
def import_data(
    supplier_file: Union[Dict[str, Any], str, None] = None,
    rfq_file: Union[Dict[str, Any], str, None] = None,
    sq_file: Union[Dict[str, Any], str, None] = None
) -> Dict[str, List[str]]:
    """API endpoint that maintains original error_map structure"""
    
    def parse_arg(arg):
        if isinstance(arg, str):
            try:
                return json.loads(arg)
            except json.JSONDecodeError:
                return None
        return arg

    # Initialize error_map with original structure
    error_map = {
        'supplier_import': [],
        'rfq_import': [],
        'sq_import': []
    }

    try:
        frappe.db.begin()
        
        # Parse file arguments
        supplier_file = parse_arg(supplier_file)
        rfq_file = parse_arg(rfq_file)
        sq_file = parse_arg(sq_file)

        orchestrator = ImportOrchestrator()
        result = orchestrator.process_all(
            supplier_file=supplier_file,
            rfq_file=rfq_file,
            sq_file=sq_file
        )
        
        # Convert orchestrator errors to legacy format
        for key, errors in result['errors'].items():
            if key == 'system':
                error_map['system'] = errors
            else:
                doc_type = key.replace('_file', '_import')
                if doc_type in error_map:
                    error_map[doc_type].extend(errors)
        
        # Commit only if no errors
        if not any(errors for errors in error_map.values()):
            frappe.db.commit()
        else:
            frappe.db.rollback()
        
        return error_map
            
    except Exception as e:
        frappe.db.rollback()
        error_map['system'] = [str(e)]
        return error_map