# utils/__init__.py
"""
Utility functions for Repository Analysis to MCP Server system.
This package provides utilities for LLM integration, search, GitHub API,
data processing, MCP server integration, and monitoring.
"""

from .llm import call_llm, stream_llm, extract_keywords_and_techstack, analyze_repository_with_llm
from .search import search_web, search_youtube, check_content_relevance
from .github import extract_github_urls, check_repository_complexity_and_size, analyze_repository
from .data_processing import format_for_mcp, generate_implementation_guides_from_analysis, format_repository_list, get_user_selection
from .mcp import create_mcp_server, start_mcp_server
from .monitoring import log_execution_time, configure_logging, increment_counter

__all__ = [
    # LLM integration
    'call_llm', 'stream_llm', 'extract_keywords_and_techstack', 'analyze_repository_with_llm',
    
    # Search utilities
    'search_web', 'search_youtube', 'check_content_relevance',
    
    # GitHub utilities
    'extract_github_urls', 'check_repository_complexity_and_size', 'analyze_repository',
    
    # Data processing
    'format_for_mcp', 'generate_implementation_guides_from_analysis', 
    'format_repository_list', 'get_user_selection',
    
    # MCP integration
    'create_mcp_server', 'start_mcp_server',
    
    # Monitoring
    'log_execution_time', 'configure_logging', 'increment_counter'
]

# Repository Analysis to MCP Server: Utility Functions

This document defines all utility functions required for the Repository Analysis to MCP Server system. The functions are organized by category following PocketFlow utility function patterns.

## 1. LLM Integration Utilities

### 1.1 `call_llm(prompt, model=None, provider=None, temperature=0.1, max_tokens=1500)`

**Purpose**: Core function for making LLM API calls.

**Input**:
- `prompt` (str): Text prompt for the LLM
- `model` (str, optional): Model name (e.g., "gpt-4o", "claude-2")
- `provider` (str, optional): Provider name (e.g., "openai", "anthropic")
- `temperature` (float): Controls randomness (0.0-1.0)
- `max_tokens` (int): Maximum response length

**Output**:
- Response text from the LLM

**Implementation Notes**:
- Uses OpenAI API by default with fallback to other providers
- Includes caching for efficiency and cost savings
- Implements retry logic for rate limit handling
- Handles API errors gracefully with meaningful messages

**Example**:
```python
from utils.llm import call_llm

analysis = call_llm(
    prompt="Analyze this repository structure and identify key features.",
    model="gpt-4o",
    temperature=0.2
)
```

### 1.2 `stream_llm(prompt, callback=None, model=None, provider=None)`

**Purpose**: Streaming version of LLM function for incremental responses.

**Input**:
- `prompt` (str): Text prompt for the LLM
- `callback` (function, optional): Function to call with each token
- `model` and `provider`: Same as `call_llm`

**Output**:
- Streams response tokens to callback function
- Returns final complete response

**Implementation Notes**:
- Uses streaming API endpoint
- Passes each token to callback as it arrives
- Accumulates full response for final return

### 1.3 `extract_keywords_and_techstack(query)`

**Purpose**: Extracts relevant keywords, tech stack, and context from user queries.

**Input**:
- `query` (str): User's natural language query

**Output**:
- Dictionary containing:
  - `original_query` (str): Original query text
  - `keywords` (list): List of extracted keywords
  - `tech_stack` (list): Technologies mentioned or implied
  - `context` (str): Interpreted context of the query
  - `features` (list): Desired features the user is looking for

**Implementation Notes**:
- Uses LLM to identify important terms, technologies, and desired features
- Formats output in consistent structure for relevance matching
- Distinguishes between general keywords and specific tech stack components
- Identifies specific features the user is trying to implement

**Example Prompt**:
```
Please analyze this query and extract the following information:

Query: "How to implement authentication with JWT in a Node.js Express app with React frontend"

Please extract:
1. Keywords - the main general concepts in the query
2. Tech Stack - specific technologies mentioned or implied
3. Features - specific functionality the user is looking for
4. Context - the overall goal/purpose of the query

Output in YAML format:
```

### 1.4 `analyze_repository_with_llm(repo_data, keywords, tech_stack, features)`

