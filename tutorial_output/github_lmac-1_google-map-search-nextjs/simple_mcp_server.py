from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import urllib.parse
import json
import sys
import argparse
import logging
import time

# Configure basic logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcp_server.log')
    ]
)
logger = logging.getLogger("simple_mcp")

# Create metrics logger
metrics_logger = logging.getLogger("mcp_metrics")
metrics_logger.setLevel(logging.INFO)

# Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Simple MCP Server for Tutorial Documentation")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--log-file", type=str, default="mcp_server.log", help="Log file path (default: mcp_server.log)")
    parser.add_argument("--metrics-file", type=str, default="mcp_metrics.log", help="Metrics log file path (default: mcp_metrics.log)")
    return parser.parse_args()

# Use environment variable for the tutorial name instead of hardcoding
TUTORIAL_NAME = os.environ.get("TUTORIAL_NAME")
if not TUTORIAL_NAME:
    logger.error("Error: TUTORIAL_NAME environment variable not set")
    sys.exit(1)

# Construct the root directory dynamically
ROOT_DIR = f"/tutorials/{TUTORIAL_NAME}"
INDEX_FILE = "index.md"

class MCPRequestHandler(BaseHTTPRequestHandler):
    def log_request_metrics(self, status_code, path, duration_ms):
        """Log request metrics in a structured format"""
        metrics = {
            "timestamp": time.time(),
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "client_address": self.client_address[0]
        }
        metrics_logger.info(json.dumps(metrics))
    
    def do_GET(self):
        start_time = time.time()
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        logger.debug(f"Received GET request for path: {path}")

        status_code = 200
        try:
            if path == "/health":
                self.serve_health()
            elif path == "/mcp_spec":
                self.serve_mcp_spec()
            elif path == "/index":
                self.serve_index()
            elif path.startswith("/chapter/"):
                self.serve_chapter(path)
            else:
                logger.warning(f"Invalid path requested: {path}")
                status_code = 404
                self.send_error(404, "Not Found")
        except Exception as e:
            status_code = 500
            logger.error(f"Error processing request: {str(e)}")
            self.send_error(500, str(e))
        finally:
            # Calculate request duration and log metrics
            duration_ms = round((time.time() - start_time) * 1000, 2)
            self.log_request_metrics(status_code, path, duration_ms)

    def serve_health(self):
        logger.debug("Serving health check")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        response = json.dumps({"status": "ok"})
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def serve_mcp_spec(self):
        logger.debug("Serving MCP spec")
        spec_path = os.path.join(ROOT_DIR, "mcp_spec.yaml")
        if not os.path.isfile(spec_path):
            logger.error(f"MCP spec file not found at {spec_path}")
            self.send_error(404, "MCP spec file not found")
            return

        try:
            with open(spec_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/yaml")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            logger.debug(f"Successfully served MCP spec ({len(content)} bytes)")
        except Exception as e:
            logger.error(f"Error reading MCP spec file: {e}")
            self.send_error(500, f"Error reading MCP spec file: {e}")

    def serve_index(self):
        logger.debug("Serving index file")
        index_path = os.path.join(ROOT_DIR, INDEX_FILE)
        if not os.path.isfile(index_path):
            logger.error(f"Index file not found at {index_path}")
            self.send_error(404, "Index file not found")
            return

        try:
            with open(index_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            logger.debug(f"Successfully served index file ({len(content)} bytes)")
        except Exception as e:
            logger.error(f"Error reading index file: {e}")
            self.send_error(500, f"Error reading index file: {e}")

    def serve_chapter(self, path):
        logger.debug(f"Serving chapter from path: {path}")
        # Expecting /chapter/{number}
        parts = path.strip("/").split("/")
        if len(parts) != 2:
            logger.warning(f"Invalid chapter path format: {path}")
            self.send_error(404, "Invalid chapter path")
            return

        chapter_num = parts[1]
        if not chapter_num.isdigit():
            logger.warning(f"Invalid chapter number: {chapter_num}")
            self.send_error(400, "Invalid chapter number")
            return

        # Format chapter filename based on the actual files in the directory
        chapter_num_padded = chapter_num.zfill(2)
        # Look for files that match the pattern chapter_XX__*.md
        chapter_files = [f for f in os.listdir(ROOT_DIR) if f.startswith(f"chapter_{chapter_num_padded}_") and f.endswith(".md")]
        
        if not chapter_files:
            logger.error(f"Chapter {chapter_num} file not found")
            self.send_error(404, f"Chapter {chapter_num} file not found")
            return
            
        chapter_path = os.path.join(ROOT_DIR, chapter_files[0])
        logger.debug(f"Found chapter file: {chapter_path}")

        try:
            with open(chapter_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            logger.debug(f"Successfully served chapter {chapter_num} ({len(content)} bytes)")
        except Exception as e:
            logger.error(f"Error reading chapter file: {e}")
            self.send_error(500, f"Error reading chapter file: {e}")


def run(server_class=HTTPServer, handler_class=MCPRequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    
    # Print server information in JSON format for the main.py script to extract
    # Format it according to MCP specification with mcpServers as an object
    server_info = {
        "mcpServers": {
            TUTORIAL_NAME: {
                "host": "localhost",
                "port": port,
                "transport": "stdio",  # or "sse" if using Server-Sent Events
                "version": "1.0.0",
                "status": "running",
                "tutorial_path": ROOT_DIR,
                "endpoints": {
                    "health": "/health",
                    "spec": "/mcp_spec",
                    "index": "/index",
                    "chapter": "/chapter/{n}"
                },
                "command": f"python {os.path.basename(__file__)}"  # Include command for stdio transport
            }
        }
    }
    print(json.dumps(server_info, indent=2))
    sys.stdout.flush()  # Ensure output is visible in Docker logs
    
    logger.info(f"Starting MCP server on port {port} for tutorial: {TUTORIAL_NAME}...")
    sys.stdout.flush()  # Ensure output is visible in Docker logs
    httpd.serve_forever()


if __name__ == "__main__":
    args = parse_args()
    
    # Configure log file
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            # Remove the default file handler
            logger.removeHandler(handler)
    
    # Add new file handler with the specified log file path
    file_handler = logging.FileHandler(args.log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Configure metrics logging
    metrics_file_handler = logging.FileHandler(args.metrics_file)
    metrics_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    metrics_logger.addHandler(metrics_file_handler)
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    logger.info(f"Logs will be written to {args.log_file}")
    logger.info(f"Metrics will be written to {args.metrics_file}")
    
    # Run server with specified port
    run(port=args.port)