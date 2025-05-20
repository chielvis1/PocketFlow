# Tutorial Documentation MCP Server

This repository contains a Model Context Protocol (MCP) server designed to serve tutorial documentation in a machine-readable format, optimized for reverse engineering software blueprints.

## Features

- **Document Retrieval**: Access tutorial chapters and content
- **Document Structure Analysis**: Extract headings, sections, and code blocks
- **Blueprint Extraction**: Identify component hierarchies and data flow
- **Code Pattern Recognition**: Detect design patterns and function signatures
- **Semantic Understanding**: Search by concepts and generate technical glossaries

## Getting Started

### Prerequisites

- Python 3.8+
- Docker (optional, for containerized deployment)

### Installation

1. Clone this repository:

```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install dependencies:

```bash
pip install -r requirements.txt
pip install fastmcp pyyaml flask markdown-it-py beautifulsoup4 numpy scikit-learn
```

### Running the Server

#### Local Development

```bash
python enhanced_mcp_server.py --tutorial-dir ./path/to/tutorial
```

#### Docker Deployment

1. Build the Docker image:

```bash
docker build -t tutorial-mcp-server .
```

2. Run the container:

```bash
docker run -p 8000:8000 -v /path/to/tutorial:/tutorials tutorial-mcp-server
```

### Environment Variables

- `TUTORIAL_DIR`: Path to tutorial directory (default: `./tutorial`)
- `MCP_HOST`: Host to bind to (default: `localhost`)
- `MCP_PORT`: Port to listen on (default: `8000`)
- `CACHE_TIMEOUT`: Cache timeout in seconds (default: `300`)
- `ENABLE_ADVANCED_FEATURES`: Enable advanced analysis features (default: `true`)

## Tutorial Directory Structure

The MCP server expects the following structure in the tutorial directory:

```
tutorial/
├── index.md                     # Main index file
├── chapter_01__Introduction.md  # First chapter
├── chapter_02__Getting_Started.md
└── ...                          # Additional chapters
```

## API Usage

### Document Retrieval

```bash
# Get the tutorial index
curl http://localhost:8000/chapter_index

# Get a specific chapter
curl http://localhost:8000/get_chapter?n=1

# Get the complete tutorial
curl http://localhost:8000/get_complete_tutorial
```

### Document Structure Analysis

```bash
# Analyze document structure
curl -X POST http://localhost:8000/analyze_document_structure -d '{"chapter_num": 1}'

# Extract code samples
curl -X POST http://localhost:8000/extract_code_samples -d '{"chapter_num": 1, "language": "typescript"}'

# Generate document outline
curl http://localhost:8000/generate_document_outline
```

### Blueprint Extraction

```bash
# Extract component diagrams
curl http://localhost:8000/extract_component_diagrams

# Extract data flow
curl http://localhost:8000/extract_data_flow

# Extract API interfaces
curl http://localhost:8000/extract_api_interfaces
```

### Code Pattern Recognition

```bash
# Identify design patterns
curl -X POST http://localhost:8000/identify_design_patterns -d '{"chapter_num": 1}'

# Extract function signatures
curl -X POST http://localhost:8000/extract_function_signatures -d '{"chapter_num": 1}'

# Analyze dependencies
curl http://localhost:8000/analyze_dependencies
```

### Semantic Understanding

```bash
# Generate technical glossary
curl http://localhost:8000/technical_glossary

# Search by concept
curl -X POST http://localhost:8000/search_by_concept -d '{"concept": "React"}'

# Find related concepts
curl -X POST http://localhost:8000/related_concepts -d '{"concept": "Component"}'
```

## License

[MIT License](LICENSE)