**Purpose**: Performs in-depth analysis of repository contents using an LLM.

**Input**:
- `repo_data` (dict): Repository data (files, structure, etc.)
- `keywords` (list): Keywords from user query
- `tech_stack` (list): Technologies from user query
- `features` (list): Features the user is looking for

**Output**:
- Detailed analysis dictionary with feature mapping, patterns, etc.

**Implementation Notes**:
- Uses structured prompting to analyze code
- Identifies key features, patterns, and utilities
- Assesses code quality, documentation, and complexity
- Maps repository to standard patterns (e.g., PocketFlow patterns)
- Evaluates compatibility with user's tech stack requirements

## 2. Search Utilities

### 2.1 `search_web(query, max_results=10)`

**Purpose**: Searches the web for relevant content.

**Input**:
- `query` (str): Search query
- `max_results` (int): Maximum number of results to return

**Output**:
- List of result dictionaries with:
  - `title` (str): Article/page title
  - `url` (str): Source URL
  - `snippet` (str): Text snippet/description
  - `source` (str): Source domain

**Implementation Notes**:
- Uses Search-Engines-Scraper for multi-engine search results
- Formats results consistently with the same interface as before
- Includes error handling and rate limit management
- Implements caching to reduce duplicate searches

**Example Implementation**:
```python
def search_web(query, max_results=10):
    try:
        from search_engines_scraper import SearchEngines
    except ImportError:
        print("Search-Engines-Scraper not installed - using fallback")
        # Fallback implementation
        return [{"title": "Dummy result (fallback)", "url": "https://example.com", "snippet": "Search engines scraper not available", "source": "fallback"}]
    
    try:
        # Initialize the search engine scraper (supports Google, Bing, Yahoo, DuckDuckGo)
        engines = ["google", "bing"]  # Can use multiple engines
        search = SearchEngines(engines)
        
        # Execute search
        results = search.search(query, pages=1)  # Get first page of results
        
        # Process and format results
        processed_results = []
        for engine, engine_results in results.items():
            for result in engine_results[:max_results]:
                processed_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("description", ""),
                    "source": extract_domain(result.get("url", ""))
                })
                
                # Stop when we reach the max results
                if len(processed_results) >= max_results:
                    break
            
            # If we have enough results, break out of the outer loop
            if len(processed_results) >= max_results:
                break
                
        return processed_results[:max_results]
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []
```

### 2.2 `search_youtube(query, max_results=5)`

**Purpose**: Searches YouTube for relevant videos.

**Input**:
- `query` (str): Search query
- `max_results` (int): Maximum number of videos to return

**Output**:
- List of result dictionaries with:
  - `title` (str): Video title
  - `url` (str): Video URL
  - `channel` (str): Channel name
  - `description` (str): Video description
  - `thumbnail` (str): Thumbnail URL
  - `published_at` (str): Publication date

**Implementation Notes**:
- Uses yt-dlp library for YouTube video search and metadata extraction
- Maintains the same output format as the previous SerpAPI implementation
- Includes comprehensive metadata including description, channel, and publication date
- Supports video filtering by relevance/date/view count
- More reliable access to YouTube content without API quotas

