"""MCP Server entry point with Streamable HTTP transport.

Uses mcp[cli] SDK. Registers all 5 tools.
Env: MCP_PORT (default 8080), JWT_SECRET (for OAuth).
"""

from __future__ import annotations

from mcp.server import Server
from mcp.types import TextContent, Tool


def create_server() -> Server:
    """Create and configure the MCP server with all tools.

    Returns:
        Configured Server instance
    """
    server = Server("oute-muscle")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available MCP tools."""
        return [
            Tool(
                name="scan_code",
                description="Scan code for security issues using Semgrep",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code to scan"},
                        "language": {
                            "type": "string",
                            "description": "Programming language",
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant identifier",
                        },
                    },
                    "required": ["code", "language", "tenant_id"],
                },
            ),
            Tool(
                name="get_incident_advisory",
                description="Get RAG-based advisory for code",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code to analyze"},
                        "context": {
                            "type": "string",
                            "description": "Optional context",
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant identifier",
                        },
                    },
                    "required": ["code", "tenant_id"],
                },
            ),
            Tool(
                name="list_relevant_incidents",
                description="List incidents relevant to code or query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Optional semantic search query",
                        },
                        "category": {
                            "type": "string",
                            "description": "Optional category filter",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10,
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant identifier",
                        },
                    },
                    "required": ["tenant_id"],
                },
            ),
            Tool(
                name="synthesize_rules",
                description="Synthesize new detection rules from incidents (Enterprise only)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "incident_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Incidents to synthesize from",
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant identifier",
                        },
                    },
                    "required": ["incident_ids", "tenant_id"],
                },
            ),
            Tool(
                name="validate_fix",
                description="Validate that a fix resolves the issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "original_code": {
                            "type": "string",
                            "description": "Original code with issue",
                        },
                        "fixed_code": {
                            "type": "string",
                            "description": "Proposed fixed code",
                        },
                        "rule_id": {
                            "type": "string",
                            "description": "Rule to check",
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "Tenant identifier",
                        },
                    },
                    "required": ["original_code", "fixed_code", "rule_id", "tenant_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Route tool calls to handlers.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            List of TextContent responses
        """
        # Import here to avoid circular imports
        from apps.mcp.src.tools.get_incident_advisory import get_incident_advisory
        from apps.mcp.src.tools.list_relevant_incidents import (
            list_relevant_incidents,
        )
        from apps.mcp.src.tools.scan_code import scan_code
        from apps.mcp.src.tools.synthesize_rules import synthesize_rules
        from apps.mcp.src.tools.validate_fix import validate_fix

        try:
            if name == "scan_code":
                result = await scan_code(
                    code=arguments["code"],
                    language=arguments["language"],
                    tenant_id=arguments["tenant_id"],
                    user_id=arguments.get("user_id", "anonymous"),
                )
            elif name == "get_incident_advisory":
                result = await get_incident_advisory(
                    code=arguments["code"],
                    context=arguments.get("context"),
                    tenant_id=arguments["tenant_id"],
                    user_id=arguments.get("user_id", "anonymous"),
                )
            elif name == "list_relevant_incidents":
                result = await list_relevant_incidents(
                    query=arguments.get("query"),
                    category=arguments.get("category"),
                    max_results=arguments.get("max_results", 10),
                    tenant_id=arguments["tenant_id"],
                    user_id=arguments.get("user_id", "anonymous"),
                )
            elif name == "synthesize_rules":
                result = await synthesize_rules(
                    incident_ids=arguments["incident_ids"],
                    tenant_id=arguments["tenant_id"],
                    user_id=arguments.get("user_id", "anonymous"),
                    tier=arguments.get("tier", "free"),
                )
            elif name == "validate_fix":
                result = await validate_fix(
                    original_code=arguments["original_code"],
                    fixed_code=arguments["fixed_code"],
                    rule_id=arguments["rule_id"],
                    tenant_id=arguments["tenant_id"],
                    user_id=arguments.get("user_id", "anonymous"),
                )
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            return [TextContent(type="text", text=str(result))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e!s}")]

    return server


if __name__ == "__main__":
    import asyncio

    from mcp.server.stdio import stdio_server

    server = create_server()
    asyncio.run(stdio_server(server))
