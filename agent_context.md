# GitHub Repository Finder Agent: Context and Architecture

## Overview
The GitHub Repository Finder is an agent built using the PocketFlow framework that searches for relevant GitHub repositories based on user queries. It uses both web search and YouTube search to find and extract GitHub URLs, focusing on repositories that match the user's requirements for technologies, keywords, and features.

## Key Files and Their Purposes

### Core System Files
1. `/home/vboxuser/Documents/mnt/PocketFlow/pocketflow/__init__.py`
   - The core PocketFlow framework (100-line minimalist LLM framework)
   - Provides Node, Flow, BatchNode, AsyncNode, and other core abstractions

2. `/home/vboxuser/Documents/mnt/PocketFlow/utils/search.py`
   - The main module we've been modifying
   - Handles web and YouTube searches using external libraries
   - Provides methods to scrape content and extract GitHub URLs
   - Includes functions for interactive user input and result display

3. `/home/vboxuser/Documents/mnt/PocketFlow/utils/github.py`
   - Contains utilities for extracting GitHub URLs from text content
   - Helps analyze GitHub repositories for complexity and size
   - Provides functionality to analyze repository contents

4. `/home/vboxuser/Documents/mnt/PocketFlow/utils/llm.py`
   - Handles communication with various LLM providers
   - Provides utilities for prompt construction and response parsing
   - Used throughout the system for text analysis and generation

5. `/home/vboxuser/Documents/mnt/PocketFlow/utils/monitoring.py`
   - Provides execution time logging for performance monitoring
   - Contains the `log_execution_time` decorator used in search functions

6. `/home/vboxuser/Documents/mnt/PocketFlow/utils/data_processing.py`
   - Handles data formatting and processing
   - Generates implementation guides from repository analysis
   - Formats repository lists for user selection

7. `/home/vboxuser/Documents/mnt/PocketFlow/utils/mcp.py`
   - MCP (Modular Computation Protocol) server utilities
   - Creates and manages MCP servers for repository analysis

8. `/home/vboxuser/Documents/mnt/PocketFlow/nodes.py`
   - Contains PocketFlow node definitions for the agent
   - Implements nodes for query analysis, search, filtering, etc.

9. `/home/vboxuser/Documents/mnt/PocketFlow/flow.py`
   - Defines the flow connections between nodes
   - Creates the overall agent workflow

10. `/home/vboxuser/Documents/mnt/PocketFlow/main.py`
    - Entry point for the application
    - Initializes and runs the flow with the shared data store

11. `/home/vboxuser/Documents/mnt/PocketFlow/requirements.txt`
    - Lists all dependencies required by the agent:
      - pocketflow, openai, anthropic, google-generativeai
      - requests, pyyaml, python-dotenv
      - yt-dlp for YouTube search/scraping
      - Search-Engines-Scraper for web search
      - beautifulsoup4 for HTML parsing

### External Tools Integrated

1. **yt-dlp**
   - Used for YouTube video search and metadata extraction
   - Extracts video descriptions, comments, and other metadata
   - Helps find GitHub URLs mentioned in video descriptions or comments

2. **Search-Engines-Scraper**
   - Performs web searches across multiple search engines
   - Extracts search results including titles, URLs, and snippets
   - Used to find web pages that might contain GitHub URLs

3. **BeautifulSoup4**
   - Parses HTML content from web pages
   - Extracts links, code blocks, and other content
   - Helps identify GitHub URLs in web content

## Data Flow and Process

### 1. User Input Phase
- User provides a search query and optional filtering parameters:
  - Keywords for filtering
  - Technologies/frameworks (tech stack)
  - Desired features
  - Number of YouTube videos to analyze
  - Number of web pages to analyze

### 2. Search Phase
- **YouTube Search**:
  - Uses yt-dlp to search for relevant videos
  - Enhances query with keywords, tech stack, and features
  - Extracts video metadata including any GitHub URLs in descriptions

- **Web Search**:
  - Uses Search-Engines-Scraper to search across multiple engines
  - Enhances query with keywords, tech stack, and features
  - Collects search results with titles, URLs, and snippets

### 3. Content Relevance Analysis
- Analyzes search results for relevance to user's requirements
- Scores content based on:
  - Presence of GitHub URLs (40% weight)
  - Matching features (30% weight)
  - Matching tech stack (20% weight)
  - Matching keywords (10% weight)
- Filters out low-relevance content

### 4. Content Scraping
- For relevant YouTube videos:
  - Scrapes full video descriptions and comments
  - Extracts GitHub URLs and other repository references

- For relevant web pages:
  - Scrapes HTML content using requests and BeautifulSoup
  - Extracts links, code blocks, and GitHub URLs
  - Analyzes content for repository references

### 5. Result Presentation
- Displays YouTube results with GitHub URLs
- Displays web page results with GitHub URLs
- Shows total unique GitHub repositories found
- Lists all extracted GitHub URLs

## PocketFlow Pattern Implementation

