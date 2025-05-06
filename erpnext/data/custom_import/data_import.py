from abc import ABC
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