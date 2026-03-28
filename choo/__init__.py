import logging


# Pre-configure logging before SDK import (which calls basicConfig(DEBUG))
logging.basicConfig(level=logging.WARNING)

__version__ = "0.1.0"
