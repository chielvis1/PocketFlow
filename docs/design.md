# Repository Analysis to MCP Server: Design Document

## 1. Requirements

### Problem Statement
Users often spend significant time searching for reference GitHub repositories when implementing features. After finding repositories, they must analyze them manually to understand how to apply them to their own projects, especially if they use a different tech stack than the repository.

### User-Centric Goals
- Find high-quality GitHub repositories that implement specific features
- Get detailed implementation guides tailored to the user's tech stack
- Access these guides through a structured API (MCP server)

### Success Criteria
- Successful identification of relevant repositories with 80%+ relevant rate
- Generation of detailed, actionable implementation guides
- Creation of a functional MCP server that exposes the guides via API

## 2. Flow Design

The system uses an **Agent** design pattern with multiple decision points, combined with **Workflow** pattern for the sequential processing steps.

### Key Flows

```mermaid
flowchart TD
    start([Start]) --> query[Query Analysis]
    query -->|insufficient info| clarify[Clarify Query]
    clarify --> query
    
    query -->|sufficient info| search[Search Web]
    search -->|no results| youtube[Search YouTube]
    search -->|results| filter[Filter Results]
    
    youtube --> extract[Extract Repos]
    filter --> extract
    
    extract -->|no repos| noRepos[No Repos Found]
    extract -->|repos found| checkRepos[Check Repos]
    
    noRepos --> clarify
    
    checkRepos -->|low quality| noQuality[No Quality Repos]
    checkRepos -->|quality repos| display[Display Repos]
    
    noQuality --> display
    
    display --> select[Select Repo]
    select --> analyze[Analyze Repo]
    
    analyze -->|error| analyzeError[Analysis Error]
    analyze -->|success| analyzeLLM[Analyze With LLM]
    
    analyzeError --> display
    
    analyzeLLM --> guides[Generate Guides]
    guides --> formatMCP[Format for MCP]
    formatMCP --> createMCP[Create MCP Server]
    createMCP --> startMCP[Start MCP Server]
    
    startMCP -->|error| serverError[Server Error]
    startMCP -->|success| complete[Process Complete]
    
    serverError --> complete
    
    complete --> end([End])
```

## 3. Utilities

The system relies on several external utility functions:

| Category | Utility | Input | Output | Necessity |
|----------|---------|-------|--------|-----------|
| LLM | `call_llm` | `prompt`, `model`, `provider` | Response text | Core LLM interaction |
| LLM | `extract_keywords_and_techstack` | `query` | Keywords, tech stack, features | Initial query understanding |
| Search | `search_web` | `query` | Search results | Find repositories |
| Search | `search_youtube` | `query` | Video results | Additional repository sources |
| GitHub | `extract_github_urls` | `content` | GitHub URLs | Extract repository links |
| GitHub | `analyze_repository` | `repo_url` | Repository data | Detailed repository analysis |
| Data Processing | `format_for_mcp` | `data` | MCP package | MCP server preparation |
| MCP | `create_mcp_server` | `name`, `tools`, `guides` | MCP server | Implementation guide access |

## 4. Node Design

### Shared Store Design
```python
shared = {
    # User query and analysis
    "user_query": "authentication with JWT in Node.js",
    "query_analysis": {
        "keywords": ["authentication", "security"],
        "tech_stack": ["Node.js", "Express", "JWT"],
        "features": ["authentication", "user management"],
        "context": "Implementing authentication system"
    },
    
    # Search results
    "web_search_results": [...],  # List of search results
    "youtube_results": [...],     # List of YouTube results
    "relevant_results": [...],    # Filtered results
    
    # Repository data
    "repository_urls": ["https://github.com/user/repo", ...],
    "repository_quality_data": [...],  # Repository quality metrics
    "quality_repositories": [...],     # Filtered quality repositories
    "selected_repository": {...},      # User-selected repository
    
    # Analysis results
    "repository_analysis": {
        "basic_info": {...},
        "file_structure": {...},
        "detailed_analysis": {...}
    },
    
    # Guides and MCP data
    "implementation_guides": {...},
    "mcp_package": {...},
    "mcp_server": <server_instance>,
    "server_info": {...}
}
```

### Key Nodes

#### 1. Query Analysis Node
- **Type**: Regular
- **Prep**: Read `user_query` from shared
- **Exec**: Call LLM to extract keywords, tech stack, features
- **Post**: Write results to shared, determine if clarification needed

#### 2. Search Nodes
- **Type**: Regular
- **Prep**: Read keywords, tech stack, features from shared
- **Exec**: Call web/YouTube search
- **Post**: Write results to shared

#### 3. Repository Analysis Node
- **Type**: Regular
- **Prep**: Read selected repository URL
- **Exec**: Call GitHub API
- **Post**: Write repository data to shared

#### 4. Generate Implementation Guides Node
- **Type**: Regular
- **Prep**: Read repository analysis and tech stack
- **Exec**: Call LLM to generate guides
- **Post**: Write guides to shared

#### 5. MCP Server Nodes
- **Type**: Regular
- **Prep**: Read repository analysis and guides
- **Exec**: Create and start MCP server
- **Post**: Write server info to shared

## 5. Implementation

Implementation follows the PocketFlow design patterns:
- Nodes are implemented in `nodes.py`
- Flow connections are defined in `flow.py`
- Utility functions are in `utils/` directory
- Entry point is `main.py`

## 6. Optimization

- **Performance**: Batch nodes for repository checking and result filtering
- **Prompt Engineering**: Carefully crafted prompts for LLM analysis
- **Error Handling**: Comprehensive error states and recovery paths

## 7. Reliability

- Retry logic for API calls
- Graceful degradation when APIs fail
- Fallback providers for LLM services
- Logging and monitoring of all key operations 