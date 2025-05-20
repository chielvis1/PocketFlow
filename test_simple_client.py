#!/usr/bin/env python3
"""
Simple MCP client to test the tutorial MCP server
"""

import json
import requests
import uuid
import sys

def main():
    # Server URL
    server_url = "http://localhost:8000/mcp/"
    
    # Create a session ID
    session_id = str(uuid.uuid4())
    print(f"Using session ID: {session_id}")
    
    # Headers for all requests
    headers = {
        "Accept": "text/event-stream, application/json",
        "Content-Type": "application/json",
        "MCP-Session-ID": session_id
    }
    
    # Step 1: Create a session
    create_session_payload = {
        "jsonrpc": "2.0",
        "method": "session.create",
        "params": {},
        "id": "1"
    }
    
    try:
        print("\nCreating session...")
        response = requests.post(server_url, headers=headers, json=create_session_payload)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code != 200:
            print("Failed to create session. Exiting.")
            sys.exit(1)
        
        # Step 2: List tools
        list_tools_payload = {
            "jsonrpc": "2.0",
            "method": "tool.list",
            "params": {},
            "id": "2"
        }
        
        print("\nListing tools...")
        response = requests.post(server_url, headers=headers, json=list_tools_payload)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            tools_data = response.json()
            print("\nAvailable tools:")
            if "result" in tools_data:
                tools = tools_data["result"]
                for i, tool in enumerate(tools, 1):
                    print(f"\n{i}. {tool['name']}")
                    print(f"   Description: {tool['description']}")
                    
                    if "parameters" in tool and tool['parameters']:
                        print(f"   Parameters: {json.dumps(tool['parameters'], indent=6)}")
                    else:
                        print(f"   Parameters: None")
                    
                    if "returns" in tool:
                        print(f"   Returns: {json.dumps(tool['returns'], indent=6)}")
            else:
                print(f"Error: {tools_data}")
        else:
            print(f"Failed to list tools: {response.text}")
        
        # Step 3: Call a simple tool (chapter_index)
        call_tool_payload = {
            "jsonrpc": "2.0",
            "method": "tool.call",
            "params": {
                "name": "chapter_index",
                "params": {}
            },
            "id": "3"
        }
        
        print("\nCalling chapter_index tool...")
        response = requests.post(server_url, headers=headers, json=call_tool_payload)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result_data = response.json()
            if "result" in result_data:
                print("\nChapter index content (first 200 chars):")
                content = result_data["result"][0]["content"]
                if isinstance(content, str):
                    print(content[:200] + "..." if len(content) > 200 else content)
                else:
                    print(json.dumps(content, indent=2)[:200] + "..." if len(json.dumps(content, indent=2)) > 200 else json.dumps(content, indent=2))
            else:
                print(f"Error: {result_data}")
        else:
            print(f"Failed to call chapter_index: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 