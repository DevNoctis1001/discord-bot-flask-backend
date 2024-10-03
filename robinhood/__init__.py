# __init__.py

from .robinhood import RobinhoodClient

__version__ = "1.0.0"
__author__ = "Mark Elbaz"

print("Initializing Robinhood package")

__all__ = ['RobinhoodClient']