**Example Implementation**:
```python
def search_youtube(query, max_results=5):
    """
    Searches YouTube for relevant videos using yt-dlp.
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of videos to return
        
    Returns:
        list: List of result dictionaries with video info
    """
    try:
        import yt_dlp
    except ImportError:
        print("yt-dlp not installed - using fallback")
        # Fallback implementation
        return [{"title": "Dummy video (fallback)", "url": "https://youtube.com", "channel": "None", "description": "yt-dlp not available", "thumbnail": "", "published_at": ""}]
    
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True,
            'format': 'best',
            'skip_download': True,
            'no_warnings': True,
            'playlist_items': f'1-{max_results}',  # Limit number of results
        }
        
        # Create search URL
        search_url = f"ytsearch{max_results}:{query}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Fetch search results
            info = ydl.extract_info(search_url, download=False)
            
            if 'entries' not in info:
                return []
                
            processed_results = []
            for video in info['entries']:
                # Get additional metadata for each video
                video_url = f"https://www.youtube.com/watch?v={video.get('id', '')}"
                
                processed_results.append({
                    "title": video.get("title", ""),
                    "url": video_url,
                    "channel": video.get("channel", ""),
                    "description": video.get("description", ""),
                    "thumbnail": video.get("thumbnail", ""),
                    "published_at": video.get("upload_date", "")
                })
                
            return processed_results
            
    except Exception as e:
        print(f"YouTube search error: {str(e)}")
        return []

### 2.3 `check_content_relevance(content, keywords, tech_stack, features, threshold=0.7)`

**Purpose**: Evaluates the relevance of search results specifically for the user's tech stack, features, and context.

**Input**:
- `content` (dict): Search result with title, url, snippet
- `keywords` (list): Keywords from user query
- `tech_stack` (list): Technologies from user query  
- `features` (list): Features the user is looking for
- `threshold` (float): Minimum relevance score (0.0-1.0)

**Output**:
- Dictionary with original content plus:
  - `relevance_score` (float): 0.0-1.0 relevance score
  - `tech_stack_match` (list): Technologies matched in the content
  - `feature_match` (list): Features matched in the content
  - `reasoning` (str): Explanation for relevance judgment
  - `is_relevant` (bool): True if score >= threshold

**Implementation Notes**:
- Uses LLM to evaluate relevance specifically to tech stack and features
- Provides detailed reasoning for each judgment
- Identifies specific matches between content and user requirements
- Returns higher scores for content that mentions specific features with the user's tech stack

**Example Prompt**:
```
Evaluate how relevant this content is to the user's requirements:

CONTENT:
Title: "{content['title']}"
Snippet: "{content['snippet']}"

USER REQUIREMENTS:
Keywords: {keywords}
Tech Stack: {tech_stack}
Features: {features}

Evaluate specifically:
1. Does the content cover the specific features the user is looking for?
2. Does it mention or relate to the user's tech stack?
3. How directly relevant is it to implementing these features with this tech stack?

Output in YAML format:
```

## 3. GitHub Utilities

### 3.1 `extract_github_urls(content)`

**Purpose**: Extracts GitHub repository URLs from text.

**Input**:
- `content` (str or dict): Text content or structured content item

**Output**:
- List of GitHub repository URLs

**Implementation Notes**:
- Uses regex pattern matching for GitHub URLs
- Handles various GitHub URL formats
- Cleans and normalizes URLs (remove fragments, etc.)
- Deduplicates results

### 3.2 `check_repository_complexity_and_size(repo_url, min_stars=10)`

**Purpose**: Evaluates repository quality, complexity metrics, and code size.

**Input**:
- `repo_url` (str): GitHub repository URL
- `min_stars` (int): Minimum stars threshold

**Output**:
- Repository quality and size metrics dictionary:
  - `stars` (int): Star count
  - `forks` (int): Fork count
  - `issues` (int): Open issues count
  - `last_update` (str): Last update date
  - `size` (int): Size in KB
  - `file_count` (int): Number of files
  - `loc` (int): Estimated lines of code
  - `complexity_score` (float): Overall complexity score
  - `implementation_difficulty` (str): Easy/Medium/Hard assessment
  - `meets_criteria` (bool): Whether repo meets quality criteria

**Implementation Notes**:
- Uses GitHub API for repository metadata
- Calculates composite quality score that includes size metrics
- Evaluates implementation difficulty based on code size and structure
- Checks for minimal documentation (README, etc.)
- Evaluates recent activity
- Does NOT use Perplexity, relies only on GitHub API and LLM

### 3.3 `analyze_repository(repo_url)`

**Purpose**: Extracts comprehensive data from a GitHub repository.

**Input**:
- `repo_url` (str): GitHub repository URL

**Output**:
- Comprehensive repository data dictionary:
  - `basic_info`: Repository metadata
  - `file_structure`: Directory and file listings
  - `readme_content`: Parsed README content
  - `main_files`: Content of key files
  - `languages`: Language breakdown
  - `size_metrics`: Detailed size information

**Implementation Notes**:
- Uses GitHub API with pagination for large repos
- Clones repository locally if needed for deeper analysis
- Reads and parses key files (README, setup.py, etc.)
- Extracts documentation if available
- Gathers detailed size metrics for implementation difficulty assessment

## 4. Data Processing Utilities

### 4.1 `format_for_mcp(data)`

**Purpose**: Formats repository analysis data for MCP server.

**Input**:
- `data` (dict): Repository analysis data

**Output**:
- MCP-formatted data package:
  - Server configuration
  - Tool definitions
  - Implementation guides (basic)

**Implementation Notes**:
- Transforms data structure to MCP format
- Creates valid schemas for tools
- Generates basic documentation
- Follows FastMCP patterns seen in cookbook/pocketflow-mcp

**Example Implementation**:
```python
def format_for_mcp(data):
    """Format repository analysis data for MCP server.
    
    Based on the MCP format shown in cookbook/pocketflow-mcp
    """
    repo_name = data.get("basic_info", {}).get("name", "repository")
    repo_url = data.get("basic_info", {}).get("url", "")
    
    # Create basic MCP package
    mcp_package = {
        "name": f"{repo_name}-mcp",
        "version": "1.0.0",
        "description": f"MCP server for {repo_name} repository",
        "repository": repo_url,
        "server_info": {
            "host": "localhost",
            "port": 8000
        },
        "tools": [],
        "implementation_guides": {},
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "source_repo": repo_url
        }
    }
    
    # Add tools based on features
    features = data.get("detailed_analysis", {}).get("feature_map", {})
    for feature_name, feature_details in features.items():
        tool = {
            "name": f"get_{feature_name.lower().replace(' ', '_')}",
            "description": f"Get information about {feature_name}",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "detail_level": {
                        "type": "string",
                        "enum": ["basic", "detailed"],
                        "description": "Level of detail to return"
                    }
                }
            }
        }
        mcp_package["tools"].append(tool)
    
    return mcp_package
