#!/usr/bin/env python3
"""
Enhanced MCP Server for Tutorial Documentation

This script runs an MCP server that serves tutorial documentation with
advanced features for blueprint extraction and code analysis.
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tutorial_mcp_server.log')
    ]
)
logger = logging.getLogger("enhanced_mcp")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run an enhanced MCP server for tutorial documentation")
    
    # First check for TUTORIAL_NAME environment variable (used in Docker)
    tutorial_name = os.environ.get("TUTORIAL_NAME")
    default_tutorial_dir = f"/tutorials/{tutorial_name}" if tutorial_name else os.environ.get("TUTORIAL_DIR", "./tutorial")
    
    parser.add_argument(
        "--tutorial-dir",
        type=str,
        default=default_tutorial_dir,
        help="Directory containing tutorial markdown files (default: from TUTORIAL_NAME or TUTORIAL_DIR env var)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0 or MCP_HOST env var)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8000")),
        help="Port to listen on (default: 8000 or MCP_PORT env var)"
    )
    
    parser.add_argument(
        "--cache-timeout",
        type=int,
        default=int(os.environ.get("CACHE_TIMEOUT", "300")),
        help="Cache timeout in seconds (default: 300 or CACHE_TIMEOUT env var)"
    )
    
    parser.add_argument(
        "--enable-advanced-features",
        action="store_true",
        default=os.environ.get("ENABLE_ADVANCED_FEATURES", "true").lower() == "true",
        help="Enable advanced analysis features (default: true or ENABLE_ADVANCED_FEATURES env var)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    return parser.parse_args()

def get_tool_descriptions():
    """Get descriptions of all available tools"""
    # Basic tools
    tools = [
        {
            "name": "chapter_index",
            "description": "Returns the tutorial index markdown",
            "parameters": {},
            "returns": {"content": "Markdown content", "format": "markdown"}
        },
        {
            "name": "get_chapter",
            "description": "Returns one chapter's markdown by number",
            "parameters": {"n": "Chapter number (integer)"},
            "returns": {"content": "Markdown content", "format": "markdown", "chapter_number": "Integer"}
        },
        {
            "name": "get_complete_tutorial",
            "description": "Returns the complete tutorial markdown",
            "parameters": {},
            "returns": {"content": "Markdown content", "format": "markdown"}
        },
        {
            "name": "analyze_document_structure",
            "description": "Analyzes document structure of a specific chapter",
            "parameters": {"chapter_num": "Chapter number (integer)"},
            "returns": {
                "headings": "List of heading objects with level, text, and line number",
                "sections": "List of section objects with heading and content",
                "codeBlocks": "List of code block objects with language and code"
            }
        },
        {
            "name": "extract_code_samples",
            "description": "Extracts code samples from a chapter with optional language filtering",
            "parameters": {
                "chapter_num": "Chapter number (integer)",
                "language": "Optional programming language filter (string)"
            },
            "returns": {
                "samples": "List of code samples with language and code",
                "count": "Number of samples found"
            }
        },
        {
            "name": "generate_document_outline",
            "description": "Creates hierarchical representation of document structure",
            "parameters": {},
            "returns": {"outline": "List of chapters with headings"}
        },
        {
            "name": "extract_component_diagrams",
            "description": "Identifies React component hierarchies from documentation",
            "parameters": {},
            "returns": {
                "components": "Dictionary of component names to component info",
                "graph": "Component relationship graph with nodes and edges"
            }
        },
        {
            "name": "extract_data_flow",
            "description": "Analyzes and visualizes data flow between components",
            "parameters": {},
            "returns": {
                "dataFlows": "List of data flow descriptions",
                "components": "List of component names"
            }
        },
        {
            "name": "extract_api_interfaces",
            "description": "Identifies API interfaces and data structures",
            "parameters": {},
            "returns": {
                "interfaces": "List of interface definitions",
                "count": "Number of interfaces found"
            }
        }
    ]
    
    # Advanced tools
    advanced_tools = [
        {
            "name": "identify_design_patterns",
            "description": "Detects common software design patterns in code samples",
            "parameters": {"chapter_num": "Chapter number (integer)"},
            "returns": {
                "results": "List of results with language and patterns",
                "count": "Number of patterns found"
            }
        },
        {
            "name": "extract_function_signatures",
            "description": "Parses and categorizes function definitions",
            "parameters": {"chapter_num": "Chapter number (integer)"},
            "returns": {
                "results": "List of results with language and functions",
                "count": "Number of functions found"
            }
        },
        {
            "name": "analyze_dependencies",
            "description": "Maps relationships between components/modules",
            "parameters": {},
            "returns": {
                "graph": "Dependency graph with nodes and edges",
                "nodeCount": "Number of nodes",
                "edgeCount": "Number of edges"
            }
        },
        {
            "name": "technical_glossary",
            "description": "Extracts and defines technical terms used in the documentation",
            "parameters": {},
            "returns": {
                "glossary": "Dictionary of terms to definitions",
                "count": "Number of terms"
            }
        },
        {
            "name": "search_by_concept",
            "description": "Allows searching by technical concepts rather than just keywords",
            "parameters": {"concept": "Technical concept to search for (string)"},
            "returns": {
                "results": "List of search results with chapter and matches",
                "totalMatches": "Total number of matches"
            }
        },
        {
            "name": "related_concepts",
            "description": "Finds related technical concepts within documentation",
            "parameters": {"concept": "Technical concept to find related concepts for (string)"},
            "returns": {
                "concept": "Original concept",
                "related": "List of related concepts with term, definition, and relevance",
                "count": "Number of related concepts"
            }
        }
    ]
    
    # Combine basic and advanced tools
    return tools + advanced_tools

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Validate tutorial directory
    tutorial_dir = Path(args.tutorial_dir)
    logger.info(f"Checking tutorial directory: {tutorial_dir} (absolute: {tutorial_dir.absolute()})")
    
    if not tutorial_dir.exists():
        logger.error(f"Tutorial directory not found: {tutorial_dir}")
        # List parent directory contents to help debug
        parent_dir = tutorial_dir.parent
        if parent_dir.exists():
            logger.error(f"Contents of parent directory {parent_dir}:")
            for item in parent_dir.iterdir():
                logger.error(f"  {item.name} ({'dir' if item.is_dir() else 'file'})")
        sys.exit(1)
    
    # Check for index file
    index_file = tutorial_dir / "index.md"
    if not index_file.exists():
        logger.error(f"Index file not found: {index_file}")
        # List tutorial directory contents to help debug
        logger.error(f"Contents of tutorial directory {tutorial_dir}:")
        for item in tutorial_dir.iterdir():
            logger.error(f"  {item.name} ({'dir' if item.is_dir() else 'file'})")
        sys.exit(1)
    
    # Check for chapter files
    chapter_files = list(tutorial_dir.glob("chapter_*__*.md"))
    if not chapter_files:
        logger.error(f"No chapter files found in {tutorial_dir}")
        # List all markdown files in the directory
        md_files = list(tutorial_dir.glob("*.md"))
        if md_files:
            logger.error(f"Found {len(md_files)} markdown files with different naming pattern:")
            for md_file in md_files:
                logger.error(f"  {md_file.name}")
        sys.exit(1)
    
    logger.info(f"Found {len(chapter_files)} chapter files in {tutorial_dir}")
    
    # Import tutorial MCP server
    try:
        # Try relative import first (when installed as a package)
        try:
            from utils.tutorial_mcp import start_tutorial_mcp_server
        except ImportError:
            # Fall back to absolute import (when run directly)
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from utils.tutorial_mcp import start_tutorial_mcp_server
        
        # Start server
        logger.info(f"Starting tutorial MCP server on {args.host}:{args.port}")
        
        # Redirect stdout temporarily to prevent any output from start_tutorial_mcp_server
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        
        try:
            server_info = start_tutorial_mcp_server(
                str(tutorial_dir),
                host=args.host,
                port=args.port,
                debug=args.debug
            )
        finally:
            # Restore stdout
            sys.stdout.close()
            sys.stdout = original_stdout
        
        # Log server info but don't print to stdout
        logger.info(f"Server started: {server_info}")
        
        # Get tool descriptions
        tool_descriptions = get_tool_descriptions()
        
        # Create MCP config according to proper MCP JSON format
        # mcpServers must be an object with server names as keys
        mcp_config = {
            "mcpServers": {
                "tutorial_mcp_server": {
                    "transport": "http",
                    "host": args.host,
                    "port": args.port,
                    "status": server_info.get("status", "unknown"),
                    "tutorial_dir": str(tutorial_dir.absolute()),
                    "chapter_count": len(chapter_files)
                }
            },
            "tools": tool_descriptions
        }
        
        # Print ONLY the JSON - no other text or markers
        # This is critical for proper MCP integration
        print(json.dumps(mcp_config, indent=2))
        
        # Keep the script running
        if server_info.get("status") == "running":
            try:
                logger.info("Server is running. Press Ctrl+C to stop.")
                # If there's a process object, wait for it
                process = server_info.get("process")
                if process and hasattr(process, "wait"):
                    process.wait()
                else:
                    # Otherwise, just keep the script running
                    import time
                    while True:
                        time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal. Shutting down...")
        else:
            logger.error(f"Server failed to start: {server_info}")
            sys.exit(1)
    
    except ImportError as e:
        logger.error(f"Failed to import required modules: {str(e)}")
        logger.error("Please ensure fastmcp is installed: pip install fastmcp")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 