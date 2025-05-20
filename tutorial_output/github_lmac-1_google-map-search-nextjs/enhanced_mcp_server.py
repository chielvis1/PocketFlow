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
        default=os.environ.get("MCP_HOST", "localhost"),
        help="Host to bind to (default: localhost or MCP_HOST env var)"
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
        server_info = start_tutorial_mcp_server(
            str(tutorial_dir),
            host=args.host,
            port=args.port,
            debug=args.debug
        )
        
        # Log server info
        logger.info(f"Server started: {server_info}")
        
        # Print JSON server info to stdout for container orchestration
        import json
        server_json = {
            "mcpServers": [
                {
                    "name": "tutorial_mcp_server",
                    "transport": "http",
                    "host": args.host,
                    "port": args.port,
                    "status": server_info.get("status", "unknown"),
                    "tutorial_dir": str(tutorial_dir.absolute()),
                    "chapter_count": len(chapter_files)
                }
            ]
        }
        print(json.dumps(server_json, indent=2))
        
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