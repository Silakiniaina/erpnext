from abc import ABC, abstractmethod
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
