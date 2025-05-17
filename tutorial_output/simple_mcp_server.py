import os
import urllib
from http.server import SimpleHTTPRequestHandler, HTTPServer

BASE_DIR = os.path.join(os.path.dirname(__file__), 'tutorial_output')

class TutorialHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path_parts = parsed.path.strip('/').split('/')
        
        # /index
        if parsed.path == '/index':
            file_path = os.path.join(BASE_DIR, 'index.md')
        # /chapter/{number}
        elif len(path_parts) == 2 and path_parts[0] == 'chapter':
            num = path_parts[1]
            file_path = os.path.join(BASE_DIR, f'chapter{num}.md')
        else:
            self.send_error(404, "Not Found")
            return

        if os.path.isfile(file_path):
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/markdown; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except IOError:
                self.send_error(500, "Internal Server Error")
        else:
            self.send_error(404, "File Not Found")

if __name__ == '__main__':
    port = 8000
    server = HTTPServer(('0.0.0.0', port), TutorialHandler)
    print(f"Serving tutorial_output on http://0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nServer stopped.")