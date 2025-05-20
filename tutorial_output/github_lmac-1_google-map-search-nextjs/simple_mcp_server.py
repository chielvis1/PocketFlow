from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import urllib.parse
import json
import sys

# Use environment variable for the tutorial name instead of hardcoding
TUTORIAL_NAME = os.environ.get("TUTORIAL_NAME")
if not TUTORIAL_NAME:
    print("Error: TUTORIAL_NAME environment variable not set")
    sys.exit(1)

# Construct the root directory dynamically
ROOT_DIR = f"/tutorials/{TUTORIAL_NAME}"
INDEX_FILE = "index.md"

class MCPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == "/health":
            self.serve_health()
        elif path == "/mcp_spec":
            self.serve_mcp_spec()
        elif path == "/index":
            self.serve_index()
        elif path.startswith("/chapter/"):
            self.serve_chapter(path)
        else:
            self.send_error(404, "Not Found")

    def serve_health(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        response = json.dumps({"status": "ok"})
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def serve_mcp_spec(self):
        spec_path = os.path.join(ROOT_DIR, "mcp_spec.yaml")
        if not os.path.isfile(spec_path):
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
        except Exception as e:
            self.send_error(500, f"Error reading MCP spec file: {e}")

    def serve_index(self):
        index_path = os.path.join(ROOT_DIR, INDEX_FILE)
        if not os.path.isfile(index_path):
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
        except Exception as e:
            self.send_error(500, f"Error reading index file: {e}")

    def serve_chapter(self, path):
        # Expecting /chapter/{number}
        parts = path.strip("/").split("/")
        if len(parts) != 2:
            self.send_error(404, "Invalid chapter path")
            return

        chapter_num = parts[1]
        if not chapter_num.isdigit():
            self.send_error(400, "Invalid chapter number")
            return

        # Format chapter filename based on the actual files in the directory
        chapter_num_padded = chapter_num.zfill(2)
        # Look for files that match the pattern chapter_XX__*.md
        chapter_files = [f for f in os.listdir(ROOT_DIR) if f.startswith(f"chapter_{chapter_num_padded}_") and f.endswith(".md")]
        
        if not chapter_files:
            self.send_error(404, f"Chapter {chapter_num} file not found")
            return
            
        chapter_path = os.path.join(ROOT_DIR, chapter_files[0])

        try:
            with open(chapter_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
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
    
    print(f"Starting MCP server on port {port} for tutorial: {TUTORIAL_NAME}...")
    sys.stdout.flush()  # Ensure output is visible in Docker logs
    httpd.serve_forever()


if __name__ == "__main__":
    run()