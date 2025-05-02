import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from app.tool.mcp import MCPClients


@asynccontextmanager
async def mock_stdio_client(*args, **kwargs):
    """A simplified mock for stdio_client that simulates the cancel scope error."""
    # Create a task in a different context
    task = asyncio.create_task(asyncio.sleep(100))  # Long-running background task

    try:
        # Return mock streams
        yield (AsyncMock(), AsyncMock())
    finally:
        # Simulate the error when exiting
        if not task.done():
            task.cancel()
            # This is the key part - simulate the error that happens in the real code
            raise RuntimeError("Attempted to exit cancel scope in a different task than it was entered in")


@pytest.mark.asyncio
async def test_disconnect_with_cancel_scope_error():
    """Test that the disconnect method handles cancel scope errors properly."""
    # Create MCPClients instance
    mcp_clients = MCPClients()

    # Mock the stdio_client to use our simplified implementation
    with patch('app.tool.mcp.stdio_client', mock_stdio_client):
        with patch('app.tool.mcp.ClientSession') as mock_session:
            # Set up mock session
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            mock_session_instance.list_tools.return_value.tools = []

            # Connect to two mock servers
            await mcp_clients.connect_stdio("server1", [], "server1")
            await mcp_clients.connect_stdio("server2", [], "server2")

            # Verify connections were established
            assert "server1" in mcp_clients.sessions
            assert "server2" in mcp_clients.sessions

            # Now disconnect from all servers - this should trigger the error
            # but our implementation should handle it gracefully
            await mcp_clients.disconnect()

            # Verify all servers were disconnected despite the error
            assert not mcp_clients.sessions
            assert not mcp_clients.exit_stacks
