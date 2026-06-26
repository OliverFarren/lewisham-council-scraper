import os

import httpx
from mcp.server.fastmcp import FastMCP

LEWISHAM_SERVER_URL = os.getenv("LEWISHAM_SERVER_URL", "http://localhost:8000")

mcp = FastMCP("lewisham-mcp")


@mcp.tool()
async def get_bins() -> str:
    """Get bin collection information from lewisham-server."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{LEWISHAM_SERVER_URL}/bins/")
        response.raise_for_status()
        return response.text


if __name__ == "__main__":
    mcp.run()