```

### 4.2 `generate_implementation_guides_from_analysis(analysis, tech_stack)`

**Purpose**: Creates detailed implementation guides from repository analysis tailored to user's tech stack.

**Input**:
- `analysis` (dict): Repository analysis data
- `tech_stack` (list): User's technology stack

**Output**:
- Dictionary of implementation guides by feature

**Implementation Notes**:
- Uses analysis to identify key features
- Creates structured guides for each feature
- Includes code examples and implementation steps
- Formats guides for AI agent consumption
- Tailors guides to be compatible with the user's tech stack

### 4.3 `format_repository_list(repositories)`

**Purpose**: Formats repository list for user display.

**Input**:
- `repositories` (list): List of repository dictionaries

**Output**:
- Formatted string for display

**Implementation Notes**:
- Creates numbered list with key details
- Highlights important metrics (stars, etc.)
- Includes size and complexity assessments
- Shows tech stack compatibility scores

### 4.4 `get_user_selection(prompt, options)`

**Purpose**: Handles user selection from a list of options.

**Input**:
- `prompt` (str): Prompt to display to user
- `options` (list): List of options

**Output**:
- Selected option (or None if canceled)

**Implementation Notes**:
- Displays prompt and numbered options
- Validates user input
- Handles invalid selections and retries

## 5. MCP Integration Utilities

### 5.1 `create_mcp_server(name, tools, implementation_guides)`

**Purpose**: Creates and configures an MCP server with dynamically generated tools.

**Input**:
- `name` (str): Server name
- `tools` (list): Tool definitions
- `implementation_guides` (dict): Implementation guides by feature

**Output**:
- Configured FastMCP server instance

**Implementation Notes**:
- Uses FastMCP from the cookbook example
- Dynamically registers tools based on repository features
- Creates tool functions that return implementation guide content
- Includes standard utility tools

**Example Implementation**:
```python
from fastmcp import FastMCP

