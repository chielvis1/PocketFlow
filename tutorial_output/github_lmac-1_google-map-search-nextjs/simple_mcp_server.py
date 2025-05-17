import os
from flask import Flask, abort, send_file, Response

app = Flask(__name__)

BASE_DIR = "tutorial_output/github_lmac-1_google-map-search-nextjs"

@app.route('/index', methods=['GET'])
def serve_index():
    index_path = os.path.join(BASE_DIR, "index.md")
    if not os.path.isfile(index_path):
        abort(404, description="index.md not found")
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return Response(content, mimetype='text/markdown')

@app.route('/chapter/<int:chapter_number>', methods=['GET'])
def serve_chapter(chapter_number):
    # Construct chapter filename, assuming format like 'chapter1.md', 'chapter2.md', etc.
    chapter_filename = f"chapter{chapter_number}.md"
    chapter_path = os.path.join(BASE_DIR, chapter_filename)
    if not os.path.isfile(chapter_path):
        abort(404, description=f"{chapter_filename} not found")
    with open(chapter_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return Response(content, mimetype='text/markdown')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)