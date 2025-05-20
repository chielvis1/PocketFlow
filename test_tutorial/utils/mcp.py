"""
MCP server utilities for Repository Analysis to MCP Server system.
"""

import json
import logging
import os
import subprocess
import sys
import time
from typing import Dict, List, Any, Optional, Callable

from .monitoring import log_execution_time

def create_mcp_server(name: str, tools: List[Dict[str, Any]], 
                     implementation_guides: Dict[str, Any]) -> Any:
    """
    Creates and configures an MCP server with dynamically generated tools.
    
    Args:
        name: Server name
        tools: Tool definitions
        implementation_guides: Implementation guides by feature
        
    Returns:
        Configured FastMCP server instance
    """
    # Always use FastMCP; ensure fastmcp is installed
    from fastmcp import FastMCP
    
    # Create a named server
    mcp = FastMCP(name)
    
    # Register dynamic tools
    for tool in tools:
        tool_name = tool["name"]
        feature_name = tool_name.replace("get_", "").replace("_", " ")
        
        # Create a closure to capture the feature_name
        def create_tool_handler(feature):
            def get_feature_info(detail_level="basic"):
                if feature in implementation_guides:
                    if detail_level == "basic":
                        return {
                            "overview": implementation_guides[feature]["overview"],
                            "core_concepts": implementation_guides[feature]["core_concepts"]
                        }
                    else:
                        return implementation_guides[feature]
                else:
                    return {"error": f"No guide found for {feature}"}
            return get_feature_info
        
        # Register the tool with the dynamically created handler
        mcp.tool(name=tool_name)(create_tool_handler(feature_name))
    
    # Register generic tools
    
    @mcp.tool(name="list_features")
    def list_features():
        """List all available features from the repository"""
        return list(implementation_guides.keys())
    
    @mcp.tool(name="get_repository_overview")
    def get_repository_overview():
        """Get overview information about the repository"""
        return {
            "name": name,
            "features": list(implementation_guides.keys()),
            "implementation_difficulty": calculate_overall_difficulty(implementation_guides)
        }
    
    return mcp

def calculate_overall_difficulty(implementation_guides: Dict[str, Any]) -> str:
    """
    Calculate overall implementation difficulty based on guides
    
    Args:
        implementation_guides: Implementation guides by feature
        
    Returns:
        Difficulty rating: "Easy", "Medium", or "Hard"
    """
    if not implementation_guides:
        return "Unknown"
    
    # Count steps across all guides to estimate difficulty
    total_steps = 0
    for feature, guide in implementation_guides.items():
        if "step_by_step_implementation" in guide:
            steps = guide["step_by_step_implementation"]
            if isinstance(steps, list):
                total_steps += len(steps)
            elif isinstance(steps, dict):
                total_steps += len(steps.keys())
    
    # Determine difficulty based on total step count
    if total_steps < 15:
        return "Easy"
    elif total_steps < 40:
        return "Medium"
    else:
        return "Hard"

