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

When you run main.py, the GitHub Repository Finder executes a flow of operations designed to find relevant GitHub repositories based on your query. Here's what happens in the entire flow:

1. **Command-line argument parsing**:
   - The script parses command-line arguments like `--interactive`, `--no-youtube`, `--web-count`, etc.
   - If no query is provided, it prompts you to enter one.

2. **Flow Initialization**:
   - The main flow is created using `create_repo_analyzer_flow()`
   - A shared data dictionary is initialized with your query and config options

3. **Execution modes**:
   - **Interactive mode** (`--interactive`): Runs the interactive search UI where you can specify keywords, tech stack, and features, then skips directly to repository quality checks.
   - **Standard mode**: Follows the full flow starting with query analysis.

4. **The full flow sequence**:

   a. **Skip Search Decision**:
      - Checks if `skip_search=True` (set in interactive mode)
      - If true, jumps directly to repository checking
      - If false, continues with query analysis

   b. **Query Analysis**:
      - Analyzes your query using LLM to extract keywords, tech stack, and features
      - If sufficient details are extracted, proceeds to search
      - If details are insufficient, asks you to clarify your query

   c. **Parallel Search**:
      - Performs parallel searches across web and YouTube based on your configuration
      - Uses `search_and_scrape` function with retry mechanism for handling 403 errors
      - Rotates user agents to avoid blocking
      - Reports search statistics like scraping success rate and content relevance
      - Stores results in shared data dictionary

   d. **Repository Checking**:
      - Takes the GitHub URLs found during search
      - Checks repository complexity, quality, and size
      - Filters repositories based on quality criteria

   e. **Repository Display**:
      - Shows you a list of repositories with quality metrics
      - If no quality repositories are found, can show all repositories

   f. **Repository Selection**:
      - Prompts you to select a repository to analyze
      - Stores your selection in shared data

   g. **Repository Analysis**:
      - Analyzes the selected repository in depth
      - If analysis fails, returns to repository display
      - Uses LLM to further analyze the repository's usefulness

   h. **Implementation Guide Generation**:
      - Generates implementation guides based on repository analysis
      - Formats the data for MCP server creation

   i. **MCP Server Creation and Startup**:
      - Creates an MCP server with the guides and tools
      - Starts the MCP server
      - If server startup fails, reports the error

   j. **Process Completion**:
      - Presents final results with server information
      - Shows implementation guides available through the MCP API

5. **Error Handling**:
   - Throughout the flow, errors are handled gracefully
   - If repositories aren't found, you're prompted to refine your query
   - The scraping system has built-in retry mechanism with 5-second delays
   - Failed scrapes are tracked and reported

6. **Interactive Branching**:
   - At several points, the flow may branch based on your inputs
   - You can select repositories, clarify queries, or retry searches

The flow is designed as a directed graph using PocketFlow's action-based transitions, allowing it to adapt to different scenarios and user inputs while maintaining a coherent process from search to final repository analysis.
