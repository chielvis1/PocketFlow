#!/usr/bin/env python3
import asyncio
import sys
import json
from fastmcp import Client

async def main():
    server_url = "http://host.docker.internal:8000/mcp"
    print(f"Connecting to MCP server at {server_url}")
    
    try:
        async with Client(server_url) as client:
            # List available tools
            tools = await client.list_tools()
            print(f"Available tools: {[tool.name for tool in tools]}")
            
            # Test chapter_index tool
            print("\nTesting chapter_index tool...")
            result = await client.call_tool("chapter_index")
            content = result[0].text
            try:
                content_json = json.loads(content)
                print(f"Chapter index content: {content_json.get('content', '')}")
            except:
                print(f"Raw content: {content[:200]}...")
            
            # Test get_chapter tool
            print("\nTesting get_chapter tool...")
            result = await client.call_tool("get_chapter", {"n": 1})
            content = result[0].text
            try:
                content_json = json.loads(content)
                print(f"Chapter content: {content_json.get('content', '')[:200]}...")
            except:
                print(f"Raw content: {content[:200]}...")
            
            # Test analyze_document_structure tool
            print("\nTesting analyze_document_structure tool...")
            result = await client.call_tool("analyze_document_structure", {"chapter_num": 1})
            content = result[0].text
            try:
                content_json = json.loads(content)
                headings = content_json.get("headings", [])
                sections = content_json.get("sections", [])
                code_blocks = content_json.get("codeBlocks", [])
                print(f"Found {len(headings)} headings, {len(sections)} sections, {len(code_blocks)} code blocks")
            except:
                print(f"Raw content: {content[:200]}...")
            
            # Test extract_code_samples tool
            print("\nTesting extract_code_samples tool...")
            result = await client.call_tool("extract_code_samples", {"chapter_num": 1})
            content = result[0].text
            try:
                content_json = json.loads(content)
                samples = content_json.get("samples", [])
                count = content_json.get("count", 0)
                print(f"Found {count} code samples")
            except:
                print(f"Raw content: {content[:200]}...")
            
    except Exception as e:
        print(f"Error connecting to MCP server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
