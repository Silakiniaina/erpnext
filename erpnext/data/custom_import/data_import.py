from abc import ABC, abstractmethod
from datetime import datetime
from frappe import _

class DataImport(ABC):
    """
    Abstract class for handling data imports
    """
    def __init__(self, filename):
        self.errors = []
        self.valid = True
        self.filename = filename
        self.line_number = 0

    @abstractmethod
    def check_integrity(self):
        """Check the integrity of the data"""
        pass

    @abstractmethod
    def check_foreign_key(self):
        """Check foreign key references"""
        pass

    @abstractmethod
    def insert_data(self):
        """Insert data into the system"""
        pass

    def check_required_value(self, value, field_name):
        """
        Check if required value is present
        """
        if not value or value.strip() == "":
            self.errors.append(f"Line {self.line_number}: {field_name} is required")
            self.valid = False
            return False
        return True
    
    def validate_number(self, number, min_value=None):
        """
        Validate if value is a number and optionally check minimum value
        """ 
        try:
            num_val = float(number)
            if min_value is not None and num_val < min_value:
                self.errors.append(f"Line {self.line_number}: Value {number} must be at least {min_value}")
                self.valid = False
                return False
            return True
        except (ValueError, TypeError):
            self.errors.append(f"Line {self.line_number}: Value '{number}' is not a valid number")
            self.valid = False
            return False
        
    def validate_date(self, date_str):
        """
        Validate if the string is a valid date format
        """ 
        try:
            for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                try:
                    datetime.strptime(date_str, fmt)
                    return True
                except ValueError:
                    continue
                    
            self.errors.append(f"Line {self.line_number}: '{date_str}' is not a valid date format")
            self.valid = False
            return False
        except Exception as e:
            self.errors.append(f"Line {self.line_number}: Error validating date: {str(e)}")
            self.valid = False
            return False
        
    def validate(self):
        """
        Run validation checks on the data
        """
        self.check_integrity()
        self.check_foreign_key()  
        pass
