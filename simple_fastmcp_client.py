#!/usr/bin/env python3
"""
Simple FastMCP client to test the tutorial MCP server
"""

import os
import subprocess
import tempfile

def create_docker_client():
    """Create a Docker client container with proper platform compatibility"""
    # Create a temporary Dockerfile
    dockerfile_content = """FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

# Install dependencies
RUN pip install fastmcp requests

# Copy the test client script
COPY - /app/test_client.py
RUN chmod +x /app/test_client.py

# Run the client with proper error handling
CMD ["python", "-u", "/app/test_client.py"]
"""
    
    # Create test client script
    test_client_script = """#!/usr/bin/env python3
import asyncio
import sys
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
            print("\\nTesting chapter_index tool...")
            result = await client.call_tool("chapter_index")
            print(f"Response type: {type(result)}")
            print(f"Response: {result}")
            
            # Get the first 500 characters of the content
            content = result[0].text
            print(f"\\nFirst 500 characters of chapter_index content:")
            print(content[:500] + "..." if len(content) > 500 else content)
            
    except Exception as e:
        print(f"Error connecting to MCP server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
"""
    
    # Write Dockerfile and test client script to temporary files
    with tempfile.NamedTemporaryFile(prefix='dockerfile_', suffix='.tmp', delete=False) as f:
        f.write(dockerfile_content.encode('utf-8'))
        dockerfile_path = f.name
    
    with tempfile.NamedTemporaryFile(prefix='test_client_', suffix='.py', delete=False) as f:
        f.write(test_client_script.encode('utf-8'))
        test_client_path = f.name
    
    try:
        # Build the client Docker image
        print("Building FastMCP client Docker image...")
        subprocess.run([
            "docker", "build", 
            "--platform", "linux/amd64", 
            "-t", "fastmcp-client", 
            "-f", dockerfile_path,
            "--build-arg", f"TEST_CLIENT={test_client_path}", 
            "."
        ], check=True)
        
        # Run the client Docker container
        print("Running FastMCP client Docker container...")
        subprocess.run([
            "docker", "run", 
            "--rm", 
            "--add-host=host.docker.internal:host-gateway", 
            "fastmcp-client"
        ], check=True)
    
    finally:
        # Clean up the temporary files
        if os.path.exists(dockerfile_path):
            os.remove(dockerfile_path)
        if os.path.exists(test_client_path):
            os.remove(test_client_path)

if __name__ == "__main__":
    create_docker_client() 