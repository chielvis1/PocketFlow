#!/usr/bin/env python3
"""
Simple client script to test the MCP server using the requests library
"""

import sys
import json
import requests
import uuid
import time

def main():
    """Main entry point"""
    # Test the MCP server
    base_url = "http://localhost:8001/mcp"
    
    # Try a different approach - use the root endpoint
    try:
        # List tools
        payload = {
            "jsonrpc": "2.0",
            "method": "_mcp_list_tools",
            "params": {},
            "id": 1
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        response = requests.post(base_url, json=payload, headers=headers)
        print(f"List tools status code: {response.status_code}")
        print(f"Response: {response.text}")
        
        # If successful, try to list tools
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                tools = data["result"]
                print("\nAvailable tools:")
                for tool in tools:
                    print(f"- {tool}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 