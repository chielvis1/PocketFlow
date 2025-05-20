#!/usr/bin/env python3
"""
Script to run a FastMCP client in a Docker container
"""

import asyncio
import os
import json
from fastmcp import Client

async def main():
    # Connect to the MCP server running in the Docker container
    # Use host.docker.internal to access the host from within a Docker container
    server_url = "http://host.docker.internal:8001/mcp"
    print(f"Connecting to MCP server at {server_url}")
    
    try:
        async with Client(server_url) as client:
            # List available tools
            tools = await client.list_tools()
            print(f"Available tools: {[tool.name for tool in tools]}")
            
            # Test the chapter_index tool
            print("\nTesting chapter_index tool...")
            result = await client.call_tool("chapter_index", {})
            
            # Process the response (which is a list of TextContent objects)
            if result and len(result) > 0:
                # Access the first TextContent object's text attribute
                content_text = result[0].text
                # Parse the JSON content
                try:
                    content_json = json.loads(content_text)
                    print(f"Chapter index content (first 500 chars): {content_json.get('content', '')[:500]}...")
                except json.JSONDecodeError:
                    print(f"Raw text content (first 500 chars): {content_text[:500]}...")
            else:
                print("No content returned from chapter_index tool")
            
            # Test the get_chapter tool with parameter 1
            print("\nTesting get_chapter tool with chapter 1...")
            result = await client.call_tool("get_chapter", {"n": 1})
            
            # Process the response
            if result and len(result) > 0:
                content_text = result[0].text
                try:
                    content_json = json.loads(content_text)
                    print(f"Chapter 1 content (first 500 chars): {content_json.get('content', '')[:500]}...")
                except json.JSONDecodeError:
                    print(f"Raw text content (first 500 chars): {content_text[:500]}...")
            else:
                print("No content returned from get_chapter tool")
            
    except Exception as e:
        print(f"Error connecting to MCP server: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 