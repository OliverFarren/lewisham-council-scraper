from lewisham_mcp.server import mcp


def test_mcp_server_has_get_bins_tool() -> None:
    tools = {t.name for t in mcp._tool_manager.list_tools()}  # type: ignore[attr-defined]
    assert "get_bins" in tools