def create_mcp_server(name, tools, implementation_guides):
    """Create an MCP server with dynamic tools based on repository analysis.
    """
    # Create a named server
    mcp = FastMCP(name)
    
    # Register dynamic tools
    for tool in tools:
        tool_name = tool["name"]
        
        # Create a closure to capture the feature_name
        def create_tool_handler(feature):
            def get_feature_info(detail_level="basic"):
                if feature in implementation_guides:
                    if detail_level == "basic":
                        return {
                            "overview": implementation_guides[feature]["overview"],
                            "core_concepts": implementation_guides[feature]["core_concepts"]
                        }
                    else:
                        return implementation_guides[feature]
                else:
                    return {"error": f"No guide found for {feature}"}
            return get_feature_info
        
        # Register the tool with the dynamically created handler
        tool_handler = create_tool_handler(feature_name)
        mcp.tool(name=tool_name)(tool_handler)
    
    # Register generic tools
    
    @mcp.tool()
    def list_features():
        """List all available features from the repository"""
        return list(implementation_guides.keys())
    
    @mcp.tool()
    def get_repository_overview():
        """Get overview information about the repository"""
        return {
            "name": name,
            "features": list(implementation_guides.keys()),
            "implementation_difficulty": calculate_overall_difficulty(implementation_guides)
        }
    
    return mcp
```

### 5.2 `start_mcp_server(mcp, host="localhost", port=8000)`

**Purpose**: Starts the MCP server and exposes it via API.

**Input**:
- `mcp` (FastMCP): Configured MCP server instance
- `host` (str): Host to bind to
- `port` (int): Port to listen on

**Output**:
- Running server process

**Implementation Notes**:
- Configures server with appropriate host/port
- Handles graceful shutdown
- Returns server process information

## 6. Monitoring Utilities

### 6.1 `log_execution_time(operation_name=None)`

**Purpose**: Decorator for timing node execution.

**Input**:
- `operation_name` (str, optional): Name of operation

**Output**:
- Decorated function that logs execution time

**Implementation Notes**:
- Records start and end times
- Logs duration to monitoring system
- Adds execution metadata to results

### 6.2 `configure_logging(level, format_string=None)`

**Purpose**: Configures structured logging for the system.

**Input**:
- `level` (str or int): Logging level
- `format_string` (str, optional): Custom log format

**Output**:
- Configured logger

**Implementation Notes**:
- Sets up consistent logging format
- Configures log outputs (file, console)
- Supports different log levels by component

### 6.3 `increment_counter(name, value=1, tags=None)`

**Purpose**: Tracks metric counters for monitoring.

**Input**:
- `name` (str): Counter name
- `value` (int): Value to increment by
- `tags` (dict, optional): Metadata tags

**Output**:
- None

**Implementation Notes**:
- Increments named counter
- Adds metadata tags for filtering
- Integrates with monitoring system

## Implementation Example

Each utility should be implemented in a dedicated file with unit tests:

```
utils/
├── __init__.py
├── llm.py             # LLM integration utilities
├── search.py          # Web and YouTube search
├── github.py          # GitHub API utilities
├── data_processing.py # Data formatting utilities
├── mcp.py             # MCP server utilities
├── monitoring.py      # Logging and monitoring
└── tests/             # Unit tests for utilities
```

Example implementation for `search_web` and `search_youtube` using the new tools:

```python
# utils/search.py
import os
import json
from typing import Dict, List, Optional, Any
from functools import lru_cache
from urllib.parse import urlparse

from .llm import call_llm
from .monitoring import log_execution_time

@lru_cache(maxsize=100)
@log_execution_time("web_search")
def search_web(query, max_results=10) -> List[Dict[str, str]]:
    """
    Searches the web for relevant content using Search-Engines-Scraper.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        
    Returns:
        List of result dictionaries with title, url, snippet, source
    """
    try:
        from search_engines_scraper import SearchEngines
    except ImportError:
        print("Search-Engines-Scraper not installed - using fallback")
        # Simple fallback with minimal results
        return [{"title": "Dummy result (fallback)", "url": "https://example.com", "snippet": "Search engines scraper not available", "source": "fallback"}]
    
    try:
        # Initialize the search engine scraper with multiple engines for better results
        engines = ["google", "bing"]  # Can use multiple engines for more comprehensive results
        search = SearchEngines(engines)
        
        # Execute search
        results = search.search(query, pages=1)  # Get first page of results
        
        # Process and format results
        processed_results = []
        for engine, engine_results in results.items():
            for result in engine_results[:max_results]:
                processed_results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("description", ""),
                    "source": extract_domain(result.get("url", ""))
                })
                
                # Stop when we reach the max results
                if len(processed_results) >= max_results:
                    break
            
            # If we have enough results, break out of the outer loop
            if len(processed_results) >= max_results:
                break
                
        return processed_results[:max_results]
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return []

