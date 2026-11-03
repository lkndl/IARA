"""IARA - Interface Analysis and Recognition Architecture."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("iara")
except PackageNotFoundError:
    __version__ = "unknown"
