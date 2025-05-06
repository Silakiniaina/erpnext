import frappe
from frappe import _
from abc import ABC, abstractmethod
from frappe.utils import getdate, formatdate, flt, today

class BaseImport(ABC):
    """Abstract base class for all importers"""
    def __init__(self, filename):
        self.errors = []
        self.valid = True
        self.filename = filename
        self.line_number = 0

    @abstractmethod
    def check_integrity(self):
        pass

    @abstractmethod
    def insert_data(self):
        pass

    def check_required_value(self, value, field_name):
        if not value or value.strip() == "":
            self.errors.append(f"Line {self.line_number}: {field_name} is required")
            self.valid = False

    def validate_number(self, number, min_value=None):
        try:
            num_val = flt(number)
            if min_value is not None and num_val < min_value:
                self.errors.append(f"Line {self.line_number}: Value must be ≥ {min_value}")
                self.valid = False
        except ValueError:
            self.errors.append(f"Line {self.line_number}: Invalid number format")
            self.valid = False

    def validate_date(self, date_str):
        try:
            getdate(date_str)  # Frappe's built-in date validation
        except Exception:
            self.errors.append(f"Line {self.line_number}: Invalid date format")
            self.valid = False

    def validate(self):
        self.check_integrity()
        if self.valid:
            return True
        return False