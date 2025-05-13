# Repository Analysis to MCP Server Agent

This project implements an agent that analyzes GitHub repositories based on user requirements and creates an MCP (Model-Controller-Presenter) server with implementation guides. The agent uses the PocketFlow framework to orchestrate the workflow.

## Features

- Extracts keywords, tech stack, and features from user queries
- Searches the web and YouTube for relevant GitHub repositories
- Filters and ranks repositories based on quality and relevance
- Performs detailed analysis of selected repositories
- Generates implementation guides tailored to the user's tech stack
- Creates and starts an MCP server providing access to the guides

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up required API keys as environment variables:
   ```
   export OPENAI_API_KEY=<your-openai-api-key>
   export SERPAPI_API_KEY=<your-serpapi-api-key>
   export GITHUB_TOKEN=<your-github-token>
   ```

## Usage

Run the agent with a query:

```
python main.py "authentication in Node.js with JWT"
```

Or start it interactively:

```
python main.py
```

For verbose logging, use the `-v` flag:

```
python main.py -v
```

## Architecture

The project follows the PocketFlow design patterns:

- **Nodes**: Individual processing steps defined in `nodes.py`
- **Flow**: Connected nodes that form the agent workflow in `flow.py`
- **Shared Store**: Communication between nodes via shared dictionary
- **Utilities**: External API and helper functions in `utils/`

The agent workflow consists of these main phases:
1. Query analysis and search
2. Repository discovery and filtering
3. Detailed repository analysis
4. Implementation guide generation
5. MCP server creation and deployment

## Utility Functions

- **LLM Integration**: OpenAI and Anthropic API wrappers
- **Search**: Web and YouTube search using SerpAPI
- **GitHub**: Repository analysis using GitHub API
- **Data Processing**: Formatting and presenting data to users
- **MCP**: Server creation and management
- **Monitoring**: Logging and performance tracking

## Dependencies

- pocketflow: Core framework for node and flow orchestration
- openai: OpenAI API client for GPT models
- anthropic: Anthropic API client for Claude models
- google-search-results: SerpAPI client for web search
- requests: HTTP client for GitHub API
- pyyaml: YAML parsing for structured data

## License

[Specify license information here] 