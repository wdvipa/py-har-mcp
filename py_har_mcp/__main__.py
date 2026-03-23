from __future__ import annotations

import argparse

from .server import mcp


def main() -> int:
    parser = argparse.ArgumentParser("Python HAR MCP Server")
    parser.add_argument(
        "--http",
        help="Serve MCP server over streamable HTTP.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--port",
        help="Port for --http (default:8000)",
        default=8000,
        type=int,
    )
    args = parser.parse_args()

    if args.http:
        mcp.run(transport="streamable-http", port=args.port)
    else:
        mcp.run()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
