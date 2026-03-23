"""Python HAR MCP server package."""

from __future__ import annotations

from .__main__ import main
from .server import mcp

__all__ = ["__version__", "main", "mcp"]

__version__ = "0.1.1"
