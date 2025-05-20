#!/usr/bin/env python3
"""
Script to run a FastMCP client in a Docker container
"""

import asyncio
import os
import json
import sys
import subprocess
from fastmcp import Client

def create_docker_client():
    """Create a Docker client container with proper platform compatibility"""
    # Create a temporary Dockerfile
    dockerfile_content = """FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

# Install dependencies
RUN pip install fastmcp requests

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Copy the client script
COPY test_fastmcp_client.py .

# Run the client with proper error handling
CMD ["python", "-u", "test_fastmcp_client.py"]
"""
    
    with open("Dockerfile.client.tmp", "w") as f:
        f.write(dockerfile_content)
    
    try:
        # Build the client Docker image
        print("Building FastMCP client Docker image...")
        subprocess.run(["docker", "build", "--platform", "linux/amd64", "-t", "fastmcp-client", "-f", "Dockerfile.client.tmp", "."], check=True)
        
        # Run the client Docker container
        print("Running FastMCP client Docker container...")
        subprocess.run(["docker", "run", "--rm", "--add-host=host.docker.internal:host-gateway", "fastmcp-client"], check=True)
    
    finally:
        # Clean up the temporary Dockerfile
        if os.path.exists("Dockerfile.client.tmp"):
            os.remove("Dockerfile.client.tmp")

async def format_tool_response(tool_name, result):
    """Format the response from a tool based on its type"""
    if not result or len(result) == 0:
        return "No content returned"
    
    # Access the first TextContent object's text attribute
    content_text = result[0].text
    
    # Try to parse as JSON
    try:
        content_json = json.loads(content_text)
        
        # Format based on tool type
        if tool_name in ["chapter_index", "get_chapter", "get_complete_tutorial"]:
            # Document retrieval tools
            return f"Content (first 200 chars): {content_json.get('content', '')[:200]}..."
        
        elif tool_name == "analyze_document_structure":
            # Structure analysis
            headings = content_json.get("headings", [])
            sections = content_json.get("sections", [])
            code_blocks = content_json.get("codeBlocks", [])
            return f"Found {len(headings)} headings, {len(sections)} sections, {len(code_blocks)} code blocks"
        
        elif tool_name == "extract_code_samples":
            # Code samples
            samples = content_json.get("samples", [])
            count = content_json.get("count", 0)
            return f"Found {count} code samples"
        
        elif tool_name in ["extract_component_diagrams", "extract_data_flow"]:
            # Component analysis
            components = content_json.get("components", {})
            return f"Found {len(components)} components"
        
        elif tool_name == "extract_api_interfaces":
            # API interfaces
            interfaces = content_json.get("interfaces", [])
            count = content_json.get("count", 0)
            return f"Found {count} interfaces"
        
        elif tool_name in ["identify_design_patterns", "extract_function_signatures"]:
            # Code patterns
            results = content_json.get("results", [])
            count = content_json.get("count", 0)
            return f"Found {count} results"
        
        elif tool_name == "technical_glossary":
            # Glossary
            glossary = content_json.get("glossary", {})
            count = content_json.get("count", 0)
            return f"Found {count} terms in glossary"
        
        elif tool_name in ["search_by_concept", "related_concepts"]:
            # Search results
            if "results" in content_json:
                results = content_json.get("results", [])
                total_matches = content_json.get("totalMatches", 0)
                return f"Found {total_matches} matches"
            elif "related" in content_json:
                related = content_json.get("related", [])
                count = content_json.get("count", 0)
                return f"Found {count} related concepts"
        
        # Default: return a summary of the JSON
        return f"Response: {str(content_json)[:200]}..."
    
    except json.JSONDecodeError:
        # If not valid JSON, return raw text
        return f"Raw text (first 200 chars): {content_text[:200]}..."

async def test_tool(client, tool_name, params=None):
    """Test a specific tool and print the result"""
    print(f"\nTesting {tool_name} tool...")
    try:
        if params is None:
            params = {}
        
        # Call the tool
        result = await client.call_tool(tool_name, params)
        
        # Format and print the response
        response_summary = await format_tool_response(tool_name, result)
        print(f"Result: {response_summary}")
        return True
    except Exception as e:
        print(f"Error testing {tool_name}: {e}")
        return False

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
            
            # Test basic document retrieval tools
            await test_tool(client, "chapter_index")
            await test_tool(client, "get_chapter", {"n": 1})
            
            # Test structure analysis tools
            try:
                await test_tool(client, "analyze_document_structure", {"chapter_num": 1})
                await test_tool(client, "extract_code_samples", {"chapter_num": 1})
                await test_tool(client, "generate_document_outline")
            except Exception as e:
                print(f"Error with structure analysis tools: {e}")
            
            # Test component analysis tools
            try:
                await test_tool(client, "extract_component_diagrams")
                await test_tool(client, "extract_data_flow")
                await test_tool(client, "extract_api_interfaces")
            except Exception as e:
                print(f"Error with component analysis tools: {e}")
            
            # Test advanced tools if available
            advanced_tools = [
                ("identify_design_patterns", {"chapter_num": 1}),
                ("extract_function_signatures", {"chapter_num": 1}),
                ("analyze_dependencies", {}),
                ("technical_glossary", {}),
                ("search_by_concept", {"concept": "React"}),
                ("related_concepts", {"concept": "Component"})
            ]
            
            for tool_name, params in advanced_tools:
                try:
                    if tool_name in [t.name for t in tools]:
                        await test_tool(client, tool_name, params)
                except Exception as e:
                    print(f"Error with advanced tool {tool_name}: {e}")
            
    except Exception as e:
        print(f"Error connecting to MCP server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if we're running in a Docker container
    if os.path.exists("/.dockerenv"):
        # We're inside Docker, run the client
        asyncio.run(main())
    else:
        # We're not in Docker, create a Docker client
        create_docker_client() 