#!/usr/bin/env python3
"""
Simple script to test the MCP server
"""

import sys
import json
import requests
import uuid

def main():
    """Main entry point"""
    # Test the MCP server
    base_url = "http://localhost:8001/mcp"
    
    # Create a session ID
    session_id = str(uuid.uuid4())
    print(f"Using session ID: {session_id}")
    
    # Headers for streamable HTTP transport
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    # Create session
    url = f"{base_url}?session={session_id}"
    try:
        response = requests.get(url, headers=headers)
        print(f"Session creation status code: {response.status_code}")
        if response.status_code != 200:
            print(f"Failed to create session: {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"Error creating session: {str(e)}")
        sys.exit(1)
    
    # List tools
    payload = {
        "jsonrpc": "2.0",
        "method": "_mcp_list_tools",
        "id": 1
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"List tools status code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error listing tools: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 