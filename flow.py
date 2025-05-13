"""
Flow definitions for Repository Analysis to MCP Server agent.

This file connects the nodes defined in nodes.py to create the complete agent flow.
The flow follows an agent pattern with multiple decision points and branching paths.
"""

from pocketflow import Flow
from nodes import (
    # Nodes for query analysis and clarification
    QueryAnalysisNode, ClarifyQueryNode,
    
    # Nodes for search
    SearchWebNode, SearchYouTubeNode, FilterSearchResultsNode,
    
    # Nodes for repository extraction and analysis
    ExtractGitHubReposNode, CheckRepositoriesNode,
    
    # Nodes for error handling
    NoReposFoundNode, NoQualityReposNode,
    
    # Nodes for repository display and selection
    DisplayRepositoriesNode, SelectRepositoryNode,
    
    # Nodes for detailed analysis
    AnalyzeRepositoryNode, AnalysisErrorNode, AnalyzeWithLLMNode,
    
    # Nodes for guide generation and MCP creation
    GenerateImplementationGuidesNode, FormatForMCPNode,
    CreateMCPServerNode, StartMCPServerNode,
    
    # Nodes for completion and error handling
    ServerErrorNode, ProcessCompleteNode
)

def create_repo_analyzer_flow() -> Flow:
    """
    Creates and returns the complete repository analyzer flow.
    
    Returns:
        Flow: The configured repository analyzer flow
    """
    # Create nodes
    query_analysis = QueryAnalysisNode()
    clarify_query = ClarifyQueryNode()
    
    search_web = SearchWebNode()
    search_youtube = SearchYouTubeNode()
    filter_results = FilterSearchResultsNode()
    
    extract_repos = ExtractGitHubReposNode()
    check_repos = CheckRepositoriesNode()
    
    no_repos_found = NoReposFoundNode()
    no_quality_repos = NoQualityReposNode()
    
    display_repos = DisplayRepositoriesNode()
    select_repo = SelectRepositoryNode()
    
    analyze_repo = AnalyzeRepositoryNode()
    analysis_error = AnalysisErrorNode()
    analyze_with_llm = AnalyzeWithLLMNode()
    
    generate_guides = GenerateImplementationGuidesNode()
    format_for_mcp = FormatForMCPNode()
    create_mcp = CreateMCPServerNode()
    start_mcp = StartMCPServerNode()
    
    server_error = ServerErrorNode()
    process_complete = ProcessCompleteNode()
    
    # Define the flow with actions
    
    # Query analysis and clarification
    query_analysis - "clarify" >> clarify_query
    query_analysis - "search" >> search_web
    
    # Search paths
    search_web - "youtube_search" >> search_youtube
    search_web - "filter_results" >> filter_results
    
    # Add default transitions to handle cases where post() doesn't return a specific action
    search_youtube >> extract_repos
    filter_results >> extract_repos
    
    # Repository extraction and validation
    extract_repos - "no_repos_found" >> no_repos_found
    extract_repos - "check_repos" >> check_repos
    extract_repos >> check_repos  # Add default transition for extract_repos
    
    # Handle no repositories found
    no_repos_found - "clarify" >> clarify_query
    
    # Repository quality check
    check_repos - "no_quality_repos" >> no_quality_repos
    check_repos - "display_repos" >> display_repos
    check_repos >> display_repos  # Add default transition
    
    # Handle no quality repositories
    no_quality_repos - "display_all_repos" >> display_repos
    
    # Repository display and selection
    display_repos - "select_repo" >> select_repo
    display_repos >> select_repo  # Add default transition
    
    # Analysis flow
    # Note: selection happens outside the flow; we assume selected_repository is set in shared
    # before analyze_repo runs
    
    analyze_repo - "analysis_error" >> analysis_error
    analyze_repo - "analyze_with_llm" >> analyze_with_llm
    analyze_repo >> analyze_with_llm  # Add default transition
    
    # Handle analysis error
    analysis_error - "display_repos" >> display_repos
    
    # Guide generation and MCP creation
    analyze_with_llm - "generate_guides" >> generate_guides
    analyze_with_llm >> generate_guides  # Add default transition
    generate_guides - "format_for_mcp" >> format_for_mcp
    generate_guides >> format_for_mcp  # Add default transition
    format_for_mcp - "create_mcp" >> create_mcp
    format_for_mcp >> create_mcp  # Add default transition
    create_mcp - "start_mcp" >> start_mcp
    create_mcp >> start_mcp  # Add default transition
    
    # Handle server error and completion
    start_mcp - "server_error" >> server_error
    start_mcp - "complete" >> process_complete
    start_mcp >> process_complete  # Add default transition
    server_error - "complete" >> process_complete
    server_error >> process_complete  # Add default transition
    
    # Create and return the flow
    return Flow(start=query_analysis)

def handle_user_selection(shared, selection):
    """
    Helper function to handle repository selection by the user.
    
    Args:
        shared: The shared data dictionary
        selection: The user's selected repository
    
    Returns:
        str: The next node to execute ('analyze_repo' or 'display_repos')
    """
    if selection:
        # Store the selected repository
        shared["selected_repository"] = selection
        return "analyze_repo"
    else:
        # User canceled selection
        return "display_repos"

if __name__ == "__main__":
    # Just for testing the flow creation
    flow = create_repo_analyzer_flow()
    print("Flow created successfully with", len(flow.start_node.successors), "initial paths") 