The system follows these PocketFlow patterns:

1. **Node Pattern**:
   - Each task is encapsulated in a Node with prep-exec-post lifecycle
   - YouTube search, web search, and scraping are all handled by dedicated nodes

2. **BatchNode Pattern**:
   - Used to process multiple search results in parallel
   - Filters and analyzes search results batch-wise

3. **Workflow Pattern**:
   - Chains multiple nodes into a sequential pipeline
   - Connects query analysis → search → filtering → scraping → presentation

4. **MapReduce Pattern**:
   - Maps the search query to multiple sources (YouTube, web)
   - Reduces results by filtering and deduplicating GitHub URLs

5. **Utility Functions**:
   - External tools (yt-dlp, Search-Engines-Scraper) are wrapped as utilities
   - Clear separation between core logic and external tool integration

## Future Enhancements

1. **Repository Analysis**:
   - In-depth analysis of found repositories
   - Code quality assessment, activity metrics, contributor analysis

2. **MCP Integration**:
   - Packaging analysis results into MCP servers
   - Providing implementation guides based on repository analysis

3. **Parallel Processing**:
   - Implementing AsyncParallelBatchNode for concurrent processing
   - Improving performance for large numbers of search results

4. **User Feedback**:
   - Adding user feedback loops for repository selection
   - Fine-tuning search based on user preferences

## Detailed Flow Implementation

The agent's flow is defined in `/home/vboxuser/Documents/mnt/PocketFlow/flow.py` and follows a complex graph structure with multiple decision points and branching paths:

### Flow Components

1. **Query Analysis & Clarification**
   - Starts with `QueryAnalysisNode` that extracts keywords, tech stack, and features
   - If query lacks sufficient detail, branches to `ClarifyQueryNode` for additional user input
   - Otherwise, proceeds to search phase

2. **Search Phase (Parallel Paths)**
   - `SearchWebNode` for web search
   - `SearchYouTubeNode` for YouTube search
   - `FilterSearchResultsNode` to filter and analyze search results relevance

3. **Repository Extraction & Validation**
   - `ExtractGitHubReposNode` extracts GitHub URLs from all search results
   - If no repositories found, goes to `NoReposFoundNode` which leads to query clarification
   - `CheckRepositoriesNode` evaluates repository quality and complexity

4. **Repository Selection**
   - `DisplayRepositoriesNode` presents repositories to the user
   - `SelectRepositoryNode` handles user selection of a repository for analysis
   - If no quality repos, can show all repositories with `NoQualityReposNode`

5. **Analysis Phase**
   - `AnalyzeRepositoryNode` performs initial repository analysis
   - In case of error, `AnalysisErrorNode` handles graceful error recovery
   - `AnalyzeWithLLMNode` uses LLM to evaluate repository usefulness

6. **Results Generation**
   - `GenerateImplementationGuidesNode` creates implementation guides
   - `FormatForMCPNode` formats analysis for MCP server
   - `CreateMCPServerNode` and `StartMCPServerNode` create and start an MCP server

7. **Completion**
   - `ServerErrorNode` handles MCP server startup errors
   - `ProcessCompleteNode` presents final results to the user

### Flow Diagram

```mermaid
flowchart TD
    query_analysis[Query Analysis] -->|clarify| clarify_query[Clarify Query]
    query_analysis -->|search| search_web[Search Web]
    
    search_web -->|YouTube search| search_youtube[Search YouTube]
    search_web -->|filter results| filter_results[Filter Results]
    
    search_youtube --> extract_repos[Extract GitHub Repos]
    filter_results --> extract_repos
    
    extract_repos -->|no repos| no_repos_found[No Repos Found]
    extract_repos -->|check repos| check_repos[Check Repositories]
    
    no_repos_found --> clarify_query
    
    check_repos -->|no quality repos| no_quality_repos[No Quality Repos]
    check_repos -->|display repos| display_repos[Display Repositories]
    
    no_quality_repos -->|display all repos| display_repos
    
    display_repos --> select_repo[Select Repository]
    
    select_repo --> analyze_repo[Analyze Repository]
    
    analyze_repo -->|error| analysis_error[Analysis Error]
    analyze_repo -->|analyze with LLM| analyze_with_llm[Analyze With LLM]
    
    analysis_error --> display_repos
    
    analyze_with_llm --> generate_guides[Generate Implementation Guides]
    generate_guides --> format_for_mcp[Format for MCP]
    format_for_mcp --> create_mcp[Create MCP Server]
    create_mcp --> start_mcp[Start MCP Server]
    
    start_mcp -->|error| server_error[Server Error]
    start_mcp -->|complete| process_complete[Process Complete]
    
    server_error --> process_complete
```

### Flow Execution Pattern

The flow follows a dynamic, adaptable execution pattern:
- Each node returns an "action" string from its `post()` method
- The action determines which node gets executed next
- Default transitions are provided for nodes that don't return specific actions
- External events (like user selection) can influence the flow's path 