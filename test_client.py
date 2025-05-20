
import sys
import json
from fastmcp import FastMCPClient

def main():
    # Connect to the MCP server
    client = FastMCPClient("http://host.docker.internal:8001/mcp")
    
    try:
        # List tools
        tools = client.list_tools()
        print("Available tools:")
        for tool in tools:
            print(f"- {tool}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