def start_mcp_server(mcp: Any, host: str = "0.0.0.0", port: int = 8000, debug: bool = False, return_info: bool = True) -> Any:
    """
    Start the MCP server with the given host and port.
    For FastMCP objects, this will use the run() method.
    
    Args:
        mcp: The MCP server object
        host: The host to bind to (default: "0.0.0.0")
        port: The port to bind to (default: 8000)
        debug: Whether to enable debug logging (default: False)
        return_info: Whether to return server info (default: True)
    
    Returns:
        dict: Server information in JSON format
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger("mcp_server")
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled for MCP server")
        logger.debug(f"Server configuration: host={host}, port={port}")
        logger.debug(f"Server name: {getattr(mcp, 'name', 'unknown')}")
        logger.debug(f"Available tools: {dir(mcp)}")
        logger.debug("Starting server...")
        print("Debug logging enabled for MCP server")
    
    print(f"Starting MCP server at http://{host}:{port}...")
    
    try:
        # For FastMCP objects (version 2.x)
        if hasattr(mcp, "run"):
            # Start the server in a separate thread
            import threading
            
            def run_server():
                # FastMCP.run() doesn't accept host/port directly
                try:
                    # Use run_http_async which accepts host and port
                    import asyncio
                    # Force host to be "0.0.0.0" to listen on all interfaces
                    asyncio.run(mcp.run_http_async(host="0.0.0.0", port=port))
                except Exception as e:
                    print(f"Error in server thread: {e}")
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Create a mock process object for status checks
            class MockProcess:
                def poll(self):
                    return None if server_thread.is_alive() else 1
                
                def terminate(self):
                    # No direct way to stop the server
                    pass
            
            process = MockProcess()
            
            # Give the server time to start
            import time
            time.sleep(2)
            
            if debug:
                logger.debug("Server process started")
            
            print(f"MCP server started successfully at http://{host}:{port}")
            
            # Create server info with mcpServers format for container orchestration
            server_info = {
                "mcpServers": [
                    {
                        "name": getattr(mcp, "name", "mcp_server"),
                        "transport": "http",
                        "host": host,
                        "port": port
                    }
                ],
                "process": process,
                "url": f"http://{host}:{port}",
                "status": "running"
            }
            
            # Print server info as JSON for container orchestration
            import json
            server_json = json.dumps({"mcpServers": server_info["mcpServers"]}, indent=2)
            print(server_json)
            
            if debug:
                logger.debug(f"Server info: {server_json}")
            
            return server_info
        else:
            # For other MCP implementations that might use serve()
            server_process = mcp.serve(host=host, port=port)
            
            if debug:
                logger.debug(f"Server process started")
            
            print(f"MCP server started successfully at http://{host}:{port}")
            
            # Create server info with mcpServers format for container orchestration
            server_info = {
                "mcpServers": [
                    {
                        "name": getattr(mcp, "name", "mcp_server"),
                        "transport": "http",
                        "host": host,
                        "port": port
                    }
                ],
                "process": server_process,
                "url": f"http://{host}:{port}",
                "status": "running"
            }
            
            # Print server info as JSON for container orchestration
            server_json = json.dumps({"mcpServers": server_info["mcpServers"]}, indent=2)
            print(server_json)
            
            if debug:
                logger.debug(f"Server info: {server_json}")
            
            return server_info
    except Exception as e:
        import traceback
        error_msg = f"Error starting MCP server: {str(e)}"
        print(error_msg)
        
        if debug:
            logger = logging.getLogger("mcp_server")
            logger.error(error_msg)
            logger.error("Detailed traceback:")
            for line in traceback.format_exc().split("\n"):
                logger.error(line)
            print(traceback.format_exc())
            
        return {
            "host": host,
            "port": port,
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc() if debug else None
        }

class MockMCPServer:
    """
    Mock implementation of MCP server for environments without FastMCP
    """
    def __init__(self, name, tools, implementation_guides):
        self.name = name
        self.tools = tools
        self.guides = implementation_guides
        self.tool_handlers = {}
        
        # Set up basic tools
        self.tool_handlers["list_features"] = lambda: list(self.guides.keys())
        self.tool_handlers["get_repository_overview"] = lambda: {
            "name": self.name,
            "features": list(self.guides.keys()),
            "implementation_difficulty": calculate_overall_difficulty(self.guides)
        }
        
        # Set up feature-specific tools
        for tool in tools:
            tool_name = tool["name"]
            feature_name = tool_name.replace("get_", "").replace("_", " ")
            
            def create_handler(feature):
                def handler(detail_level="basic"):
                    if feature in self.guides:
                        if detail_level == "basic":
                            return {
                                "overview": self.guides[feature]["overview"],
                                "core_concepts": self.guides[feature]["core_concepts"]
                            }
                        else:
                            return self.guides[feature]
                    else:
                        return {"error": f"No guide found for {feature}"}
                return handler
            
            self.tool_handlers[tool_name] = create_handler(feature_name)
    
    def tool(self, name=None):
        """Mock decorator for tool registration"""
        def decorator(func):
            if name:
                self.tool_handlers[name] = func
            else:
                import inspect
                self.tool_handlers[func.__name__] = func
            return func
        return decorator
    
    def start(self, host, port):
        """Mock server start"""
        print(f"Mock MCP server '{self.name}' would start at http://{host}:{port}")
        print(f"Available tools: {list(self.tool_handlers.keys())}")
        
        return {
            "host": host,
            "port": port,
            "status": "running (mock)",
            "tools": list(self.tool_handlers.keys())
        }
    
    def call_tool(self, tool_name, **kwargs):
        """Mock tool invocation for testing"""
        if tool_name in self.tool_handlers:
            return self.tool_handlers[tool_name](**kwargs)
        else:
            return {"error": f"Tool '{tool_name}' not found"}

if __name__ == "__main__":
    # Test mock MCP server
    test_tools = [
        {
            "name": "get_authentication",
            "description": "Get information about authentication"
        },
        {
            "name": "get_data_processing",
            "description": "Get information about data processing"
        }
    ]
    
    test_guides = {
        "authentication": {
            "overview": "Authentication implementation guide",
            "core_concepts": ["JWT", "OAuth", "Sessions"],
            "step_by_step_implementation": ["Step 1", "Step 2", "Step 3"]
        },
        "data processing": {
            "overview": "Data processing implementation guide", 
            "core_concepts": ["ETL", "Batch Processing"],
            "step_by_step_implementation": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"]
        }
    }
    
    # Create mock server
    mock_server = create_mcp_server("TestMCP", test_tools, test_guides)
    
    # Start mock server
    server_info = start_mcp_server(mock_server)
    
    # Test tool calls if using mock
    if isinstance(mock_server, MockMCPServer):
        print("\nTesting tool calls:")
        print("list_features:", mock_server.call_tool("list_features"))
        print("get_authentication (basic):", mock_server.call_tool("get_authentication"))
        print("get_authentication (detailed):", mock_server.call_tool("get_authentication", detail_level="detailed")) 