import logging


# Pre-configure logging before SDK import (which calls basicConfig(DEBUG))
logging.basicConfig(level=logging.WARNING)

from importlib.metadata import version

__version__ = version("choo")