def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc
    except:
        return ""

@lru_cache(maxsize=50)
@log_execution_time("youtube_search")
def search_youtube(query, max_results=5) -> List[Dict[str, str]]:
    """
    Searches YouTube for relevant videos using yt-dlp.
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of videos to return
        
    Returns:
        list: List of result dictionaries with video info
    """
    try:
        import yt_dlp
    except ImportError:
        print("yt-dlp not installed - using fallback")
        # Simple fallback implementation
        return [{"title": "Dummy video (fallback)", "url": "https://youtube.com", "channel": "None", "description": "yt-dlp not available", "thumbnail": "", "published_at": ""}]
    
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True,
            'format': 'best',
            'skip_download': True,
            'no_warnings': True,
            'playlist_items': f'1-{max_results}',  # Limit number of results
        }
        
        # Create search URL (ytsearch is a special yt-dlp format)
        search_url = f"ytsearch{max_results}:{query}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Fetch search results
            info = ydl.extract_info(search_url, download=False)
            
            if 'entries' not in info:
                return []
                
            processed_results = []
            for video in info['entries']:
                # Get additional metadata for each video
                video_url = f"https://www.youtube.com/watch?v={video.get('id', '')}"
                
                processed_results.append({
                    "title": video.get("title", ""),
                    "url": video_url,
                    "channel": video.get("channel", ""),
                    "description": video.get("description", ""),
                    "thumbnail": video.get("thumbnail", ""),
                    "published_at": video.get("upload_date", "")
                })
                
            return processed_results
            
    except Exception as e:
        print(f"YouTube search error: {str(e)}")
        return []

@log_execution_time("content_relevance_check")
def check_content_relevance(content, keywords, tech_stack, features, threshold=0.7):
    """Check the relevance of content against user requirements."""
    # Existing implementation... 

def scrape_webpage(url: str, max_retries: int = 2) -> Dict[str, Any]:
    """
    Scrapes a webpage to extract content and GitHub URLs.
    Focuses specifically on finding GitHub repository references.
    Includes retry mechanism with fixed 5-second delay between retries for handling 403 errors.
    
    Args:
        url: Webpage URL
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary with:
        - title: Page title
        - content: Main text content (limited to 5000 chars)
        - links: List of link dictionaries with url and text
        - github_urls: List of detected GitHub repository URLs
        - code_blocks: Code blocks that might contain GitHub references
        - scrape_failed: Boolean flag indicating if scraping failed after all retries
    """
    pass 

def search_and_scrape(query: str, 
                     keywords: List[str] = None, 
                     tech_stack: List[str] = None,
                     features: List[str] = None,
                     youtube_count: int = 5, 
                     web_count: int = 5,
                     use_youtube: bool = True,
                     use_web: bool = True,
                     use_llm: bool = True) -> Dict[str, Any]:
    """
    Performs search and scrape process to find GitHub repositories.
    Combines YouTube and web search, with scraping to extract GitHub URLs.
    Includes error handling with retry mechanism and failure reporting.
    
    Args:
        query: Search query
        keywords: Keywords for relevance filtering
        tech_stack: Technologies for relevance filtering
        features: Features for relevance filtering
        youtube_count: Number of YouTube videos to search
        web_count: Number of web pages to search
        use_youtube: Whether to include YouTube search
        use_web: Whether to include web search
        use_llm: Whether to use LLM enhancements
        
    Returns:
        Dictionary with:
        - query: Original search query
        - refined_query: LLM-enhanced query (if use_llm=True)
        - keywords, tech_stack, features: Filtering criteria
        - youtube_results: List of relevant YouTube videos with GitHub URLs
        - web_results: List of relevant web pages with GitHub URLs
        - github_urls: Combined list of all unique GitHub repository URLs
        - repos_with_quality: Repository quality assessments (if use_llm=True)
        - total_github_urls: Count of unique GitHub URLs found
        - llm_enhanced: Whether LLM enhancements were used
        - average_relevance: Average relevance score of processed content
        - scrape_success_rate: Percentage of successful scrape attempts
    """
    pass 