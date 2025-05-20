#!/bin/bash

# Cleanup script to remove unnecessary test files

echo "Cleaning up test files..."

# Remove old test files
rm -f test_mcp.py
rm -f test_mcp_client.py
rm -f test_tutorial_mcp.py

# Remove Docker files
rm -f Dockerfile.client
rm -f Dockerfile.client.tmp

echo "Cleanup complete!" 